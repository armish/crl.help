#!/usr/bin/env python3
"""Compare two CRL database snapshots and list new additions."""

import argparse
import re
import sys
import urllib.parse

import duckdb


def slugify(text):
    if not text:
        return ""
    s = text.lower().strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^\w\-]+", "", s)
    s = re.sub(r"\-\-+", "-", s)
    s = s.strip("-")
    return s


def get_url(crl):
    parts = []
    if crl["letter_type"]:
        parts.append(slugify(crl["letter_type"]))
    if crl.get("application_type"):
        parts.append(slugify(crl["application_type"]))
    if crl["company_name"]:
        parts.append(slugify(crl["company_name"]))
    if crl["therapeutic_category"]:
        parts.append(slugify(crl["therapeutic_category"]))
    slug = "-".join(p for p in parts if p)
    encoded_id = urllib.parse.quote(crl["id"], safe="")
    if slug:
        return f"https://crl.help/crl/{encoded_id}/{slug}"
    return f"https://crl.help/crl/{encoded_id}"


def compare(old_path, new_path):
    old_db = duckdb.connect(old_path, read_only=True)
    new_db = duckdb.connect(new_path, read_only=True)

    old_ids = set(r[0] for r in old_db.execute("SELECT id FROM crls").fetchall())
    new_ids = set(r[0] for r in new_db.execute("SELECT id FROM crls").fetchall())

    old_count = len(old_ids)
    new_count = len(new_ids)
    added_ids = new_ids - old_ids
    removed_ids = old_ids - new_ids

    print(f"Old snapshot: {old_count} entries ({old_path})")
    print(f"New snapshot: {new_count} entries ({new_path})")
    print(f"Added: {len(added_ids)} | Removed: {len(removed_ids)}")
    print()

    if not added_ids:
        print("No new additions found.")
        old_db.close()
        new_db.close()
        return

    placeholders = ",".join(f"'{x}'" for x in added_ids)
    rows = new_db.execute(f"""
        SELECT id, application_number, letter_date, letter_type,
               company_name, product_name, deficiency_reason, therapeutic_category
        FROM crls
        WHERE id IN ({placeholders})
        ORDER BY letter_date ASC
    """).fetchall()

    print(f"=== New additions ({len(rows)}) ===\n")
    for r in rows:
        crl_id, app_nums, letter_date, letter_type, company, product, reason, category = r
        app = app_nums[0] if app_nums else "Unknown"
        product = product or "Unknown"
        reason = reason or "unknown"
        reason_short = reason.lower().replace(" / ", "/").rstrip("/")
        date_str = letter_date.strftime("%-m/%-d/%Y") if letter_date else "Unknown"

        url = get_url({
            "id": crl_id,
            "letter_type": letter_type,
            "application_type": None,
            "company_name": company,
            "therapeutic_category": category,
        })

        if product and product != "Unknown":
            print(f"- **{date_str} — {app}**: {company} - {product} ({reason_short}) {url}")
        else:
            print(f"- **{date_str} — {app}**: {company} ({reason_short}) {url}")
        print()

    old_db.close()
    new_db.close()


def main():
    parser = argparse.ArgumentParser(description="Compare two CRL database snapshots and list new additions.")
    parser.add_argument("old", help="Path to the older database snapshot")
    parser.add_argument("new", help="Path to the newer database snapshot")
    args = parser.parse_args()
    compare(args.old, args.new)


if __name__ == "__main__":
    main()
