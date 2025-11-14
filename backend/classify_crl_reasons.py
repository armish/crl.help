#!/usr/bin/env python3
"""
Script to classify CRLs by deficiency reason using AI.

This script analyzes CRL text and classifies the primary deficiency reason into one of:
- Clinical
- CMC / Quality
- Facilities / GMP
- Combination Product / Device
- Regulatory / Labeling / Other

Usage:
    python classify_crl_reasons.py [options]

Options:
    --regenerate        Reclassify ALL CRLs (including existing ones)
    --limit N           Process only N CRLs (default: all without classification)
    --batch-size N      Number of concurrent API calls (default: 10)
    --sequential        Process one at a time (slower, for debugging)

Examples:
    # Classify new CRLs only (incremental)
    python classify_crl_reasons.py

    # Process first 10 CRLs
    python classify_crl_reasons.py --limit 10

    # Reclassify ALL CRLs (use with caution!)
    python classify_crl_reasons.py --regenerate

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

DEFICIENCY_CATEGORIES = [
    "Clinical",
    "CMC / Quality",
    "Facilities / GMP",
    "Combination Product / Device",
    "Regulatory / Labeling / Other"
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
    """Get CRLs that need deficiency reason classification."""
    logger.info("Fetching CRLs needing classification...")

    if regenerate:
        query = """
            SELECT c.id, s.summary
            FROM crls c
            INNER JOIN crl_summaries s ON c.id = s.crl_id
            WHERE s.summary IS NOT NULL AND s.summary != ''
            ORDER BY c.letter_date DESC
        """
    else:
        query = """
            SELECT c.id, s.summary
            FROM crls c
            INNER JOIN crl_summaries s ON c.id = s.crl_id
            WHERE (c.deficiency_reason IS NULL OR c.deficiency_reason = '')
            AND s.summary IS NOT NULL AND s.summary != ''
            ORDER BY c.letter_date DESC
        """

    if limit:
        query += f" LIMIT {limit}"

    results = conn.execute(query).fetchall()
    crls = [{"id": row[0], "summary": row[1]} for row in results]

    logger.info(f"Found {len(crls)} CRLs needing classification (with summaries)")
    return crls


def classify_deficiency_reason(summary: str, client: OpenAIClient) -> str:
    """Classify the primary deficiency reason using OpenAI with clarification retry."""
    prompt = f"""Analyze this FDA Complete Response Letter summary and classify the PRIMARY deficiency reason into ONE of these categories:

1. Clinical - Issues with clinical trial design, efficacy, safety data, or patient outcomes
2. CMC / Quality - Chemistry, Manufacturing, and Controls issues; product quality, stability, or specifications
3. Facilities / GMP - Manufacturing facility issues or Good Manufacturing Practice violations
4. Combination Product / Device - Device component issues in combination products
5. Regulatory / Labeling / Other - Regulatory compliance, labeling, or other administrative issues

CRL Summary:
{summary}

Respond with ONLY the category name, nothing else."""

    try:
        classification = client.create_chat_completion(
            model=settings.openai_summary_model,
            messages=[
                {"role": "system", "content": "You are an FDA regulatory expert who classifies deficiency reasons in Complete Response Letters."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3
        ).strip()

        # Validate classification
        if classification in DEFICIENCY_CATEGORIES:
            return classification

        # Try to match partial responses
        for category in DEFICIENCY_CATEGORIES:
            if category.lower() in classification.lower():
                return category

        # If no match, make a clarification request
        logger.info(f"Unclear classification '{classification}', requesting clarification...")
        clarification_prompt = f"""Your previous response was: "{classification}"

This does not exactly match one of the required categories. Please respond with ONLY ONE of these exact category names:

1. Clinical
2. CMC / Quality
3. Facilities / GMP
4. Combination Product / Device
5. Regulatory / Labeling / Other

