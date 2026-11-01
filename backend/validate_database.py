#!/usr/bin/env python3
"""Release gate: validate a snapshot using the service's DuckDB reader."""

import argparse
import json

from app.snapshot import validate_snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    args = parser.parse_args()
    print(json.dumps(validate_snapshot(args.path), indent=2))
