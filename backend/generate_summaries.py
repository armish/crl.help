#!/usr/bin/env python3
"""
Script to generate AI summaries for CRLs in the database.

Usage:
    python generate_summaries.py [options]

Options:
    --regenerate        Regenerate summaries for ALL CRLs (including existing ones)
    --limit N           Process only N CRLs (default: all without summaries)
    --batch-size N      Number of concurrent API calls (default: 10)
    --retry-failed      Retry only CRLs that previously failed
    --sequential        Process one at a time (slower, for debugging)

Examples:
    # Generate summaries for new CRLs only (incremental)
    python generate_summaries.py

    # Process first 10 CRLs
    python generate_summaries.py --limit 10

    # Regenerate ALL summaries (use with caution!)
    python generate_summaries.py --regenerate

    # Retry failed CRLs
    python generate_summaries.py --retry-failed

    # Use 20 concurrent API calls (faster)
    python generate_summaries.py --batch-size 20

    --help, -h    Show this help message and exit
"""

import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set

# Check for help first
if "--help" in sys.argv or "-h" in sys.argv:
    print(__doc__)
    sys.exit(0)

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
        "sequential": "--sequential" in sys.argv,
        "limit": None,
        "batch_size": 10,  # Default concurrent API calls
    }

    # Validate mutually exclusive options
    if args["regenerate"] and args["retry_failed"]:
        logger.warning("Both --regenerate and --retry-failed specified. Using --regenerate.")
        args["retry_failed"] = False

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


