#!/usr/bin/env python3
"""
Script to extract indications from CRLs using AI.

This script analyzes the full CRL text and extracts the medical indication(s) or
condition(s) that the therapeutic product targets. Indications represent the
disease, disorder, or medical condition that the product is intended to treat,
prevent, or diagnose.

All identified indications are combined into a single string.

Usage:
    python extract_indications.py [options]

Options:
    --regenerate        Re-extract ALL indications (including existing ones)
    --limit N           Process only N CRLs (default: all without indications)
    --batch-size N      Number of concurrent API calls (default: 10)
    --sequential        Process one at a time (slower, for debugging)

Examples:
    # Extract indications from new CRLs only (incremental)
    python extract_indications.py

    # Process first 10 CRLs
    python extract_indications.py --limit 10

    # Re-extract ALL indications (use with caution!)
    python extract_indications.py --regenerate

    --help, -h    Show this help message and exit
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Check for help first
if "--help" in sys.argv or "-h" in sys.argv:
    print(__doc__)
    sys.exit(0)

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import init_db
from app.utils.openai_client import OpenAIClient
from app.utils.logging_config import get_logger, setup_logging
import duckdb

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Setup logging
setup_logging(log_level="INFO", enable_file_logging=True)
logger = get_logger(__name__)




def parse_args():
    """Parse command line arguments."""
    args = {
        "regenerate": "--regenerate" in sys.argv,
        "sequential": "--sequential" in sys.argv,
        "limit": None,
        "batch_size": 10,
    }

    if "--limit" in sys.argv:
        try:
            limit_idx = sys.argv.index("--limit")
            args["limit"] = int(sys.argv[limit_idx + 1])
        except (IndexError, ValueError):
            logger.error("--limit requires a numeric argument")
            sys.exit(1)

    if "--batch-size" in sys.argv:
        try:
            batch_idx = sys.argv.index("--batch-size")
            args["batch_size"] = int(sys.argv[batch_idx + 1])
        except (IndexError, ValueError):
            logger.error("--batch-size requires a numeric argument")
            sys.exit(1)

    return args


def get_crls_needing_extraction(conn, regenerate: bool = False, limit: int = None) -> List[Dict]:
    """Get CRLs that need indications extraction."""
    logger.info("Fetching CRLs needing indications extraction...")

    if regenerate:
        query = """
            SELECT id, text FROM crls
            WHERE text IS NOT NULL AND text != ''
            ORDER BY letter_date DESC
        """
    else:
        query = """
            SELECT id, text FROM crls
            WHERE (indications IS NULL OR indications = '')
            AND text IS NOT NULL AND text != ''
            ORDER BY letter_date DESC
        """

    if limit:
        query += f" LIMIT {limit}"

    results = conn.execute(query).fetchall()
    crls = [{"id": row[0], "text": row[1]} for row in results]

    logger.info(f"Found {len(crls)} CRLs needing indications extraction")
    return crls


def extract_indications(text: str, client: OpenAIClient) -> str:
    """Extract indication(s) from CRL text using OpenAI.

    Args:
        text: Full CRL text (will be truncated to first 8000 chars if needed)
        client: OpenAI client instance

    Returns:
        Indication(s) as a single string (may include multiple indications separated by semicolons)
    """
    # Use up to 8000 characters from the beginning of the text
    # This captures the most relevant information while staying within token limits
    text_excerpt = text[:8000] if len(text) > 8000 else text

    prompt = f"""Analyze this FDA Complete Response Letter and extract the medical indication(s) mentioned.

The indication is the disease, disorder, or medical condition that the therapeutic product is intended to treat, prevent, or diagnose.

Examples of indications:
- "Type 2 diabetes mellitus"
- "Non-small cell lung cancer"
- "COVID-19 prevention"
- "Rheumatoid arthritis"
- "Chronic lymphocytic leukemia in adults with del(17p)"

Instructions:
1. Identify the primary indication(s) that the product targets
2. Be specific - include details like cancer type, disease stage, patient population if mentioned
3. If multiple distinct indications are mentioned, separate them with "; " (semicolon-space)
4. Use medical terminology as it appears in the letter
5. If only one indication is found, return just that indication
6. If NO indication can be identified, return "Unknown"

CRL Text (beginning):
{text_excerpt}