Which category best matches your previous assessment? Respond with the category name only."""

        clarified_classification = client.create_chat_completion(
            model=settings.openai_summary_model,
            messages=[
                {"role": "system", "content": "You are an FDA regulatory expert who classifies deficiency reasons in Complete Response Letters."},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": classification},
                {"role": "user", "content": clarification_prompt}
            ],
            max_tokens=50,
            temperature=0.1  # Lower temperature for more precise response
        ).strip()

        # Validate clarified response
        if clarified_classification in DEFICIENCY_CATEGORIES:
            logger.info(f"Clarification successful: '{clarified_classification}'")
            return clarified_classification

        # Try partial match on clarified response
        for category in DEFICIENCY_CATEGORIES:
            if category.lower() in clarified_classification.lower():
                logger.info(f"Clarification matched: '{category}'")
                return category

        # If still no match, default to Regulatory / Labeling / Other
        logger.warning(f"Clarification failed. Original: '{classification}', Clarified: '{clarified_classification}'. Defaulting to 'Regulatory / Labeling / Other'")
        return "Regulatory / Labeling / Other"

    except Exception as e:
        logger.error(f"Classification error: {e}")
        return "Regulatory / Labeling / Other"


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
                classify_deficiency_reason,
                crl_summary,
                client
            )

            # Update database
            conn.execute(
                "UPDATE crls SET deficiency_reason = ? WHERE id = ?",
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

    logger.info(f"Starting concurrent classification of {len(crls)} CRLs...")
    logger.info(f"Concurrent API calls: {batch_size}")

    semaphore = asyncio.Semaphore(batch_size)

    if HAS_TQDM:
        pbar = tqdm(total=len(crls), desc="Classifying CRLs", unit="CRL")

    tasks = [
        process_single_crl(crl, client, conn, semaphore)
        for crl in crls
    ]

    for coro in asyncio.as_completed(tasks):
        result = await coro

        if result["status"] == "success":
            stats["success"] += 1
            if HAS_TQDM:
                tqdm.write(f" {result['crl_id']}: {result['classification']}")
        elif result["status"] == "failed":
            stats["failed"] += 1
            if HAS_TQDM:
                tqdm.write(f" {result['crl_id']}: {result.get('error', 'Unknown error')}")
        elif result["status"] == "skipped":
            stats["skipped"] += 1

        if HAS_TQDM:
            pbar.update(1)
            pbar.set_postfix({"": stats["success"], "": stats["failed"]})

    if HAS_TQDM:
        pbar.close()

    return stats


def main():
    """Main function."""
    try:
        args = parse_args()

        logger.info("=" * 60)
        logger.info("CRL Deficiency Reason Classification Script")
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
        logger.info(" Database initialized")

        # Get OpenAI client
        if not settings.openai_api_key:
            logger.error("L OpenAI API key not configured")
            return 1

        client = OpenAIClient(settings)
        logger.info(f" Using OpenAI model: {settings.openai_summary_model}")

        # Get CRLs
        crls = get_crls_needing_classification(
            conn,
            regenerate=args["regenerate"],
            limit=args["limit"]
        )

        if not crls:
            logger.info(" No CRLs need classification. All done!")
            return 0

        # Classify
        logger.info("\nClassifying CRLs...")
        stats = asyncio.run(classify_crls_async(
            crls, client, conn, args["batch_size"]
        ))

        # Results
        logger.info("\n" + "=" * 60)
        logger.info("CLASSIFICATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total CRLs processed:  {stats['total']}")
        logger.info(f" Successful:          {stats['success']}")
        logger.info(f" Failed:              {stats['failed']}")
        logger.info(f"� Skipped:             {stats['skipped']}")

        if stats["failed"] > 0:
            logger.warning(f"\n�  {stats['failed']} CRLs failed")
            return 1

        logger.info("\n All CRLs classified successfully!")
        return 0

    except KeyboardInterrupt:
        logger.warning("\n�  Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\n Classification failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
