"""
Silver-layer data interface.

Provides a single, stable entry-point for loading *prepared* (Silver) data.
All functions are pure Python – no Streamlit dependency – so they work from:
  * Streamlit pages
  * Jupyter notebooks
  * ML training scripts
  * External contractor tooling

Usage example::

    from silver.data_interface import get_silver_etu, get_silver_nida, get_silver_linked

    # All ETU missions filtered to only RTW vehicles
    df = get_silver_etu(filters={"EINSATZMITTELTYP": "Rettungswagen (RTW)"})

    # Fully linked ETU + NIDA dataset (primary dataset for analysis)
    df = get_silver_linked()

    # Generic entry-point
    df = query_silver("linked")
"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from silver.minio_client import SILVER_BUCKET, list_objects, read_parquet

# Object keys – must stay in sync with silver/pipeline.py
_SILVER_NIDA_KEY = "nida/nida_silver.parquet"
_SILVER_ETU_KEY = "etu/etu_silver.parquet"
_SILVER_LINKED_KEY = "linked/etu_nida_silver.parquet"

_CACHE_TTL = int(os.getenv("SILVER_CACHE_TTL", "3600"))


# ---------------------------------------------------------------------------
# Low-level read helper
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


def get_silver_etu(filters: Optional[dict] = None) -> pd.DataFrame:
    """
    Return the prepared Silver ETU/LST (Leitstelle/Dispatch) dataset.

    This is the output of :func:`~silver.transformers.prepare_etu_silver`:
    all ETU records with normalised callsigns, optional Eckpunktevereinbarung
    filter applied, deduplicated on ``EINSATZ_NR``, and PII masked.

    Parameters
    ----------
    filters : dict, optional
        Column-based equality filters, e.g.
        ``{"EINSATZMITTELTYP": "Rettungswagen (RTW)"}``.

    Returns
    -------
    pd.DataFrame
        Prepared ETU data ready for direct analysis.
    """
    df = _read_silver(_SILVER_ETU_KEY)
    return _apply_filters(df, filters)


def get_silver_nida(filters: Optional[dict] = None) -> pd.DataFrame:
    """
    Return the prepared Silver NIDA dataset.

    This is the output of :func:`~silver.transformers.prepare_nida_silver`:
    NIDA Index and Details merged on ``protocolId`` (exactly as every
    Streamlit page does), with duplicate columns removed and PII masked.

    Parameters
    ----------
    filters : dict, optional
        Column-based equality filters.

    Returns
    -------
    pd.DataFrame
        Prepared NIDA data ready for direct analysis.
    """
    df = _read_silver(_SILVER_NIDA_KEY)
    return _apply_filters(df, filters)


def get_silver_linked(filters: Optional[dict] = None) -> pd.DataFrame:
    """
    Return the fully linked ETU + NIDA Silver dataset.

    Each row is one ETU mission enriched with NIDA protocol attributes.
    This is the primary dataset for contractor analysis and ML applications.

    Parameters
    ----------
    filters : dict, optional
        Column-based equality filters applied after loading.

    Returns
    -------
    pd.DataFrame
        Linked, prepared data ready for direct analysis.
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
    dataset : {"etu", "nida", "linked"}
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
        "etu": get_silver_etu,
        "nida": get_silver_nida,
        "linked": get_silver_linked,
    }
    if dataset not in _handlers:
        raise ValueError(
            f"Unknown Silver dataset '{dataset}'. "
            f"Valid options: {sorted(_handlers.keys())}"
        )
    return _handlers[dataset](filters=filters)


def list_silver_datasets() -> list:
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
