#!/usr/bin/env python3
"""
Script to generate AI summaries for CRLs in the database.

Usage:
    python generate_summaries.py [options]

Options:
    --regenerate    Regenerate summaries for ALL CRLs (including existing ones)
    --limit N       Process only N CRLs (default: all without summaries)
    --batch-size N  Progress reporting interval (default: 50)
    --retry-failed  Retry only CRLs that previously failed

Examples:
    # Generate summaries for new CRLs only (incremental)
    python generate_summaries.py

    # Process first 10 CRLs
    python generate_summaries.py --limit 10

    # Regenerate ALL summaries (use with caution!)
    python generate_summaries.py --regenerate

    # Retry failed CRLs
    python generate_summaries.py --retry-failed
"""

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import init_db, CRLRepository, SummaryRepository
from app.services.summarization import SummarizationService
from app.utils.logging_config import get_logger, setup_logging

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    logger = get_logger(__name__)
    logger.warning("tqdm not installed. Install with 'pip install tqdm' for progress bars.")

# Setup logging
setup_logging(log_level="INFO", enable_file_logging=True)
logger = get_logger(__name__)


def parse_args():
    """Parse command line arguments."""
    args = {
        "regenerate": "--regenerate" in sys.argv,
        "retry_failed": "--retry-failed" in sys.argv,
        "limit": None,
        "batch_size": 50,  # Default batch size for progress reporting
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
    regenerate: bool = False,
    retry_failed: bool = False,
    limit: int = None
) -> List[Dict[str, Any]]:
    """
    Get CRLs that need summaries generated.

    Args:
        crl_repo: CRL repository
        summary_repo: Summary repository
        regenerate: If True, regenerate all summaries (overwrite existing)
        retry_failed: If True, only return CRLs with empty/failed summaries
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

    # Determine which CRLs need processing
    if regenerate:
        logger.info("⚠️  Regenerating summaries for ALL CRLs (existing summaries will be replaced)")
        return all_crls
    elif retry_failed:
        # Find CRLs with empty or very short summaries (likely failed)
        crls_to_retry = []
        for crl in all_crls:
            existing = summary_repo.get_by_crl_id(crl["id"])
            if existing and (not existing.get("summary") or len(existing.get("summary", "").strip()) < 50):
                crls_to_retry.append(crl)
        logger.info(f"Found {len(crls_to_retry)} CRLs with failed/empty summaries to retry")
        return crls_to_retry
    else:
        # Default: only CRLs without summaries (incremental)
        crls_needing_summaries = []
        for crl in all_crls:
            if not summary_repo.exists(crl["id"]):
                crls_needing_summaries.append(crl)

        logger.info(
            f"✓ Found {len(crls_needing_summaries)} CRLs without summaries (incremental mode)"
        )
        return crls_needing_summaries


def generate_summaries(
    crls: List[Dict[str, Any]],
    summary_service: SummarizationService,
    summary_repo: SummaryRepository,
    batch_size: int = 50,
    max_retries: int = 3
) -> Dict[str, int]:
    """
    Generate and store summaries for CRLs with progress bar and retry logic.

    Args:
        crls: List of CRL dictionaries
        summary_service: Summarization service
        summary_repo: Summary repository
        batch_size: Progress reporting interval
        max_retries: Maximum retry attempts for failed CRLs

    Returns:
        Statistics dictionary with success/failure counts
    """
    stats = {
        "total": len(crls),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "retried": 0,
    }

    failed_crls: Set[str] = set()

    logger.info(f"Starting summarization of {len(crls)} CRLs...")
    logger.info(f"Progress reporting interval: {batch_size} CRLs")
    logger.info(f"Max retries per CRL: {max_retries}")

    # Create progress bar if tqdm is available
    iterator = tqdm(crls, desc="Generating summaries", unit="CRL") if HAS_TQDM else crls

    for crl in iterator:
        crl_id = crl["id"]
        crl_text = crl.get("text", "")

        # Skip CRLs with no text
        if not crl_text or not crl_text.strip():
            if HAS_TQDM:
                tqdm.write(f"⊘ Skipping {crl_id}: no text content")
            else:
                logger.warning(f"Skipping CRL {crl_id}: no text content")
            stats["skipped"] += 1
            continue

        # Try to generate summary with retries
        success = False
        for attempt in range(max_retries):
            try:
                # Generate summary
                summary_text = summary_service.summarize_crl(
                    crl_text,
                    max_summary_length=300
                )

                # Validate summary is not empty
                if not summary_text or len(summary_text.strip()) < 50:
                    raise ValueError(f"Generated summary is too short ({len(summary_text)} chars)")

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
                success = True

                if attempt > 0:
                    stats["retried"] += 1
                    if HAS_TQDM:
                        tqdm.write(f"✓ {crl_id} (succeeded on retry {attempt + 1})")

                break  # Success, exit retry loop

            except Exception as e:
                if attempt < max_retries - 1:
                    # Log retry attempt
                    if HAS_TQDM:
                        tqdm.write(f"⟳ {crl_id}: Retry {attempt + 1}/{max_retries - 1} after error: {str(e)[:100]}")
                    else:
                        logger.warning(f"Retry {attempt + 1} for CRL {crl_id}: {e}")
                    continue
                else:
                    # Final failure after all retries
                    failed_crls.add(crl_id)
                    stats["failed"] += 1
                    if HAS_TQDM:
                        tqdm.write(f"✗ {crl_id}: Failed after {max_retries} attempts: {str(e)[:100]}")
                    else:
                        logger.error(f"Failed to generate summary for CRL {crl_id} after {max_retries} attempts: {e}")

        # Update progress bar description with stats
        if HAS_TQDM:
            iterator.set_postfix({
                "✓": stats["success"],
                "✗": stats["failed"],
                "⊘": stats["skipped"]
            })

    # Log failed CRLs for easy retry
    if failed_crls:
        logger.warning(f"\nFailed CRL IDs ({len(failed_crls)}):")
        for crl_id in sorted(failed_crls):
            logger.warning(f"  - {crl_id}")
        logger.info(f"\nTo retry failures, run: python generate_summaries.py --retry-failed")

    return stats


def main():
    """Main function to generate summaries."""
    try:
        args = parse_args()

        logger.info("=" * 60)
        logger.info("CRL Summary Generation Script")
        logger.info("=" * 60)

        # Display mode
        if args['regenerate']:
            logger.info("Mode: REGENERATE (will replace ALL existing summaries)")
        elif args['retry_failed']:
            logger.info("Mode: RETRY FAILED (only CRLs with empty/failed summaries)")
        else:
            logger.info("Mode: INCREMENTAL (only new CRLs without summaries)")

        logger.info(f"Limit: {args['limit'] or 'No limit'}")
        logger.info(f"Progress interval: {args['batch_size']} CRLs")

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
                "❌ OpenAI API key not configured. "
                "Please set OPENAI_API_KEY in .env file."
            )
            return 1

        logger.info(f"✓ Using OpenAI model: {settings.openai_summary_model}")
        if settings.ai_dry_run:
            logger.warning("⚠️  AI_DRY_RUN is enabled - summaries will be mocked")

        # Get CRLs needing summaries
        logger.info("\n[Step 2/3] Fetching CRLs needing summaries...")
        crls = get_crls_needing_summaries(
            crl_repo,
            summary_repo,
            regenerate=args["regenerate"],
            retry_failed=args["retry_failed"],
            limit=args["limit"]
        )

        if not crls:
            logger.info("✓ No CRLs need summaries. All done!")
            return 0

        # Generate summaries
        logger.info("\n[Step 3/3] Generating summaries...")
        if not HAS_TQDM:
            logger.warning("⚠️  Install tqdm for progress bars: pip install tqdm")

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
        logger.info(f"✓ Successful:          {stats['success']}")
        if stats['retried'] > 0:
            logger.info(f"⟳ Retried & succeeded: {stats['retried']}")
        logger.info(f"✗ Failed:              {stats['failed']}")
        logger.info(f"⊘ Skipped (no text):   {stats['skipped']}")

        # Get summary statistics
        total_summaries = summary_repo.conn.execute(
            "SELECT COUNT(*) FROM crl_summaries"
        ).fetchone()[0]

        logger.info(f"\n📊 Total summaries in database: {total_summaries}")
        logger.info(f"💾 Database location: {settings.database_path}")

        if stats["failed"] > 0:
            logger.warning(
                f"\n⚠️  {stats['failed']} CRLs failed after retries. "
                "Run with --retry-failed to retry them."
            )
            return 1

        logger.info("\n✓ All summaries generated successfully!")
        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user. Progress has been saved.")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"\n✗ Summary generation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
