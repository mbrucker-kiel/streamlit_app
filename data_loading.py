import streamlit as st
import pandas as pd
from typing import Optional, Tuple, List, Any

from db_connection import get_mongodb_connection, close_mongodb_connection
from loaders import LOADERS
from data_filtering import filter_data_by_year, get_data_for_protocols


@st.cache_data(ttl=604800, show_spinner="Filtering data by year...")
def cached_year_filter(start_year: int, end_year: int, limit: int = 10000):
    """Cached function to filter data by year range"""
    return filter_data_by_year(start_year, end_year, limit)


@st.cache_data(ttl=604800, show_spinner="Loading data...")
def cached_db_query(
    metric: str,
    limit: int = 10000,
    med_name: Optional[str] = None,
    protocol_ids: Optional[List[str]] = None,
):
    """Cached database query function that handles the actual data retrieval"""
    db, client = get_mongodb_connection()
    try:
        if metric not in LOADERS:
            raise ValueError(f"Unknown metric: {metric}")

        # Handle different metric types
        if metric in ["GCS", "Schmerzen"]:
            df = LOADERS[metric](db, metric=metric, limit=limit)
        elif metric in [
            "af",
            "bd",
            "bz",
            "co2",
            "co",
            "hb",
            "hf",
            "puls",
            "spo2",
            "temp",
        ]:
            # For vitals, pass the shortcode directly
            df = LOADERS[metric](db, vital=metric, limit=limit)
        elif metric == "Medikamente" and med_name:
            # For medications with specific name filter
            df = LOADERS[metric](db, med_name=med_name, limit=limit)
        elif protocol_ids:
            # When we have specific protocol IDs to filter by
            df = get_data_for_protocols(metric, protocol_ids, limit, med_name)
        else:
            df = LOADERS[metric](db, limit=limit)

        # Remove duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]
        return df
    finally:
        close_mongodb_connection(client)


def data_loading(
    metric: str,
    limit: int = 10000,
    med_name: Optional[str] = None,
    year_filter: Optional[Tuple[int, int]] = None,
):
    """
    Generic function to load a metric into a dataframe

    Parameters:
    - metric: The type of data to load
    - limit: Maximum number of records to return
    - med_name: Optional name of medication to filter by (only used with 'Medikamente' metric)
    - year_filter: Optional tuple (start_year, end_year) to filter by mission date
    """
    # If year filter is provided, get the protocol IDs for that year range
    if year_filter:
        start_year, end_year = year_filter
        _, protocol_ids = cached_year_filter(start_year, end_year, 100000)

        if not protocol_ids:
            # Return empty DataFrame if no protocols found for the year range
            return pd.DataFrame()

        # Get data for the filtered protocol IDs
        return cached_db_query(metric, 100000, med_name, protocol_ids)

    # If no year filter, proceed with normal data loading
    return cached_db_query(metric, 100000, med_name)
