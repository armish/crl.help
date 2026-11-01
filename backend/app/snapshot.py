"""Validate a self-contained database snapshot without creating or changing it."""

from pathlib import Path

import duckdb


def validate_snapshot(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Database snapshot is missing or empty: {path}")
    wal = Path(f"{path}.wal")
    if wal.exists() and wal.stat().st_size:
        raise ValueError(f"Database snapshot has an uncheckpointed WAL: {wal}")

    # Use the same DuckDB version as the service, in read-only mode. A missing
    # file must never be turned into an empty database by the validator.
    with duckdb.connect(str(path), read_only=True) as conn:
        # Bind all fields used by the listing before accepting the snapshot.
        conn.execute("""
            SELECT id, application_number, letter_date, letter_year, letter_type,
                   approval_status, company_name, text, therapeutic_category,
                   product_name, indications, deficiency_reason
            FROM main.crls LIMIT 0
        """)
        crls = conn.execute("SELECT count(*) FROM main.crls").fetchone()[0]
        summaries = conn.execute("""
            SELECT count(DISTINCT s.crl_id)
            FROM main.crl_summaries s JOIN main.crls c ON c.id = s.crl_id
            WHERE length(trim(s.summary)) > 0
        """).fetchone()[0]
        updated = conn.execute("""
            SELECT value FROM main.processing_metadata
            WHERE key = 'last_data_update'
        """).fetchone()
        if not crls or not summaries:
            raise ValueError(f"Database has no usable data: {crls} CRLs, {summaries} summaries")
        if not updated or not updated[0]:
            raise ValueError("Database has no last_data_update metadata")
        return {"total_crls": crls, "total_summaries": summaries,
                "last_data_update": updated[0], "duckdb_version": duckdb.__version__}
