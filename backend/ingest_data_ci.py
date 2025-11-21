#!/usr/bin/env python3
"""
CRL Data Ingestion Script (CI/CD Version)

Non-interactive version of ingest_data.py for automated pipelines.
No prompts, no confirmations - just runs the pipeline.

Total estimated time: ~30 minutes
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def log(message: str, level: str = "INFO"):
    """Simple logging function."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def run_script(script_name: str, description: str) -> bool:
    """Run a Python script and handle errors."""
    log(f"Starting: {description}")

    start_time = datetime.now()
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False,
            text=True
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        log(f"Completed: {description} ({elapsed:.1f}s)")
        return True

    except subprocess.CalledProcessError as e:
        log(f"Failed: {script_name} - {str(e)}", "ERROR")
        return False
    except KeyboardInterrupt:
        log("Process interrupted", "WARN")
        return False


def check_environment() -> bool:
    """Check if required environment variables are set."""
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        log(f"Missing required environment variables: {', '.join(missing_vars)}", "ERROR")
        return False

    log("Environment variables configured")
    return True


def cleanup_old_data():
    """Remove old database and raw data files."""
    backend_dir = Path(__file__).parent
    db_path = backend_dir / "data" / "crl_explorer.duckdb"
    raw_dir = backend_dir / "data" / "raw"

    if db_path.exists():
        db_path.unlink()
        log(f"Deleted old database: {db_path}")

    if raw_dir.exists():
        for f in raw_dir.glob("*"):
            if f.is_file():
                f.unlink()
        log(f"Cleaned raw data directory: {raw_dir}")


def main() -> int:
    """Main ingestion pipeline."""
    log("=" * 60)
    log("CRL Data Ingestion Pipeline (CI/CD)")
    log("=" * 60)

    overall_start = datetime.now()

    # Check environment
    if not check_environment():
        return 1

    # Cleanup old data
    log("Cleaning up old data...")
    cleanup_old_data()

    # Define pipeline steps
    steps = [
        ("load_data.py", "Loading CRL data from openFDA API"),
        ("generate_summaries.py", "Generating AI summaries"),
        ("extract_indications.py", "Extracting product indications"),
        ("extract_product_name.py", "Extracting product names"),
        ("classify_crl_reasons.py", "Classifying deficiency reasons"),
        ("classify_crl_tx_category.py", "Classifying therapeutic categories"),
        ("set_last_update.py", "Setting last update timestamp"),
    ]

    # Run each step
    for i, (script, description) in enumerate(steps, start=1):
        log(f"[{i}/{len(steps)}] {description}")
        if not run_script(script, description):
            log(f"Pipeline failed at step {i}", "ERROR")
            return 1

    # Store the hash after successful ingestion
    log("Storing FDA data hash...")
    try:
        result = subprocess.run(
            [sys.executable, "check_for_updates.py", "--store-hash"],
            check=True,
            capture_output=True,
            text=True
        )
        log("Hash stored successfully")
    except subprocess.CalledProcessError as e:
        log(f"Warning: Could not store hash: {e}", "WARN")

    # Success
    total_elapsed = (datetime.now() - overall_start).total_seconds()
    minutes = int(total_elapsed // 60)
    seconds = int(total_elapsed % 60)

    log("=" * 60)
    log(f"Data Ingestion Complete! Total time: {minutes}m {seconds}s")
    log("=" * 60)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("Ingestion cancelled by user", "WARN")
        sys.exit(1)
    except Exception as e:
        log(f"Unexpected error: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
