#!/usr/bin/env python3
"""
Helper script to manually set the last_data_update metadata.

Usage:
    python set_last_update.py [YYYY-MM-DD]

If no date is provided, uses today's date.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import MetadataRepository, init_db


def main():
    # Get date from command line or use today
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        # Validate date format
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"Error: Invalid date format '{date_str}'. Please use YYYY-MM-DD format.")
            return 1
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    try:
        # Initialize database (if needed)
        init_db()

        # Set the metadata
        repo = MetadataRepository()
        repo.set("last_data_update", date_str)

        print(f"✓ Set last_data_update to {date_str}")
        print(f"Current value: {repo.get('last_data_update')}")

        return 0

    except Exception as e:
        print(f"✗ Failed to set metadata: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
