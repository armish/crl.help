#!/usr/bin/env python3
"""
Utility script to clean up duplicate summaries and embeddings in the database.

This script removes duplicate entries keeping only the most recent one for each CRL.

Usage:
    python cleanup_duplicates.py [options]

Options:
    --dry-run     Show what would be deleted without actually deleting
    --help, -h    Show this help message and exit

Example:
    python cleanup_duplicates.py --dry-run   # Preview changes
    python cleanup_duplicates.py             # Clean up duplicates
"""

import sys
from pathlib import Path

# Check for help first
if "--help" in sys.argv or "-h" in sys.argv:
    print(__doc__)
    sys.exit(0)

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_db, SummaryRepository
from app.utils.logging_config import get_logger, setup_logging

# Setup logging
setup_logging(log_level="INFO", enable_file_logging=True)
logger = get_logger(__name__)


def cleanup_duplicate_summaries(summary_repo: SummaryRepository, dry_run: bool = False):
    """Remove duplicate summaries, keeping only the most recent one per CRL."""

    logger.info("Analyzing crl_summaries table...")

    # Find duplicates
    duplicates = summary_repo.conn.execute("""
        SELECT crl_id, COUNT(*) as count
        FROM crl_summaries
        GROUP BY crl_id
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """).fetchall()

    if not duplicates:
        logger.info("✓ No duplicate summaries found!")
        return 0

    total_crls_with_dupes = len(duplicates)
    total_duplicate_rows = sum(count - 1 for _, count in duplicates)

    logger.warning(f"Found {total_crls_with_dupes} CRLs with duplicate summaries")
    logger.warning(f"Total duplicate rows to remove: {total_duplicate_rows}")

    # Show top 10 worst offenders
    logger.info("\nTop 10 CRLs with most duplicates:")
    for crl_id, count in duplicates[:10]:
        logger.info(f"  {crl_id}: {count} summaries")

    if dry_run:
        logger.info("\n[DRY-RUN] Would delete these duplicates, but not actually doing it.")
        return total_duplicate_rows

    # Delete old duplicates, keeping only the most recent
    logger.info("\nRemoving duplicate summaries (keeping most recent)...")

    deleted_count = summary_repo.conn.execute("""
        DELETE FROM crl_summaries
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (PARTITION BY crl_id ORDER BY generated_at DESC) as rn
                FROM crl_summaries
            )
            WHERE rn > 1
        )
    """).fetchone()[0]

    logger.info(f"✓ Deleted {deleted_count} duplicate summary rows")

    # Verify
    remaining_dupes = summary_repo.conn.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT crl_id
            FROM crl_summaries
            GROUP BY crl_id
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    if remaining_dupes == 0:
        logger.info("✓ All duplicates removed successfully!")
    else:
        logger.warning(f"⚠️  Still have {remaining_dupes} CRLs with duplicates")

    return deleted_count


def cleanup_duplicate_embeddings(summary_repo: SummaryRepository, dry_run: bool = False):
    """Remove duplicate embeddings, keeping only the most recent one per CRL."""

    logger.info("\nAnalyzing crl_embeddings table...")

    # Find duplicates
    duplicates = summary_repo.conn.execute("""
        SELECT crl_id, embedding_type, COUNT(*) as count
        FROM crl_embeddings
        GROUP BY crl_id, embedding_type
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """).fetchall()

    if not duplicates:
        logger.info("✓ No duplicate embeddings found!")
        return 0

    total_duplicate_rows = sum(count - 1 for _, _, count in duplicates)

    logger.warning(f"Found {len(duplicates)} CRL+type combinations with duplicate embeddings")
    logger.warning(f"Total duplicate rows to remove: {total_duplicate_rows}")

    if dry_run:
        logger.info("\n[DRY-RUN] Would delete these duplicates, but not actually doing it.")
        return total_duplicate_rows

    # Delete old duplicates, keeping only the most recent
    logger.info("\nRemoving duplicate embeddings (keeping most recent)...")

    deleted_count = summary_repo.conn.execute("""
        DELETE FROM crl_embeddings
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY crl_id, embedding_type
                           ORDER BY generated_at DESC
                       ) as rn
                FROM crl_embeddings
            )
            WHERE rn > 1
        )
    """).fetchone()[0]

    logger.info(f"✓ Deleted {deleted_count} duplicate embedding rows")

    return deleted_count


def main():
    """Main function."""
    dry_run = "--dry-run" in sys.argv

    logger.info("=" * 60)
    logger.info("Database Cleanup Utility")
    logger.info("=" * 60)

    if dry_run:
        logger.info("Mode: DRY-RUN (no actual changes will be made)")
    else:
        logger.info("Mode: LIVE (will delete duplicates)")

    # Initialize database
    logger.info("\nInitializing database...")
    init_db()
    summary_repo = SummaryRepository()

    # Get initial counts
    total_summaries = summary_repo.conn.execute("SELECT COUNT(*) FROM crl_summaries").fetchone()[0]
    total_embeddings = summary_repo.conn.execute("SELECT COUNT(*) FROM crl_embeddings").fetchone()[0]

    logger.info(f"\nCurrent state:")
    logger.info(f"  Total summaries: {total_summaries}")
    logger.info(f"  Total embeddings: {total_embeddings}")

    # Clean up duplicates
    logger.info("\n" + "=" * 60)
    deleted_summaries = cleanup_duplicate_summaries(summary_repo, dry_run)

    logger.info("\n" + "=" * 60)
    deleted_embeddings = cleanup_duplicate_embeddings(summary_repo, dry_run)

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("CLEANUP COMPLETE")
    logger.info("=" * 60)

    if dry_run:
        logger.info(f"Would delete:")
        logger.info(f"  Duplicate summaries: {deleted_summaries}")
        logger.info(f"  Duplicate embeddings: {deleted_embeddings}")
        logger.info(f"\nRun without --dry-run to actually delete.")
    else:
        logger.info(f"Deleted:")
        logger.info(f"  ✓ Duplicate summaries: {deleted_summaries}")
        logger.info(f"  ✓ Duplicate embeddings: {deleted_embeddings}")

        # Get final counts
        final_summaries = summary_repo.conn.execute("SELECT COUNT(*) FROM crl_summaries").fetchone()[0]
        final_embeddings = summary_repo.conn.execute("SELECT COUNT(*) FROM crl_embeddings").fetchone()[0]

        logger.info(f"\nFinal state:")
        logger.info(f"  Total summaries: {final_summaries} (was {total_summaries})")
        logger.info(f"  Total embeddings: {final_embeddings} (was {total_embeddings})")
        logger.info(f"\n✓ Database cleaned!")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
