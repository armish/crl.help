#!/usr/bin/env python3
"""
Script to generate AI summaries for CRLs in the database.

Usage:
    python generate_summaries.py [--all] [--limit N] [--batch-size N]

Options:
    --all           Process all CRLs, including those with existing summaries
    --limit N       Process only N CRLs (default: all)
    --batch-size N  Number of CRLs to process before committing (default: 10)
"""

import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import init_db, CRLRepository, SummaryRepository
from app.services.summarization import SummarizationService
from app.utils.logging_config import get_logger, setup_logging

# Setup logging
setup_logging(log_level="INFO", enable_file_logging=True)
logger = get_logger(__name__)


def parse_args():
    """Parse command line arguments."""
    args = {
        "regenerate_all": "--all" in sys.argv,
        "limit": None,
        "batch_size": 10,
    }

    # Parse --limit
    if "--limit" in sys.argv:
        try:
            limit_idx = sys.argv.index("--limit")
            args["limit"] = int(sys.argv[limit_idx + 1])
        except (IndexError, ValueError):
            logger.error("--limit requires a numeric argument")
            sys.exit(1)

    # Parse --batch-size
    if "--batch-size" in sys.argv:
        try:
            batch_idx = sys.argv.index("--batch-size")
            args["batch_size"] = int(sys.argv[batch_idx + 1])
        except (IndexError, ValueError):
            logger.error("--batch-size requires a numeric argument")
            sys.exit(1)

    return args


def get_crls_needing_summaries(
    crl_repo: CRLRepository,
    summary_repo: SummaryRepository,
    regenerate_all: bool = False,
    limit: int = None
) -> List[Dict[str, Any]]:
    """
    Get CRLs that need summaries generated.

    Args:
        crl_repo: CRL repository
        summary_repo: Summary repository
        regenerate_all: If True, get all CRLs regardless of existing summaries
        limit: Maximum number of CRLs to return

    Returns:
        List of CRL dictionaries with id and text fields
    """
    logger.info("Fetching CRLs needing summaries...")

    # Get all CRLs (paginate to handle large datasets)
    all_crls = []
    offset = 0
    page_size = 1000

    while True:
        crls, total = crl_repo.get_all(
            limit=page_size,
            offset=offset,
            sort_by="letter_date",
            sort_order="DESC"
        )

        if not crls:
            break

        all_crls.extend(crls)
        offset += page_size

        if limit and len(all_crls) >= limit:
            all_crls = all_crls[:limit]
            break

        # Stop if we've fetched all available CRLs
        if offset >= total:
            break

    logger.info(f"Found {len(all_crls)} total CRLs in database")

    # Filter out CRLs that already have summaries (unless regenerating)
    if not regenerate_all:
        crls_needing_summaries = []
        for crl in all_crls:
            if not summary_repo.exists(crl["id"]):
                crls_needing_summaries.append(crl)

        logger.info(
            f"Filtered to {len(crls_needing_summaries)} CRLs without summaries"
        )
        return crls_needing_summaries
    else:
        logger.info("Regenerating summaries for all CRLs")
        return all_crls


def generate_summaries(
    crls: List[Dict[str, Any]],
    summary_service: SummarizationService,
    summary_repo: SummaryRepository,
    batch_size: int = 10
) -> Dict[str, int]:
    """
    Generate and store summaries for CRLs.

    Args:
        crls: List of CRL dictionaries
        summary_service: Summarization service
        summary_repo: Summary repository
        batch_size: Number of CRLs to process before logging progress

    Returns:
        Statistics dictionary with success/failure counts
    """
    stats = {
        "total": len(crls),
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }

    logger.info(f"Starting summarization of {len(crls)} CRLs...")
    logger.info(f"Batch size: {batch_size}")

    for i, crl in enumerate(crls, 1):
        crl_id = crl["id"]
        crl_text = crl.get("text", "")

        # Skip CRLs with no text
        if not crl_text or not crl_text.strip():
            logger.warning(f"Skipping CRL {crl_id}: no text content")
            stats["skipped"] += 1
            continue

        try:
            # Generate summary
            logger.debug(f"Generating summary for CRL {crl_id}")
            summary_text = summary_service.summarize_crl(
                crl_text,
                max_summary_length=300
            )

            # Store summary
            summary_data = {
                "id": str(uuid.uuid4()),
                "crl_id": crl_id,
                "summary": summary_text,
                "model": settings.openai_summary_model,
                "tokens_used": 0,  # Could be enhanced to track actual tokens
            }

            summary_repo.create(summary_data)
            stats["success"] += 1

            # Log progress
            if i % batch_size == 0:
                logger.info(
                    f"Progress: {i}/{stats['total']} "
                    f"({stats['success']} success, {stats['failed']} failed, "
                    f"{stats['skipped']} skipped)"
                )

        except Exception as e:
            logger.error(f"Failed to generate summary for CRL {crl_id}: {e}")
            stats["failed"] += 1
            continue

    return stats


def main():
    """Main function to generate summaries."""
    try:
        args = parse_args()

        logger.info("=" * 60)
        logger.info("CRL Summary Generation Script")
        logger.info("=" * 60)
        logger.info(f"Regenerate all: {args['regenerate_all']}")
        logger.info(f"Limit: {args['limit'] or 'No limit'}")
        logger.info(f"Batch size: {args['batch_size']}")

        # Initialize database
        logger.info("\n[Step 1/3] Initializing database...")
        init_db()
        logger.info("✓ Database initialized")

        # Initialize services and repositories
        crl_repo = CRLRepository()
        summary_repo = SummaryRepository()
        summary_service = SummarizationService(settings)

        # Check OpenAI configuration
        if not settings.openai_api_key:
            logger.error(
                "OpenAI API key not configured. "
                "Please set OPENAI_API_KEY environment variable."
            )
            return 1

        logger.info(f"Using OpenAI model: {settings.openai_summary_model}")
        if settings.ai_dry_run:
            logger.warning("AI_DRY_RUN is enabled - summaries will be mocked")

        # Get CRLs needing summaries
        logger.info("\n[Step 2/3] Fetching CRLs needing summaries...")
        crls = get_crls_needing_summaries(
            crl_repo,
            summary_repo,
            regenerate_all=args["regenerate_all"],
            limit=args["limit"]
        )

        if not crls:
            logger.info("No CRLs need summaries. Exiting.")
            return 0

        # Generate summaries
        logger.info("\n[Step 3/3] Generating summaries...")
        stats = generate_summaries(
            crls,
            summary_service,
            summary_repo,
            batch_size=args["batch_size"]
        )

        # Display results
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY GENERATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total CRLs processed:  {stats['total']}")
        logger.info(f"Successful:            {stats['success']}")
        logger.info(f"Failed:                {stats['failed']}")
        logger.info(f"Skipped (no text):     {stats['skipped']}")

        # Get summary statistics
        total_summaries = summary_repo.conn.execute(
            "SELECT COUNT(*) FROM crl_summaries"
        ).fetchone()[0]

        logger.info(f"\nTotal summaries in database: {total_summaries}")
        logger.info(f"Database location: {settings.database_path}")

        if stats["failed"] > 0:
            logger.warning(
                f"\n⚠ {stats['failed']} CRLs failed to generate summaries. "
                "Check logs for details."
            )
            return 1

        logger.info("\n✓ All summaries generated successfully!")
        return 0

    except Exception as e:
        logger.error(f"\n✗ Summary generation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
