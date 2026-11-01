#!/usr/bin/env python3
"""Wait for production to serve the published snapshot, not just HTTP 200."""

import argparse
import time

import httpx

from app.snapshot import validate_snapshot


def deployment_matches(client: httpx.Client, expected: dict) -> bool:
    health = client.get("/health")
    health.raise_for_status()
    data = health.json()
    if data.get("status") != "healthy" or any(
        data.get(key) != expected[key]
        for key in ("total_crls", "total_summaries", "last_data_update")
    ):
        return False
    listing = client.get("/api/crls", params={"limit": 1})
    listing.raise_for_status()
    data = listing.json()
    return data.get("total") == expected["total_crls"] and bool(data.get("items"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()
    expected = validate_snapshot(args.snapshot)
    deadline = time.monotonic() + args.timeout
    with httpx.Client(base_url=args.url, timeout=20, follow_redirects=True) as client:
        while time.monotonic() < deadline:
            try:
                if deployment_matches(client, expected):
                    print(f"Deployment verified: {expected}", flush=True)
                    return
            except (httpx.HTTPError, ValueError) as exc:
                print(f"Waiting for deployment ({type(exc).__name__})", flush=True)
            time.sleep(15)
    raise SystemExit("Deployment did not serve the expected nonempty snapshot before timeout")


if __name__ == "__main__":
    main()
