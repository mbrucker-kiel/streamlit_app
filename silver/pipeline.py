"""
Silver pipeline: reads from live databases → applies dashboard preparation logic
→ writes ready-to-query Parquet files to MinIO.

Run once (e.g. daily, via cron/scheduler) so that all downstream consumers
(contractors, ML pipelines, Streamlit pages) can query the Silver layer
without re-running any transformation::

    python -m silver.pipeline

Or call :func:`run_pipeline` programmatically::

    from silver.pipeline import run_pipeline
    run_pipeline(start_date="2024-01-01", end_date="2025-01-01")

Pipeline steps
--------------
1. Connect to MongoDB and load NIDA data (Index + Details) using the same
   ``LOADERS`` the Streamlit dashboard uses.
2. Connect to MariaDB and load ETU/LST data using the same loader.
3. Apply all preparation logic via :mod:`silver.transformers`:
   - Index + Details merged on ``protocolId`` (as every page does)
   - ETU callsign normalisation + Eckpunktevereinbarung filter
   - Deduplication + PII masking
4. Link ETU ↔ NIDA on the shared mission number.
5. Write three Silver Parquet files plus a JSON metadata record to MinIO.
"""

import hashlib
import inspect
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from db_connection import (
    close_mariadb_connection,
    close_mongodb_connection,
    get_mariadb_connection,
    get_mongodb_connection,
)
from silver.minio_client import SILVER_BUCKET, ensure_bucket, write_json, write_parquet
from silver.transformers import link_lst_nida, prepare_etu_silver, prepare_nida_silver

# ---------------------------------------------------------------------------
# Object-key patterns for Silver outputs
# ---------------------------------------------------------------------------
_SILVER_NIDA_KEY = "nida/nida_silver.parquet"
_SILVER_ETU_KEY = "etu/etu_silver.parquet"
_SILVER_LINKED_KEY = "linked/etu_nida_silver.parquet"
_SILVER_METADATA_KEY = "metadata/pipeline_run.json"


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------


def _source_hash(func) -> str:
    """Return a short SHA-256 digest of a function's source code."""
    src = inspect.getsource(func)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:12]


def build_metadata(
    nida_rows: int,
    etu_rows: int,
    linked_rows: int,
    start_date: Optional[str],
    end_date: Optional[str],
) -> dict:
    """Compile a metadata dict describing this pipeline run."""
    from silver import transformers  # local import avoids circular reference

    return {
        "pipeline_version": "2.0.0",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "parameters": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "output_rows": {
            "nida_silver": nida_rows,
            "etu_silver": etu_rows,
            "linked_silver": linked_rows,
        },
        "source_hashes": {
            "prepare_nida_silver": _source_hash(transformers.prepare_nida_silver),
            "prepare_etu_silver": _source_hash(transformers.prepare_etu_silver),
            "link_lst_nida": _source_hash(transformers.link_lst_nida),
            "mask_pii": _source_hash(transformers.mask_pii),
        },
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_pipeline(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """
    Execute the full database → Silver pipeline.

    Parameters
    ----------
    start_date : str or datetime-like, optional
        Lower bound for the Eckpunktevereinbarung filter applied to ETU data
        (``ALARMIERT`` column, format ``YYYY-MM-DD``).  Defaults to the value
        of the ``SILVER_START_DATE`` environment variable; if that is also
        absent the full ETU date range is kept (deduplication still applies).
    end_date : str or datetime-like, optional
        Upper bound (exclusive).  Defaults to ``SILVER_END_DATE`` env var.

    Returns
    -------
    dict
        The metadata dict written alongside the Silver files.
    """
    start_date = start_date or os.getenv("SILVER_START_DATE") or None
    end_date = end_date or os.getenv("SILVER_END_DATE") or None

    print("[pipeline] Starting database → Silver pipeline …")
    ensure_bucket(SILVER_BUCKET)

    # ------------------------------------------------------------------
    # 1. Prepare NIDA Silver  (Index + Details merged, same as all pages)
    # ------------------------------------------------------------------
    print("[pipeline] Connecting to MongoDB …")
    db, mongo_client = get_mongodb_connection()
    try:
        df_nida_silver = prepare_nida_silver(db)
    finally:
        close_mongodb_connection(mongo_client)

    # ------------------------------------------------------------------
    # 2. Prepare ETU Silver  (ETÜ loader + callsign norm + filter)
    # ------------------------------------------------------------------
    print("[pipeline] Connecting to MariaDB …")
    mariadb_conn = get_mariadb_connection()
    try:
        df_etu_silver = prepare_etu_silver(
            mariadb_conn,
            start_date=start_date,
            end_date=end_date,
        )
    finally:
        close_mariadb_connection(mariadb_conn)

    # ------------------------------------------------------------------
    # 3. Link ETU ↔ NIDA
    # ------------------------------------------------------------------
    print("[pipeline] Linking ETU ↔ NIDA …")
    df_linked = link_lst_nida(df_etu_silver, df_nida_silver)

    # ------------------------------------------------------------------
    # 4. Write Silver Parquet files
    # ------------------------------------------------------------------
    print(f"[pipeline] Writing NIDA Silver  ({len(df_nida_silver)} rows) …")
    write_parquet(df_nida_silver, _SILVER_NIDA_KEY)

    print(f"[pipeline] Writing ETU Silver   ({len(df_etu_silver)} rows) …")
    write_parquet(df_etu_silver, _SILVER_ETU_KEY)

    print(f"[pipeline] Writing Linked       ({len(df_linked)} rows) …")
    write_parquet(df_linked, _SILVER_LINKED_KEY)

    # ------------------------------------------------------------------
    # 5. Write pipeline metadata
    # ------------------------------------------------------------------
    metadata = build_metadata(
        nida_rows=len(df_nida_silver),
        etu_rows=len(df_etu_silver),
        linked_rows=len(df_linked),
        start_date=start_date,
        end_date=end_date,
    )
    write_json(metadata, _SILVER_METADATA_KEY)

    print("[pipeline] Done ✓")
    return metadata


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the database → Silver data pipeline."
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Start date for the Eckpunktevereinbarung filter (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="End date for the filter (YYYY-MM-DD, exclusive).",
    )
    args = parser.parse_args()
    run_pipeline(start_date=args.start_date, end_date=args.end_date)
