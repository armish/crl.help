#!/usr/bin/env python3
"""
Script to enrich CRLs with therapeutic category classification using AI.

This script analyzes CRL text and classifies therapeutic category into one of:
- Small molecules
- Biologics - proteins
- Vaccines
- Blood products
- Cellular therapies
- Gene therapies
- Tissue products
- Combination products
- Devices/IVDs
- Other

Usage:
    python enrich_crls.py [options]

Options:
    --regenerate        Reclassify ALL CRLs (including existing ones)
    --limit N           Process only N CRLs (default: all without classification)
    --batch-size N      Number of concurrent API calls (default: 10)
    --sequential        Process one at a time (slower, for debugging)

Examples:
    # Classify new CRLs only (incremental)
    python enrich_crls.py

    # Process first 10 CRLs
    python enrich_crls.py --limit 10

    # Reclassify ALL CRLs (use with caution!)
    python enrich_crls.py --regenerate

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

THERAPEUTIC_CATEGORIES = [
    "Small molecules",
    "Biologics - proteins",
    "Vaccines",
    "Blood products",
    "Cellular therapies",
    "Gene therapies",
    "Tissue products",
    "Combination products",
    "Devices/IVDs",
    "Other"
]


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


def get_crls_needing_classification(conn, regenerate: bool = False, limit: int = None) -> List[Dict]:
    """Get CRLs that need therapeutic category classification."""
    logger.info("Fetching CRLs needing therapeutic category classification...")

    if regenerate:
        query = "SELECT c.id, s.summary FROM crls c INNER JOIN crl_summaries s ON c.id = s.crl_id WHERE s.summary IS NOT NULL AND s.summary != '' ORDER BY c.letter_date DESC"
    else:
        query = """
            SELECT c.id, s.summary FROM crls c INNER JOIN crl_summaries s ON c.id = s.crl_id
            WHERE (c.therapeutic_category IS NULL OR c.therapeutic_category = '')
            AND s.summary IS NOT NULL AND s.summary != ''
            ORDER BY c.letter_date DESC
        """

    if limit:
        query += f" LIMIT {limit}"

    results = conn.execute(query).fetchall()
    crls = [{"id": row[0], "summary": row[1]} for row in results]

    logger.info(f"Found {len(crls)} CRLs needing therapeutic category classification")
    return crls


def classify_therapeutic_category(summary: str, client: OpenAIClient) -> str:
    """Classify the therapeutic category using OpenAI with clarification retry."""
    prompt = f"""Analyze this FDA Complete Response Letter summary and classify the product's therapeutic category into ONE of these categories:

1. Small molecules - Traditional chemical drugs, synthetic compounds
2. Biologics - proteins - Protein-based biologics, monoclonal antibodies, enzymes
3. Vaccines - Preventive or therapeutic vaccines
4. Blood products - Blood-derived products, plasma products
5. Cellular therapies - Cell-based therapies, CAR-T cells
6. Gene therapies - Gene therapy products, gene editing
7. Tissue products - Tissue-engineered products
8. Combination products - Drug-device combinations, drug-biologic combinations
9. Devices/IVDs - Medical devices, in vitro diagnostics
10. Other - Products that don't fit above categories

CRL Summary:
{summary}

Respond with ONLY the category name, nothing else."""

    try:
        classification = client.create_chat_completion(
            model=settings.openai_summary_model,
            messages=[
                {"role": "system", "content": "You are an FDA regulatory expert who classifies therapeutic products in Complete Response Letters."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3
        ).strip()

        # Validate classification
        if classification in THERAPEUTIC_CATEGORIES:
            return classification

        # Try to match partial responses
        for category in THERAPEUTIC_CATEGORIES:
            if category.lower() in classification.lower():
                return category

        # If no match, make a clarification request
        logger.info(f"Unclear classification '{classification}', requesting clarification...")
        clarification_prompt = f"""Your previous response was: "{classification}"

This does not exactly match one of the required categories. Please respond with ONLY ONE of these exact category names:

1. Small molecules
2. Biologics - proteins
3. Vaccines
4. Blood products
5. Cellular therapies
6. Gene therapies
7. Tissue products
8. Combination products
9. Devices/IVDs
10. Other

Which category best matches your previous assessment? Respond with the category name only."""

        clarified_classification = client.create_chat_completion(
            model=settings.openai_summary_model,
            messages=[
                {"role": "system", "content": "You are an FDA regulatory expert who classifies therapeutic products in Complete Response Letters."},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": classification},
                {"role": "user", "content": clarification_prompt}
            ],
            max_tokens=50,
            temperature=0.1  # Lower temperature for more precise response
        ).strip()

        # Validate clarified response
        if clarified_classification in THERAPEUTIC_CATEGORIES:
            logger.info(f"Clarification successful: '{clarified_classification}'")
            return clarified_classification

        # Try partial match on clarified response
        for category in THERAPEUTIC_CATEGORIES:
            if category.lower() in clarified_classification.lower():
                logger.info(f"Clarification matched: '{category}'")
                return category

        # If still no match, default to Other
        logger.warning(f"Clarification failed. Original: '{classification}', Clarified: '{clarified_classification}'. Defaulting to 'Other'")
        return "Other"

    except Exception as e:
        logger.error(f"Classification error: {e}")
        return "Other"


async def process_single_crl(
    crl: Dict,
    client: OpenAIClient,
    conn,
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """Process a single CRL asynchronously."""
    crl_id = crl["id"]
    crl_summary = crl.get("summary", "")

    if not crl_summary or len(crl_summary.strip()) < 50:
        return {"status": "skipped", "crl_id": crl_id, "reason": "insufficient summary"}

    async with semaphore:
        try:
            # Classify (synchronous call wrapped in executor)
            loop = asyncio.get_event_loop()
            classification = await loop.run_in_executor(
                None,
                classify_therapeutic_category,
                crl_summary,
                client
            )

            # Update database
            conn.execute(
                "UPDATE crls SET therapeutic_category = ? WHERE id = ?",
                [classification, crl_id]
            )

            return {"status": "success", "crl_id": crl_id, "classification": classification}

        except Exception as e:
            return {"status": "failed", "crl_id": crl_id, "error": str(e)[:100]}


async def classify_crls_async(
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
        pbar = tqdm(total=len(crls), desc="Classifying therapeutic categories", unit="CRL")

    tasks = [
        process_single_crl(crl, client, conn, semaphore)
        for crl in crls
    ]

    for coro in asyncio.as_completed(tasks):
        result = await coro

        if result["status"] == "success":
            stats["success"] += 1
            if HAS_TQDM:
                tqdm.write(f"✓ {result['crl_id']}: {result['classification']}")
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
        logger.info("CRL Therapeutic Category Classification Script")
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
        crls = get_crls_needing_classification(
            conn,
            regenerate=args["regenerate"],
            limit=args["limit"]
        )

        if not crls:
            logger.info("✓ No CRLs need therapeutic category classification. All done!")
            return 0

        # Classify
        logger.info("\nClassifying therapeutic categories...")
        stats = asyncio.run(classify_crls_async(
            crls, client, conn, args["batch_size"]
        ))

        # Results
        logger.info("\n" + "=" * 60)
        logger.info("THERAPEUTIC CATEGORY CLASSIFICATION COMPLETE")
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
