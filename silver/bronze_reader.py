"""Read raw (Bronze) Parquet files from MinIO for the Silver pipeline."""

import os
from typing import Optional

import pandas as pd

from silver.minio_client import BRONZE_BUCKET, read_parquet

# Default object keys – overridable via environment variables
LST_OBJECT_KEY = os.getenv("BRONZE_LST_KEY", "lst/einsatzdaten.parquet")
NIDA_INDEX_KEY = os.getenv("BRONZE_NIDA_INDEX_KEY", "nida/index.parquet")
NIDA_DETAILS_KEY = os.getenv("BRONZE_NIDA_DETAILS_KEY", "nida/details.parquet")


def read_bronze_lst(object_key: Optional[str] = None) -> pd.DataFrame:
    """
    Load the raw LST/Dispatch (Leitstelle) Bronze data from MinIO.

    The LST table originates from MariaDB and contains fields such as
    EINSATZ_NR and EINSATZMITTEL (callsigns with "Flo SL" prefixes).

    Parameters
    ----------
    object_key : str, optional
        Override the default Parquet object path inside the Bronze bucket.

    Returns
    -------
    pd.DataFrame
        Raw LST records, or an empty DataFrame if the object cannot be read.
    """
    key = object_key or LST_OBJECT_KEY
    df = read_parquet(key, bucket=BRONZE_BUCKET)
    if df.empty:
        print(f"[bronze_reader] No LST data found at s3://{BRONZE_BUCKET}/{key}")
    return df


def read_bronze_nida_index(object_key: Optional[str] = None) -> pd.DataFrame:
    """
    Load the raw NIDA Index Bronze data from MinIO.

    Contains fields: ein_nr_lst, rufname (callsigns), datum_alarm,
    zeit_alarm and related identifiers.

    Parameters
    ----------
    object_key : str, optional
        Override the default Parquet object path.

    Returns
    -------
    pd.DataFrame
    """
    key = object_key or NIDA_INDEX_KEY
    df = read_parquet(key, bucket=BRONZE_BUCKET)
    if df.empty:
        print(f"[bronze_reader] No NIDA index data found at s3://{BRONZE_BUCKET}/{key}")
    return df


def read_bronze_nida_details(object_key: Optional[str] = None) -> pd.DataFrame:
    """
    Load the raw NIDA Protocol-Details Bronze data from MinIO.

    Parameters
    ----------
    object_key : str, optional
        Override the default Parquet object path.

    Returns
    -------
    pd.DataFrame
    """
    key = object_key or NIDA_DETAILS_KEY
    df = read_parquet(key, bucket=BRONZE_BUCKET)
    if df.empty:
        print(f"[bronze_reader] No NIDA details found at s3://{BRONZE_BUCKET}/{key}")
    return df