async def process_single_crl(
    crl: Dict[str, Any],
    summary_service: SummarizationService,
    summary_repo: SummaryRepository,
    semaphore: asyncio.Semaphore,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Process a single CRL asynchronously with retry logic.

    Args:
        crl: CRL dictionary
        summary_service: Summarization service
        summary_repo: Summary repository
        semaphore: Semaphore to limit concurrent requests
        max_retries: Maximum retry attempts

    Returns:
        Dict with status and details
    """
    crl_id = crl["id"]
    crl_text = crl.get("text", "")

    # Skip CRLs with no text
    if not crl_text or not crl_text.strip():
        return {"status": "skipped", "crl_id": crl_id, "reason": "no text"}

    # Use semaphore to limit concurrent API calls
    async with semaphore:
        for attempt in range(max_retries):
            try:
                # Generate summary (synchronous call wrapped in executor)
                loop = asyncio.get_event_loop()
                summary_text = await loop.run_in_executor(
                    None,
                    summary_service.summarize_crl,
                    crl_text,
                    300  # max_summary_length
                )

                # Validate summary
                if not summary_text or len(summary_text.strip()) < 50:
                    raise ValueError(f"Summary too short ({len(summary_text)} chars)")

                # Delete any existing summaries for this CRL to avoid duplicates
                summary_repo.conn.execute(
                    "DELETE FROM crl_summaries WHERE crl_id = ?",
                    [crl_id]
                )

                # Store summary
                summary_data = {
                    "id": str(uuid.uuid4()),
                    "crl_id": crl_id,
                    "summary": summary_text,
                    "model": settings.openai_summary_model,
                    "tokens_used": 0,
                }

                summary_repo.create(summary_data)

                return {
                    "status": "success",
                    "crl_id": crl_id,
                    "attempt": attempt + 1
                }

            except Exception as e:
                if attempt < max_retries - 1:
                    # Wait briefly before retry
                    await asyncio.sleep(1)
                    continue
                else:
                    return {
                        "status": "failed",
                        "crl_id": crl_id,
                        "error": str(e)[:100]
                    }


async def generate_summaries_async(
    crls: List[Dict[str, Any]],
    summary_service: SummarizationService,
    summary_repo: SummaryRepository,
    batch_size: int = 10,
    max_retries: int = 3
) -> Dict[str, int]:
    """
    Generate and store summaries for CRLs concurrently.

    Args:
        crls: List of CRL dictionaries
        summary_service: Summarization service
        summary_repo: Summary repository
        batch_size: Number of concurrent API calls
        max_retries: Maximum retry attempts per CRL

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

    logger.info(f"Starting concurrent summarization of {len(crls)} CRLs...")
    logger.info(f"Concurrent API calls: {batch_size}")
    logger.info(f"Max retries per CRL: {max_retries}")

    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(batch_size)

    # Create progress bar if tqdm is available
    if HAS_TQDM:
        pbar = tqdm(total=len(crls), desc="Generating summaries", unit="CRL")

    # Process all CRLs concurrently
    tasks = [
        process_single_crl(crl, summary_service, summary_repo, semaphore, max_retries)
        for crl in crls
    ]

    # Gather results as they complete
    for coro in asyncio.as_completed(tasks):
        result = await coro

        # Update stats based on result
        if result["status"] == "success":
            stats["success"] += 1
            if result["attempt"] > 1:
                stats["retried"] += 1
                if HAS_TQDM:
                    tqdm.write(f"✓ {result['crl_id']} (retry {result['attempt']})")
        elif result["status"] == "failed":
            stats["failed"] += 1
            failed_crls.add(result["crl_id"])
            if HAS_TQDM:
                tqdm.write(f"✗ {result['crl_id']}: {result.get('error', 'Unknown error')}")
            else:
                logger.error(f"Failed: {result['crl_id']}: {result.get('error')}")
        elif result["status"] == "skipped":
            stats["skipped"] += 1
            if HAS_TQDM:
                tqdm.write(f"⊘ {result['crl_id']}: {result.get('reason')}")

        # Update progress bar
        if HAS_TQDM:
            pbar.update(1)
            pbar.set_postfix({
                "✓": stats["success"],
                "✗": stats["failed"],
                "⊘": stats["skipped"]
            })

    if HAS_TQDM:
        pbar.close()

    # Log failed CRLs
    if failed_crls:
        logger.warning(f"\nFailed CRL IDs ({len(failed_crls)}):")
        for crl_id in sorted(failed_crls):
            logger.warning(f"  - {crl_id}")
        logger.info(f"\nTo retry failures, run: python generate_summaries.py --retry-failed")

    return stats


def generate_summaries(
    crls: List[Dict[str, Any]],
    summary_service: SummarizationService,
    summary_repo: SummaryRepository,
    batch_size: int = 10,
    max_retries: int = 3,
    sequential: bool = False
) -> Dict[str, int]:
    """
    Generate and store summaries for CRLs (concurrent or sequential).

    Args:
        crls: List of CRL dictionaries
        summary_service: Summarization service
        summary_repo: Summary repository
        batch_size: Number of concurrent API calls (ignored if sequential=True)
        max_retries: Maximum retry attempts for failed CRLs
        sequential: If True, process one at a time (slower, for debugging)

    Returns:
        Statistics dictionary with success/failure counts
    """
    if sequential:
        # Use old sequential implementation for debugging
        logger.info("Running in SEQUENTIAL mode (slower)")
        return _generate_summaries_sequential(
            crls, summary_service, summary_repo, max_retries
        )
    else:
        # Use new async concurrent implementation (default)
        logger.info("Running in CONCURRENT mode (faster)")
        return asyncio.run(generate_summaries_async(
            crls, summary_service, summary_repo, batch_size, max_retries
        ))


def _generate_summaries_sequential(
    crls: List[Dict[str, Any]],
    summary_service: SummarizationService,
    summary_repo: SummaryRepository,
    max_retries: int = 3
) -> Dict[str, int]:
    """Sequential implementation (for debugging)."""
    stats = {
        "total": len(crls),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "retried": 0,
    }

    failed_crls: Set[str] = set()
    iterator = tqdm(crls, desc="Generating summaries", unit="CRL") if HAS_TQDM else crls

    for crl in iterator:
        crl_id = crl["id"]
        crl_text = crl.get("text", "")

        if not crl_text or not crl_text.strip():
            if HAS_TQDM:
                tqdm.write(f"⊘ {crl_id}: no text")
            stats["skipped"] += 1
            continue

        for attempt in range(max_retries):
            try:
                summary_text = summary_service.summarize_crl(crl_text, max_summary_length=300)

                if not summary_text or len(summary_text.strip()) < 50:
                    raise ValueError(f"Summary too short ({len(summary_text)} chars)")

                # Delete any existing summaries for this CRL to avoid duplicates
                summary_repo.conn.execute(
                    "DELETE FROM crl_summaries WHERE crl_id = ?",
                    [crl_id]
                )

                summary_data = {
                    "id": str(uuid.uuid4()),
                    "crl_id": crl_id,
                    "summary": summary_text,
                    "model": settings.openai_summary_model,
                    "tokens_used": 0,
                }

                summary_repo.create(summary_data)
                stats["success"] += 1

                if attempt > 0:
                    stats["retried"] += 1
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                else:
                    failed_crls.add(crl_id)
                    stats["failed"] += 1
                    if HAS_TQDM:
                        tqdm.write(f"✗ {crl_id}: {str(e)[:100]}")

        if HAS_TQDM:
            iterator.set_postfix({"✓": stats["success"], "✗": stats["failed"], "⊘": stats["skipped"]})

    if failed_crls:
        logger.warning(f"\nFailed CRL IDs ({len(failed_crls)}):")
        for crl_id in sorted(failed_crls):
            logger.warning(f"  - {crl_id}")

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
        if args['sequential']:
            logger.info("Mode: Sequential processing (1 at a time, for debugging)")
        else:
            logger.info(f"Concurrent API calls: {args['batch_size']}")

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
            batch_size=args["batch_size"],
            sequential=args["sequential"]
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
