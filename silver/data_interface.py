"""
Silver-layer data interface.

Provides a single, stable entry-point for loading *prepared* (Silver) data.
All functions are pure Python – no Streamlit dependency – so they work from:
  * Streamlit pages
  * Jupyter notebooks
  * ML training scripts
  * External contractor tooling

Usage example::

    from silver.data_interface import get_silver_lst, get_silver_nida, get_silver_linked

    df = get_silver_linked()
    print(df.head())
"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from silver.minio_client import SILVER_BUCKET, list_objects, read_parquet

# Object-key constants – must match silver/pipeline.py
_SILVER_LST_KEY = "lst/einsatzdaten_silver.parquet"
_SILVER_NIDA_KEY = "nida/index_silver.parquet"
_SILVER_LINKED_KEY = "linked/lst_nida_silver.parquet"

# Opt-in TTL for the in-process LRU cache (seconds).
# Set SILVER_CACHE_TTL=0 in the environment to disable caching.
_CACHE_TTL = int(os.getenv("SILVER_CACHE_TTL", "3600"))


# ---------------------------------------------------------------------------
# Low-level read helpers
# ---------------------------------------------------------------------------


def _read_silver(object_key: str) -> pd.DataFrame:
    """Read a Silver Parquet file, returning an empty DataFrame on failure."""
    df = read_parquet(object_key, bucket=SILVER_BUCKET)
    if df.empty:
        print(
            f"[data_interface] Silver data not found at "
            f"s3://{SILVER_BUCKET}/{object_key}. "
            "Run silver.pipeline.run_pipeline() first."
        )
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_silver_lst(filters: Optional[dict] = None) -> pd.DataFrame:
    """
    Return the cleaned Silver LST (Leitstelle/Dispatch) data.

    Parameters
    ----------
    filters : dict, optional
        Column-based equality filters, e.g.
        ``{"EINSATZMITTELTYP": "Rettungswagen (RTW)"}``.

    Returns
    -------
    pd.DataFrame
        Cleaned LST data ready for analysis.
    """
    df = _read_silver(_SILVER_LST_KEY)
    return _apply_filters(df, filters)


def get_silver_nida(filters: Optional[dict] = None) -> pd.DataFrame:
    """
    Return the cleaned Silver NIDA index data.

    Parameters
    ----------
    filters : dict, optional
        Column-based equality filters.

    Returns
    -------
    pd.DataFrame
        Cleaned NIDA data ready for analysis.
    """
    df = _read_silver(_SILVER_NIDA_KEY)
    return _apply_filters(df, filters)


def get_silver_linked(filters: Optional[dict] = None) -> pd.DataFrame:
    """
    Return the Silver data that links LST and NIDA records.

    This is the primary dataset for contractor analysis and ML applications:
    LST missions are enriched with NIDA protocol attributes so that each row
    represents one mission with dispatch *and* clinical protocol fields.

    Parameters
    ----------
    filters : dict, optional
        Column-based equality filters applied after loading.

    Returns
    -------
    pd.DataFrame
        Linked, cleaned data ready for analysis.
    """
    df = _read_silver(_SILVER_LINKED_KEY)
    return _apply_filters(df, filters)


def query_silver(
    dataset: str,
    filters: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Unified entry-point for loading any Silver dataset by name.

    Parameters
    ----------
    dataset : {"lst", "nida", "linked"}
        Which Silver dataset to load.
    filters : dict, optional
        Column-based equality filters.

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    ValueError
        If *dataset* is not one of the known names.
    """
    _handlers = {
        "lst": get_silver_lst,
        "nida": get_silver_nida,
        "linked": get_silver_linked,
    }
    if dataset not in _handlers:
        raise ValueError(
            f"Unknown Silver dataset '{dataset}'. "
            f"Valid options: {sorted(_handlers.keys())}"
        )
    return _handlers[dataset](filters=filters)


def list_silver_datasets() -> list[str]:
    """Return the object keys of all available Silver Parquet files."""
    return list_objects(prefix="", bucket=SILVER_BUCKET)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_filters(df: pd.DataFrame, filters: Optional[dict]) -> pd.DataFrame:
    """Apply simple equality filters to *df*."""
    if df.empty or not filters:
        return df
    mask = pd.Series(True, index=df.index)
    for col, value in filters.items():
        if col in df.columns:
            if isinstance(value, (list, tuple, set)):
                mask &= df[col].isin(value)
            else:
                mask &= df[col] == value
    return df[mask].reset_index(drop=True)
