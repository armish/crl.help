#!/usr/bin/env python3
"""Download and validate a database before starting the service."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from app.snapshot import validate_snapshot


def prepare_database(database_path: str, database_url: str = "") -> dict:
    destination = Path(database_path)
    if not database_url:
        return validate_snapshot(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    # Stage beside the destination so replacement is atomic, even on a volume.
    fd, temporary = tempfile.mkstemp(prefix=".crl-download-", suffix=".duckdb",
                                     dir=destination.parent)
    os.close(fd)
    staging = Path(temporary)
    try:
        # Retry HTTP errors too: the mutable data-latest asset can briefly be
        # unavailable while GitHub replaces it. Never download over good data.
        subprocess.run([
            "curl", "--fail", "--location", "--silent", "--show-error",
            "--retry", "5", "--retry-all-errors", "--retry-delay", "2",
            "--connect-timeout", "15", "--max-time", "180",
            "--output", str(staging), database_url,
        ], check=True)
        report = validate_snapshot(staging)
        # Never replace a database with pending writes from another process.
        if Path(f"{destination}.wal").exists():
            raise ValueError(f"Refusing to replace database with an existing WAL: {destination}")
        staging.chmod(0o644)
        staging.replace(destination)
        return report
    finally:
        staging.unlink(missing_ok=True)


def main() -> int:
    try:
        report = prepare_database(
            os.environ["DATABASE_PATH"], os.environ.get("DATABASE_URL", "")
        )
    except Exception as exc:
        # CalledProcessError contains the command, including potentially secret
        # URL parameters. Report the exit status without echoing the URL.
        reason = (f"download failed (curl exit {exc.returncode})"
                  if isinstance(exc, subprocess.CalledProcessError) else str(exc))
        print(f"Database preparation failed: {reason}. Refusing to start.", file=sys.stderr)
        return 1
    path = Path(os.environ["DATABASE_PATH"]).resolve()
    print(f"Database ready at {path}: {json.dumps(report)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
