#!/usr/bin/env python3
"""
Script to generate vector embeddings for CRLs in the database.

Usage:
    python generate_embeddings.py [options]

Options:
    --regenerate        Regenerate embeddings for ALL CRLs (including existing ones)
    --limit N           Process only N CRLs (default: all without embeddings)
    --batch-size N      Number of concurrent API calls (default: 50)
    --retry-failed      Retry only CRLs that previously failed
    --sequential        Process one at a time (slower, for debugging)
    --embed-full-text   Generate embeddings for full CRL text (in addition to summaries)

Examples:
    # Generate embeddings for summaries of new CRLs (incremental)
    python generate_embeddings.py

    # Process first 10 CRLs
    python generate_embeddings.py --limit 10

    # Regenerate ALL embeddings (use with caution!)
    python generate_embeddings.py --regenerate

    # Retry failed CRLs
    python generate_embeddings.py --retry-failed

    # Use 100 concurrent API calls (faster)
    python generate_embeddings.py --batch-size 100

    # Embed full text instead of summaries
    python generate_embeddings.py --embed-full-text
"""

import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import init_db, CRLRepository, SummaryRepository
from app.utils.logging_config import get_logger, setup_logging

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
        "retry_failed": "--retry-failed" in sys.argv,
        "sequential": "--sequential" in sys.argv,
        "embed_full_text": "--embed-full-text" in sys.argv,
        "limit": None,
        "batch_size": 50,  # Embeddings are faster, so higher default
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


def get_crls_needing_embeddings(
    crl_repo: CRLRepository,
    summary_repo: SummaryRepository,
    regenerate: bool = False,
    retry_failed: bool = False,
    embed_full_text: bool = False,
    limit: int = None
) -> List[Dict[str, Any]]:
    """
    Get CRLs that need embeddings generated.

    Args:
        crl_repo: CRL repository
        summary_repo: Summary repository
        regenerate: If True, regenerate all embeddings (overwrite existing)
        retry_failed: If True, only return CRLs with missing/failed embeddings
        embed_full_text: If True, embed full text; otherwise embed summaries
        limit: Maximum number of CRLs to return

    Returns:
        List of dictionaries with crl_id and text to embed
    """
    logger.info("Fetching CRLs needing embeddings...")

    # Get all CRLs with summaries (unless embedding full text)
    if embed_full_text:
        logger.info("Embedding mode: FULL TEXT")
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

            # Add full CRL text
            for crl in crls:
                all_crls.append({
                    "crl_id": crl["id"],
                    "text": crl.get("text", ""),
                    "embedding_type": "full_text"
                })

            offset += page_size
            if limit and len(all_crls) >= limit:
                all_crls = all_crls[:limit]
                break
            if offset >= total:
                break

    else:
        logger.info("Embedding mode: SUMMARIES")
        # Get all summaries
        all_summaries = summary_repo.conn.execute(
            "SELECT crl_id, summary FROM crl_summaries ORDER BY generated_at DESC"
        ).fetchall()

        all_crls = [
            {
                "crl_id": crl_id,
                "text": summary,
                "embedding_type": "summary"
            }
            for crl_id, summary in all_summaries
        ]

        if limit:
            all_crls = all_crls[:limit]

    logger.info(f"Found {len(all_crls)} CRLs/summaries in database")

    # Get existing embeddings
    embedding_type = "full_text" if embed_full_text else "summary"
    existing_embeddings = summary_repo.conn.execute(
        f"""
        SELECT crl_id
        FROM crl_embeddings
        WHERE embedding_type = '{embedding_type}'
        """
    ).fetchall()
    existing_ids = set(row[0] for row in existing_embeddings)

    # Determine which CRLs need processing
    if regenerate:
        logger.info("⚠️  Regenerating embeddings for ALL CRLs (existing embeddings will be replaced)")
        return all_crls
    elif retry_failed:
        # Find CRLs with embeddings that might have failed (e.g., all zeros)
        crls_to_retry = []
        for crl_data in all_crls:
            if crl_data["crl_id"] in existing_ids:
                # Check if embedding is valid (not all zeros)
                emb = summary_repo.conn.execute(
                    f"""
                    SELECT embedding
                    FROM crl_embeddings
                    WHERE crl_id = ? AND embedding_type = ?
                    LIMIT 1
                    """,
                    [crl_data["crl_id"], embedding_type]
                ).fetchone()

                if emb and emb[0]:
                    # Check if all values are zero (failed embedding)
                    if all(v == 0.0 for v in emb[0]):
                        crls_to_retry.append(crl_data)

        logger.info(f"Found {len(crls_to_retry)} CRLs with failed embeddings to retry")
        return crls_to_retry
    else:
        # Default: only CRLs without embeddings (incremental)
        crls_needing_embeddings = [
            crl_data for crl_data in all_crls
            if crl_data["crl_id"] not in existing_ids
        ]

        logger.info(
            f"✓ Found {len(crls_needing_embeddings)} CRLs without embeddings (incremental mode)"
        )
        return crls_needing_embeddings


