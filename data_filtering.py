import pandas as pd
from typing import Tuple, List, Any, Optional

from db_connection import get_mongodb_connection, close_mongodb_connection
from loaders import LOADERS

def filter_data_by_year(year_start, year_end, limit=10000):
    """Filter data by year range from missionDate in nida_index"""
    db, client = get_mongodb_connection()
    try:
        filters = {'year_range': (year_start, year_end)}
        index_df = LOADERS["Index"](db, filters=filters, limit=limit)
        
        if index_df.empty:
            return index_df, []
            
        protocol_ids = index_df['protocolId'].unique().tolist()
        return index_df, protocol_ids
    finally:
        close_mongodb_connection(client)

def get_data_for_protocols(metric, protocol_ids, limit=10000, med_name=None):
    """Get data for specific protocols"""
    db, client = get_mongodb_connection()
    try:
        if metric not in LOADERS:
            raise ValueError(f"Unknown metric: {metric}")
            
        # For Index and Details, use the protocol_ids filter
        if metric in ["Index", "Details"]:
            filters = {'protocol_ids': protocol_ids}
            return LOADERS[metric](db, filters=filters, limit=limit)
            
        # For other metrics, load the data and filter by protocol_ids afterward
        if metric in ["GCS", "Schmerzen"]:
            df = LOADERS[metric](db, metric=metric, limit=limit)
        elif metric in ["af", "bd", "bz", "co2", "co", "hb", "hf", "puls", "spo2", "temp"]:
            # For vitals, pass the shortcode directly
            df = LOADERS[metric](db, vital=metric, limit=limit)
        elif metric == "Medikamente" and med_name:
            # For medications with specific name filter
            df = LOADERS[metric](db, med_name=med_name, limit=limit)
        else:
            df = LOADERS[metric](db, limit=limit)
            
        # Filter by protocol_ids
        if not df.empty and 'protocolId' in df.columns:
            df = df[df['protocolId'].isin(protocol_ids)]
            
        return df
    finally:
        close_mongodb_connection(client)