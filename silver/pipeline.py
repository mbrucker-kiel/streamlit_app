"""
Silver pipeline: reads from live databases -> applies dashboard preparation
logic -> enforces Data Contract schema -> probabilistic matching -> writes
ready-to-query Parquet files to MinIO.

Run once (e.g. daily after the 4 AM Airbyte sync)::

    python -m silver.pipeline

Or call programmatically::

    from silver.pipeline import run_pipeline
    run_pipeline(start_date="2024-01-01", end_date="2025-01-01")

Pipeline steps
--------------
1. Connect to MongoDB; load + prepare NIDA Silver (Index + Details merged,
   same as every Streamlit page).
2. Connect to MariaDB; load + prepare ETU Silver (ETU loader, callsign
   normalisation, Eckpunktevereinbarung filter, Data Contract enforcement).
3. Link ETU <-> NIDA on the shared mission number (simple left join).
4. Probabilistic matching via Splink 4 (ETU <-> NIDA) producing a match
   table with unique_mission_id and match_probability.
5. Write four Silver Parquet files + one JSON lineage record to MinIO.
6. Return metadata dict for caller inspection.

Silver outputs in MinIO (silver bucket)
----------------------------------------
  nida/nida_silver.parquet        Prepared NIDA dataset
  etu/etu_silver.parquet          Prepared ETU dataset (schema validated)
  linked/etu_nida_silver.parquet  ETU left-joined with NIDA
  matches/etu_nida_matches.parquet Splink match table
  metadata/pipeline_run.json      Lineage record with code hashes + row counts
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
from silver.matcher import match_etu_nida
from silver.minio_client import SILVER_BUCKET, ensure_bucket, write_json, write_parquet
from silver.transformers import link_lst_nida, prepare_etu_silver, prepare_nida_silver

# ---------------------------------------------------------------------------
# Object-key constants for Silver outputs
# ---------------------------------------------------------------------------
_SILVER_NIDA_KEY = "nida/nida_silver.parquet"
_SILVER_ETU_KEY = "etu/etu_silver.parquet"
_SILVER_LINKED_KEY = "linked/etu_nida_silver.parquet"
_SILVER_MATCHES_KEY = "matches/etu_nida_matches.parquet"
_SILVER_METADATA_KEY = "metadata/pipeline_run.json"


# ---------------------------------------------------------------------------
# Lineage helpers
# ---------------------------------------------------------------------------


def _source_hash(func) -> str:
    """Return a 20-char SHA-256 digest of a function's source code.

    Stored in the pipeline metadata so contractors can verify which exact
    version of the cleaning code produced the Silver files.  20 hex chars
    (80 bits) gives negligible collision probability for a small set of
    tracked functions while remaining compact in the JSON output.
    """
    src = inspect.getsource(func)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:20]


def build_metadata(
    nida_rows: int,
    etu_rows: int,
    linked_rows: int,
    matches_rows: int,
    start_date: Optional[str],
    end_date: Optional[str],
) -> dict:
    """Compile a lineage/metadata dict describing this pipeline run."""
    from silver import transformers  # local import avoids circular reference

    return {
        "pipeline_version": "3.0.0",
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
            "matches": matches_rows,
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
    match_threshold: float = 0.7,
) -> dict:
    """
    Execute the full database -> Silver pipeline.

    Parameters
    ----------
    start_date : str or datetime-like, optional
        Lower bound for the Eckpunktevereinbarung filter (ALARMIERT,
        format YYYY-MM-DD).  Defaults to the SILVER_START_DATE env var.
    end_date : str or datetime-like, optional
        Upper bound (exclusive).  Defaults to SILVER_END_DATE env var.
    match_threshold : float
        Minimum match_probability for the Splink match table (default 0.7).

    Returns
    -------
    dict
        The lineage metadata dict that was written to MinIO.
    """
    start_date = start_date or os.getenv("SILVER_START_DATE") or None
    end_date = end_date or os.getenv("SILVER_END_DATE") or None

    print("[pipeline] Starting database -> Silver pipeline ...")
    ensure_bucket(SILVER_BUCKET)

    # ------------------------------------------------------------------
    # 1. Prepare NIDA Silver  (Index + Details merged, same as all pages)
    # ------------------------------------------------------------------
    print("[pipeline] Connecting to MongoDB ...")
    db, mongo_client = get_mongodb_connection()
    try:
        df_nida_silver = prepare_nida_silver(db)
    finally:
        close_mongodb_connection(mongo_client)

    # ------------------------------------------------------------------
    # 2. Prepare ETU Silver  (loader + callsign norm + schema validation)
    # ------------------------------------------------------------------
    print("[pipeline] Connecting to MariaDB ...")
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
    # 3. Deterministic left-join: ETU enriched with NIDA attributes
    # ------------------------------------------------------------------
    print("[pipeline] Linking ETU <-> NIDA (deterministic join) ...")
    df_linked = link_lst_nida(df_etu_silver, df_nida_silver)

    # ------------------------------------------------------------------
    # 4. Probabilistic matching (Splink): ETU <-> NIDA match table
    # ------------------------------------------------------------------
    print("[pipeline] Running Splink probabilistic matching ...")
    df_matches = match_etu_nida(
        df_etu_silver, df_nida_silver, threshold=match_threshold
    )

    # ------------------------------------------------------------------
    # 5. Write Silver Parquet files
    # ------------------------------------------------------------------
    print(f"[pipeline] Writing NIDA Silver  ({len(df_nida_silver)} rows) ...")
    write_parquet(df_nida_silver, _SILVER_NIDA_KEY)

    print(f"[pipeline] Writing ETU Silver   ({len(df_etu_silver)} rows) ...")
    write_parquet(df_etu_silver, _SILVER_ETU_KEY)

    print(f"[pipeline] Writing Linked       ({len(df_linked)} rows) ...")
    write_parquet(df_linked, _SILVER_LINKED_KEY)

    print(f"[pipeline] Writing Match table  ({len(df_matches)} rows) ...")
    write_parquet(df_matches, _SILVER_MATCHES_KEY)

    # ------------------------------------------------------------------
    # 6. Write pipeline lineage metadata
    # ------------------------------------------------------------------
    metadata = build_metadata(
        nida_rows=len(df_nida_silver),
        etu_rows=len(df_etu_silver),
        linked_rows=len(df_linked),
        matches_rows=len(df_matches),
        start_date=start_date,
        end_date=end_date,
    )
    write_json(metadata, _SILVER_METADATA_KEY)

    print("[pipeline] Done.")
    return metadata


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the database -> Silver data pipeline."
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
    parser.add_argument(
        "--match-threshold",
        type=float,
        default=0.7,
        help="Minimum Splink match_probability to include (default: 0.7).",
    )
    args = parser.parse_args()
    run_pipeline(
        start_date=args.start_date,
        end_date=args.end_date,
        match_threshold=args.match_threshold,
    )