Respond with ONLY the indication(s), nothing else. Examples:
- "Non-small cell lung cancer"
- "Type 2 diabetes mellitus; Obesity"
- "COVID-19 prevention in individuals 12 years of age and older"
- "Unknown"
"""

    try:
        indications = client.create_chat_completion(
            model=settings.openai_summary_model,
            messages=[
                {"role": "system", "content": "You are an FDA regulatory expert who extracts medical indication information from Complete Response Letters. You are precise and only extract what is explicitly mentioned."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,  # Allow tokens for potentially detailed indications
            temperature=0.1  # Low temperature for precise extraction
        ).strip()

        # Clean up the response
        # Remove common prefixes/artifacts
        indications = indications.replace("Indication: ", "")
        indications = indications.replace("Indications: ", "")
        indications = indications.replace("Medical indication: ", "")
        indications = indications.strip()

        # If empty or just punctuation, return Unknown
        if not indications or indications in [".", ",", "N/A", "n/a", "None", "none"]:
            return "Unknown"

        return indications

    except Exception as e:
        logger.error(f"Indications extraction error: {e}")
        return "Unknown"


async def process_single_crl(
    crl: Dict,
    client: OpenAIClient,
    conn,
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """Process a single CRL asynchronously."""
    crl_id = crl["id"]
    crl_text = crl.get("text", "")

    if not crl_text or len(crl_text.strip()) < 100:
        return {"status": "skipped", "crl_id": crl_id, "reason": "insufficient text"}

    async with semaphore:
        try:
            # Extract indications (synchronous call wrapped in executor)
            loop = asyncio.get_event_loop()
            indications = await loop.run_in_executor(
                None,
                extract_indications,
                crl_text,
                client
            )

            # Update database
            conn.execute(
                "UPDATE crls SET indications = ? WHERE id = ?",
                [indications, crl_id]
            )

            return {"status": "success", "crl_id": crl_id, "indications": indications}

        except Exception as e:
            return {"status": "failed", "crl_id": crl_id, "error": str(e)[:100]}


async def extract_indications_async(
    crls: List[Dict],
    client: OpenAIClient,
    conn,
    batch_size: int = 10
) -> Dict[str, int]:
    """Extract indications from CRLs concurrently."""
    stats = {"total": len(crls), "success": 0, "failed": 0, "skipped": 0}

    logger.info(f"Starting concurrent indications extraction of {len(crls)} CRLs...")
    logger.info(f"Concurrent API calls: {batch_size}")

    semaphore = asyncio.Semaphore(batch_size)

    if HAS_TQDM:
        pbar = tqdm(total=len(crls), desc="Extracting indications", unit="CRL")

    tasks = [
        process_single_crl(crl, client, conn, semaphore)
        for crl in crls
    ]

    for coro in asyncio.as_completed(tasks):
        result = await coro

        if result["status"] == "success":
            stats["success"] += 1
            if HAS_TQDM:
                tqdm.write(f"✓ {result['crl_id']}: {result['indications']}")
        elif result["status"] == "failed":
            stats["failed"] += 1
            if HAS_TQDM:
                tqdm.write(f"✗ {result['crl_id']}: {result.get('error', 'Unknown error')}")
        elif result["status"] == "skipped":
            stats["skipped"] += 1

        if HAS_TQDM:
            pbar.update(1)
            pbar.set_postfix({"✓": stats["success"], "✗": stats["failed"]})

    if HAS_TQDM:
        pbar.close()

    return stats


def main():
    """Main function."""
    try:
        args = parse_args()

        logger.info("=" * 60)
        logger.info("CRL Indications Extraction Script")
        logger.info("=" * 60)

        if args['regenerate']:
            logger.info("Mode: REGENERATE (will re-extract ALL indications)")
        else:
            logger.info("Mode: INCREMENTAL (only new CRLs)")

        logger.info(f"Limit: {args['limit'] or 'No limit'}")
        logger.info(f"Concurrent API calls: {args['batch_size']}")

        # Initialize
        logger.info("\nInitializing database...")
        init_db()
        conn = duckdb.connect(str(settings.database_path))
        logger.info("✓ Database initialized")

        # Get OpenAI client
        if not settings.openai_api_key:
            logger.error("❌ OpenAI API key not configured")
            return 1

        client = OpenAIClient(settings)
        logger.info(f"✓ Using OpenAI model: {settings.openai_summary_model}")

        # Get CRLs
        crls = get_crls_needing_extraction(
            conn,
            regenerate=args["regenerate"],
            limit=args["limit"]
        )

        if not crls:
            logger.info("✓ No CRLs need indications extraction. All done!")
            return 0

        # Extract
        logger.info("\nExtracting indications...")
        stats = asyncio.run(extract_indications_async(
            crls, client, conn, args["batch_size"]
        ))

        # Results
        logger.info("\n" + "=" * 60)
        logger.info("INDICATIONS EXTRACTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total CRLs processed:  {stats['total']}")
        logger.info(f"✓ Successful:          {stats['success']}")
        logger.info(f"✗ Failed:              {stats['failed']}")
        logger.info(f"⊘ Skipped:             {stats['skipped']}")

        if stats["failed"] > 0:
            logger.warning(f"\n⚠️  {stats['failed']} CRLs failed")
            return 1

        logger.info("\n✓ All indications extracted successfully!")
        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\n✗ Extraction failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
