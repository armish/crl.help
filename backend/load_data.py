#!/usr/bin/env python3
"""
Script to load FDA CRL data into the database.

Usage:
    python load_data.py [options]

Options:
    --no-cache    Force re-download even if cached data exists
    --help, -h    Show this help message and exit

Example:
    python load_data.py              # Use cached data if available
    python load_data.py --no-cache   # Force fresh download
"""

import asyncio
import sys
from pathlib import Path

# Check for help first
if "--help" in sys.argv or "-h" in sys.argv:
    print(__doc__)
    sys.exit(0)

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import init_db, CRLRepository
from app.services.data_ingestion import fetch_crl_data
from app.services.data_processor import process_crl_data
from app.utils.logging_config import get_logger, setup_logging

# Setup logging
setup_logging(log_level="INFO", enable_file_logging=True)
logger = get_logger(__name__)


async def main():
    """Main function to load CRL data."""
    try:
        # Parse command line arguments
        use_cache = "--no-cache" not in sys.argv

        logger.info("=" * 60)
        logger.info("FDA CRL Data Loading Script")
        logger.info("=" * 60)

        # Step 1: Initialize database
        logger.info("\n[Step 1/3] Initializing database...")
        init_db()
        logger.info("✓ Database initialized")

        # Step 2: Fetch CRL data
        logger.info("\n[Step 2/3] Fetching CRL data...")
        if use_cache:
            logger.info("Using cached data if available")
        else:
            logger.info("Forcing fresh download")

        data = await fetch_crl_data(use_cache=use_cache)
        logger.info(f"✓ Fetched {len(data.get('results', []))} CRL records")

        # Step 3: Process and store CRLs
        logger.info("\n[Step 3/3] Processing and storing CRLs...")
        stats = process_crl_data(data)

        # Display results
        logger.info("\n" + "=" * 60)
        logger.info("DATA LOADING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"New CRLs added:      {stats['new_crls']}")
        logger.info(f"Existing CRLs updated: {stats['updated_crls']}")
        logger.info(f"Failed records:      {stats['failed']}")
        logger.info(f"Total in database:   {stats['total_in_db']}")

        # Get some statistics
        repo = CRLRepository()
        db_stats = repo.get_stats()

        logger.info("\n" + "-" * 60)
        logger.info("DATABASE STATISTICS")
        logger.info("-" * 60)
        logger.info(f"Total CRLs: {db_stats['total_crls']}")

        if db_stats.get('by_status'):
            logger.info("\nBy Approval Status:")
            for status, count in db_stats['by_status'].items():
                logger.info(f"  {status}: {count}")

        if db_stats.get('by_year'):
            logger.info("\nBy Year:")
            for year, count in sorted(db_stats['by_year'].items(), reverse=True):
                logger.info(f"  {year}: {count}")

        logger.info("\n✓ All data loaded successfully!")
        logger.info(f"\nDatabase location: {settings.database_path}")

        return 0

    except Exception as e:
        logger.error(f"\n✗ Data loading failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
