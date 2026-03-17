"""
Silver pipeline: Bronze → Silver.

Run this module as a script to execute the full pipeline::

    python -m silver.pipeline

Or import and call :func:`run_pipeline` from another Python process.

The pipeline:
1. Reads raw Bronze Parquet from MinIO (LST + NIDA).
2. Cleans / normalises / links both datasets using :mod:`silver.transformers`.
3. Writes Silver Parquet back to MinIO.
4. Writes a JSON metadata file alongside the data so contractors can trace
   exactly which code version produced the Silver files.
"""

import hashlib
import inspect
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from silver.bronze_reader import (
    read_bronze_lst,
    read_bronze_nida_index,
)
from silver.minio_client import SILVER_BUCKET, ensure_bucket, write_json, write_parquet
from silver.transformers import clean_lst, clean_nida, link_lst_nida

# ---------------------------------------------------------------------------
# Object-key patterns for Silver outputs
# ---------------------------------------------------------------------------
_SILVER_LST_KEY = "lst/einsatzdaten_silver.parquet"
_SILVER_NIDA_KEY = "nida/index_silver.parquet"
_SILVER_LINKED_KEY = "linked/lst_nida_silver.parquet"
_SILVER_METADATA_KEY = "metadata/pipeline_run.json"


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------


def _source_hash(func) -> str:
    """Return a short SHA-256 digest of a function's source code."""
    src = inspect.getsource(func)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:12]


def build_metadata(
    lst_rows: int,
    nida_rows: int,
    linked_rows: int,
    start_date: Optional[str],
    end_date: Optional[str],
) -> dict:
    """Compile a metadata dict describing this pipeline run."""
    from silver import transformers  # local import avoids circular reference

    return {
        "pipeline_version": "1.0.0",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "parameters": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "output_rows": {
            "lst_silver": lst_rows,
            "nida_silver": nida_rows,
            "linked_silver": linked_rows,
        },
        "source_hashes": {
            "clean_lst": _source_hash(transformers.clean_lst),
            "clean_nida": _source_hash(transformers.clean_nida),
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
    Execute the full Bronze → Silver pipeline.

    Parameters
    ----------
    start_date : str or datetime-like, optional
        Lower bound for the Eckpunktevereinbarung filter applied to LST data.
        Defaults to the value of the ``SILVER_START_DATE`` environment
        variable; if that is also absent no date filter is applied.
    end_date : str or datetime-like, optional
        Upper bound (exclusive).  Defaults to ``SILVER_END_DATE`` env var.

    Returns
    -------
    dict
        The metadata dict written alongside the Silver files.
    """
    start_date = start_date or os.getenv("SILVER_START_DATE")
    end_date = end_date or os.getenv("SILVER_END_DATE")

    print("[pipeline] Starting Bronze → Silver pipeline …")
    ensure_bucket(SILVER_BUCKET)

    # ------------------------------------------------------------------
    # 1. Read Bronze
    # ------------------------------------------------------------------
    print("[pipeline] Reading Bronze LST …")
    df_lst_bronze = read_bronze_lst()

    print("[pipeline] Reading Bronze NIDA index …")
    df_nida_bronze = read_bronze_nida_index()

    # ------------------------------------------------------------------
    # 2. Transform
    # ------------------------------------------------------------------
    print("[pipeline] Cleaning LST …")
    df_lst_silver = clean_lst(df_lst_bronze, start_date=start_date, end_date=end_date)

    print("[pipeline] Cleaning NIDA …")
    df_nida_silver = clean_nida(df_nida_bronze)

    print("[pipeline] Linking LST ↔ NIDA …")
    df_linked = link_lst_nida(df_lst_silver, df_nida_silver)

    # ------------------------------------------------------------------
    # 3. Write Silver Parquet
    # ------------------------------------------------------------------
    print(f"[pipeline] Writing Silver LST  ({len(df_lst_silver)} rows) …")
    write_parquet(df_lst_silver, _SILVER_LST_KEY)

    print(f"[pipeline] Writing Silver NIDA ({len(df_nida_silver)} rows) …")
    write_parquet(df_nida_silver, _SILVER_NIDA_KEY)

    print(f"[pipeline] Writing Linked      ({len(df_linked)} rows) …")
    write_parquet(df_linked, _SILVER_LINKED_KEY)

    # ------------------------------------------------------------------
    # 4. Write metadata
    # ------------------------------------------------------------------
    metadata = build_metadata(
        lst_rows=len(df_lst_silver),
        nida_rows=len(df_nida_silver),
        linked_rows=len(df_linked),
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
        description="Run the Bronze → Silver data pipeline."
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
