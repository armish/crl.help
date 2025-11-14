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
from app.utils.openai_client import get_openai_client
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
        query = "SELECT id, text FROM crls WHERE text IS NOT NULL AND text != '' ORDER BY letter_date DESC"
    else:
        query = """
            SELECT id, text FROM crls
            WHERE (therapeutic_category IS NULL OR therapeutic_category = '')
            AND text IS NOT NULL AND text != ''
            ORDER BY letter_date DESC
        """

    if limit:
        query += f" LIMIT {limit}"

    results = conn.execute(query).fetchall()
    crls = [{"id": row[0], "text": row[1]} for row in results]

    logger.info(f"Found {len(crls)} CRLs needing therapeutic category classification")
    return crls


def classify_therapeutic_category(text: str, client) -> str:
    """Classify the therapeutic category using OpenAI."""
    prompt = f"""Analyze this FDA Complete Response Letter and classify the product's therapeutic category into ONE of these categories:

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

CRL Text (first 3000 chars):
{text[:3000]}

Respond with ONLY the category name, nothing else."""

    try:
        response = client.chat.completions.create(
            model=settings.openai_summary_model,
            messages=[
                {"role": "system", "content": "You are an FDA regulatory expert who classifies therapeutic products in Complete Response Letters."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3
        )

        classification = response.choices[0].message.content.strip()

        # Validate classification
        if classification in THERAPEUTIC_CATEGORIES:
            return classification
        else:
            # Try to match partial responses
            for category in THERAPEUTIC_CATEGORIES:
                if category.lower() in classification.lower():
                    return category
            logger.warning(f"Invalid classification returned: {classification}, defaulting to 'Other'")
            return "Other"

    except Exception as e:
        logger.error(f"Classification error: {e}")
        return "Other"


async def process_single_crl(
    crl: Dict,
    client,
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
                classify_therapeutic_category,
                crl_text,
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
    client,
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

        client = get_openai_client()
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
