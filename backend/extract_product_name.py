#!/usr/bin/env python3
"""
Script to extract product names from CRLs using AI.

This script analyzes the full CRL text and extracts the therapeutic product name(s)
mentioned in the letter. Products may have multiple names including:
- Research name (e.g., BNT162b2)
- Pre-market name (e.g., Comirnaty)
- Market name (brand name)
- Generic name

All identified names are combined into a single string.

Usage:
    python extract_product_name.py [options]

Options:
    --regenerate        Re-extract ALL product names (including existing ones)
    --limit N           Process only N CRLs (default: all without product names)
    --batch-size N      Number of concurrent API calls (default: 10)
    --sequential        Process one at a time (slower, for debugging)

Examples:
    # Extract product names from new CRLs only (incremental)
    python extract_product_name.py

    # Process first 10 CRLs
    python extract_product_name.py --limit 10

    # Re-extract ALL product names (use with caution!)
    python extract_product_name.py --regenerate

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
    """Get CRLs that need therapeutic category classification."""
    logger.info("Fetching CRLs needing product name extraction...")

    if regenerate:
        query = """
            SELECT id, text FROM crls
            WHERE text IS NOT NULL AND text != ''
            ORDER BY letter_date DESC
        """
    else:
        query = """
            SELECT id, text FROM crls
            WHERE (product_name IS NULL OR product_name = '')
            AND text IS NOT NULL AND text != ''
            ORDER BY letter_date DESC
        """

    if limit:
        query += f" LIMIT {limit}"

    results = conn.execute(query).fetchall()
    crls = [{"id": row[0], "text": row[1]} for row in results]

    logger.info(f"Found {len(crls)} CRLs needing product name extraction")
    return crls


def extract_product_name(text: str, client: OpenAIClient) -> str:
    """Extract product name(s) from CRL text using OpenAI.

    Args:
        text: Full CRL text (will be truncated to first 8000 chars if needed)
        client: OpenAI client instance

    Returns:
        Product name(s) as a single string (may include multiple names separated by slashes)
    """
    # Use up to 8000 characters from the beginning of the text
    # This captures the most relevant information while staying within token limits
    text_excerpt = text[:8000] if len(text) > 8000 else text

    prompt = f"""Analyze this FDA Complete Response Letter and extract the therapeutic product name(s) mentioned.

The product may be referred to by multiple names:
- Research/development name (e.g., BNT162b2, REGN-COV2)
- Pre-market/proprietary name (e.g., Comirnaty, REGEN-COV)
- Generic/INN name (e.g., tozinameran)
- Brand/trade name

Instructions:
1. Identify ALL names by which the product is referred to in the letter
2. Combine them into a single string
3. Separate multiple names with " / " (space-slash-space)
4. If the product has both a brand name and generic name, include both
5. If only one name is found, return just that name
6. If NO product name can be identified, return "Unknown"

CRL Text (beginning):
{text_excerpt}

Respond with ONLY the product name(s), nothing else. Examples:
- "Comirnaty / BNT162b2 / tozinameran"
- "Keytruda / pembrolizumab"
- "REGN-COV2"
- "Unknown"
"""

    try:
        product_name = client.create_chat_completion(
            model=settings.openai_summary_model,
            messages=[
                {"role": "system", "content": "You are an FDA regulatory expert who extracts product information from Complete Response Letters. You are precise and only extract what is explicitly mentioned."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,  # Allow more tokens for potentially long product names
            temperature=0.1  # Low temperature for precise extraction
        ).strip()

        # Clean up the response
        # Remove common prefixes/artifacts
        product_name = product_name.replace("Product name: ", "")
        product_name = product_name.replace("Product: ", "")
        product_name = product_name.strip()

        # If empty or just punctuation, return Unknown
        if not product_name or product_name in [".", ",", "N/A", "n/a", "None", "none"]:
            return "Unknown"

        return product_name

    except Exception as e:
        logger.error(f"Product name extraction error: {e}")
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
            # Classify (synchronous call wrapped in executor)
            loop = asyncio.get_event_loop()
            classification = await loop.run_in_executor(
                None,
                extract_product_name,
                crl_text,
                client
            )

            # Update database
            conn.execute(
                "UPDATE crls SET product_name = ? WHERE id = ?",
                [classification, crl_id]
            )

            return {"status": "success", "crl_id": crl_id, "product_name": product_name}

        except Exception as e:
            return {"status": "failed", "crl_id": crl_id, "error": str(e)[:100]}


async def extract_names_async(
    crls: List[Dict],
    client: OpenAIClient,
    conn,
    batch_size: int = 10
) -> Dict[str, int]:
    """Classify CRLs concurrently."""
    stats = {"total": len(crls), "success": 0, "failed": 0, "skipped": 0}

    logger.info(f"Starting concurrent therapeutic category classification of {len(crls)} CRLs...")
    logger.info(f"Concurrent API calls: {batch_size}")

    semaphore = asyncio.Semaphore(batch_size)

    if HAS_TQDM:
        pbar = tqdm(total=len(crls), desc="Extracting product names", unit="CRL")

    tasks = [
        process_single_crl(crl, client, conn, semaphore)
        for crl in crls
    ]

    for coro in asyncio.as_completed(tasks):
        result = await coro

        if result["status"] == "success":
            stats["success"] += 1
            if HAS_TQDM:
                tqdm.write(f"✓ {result['crl_id']}: {result['product_name']}")
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
        logger.info("CRL Product Name Extraction Script")
        logger.info("=" * 60)

        if args['regenerate']:
            logger.info("Mode: REGENERATE (will reclassify ALL CRLs)")
        else:
            logger.info("Mode: INCREMENTAL (only unclassified CRLs)")

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
            logger.info("✓ No CRLs need therapeutic category classification. All done!")
            return 0

        # Classify
        logger.info("\nClassifying therapeutic categories...")
        stats = asyncio.run(extract_names_async(
            crls, client, conn, args["batch_size"]
        ))

        # Results
        logger.info("\n" + "=" * 60)
        logger.info("PRODUCT NAME EXTRACTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total CRLs processed:  {stats['total']}")
        logger.info(f"✓ Successful:          {stats['success']}")
        logger.info(f"✗ Failed:              {stats['failed']}")
        logger.info(f"⊘ Skipped:             {stats['skipped']}")

        if stats["failed"] > 0:
            logger.warning(f"\n⚠️  {stats['failed']} CRLs failed")
            return 1

        logger.info("\n✓ All CRLs classified successfully!")
        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\n✗ Classification failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