async def process_single_embedding(
    crl_data: Dict[str, Any],
    embeddings_service,
    summary_repo: SummaryRepository,
    semaphore: asyncio.Semaphore,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Process a single CRL embedding asynchronously with retry logic.

    Args:
        crl_data: Dict with crl_id, text, and embedding_type
        embeddings_service: Embeddings service
        summary_repo: Summary repository (for storing)
        semaphore: Semaphore to limit concurrent requests
        max_retries: Maximum retry attempts

    Returns:
        Dict with status and details
    """
    crl_id = crl_data["crl_id"]
    text = crl_data["text"]
    embedding_type = crl_data["embedding_type"]

    # Skip CRLs with no text
    if not text or not text.strip():
        return {"status": "skipped", "crl_id": crl_id, "reason": "no text"}

    # Use semaphore to limit concurrent API calls
    async with semaphore:
        for attempt in range(max_retries):
            try:
                # Generate embedding (synchronous call wrapped in executor)
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None,
                    embeddings_service.generate_embedding,
                    text,
                    True  # truncate
                )

                # Validate embedding
                if not embedding or len(embedding) == 0:
                    raise ValueError("Generated embedding is empty")
                if all(v == 0.0 for v in embedding):
                    raise ValueError("Generated embedding is all zeros")

                # Store embedding
                embedding_data = {
                    "id": str(uuid.uuid4()),
                    "crl_id": crl_id,
                    "embedding_type": embedding_type,
                    "embedding": embedding,
                    "model": settings.openai_embedding_model,
                }

                summary_repo.conn.execute(
                    """
                    INSERT INTO crl_embeddings (id, crl_id, embedding_type, embedding, model, generated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    [
                        embedding_data["id"],
                        embedding_data["crl_id"],
                        embedding_data["embedding_type"],
                        embedding_data["embedding"],
                        embedding_data["model"],
                    ]
                )

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


async def generate_embeddings_async(
    crls: List[Dict[str, Any]],
    embeddings_service,
    summary_repo: SummaryRepository,
    batch_size: int = 50,
    max_retries: int = 3
) -> Dict[str, int]:
    """
    Generate and store embeddings for CRLs concurrently.

    Args:
        crls: List of CRL dictionaries
        embeddings_service: Embeddings service
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

    logger.info(f"Starting concurrent embedding generation of {len(crls)} CRLs...")
    logger.info(f"Concurrent API calls: {batch_size}")
    logger.info(f"Max retries per CRL: {max_retries}")

    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(batch_size)

    # Create progress bar if tqdm is available
    if HAS_TQDM:
        pbar = tqdm(total=len(crls), desc="Generating embeddings", unit="CRL")

    # Process all CRLs concurrently
    tasks = [
        process_single_embedding(crl_data, embeddings_service, summary_repo, semaphore, max_retries)
        for crl_data in crls
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
        logger.info(f"\nTo retry failures, run: python generate_embeddings.py --retry-failed")

    return stats


def generate_embeddings(
    crls: List[Dict[str, Any]],
    embeddings_service,
    summary_repo: SummaryRepository,
    batch_size: int = 50,
    max_retries: int = 3,
    sequential: bool = False
) -> Dict[str, int]:
    """
    Generate and store embeddings for CRLs (concurrent or sequential).

    Args:
        crls: List of CRL dictionaries
        embeddings_service: Embeddings service
        summary_repo: Summary repository
        batch_size: Number of concurrent API calls (ignored if sequential=True)
        max_retries: Maximum retry attempts for failed CRLs
        sequential: If True, process one at a time (slower, for debugging)

    Returns:
        Statistics dictionary with success/failure counts
    """
    if sequential:
        logger.info("Running in SEQUENTIAL mode (slower)")
        # Simple sequential implementation for debugging
        stats = {"total": len(crls), "success": 0, "failed": 0, "skipped": 0, "retried": 0}
        for crl_data in crls:
            result = asyncio.run(process_single_embedding(
                crl_data, embeddings_service, summary_repo,
                asyncio.Semaphore(1), max_retries
            ))
            if result["status"] == "success":
                stats["success"] += 1
            elif result["status"] == "failed":
                stats["failed"] += 1
            elif result["status"] == "skipped":
                stats["skipped"] += 1
        return stats
    else:
        logger.info("Running in CONCURRENT mode (faster)")
        return asyncio.run(generate_embeddings_async(
            crls, embeddings_service, summary_repo, batch_size, max_retries
        ))


def main():
    """Main function to generate embeddings."""
    try:
        args = parse_args()

        logger.info("=" * 60)
        logger.info("CRL Embedding Generation Script")
        logger.info("=" * 60)

        # Display mode
        if args['regenerate']:
            logger.info("Mode: REGENERATE (will replace ALL existing embeddings)")
        elif args['retry_failed']:
            logger.info("Mode: RETRY FAILED (only CRLs with empty/failed embeddings)")
        else:
            logger.info("Mode: INCREMENTAL (only new CRLs without embeddings)")

        if args['embed_full_text']:
            logger.info("Embedding: FULL TEXT of CRLs")
        else:
            logger.info("Embedding: SUMMARIES of CRLs")

        logger.info(f"Limit: {args['limit'] or 'No limit'}")
        if args['sequential']:
            logger.info("Processing: Sequential (1 at a time, for debugging)")
        else:
            logger.info(f"Concurrent API calls: {args['batch_size']}")

        # Initialize database
        logger.info("\n[Step 1/3] Initializing database...")
        init_db()
        logger.info("✓ Database initialized")

        # Initialize services and repositories
        from app.services.embeddings import EmbeddingsService
        crl_repo = CRLRepository()
        summary_repo = SummaryRepository()
        embeddings_service = EmbeddingsService(settings)

        # Check OpenAI configuration
        if not settings.openai_api_key:
            logger.error(
                "❌ OpenAI API key not configured. "
                "Please set OPENAI_API_KEY in .env file."
            )
            return 1

        logger.info(f"✓ Using OpenAI model: {settings.openai_embedding_model}")
        if settings.ai_dry_run:
            logger.warning("⚠️  AI_DRY_RUN is enabled - embeddings will be mocked")

        # Get CRLs needing embeddings
        logger.info("\n[Step 2/3] Fetching CRLs needing embeddings...")
        crls = get_crls_needing_embeddings(
            crl_repo,
            summary_repo,
            regenerate=args["regenerate"],
            retry_failed=args["retry_failed"],
            embed_full_text=args["embed_full_text"],
            limit=args["limit"]
        )

        if not crls:
            logger.info("✓ No CRLs need embeddings. All done!")
            return 0

        # Generate embeddings
        logger.info("\n[Step 3/3] Generating embeddings...")
        if not HAS_TQDM:
            logger.warning("⚠️  Install tqdm for progress bars: pip install tqdm")

        stats = generate_embeddings(
            crls,
            embeddings_service,
            summary_repo,
            batch_size=args["batch_size"],
            sequential=args["sequential"]
        )

        # Display results
        logger.info("\n" + "=" * 60)
        logger.info("EMBEDDING GENERATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total CRLs processed:  {stats['total']}")
        logger.info(f"✓ Successful:          {stats['success']}")
        if stats['retried'] > 0:
            logger.info(f"⟳ Retried & succeeded: {stats['retried']}")
        logger.info(f"✗ Failed:              {stats['failed']}")
        logger.info(f"⊘ Skipped (no text):   {stats['skipped']}")

        # Get embedding statistics
        total_embeddings = summary_repo.conn.execute(
            "SELECT COUNT(*) FROM crl_embeddings"
        ).fetchone()[0]

        logger.info(f"\n📊 Total embeddings in database: {total_embeddings}")
        logger.info(f"💾 Database location: {settings.database_path}")

        if stats["failed"] > 0:
            logger.warning(
                f"\n⚠️  {stats['failed']} CRLs failed after retries. "
                "Run with --retry-failed to retry them."
            )
            return 1

        logger.info("\n✓ All embeddings generated successfully!")
        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user. Progress has been saved.")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"\n✗ Embedding generation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
