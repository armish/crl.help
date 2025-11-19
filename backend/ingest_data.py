#!/usr/bin/env python3
"""
CRL Data Ingestion Script

This script automates the complete data ingestion pipeline for the CRL Explorer.
It handles downloading FDA data, generating AI summaries, and enriching the database.

Total estimated time: ~30 minutes
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(message):
    """Print a formatted header message"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.ENDC}\n")


def print_step(step_num, total_steps, message):
    """Print a formatted step message"""
    print(f"{Colors.CYAN}{Colors.BOLD}[Step {step_num}/{total_steps}]{Colors.ENDC} {message}")


def print_success(message):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")


def print_error(message):
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.ENDC}")


def print_warning(message):
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.ENDC}")


def print_info(message):
    """Print an info message"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.ENDC}")


def confirm(message, default=False):
    """Ask user for confirmation"""
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        response = input(f"{Colors.YELLOW}{message}{suffix}{Colors.ENDC}").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print_warning("Please answer 'y' or 'n'")


def run_script(script_name, description, estimated_time):
    """Run a Python script and handle errors"""
    print_info(f"{description} (estimated: {estimated_time})")

    start_time = datetime.now()
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False,
            text=True
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        print_success(f"Completed in {elapsed:.1f}s")
        return True

    except subprocess.CalledProcessError as e:
        print_error(f"Failed to run {script_name}")
        print_error(f"Error: {str(e)}")
        return False
    except KeyboardInterrupt:
        print_warning("\nProcess interrupted by user")
        return False


def check_environment():
    """Check if required environment variables are set"""
    print_step(0, 7, "Checking environment...")

    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print_error(f"Missing required environment variables: {', '.join(missing_vars)}")
        print_info("Please set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}=your_api_key")
        return False

    print_success("Environment variables configured")
    return True


def cleanup_old_data():
    """Remove old database and raw data files"""
    backend_dir = Path(__file__).parent
    db_path = backend_dir / "data" / "crl_explorer.duckdb"
    raw_dir = backend_dir / "data" / "raw"

    files_to_delete = []

    if db_path.exists():
        files_to_delete.append(str(db_path))

    if raw_dir.exists():
        raw_files = list(raw_dir.glob("*"))
        files_to_delete.extend([str(f) for f in raw_files if f.is_file()])

    if not files_to_delete:
        print_info("No old data files found to clean up")
        return True

    print_warning("The following files will be deleted:")
    for f in files_to_delete:
        print(f"  - {f}")

    if not confirm("Delete these files?", default=False):
        print_info("Cleanup cancelled. Exiting.")
        return False

    # Delete files
    if db_path.exists():
        db_path.unlink()
        print_success(f"Deleted {db_path}")

    if raw_dir.exists():
        for f in raw_dir.glob("*"):
            if f.is_file():
                f.unlink()
        print_success(f"Deleted {len(raw_files)} files from {raw_dir}")

    return True


def main():
    """Main ingestion pipeline"""
    print_header("CRL Data Ingestion Pipeline")
    print_info("This process will:")
    print("  1. Download FDA CRL data from openFDA API")
    print("  2. Generate AI-powered summaries")
    print("  3. Extract product indications")
    print("  4. Extract product names")
    print("  5. Classify deficiency reasons")
    print("  6. Classify therapeutic categories")
    print("  7. Update last data refresh timestamp")
    print()
    print_warning("Estimated total time: ~30 minutes")
    print()

    if not confirm("Continue with data ingestion?", default=True):
        print_info("Ingestion cancelled")
        return 1

    # Check environment
    if not check_environment():
        return 1

    # Cleanup old data
    print_step(1, 7, "Cleaning up old data...")
    if not cleanup_old_data():
        return 1

    # Define pipeline steps
    steps = [
        ("load_data.py", "Loading CRL data from openFDA API", "~2 minutes"),
        ("generate_summaries.py", "Generating AI summaries", "~15 minutes"),
        ("extract_indications.py", "Extracting product indications", "~5 minutes"),
        ("extract_product_name.py", "Extracting product names", "~3 minutes"),
        ("classify_crl_reasons.py", "Classifying deficiency reasons", "~3 minutes"),
        ("classify_crl_tx_category.py", "Classifying therapeutic categories", "~3 minutes"),
        ("set_last_update.py", "Setting last update timestamp", "<1 minute"),
    ]

    overall_start = datetime.now()

    # Run each step
    for i, (script, description, est_time) in enumerate(steps, start=2):
        print_step(i, 7, description)
        if not run_script(script, description, est_time):
            print_error(f"\nPipeline failed at step {i}")
            return 1
        print()

    # Success
    total_elapsed = (datetime.now() - overall_start).total_seconds()
    minutes = int(total_elapsed // 60)
    seconds = int(total_elapsed % 60)

    print_header("Data Ingestion Complete!")
    print_success(f"Total time: {minutes}m {seconds}s")
    print_info("The CRL database is now ready to use")
    print_info("You can start the backend server with: python -m uvicorn app.main:app --reload")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_warning("\n\nIngestion cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
