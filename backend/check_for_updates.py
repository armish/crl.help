#!/usr/bin/env python3
"""
FDA Data Update Checker

Checks if FDA CRL data has changed since the last ingestion.
Used by GitHub Actions to determine if a full pipeline run is needed.

Exit codes:
  0 - Data has changed (or first run), pipeline should run
  1 - No changes detected, pipeline can be skipped
  2 - Error occurred
"""

import sys
import hashlib
import json
from pathlib import Path

import httpx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import get_db, init_db, MetadataRepository
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Metadata keys
LAST_FDA_HASH_KEY = "last_fda_data_hash"
LAST_FDA_UPDATE_KEY = "last_fda_last_updated"


def compute_file_hash(content: bytes) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content).hexdigest()


async def fetch_fda_metadata() -> tuple[str, str | None]:
    """
    Fetch FDA data and compute hash.

    Returns:
        Tuple of (content_hash, last_updated_from_meta)
    """
    url = settings.fda_json_url
    logger.info(f"Fetching FDA data from {url}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

        content = response.content
        content_hash = compute_file_hash(content)

        # Try to extract last_updated from meta
        last_updated = None
        try:
            import zipfile
            import io
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                json_files = [f for f in zf.namelist() if f.endswith('.json')]
                if json_files:
                    with zf.open(json_files[0]) as jf:
                        data = json.load(jf)
                        last_updated = data.get('meta', {}).get('last_updated')
        except Exception as e:
            logger.warning(f"Could not extract last_updated from FDA data: {e}")

        return content_hash, last_updated


def get_stored_metadata() -> tuple[str | None, str | None]:
    """
    Get previously stored FDA data hash and last_updated.

    Returns:
        Tuple of (stored_hash, stored_last_updated)
    """
    try:
        metadata_repo = MetadataRepository()
        stored_hash = metadata_repo.get(LAST_FDA_HASH_KEY)
        stored_last_updated = metadata_repo.get(LAST_FDA_UPDATE_KEY)
        return stored_hash, stored_last_updated
    except Exception as e:
        logger.warning(f"Could not read stored metadata: {e}")
        return None, None


def store_metadata(content_hash: str, last_updated: str | None) -> None:
    """Store FDA data hash and last_updated in database."""
    try:
        metadata_repo = MetadataRepository()
        metadata_repo.set(LAST_FDA_HASH_KEY, content_hash)
        if last_updated:
            metadata_repo.set(LAST_FDA_UPDATE_KEY, last_updated)
        logger.info(f"Stored metadata: hash={content_hash[:16]}..., last_updated={last_updated}")
    except Exception as e:
        logger.warning(f"Could not store metadata: {e}")


async def check_for_updates() -> bool:
    """
    Check if FDA data has changed.

    Returns:
        True if data has changed (or first run), False if no changes
    """
    # Initialize database if needed
    init_db()

    # Fetch current FDA data hash
    current_hash, current_last_updated = await fetch_fda_metadata()
    logger.info(f"Current FDA data: hash={current_hash[:16]}..., last_updated={current_last_updated}")

    # Get stored metadata
    stored_hash, stored_last_updated = get_stored_metadata()

    if stored_hash is None:
        logger.info("No previous data hash found - this is the first run")
        return True

    logger.info(f"Stored FDA data: hash={stored_hash[:16]}..., last_updated={stored_last_updated}")

    # Compare hashes
    if current_hash != stored_hash:
        logger.info("FDA data has CHANGED! Full pipeline run needed.")
        return True
    else:
        logger.info("FDA data has NOT changed. No update needed.")
        return False


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Check if FDA CRL data has changed")
    parser.add_argument(
        "--store-hash",
        action="store_true",
        help="Store the current hash after checking (use after successful pipeline run)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force return 'changed' status regardless of actual check"
    )
    args = parser.parse_args()

    try:
        if args.force:
            print("FORCE mode: Reporting data as changed")
            sys.exit(0)

        has_changed = await check_for_updates()

        if args.store_hash:
            # Re-fetch to store (or we could cache from check)
            current_hash, current_last_updated = await fetch_fda_metadata()
            store_metadata(current_hash, current_last_updated)
            print(f"Stored hash: {current_hash[:16]}...")

        if has_changed:
            print("STATUS: DATA_CHANGED")
            sys.exit(0)  # Changed - run pipeline
        else:
            print("STATUS: NO_CHANGE")
            sys.exit(1)  # No change - skip pipeline

    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
        print(f"ERROR: {e}")
        sys.exit(2)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
