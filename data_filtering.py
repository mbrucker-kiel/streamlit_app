import pandas as pd
from typing import Tuple, List, Any, Optional

from db_connection import get_mongodb_connection, close_mongodb_connection
from loaders import LOADERS


def filter_data_by_year(year_start, year_end, limit=10000):
    """Filter data by year range from missionDate in nida_index"""
    db, client = get_mongodb_connection()
    try:
        filters = {"year_range": (year_start, year_end)}
        index_df = LOADERS["Index"](db, filters=filters, limit=limit)

        if index_df.empty:
            return index_df, []

        protocol_ids = index_df["protocolId"].unique().tolist()
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
            filters = {"protocol_ids": protocol_ids}
            return LOADERS[metric](db, filters=filters, limit=limit)

        # For other metrics, load the data and filter by protocol_ids afterward
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
        else:
            df = LOADERS[metric](db, limit=limit)

        # Filter by protocol_ids
        if not df.empty and "protocolId" in df.columns:
            df = df[df["protocolId"].isin(protocol_ids)]

        return df
    finally:
        close_mongodb_connection(client)

def reduce_etu_eckpunktevereinbarung(df_etu, start_date, end_date):
    """
    Reduce ETU data to fit the Eckpunktevereinbarung schema (Anlage 5).
    
    Parameters:
    - df_etu: DataFrame with ETU data from get_etu_data()
    - start_date: Start date (string or datetime) for filtering ALARMIERT
    - end_date: End date (string or datetime) for filtering ALARMIERT
    
    Returns:
    - pd.DataFrame with filtered ETU data
    """
    if df_etu.empty:
        return df_etu
    
    df = df_etu.copy()
    
    # Convert date parameters to datetime if they're strings
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    # ALARMIERT is not empty
    df = df[df["ALARMIERT"].notna()]
    
    # ZEIT_AN_E is not empty
    df = df[df["ZEIT_AN_E"].notna()]
    
    # Ensure ALARMIERT column is datetime
    if 'ALARMIERT' in df.columns:
        df['ALARMIERT'] = pd.to_datetime(df['ALARMIERT'], errors='coerce')
    
    # Anlage 5 2.2: Date range filter
    if 'ALARMIERT' in df.columns:
        df = df[(df['ALARMIERT'] >= start_date) & (df['ALARMIERT'] < end_date)]
    
    # Anlage 5 2.3: STORNO_GRUND IS NULL
    if 'STORNO_GRUND' in df.columns:
        df = df[df['STORNO_GRUND'].isna()]
    
    # Anlage 5 2.4: DISPO_TYP = 'E'
    if 'DISPO_TYP' in df.columns:
        df = df[df['DISPO_TYP'] == 'E']
    
    # Anlage 5 2.5: SZENARIO_BEGINN not in exclusion list
    exclusion_szenarien = ['DF', 'G-AMT', 'POL', 'NIL', 'AlarmÜb']
    if 'SZENARIO_BEGINN' in df.columns:
        df = df[(df['SZENARIO_BEGINN'].isna()) | (~df['SZENARIO_BEGINN'].isin(exclusion_szenarien))]
    
    # Anlage 5 2.5: SZENARIO_ABSCHLUSS not in exclusion list
    if 'SZENARIO_ABSCHLUSS' in df.columns:
        df = df[(df['SZENARIO_ABSCHLUSS'].isna()) | (~df['SZENARIO_ABSCHLUSS'].isin(exclusion_szenarien))]
    
    # Anlage 5 2.6: ZEIT_DISPO_2_DISPO IS NOT NULL
    if 'ZEIT_DISPO_2_DISPO' in df.columns:
        df = df[df['ZEIT_DISPO_2_DISPO'].notna()]
    
    # Anlage 5 2.6: Duration (EINSATZBEGINN to EINSATZENDE) > 3 minutes
    if 'EINSATZBEGINN' in df.columns and 'EINSATZENDE' in df.columns:
        df['EINSATZBEGINN'] = pd.to_datetime(df['EINSATZBEGINN'], errors='coerce')
        df['EINSATZENDE'] = pd.to_datetime(df['EINSATZENDE'], errors='coerce')
        df['_dauer_einsatz'] = (df['EINSATZENDE'] - df['EINSATZBEGINN']).dt.total_seconds() / 60
        df = df[df['_dauer_einsatz'] > 3]
    
    # Anlage 5 2.7: EO_X_KOORD IS NOT NULL
    if 'EO_X_KOORD' in df.columns:
        df = df[df['EO_X_KOORD'].notna()]
    
    # Anlage 5 2.7: EO_Y_KOORD IS NOT NULL
    if 'EO_Y_KOORD' in df.columns:
        df = df[df['EO_Y_KOORD'].notna()]
    
    # Anlage 5 2.8: NOT (EO_ORT IS NULL AND EO_OBJEKT IS NULL)
    if 'EO_ORT' in df.columns and 'EO_OBJEKT' in df.columns:
        df = df[~(df['EO_ORT'].isna() & df['EO_OBJEKT'].isna())]
    
    # Anlage 5 2.9: Only keep RTW or NEF
    df = df[df["EINSATZMITTELTYP"].isin(["Rettungswagen (RTW)", "Notarzteinsatzfahrzeug (NEF)"])]
    
    # Duration at scene (ZEIT_AB_E - ZEIT_AN_E) > 1 minute
    if 'ZEIT_AB_E' in df.columns and 'ZEIT_AN_E' in df.columns:
        df["_dauer_ao_e"] = (
            pd.to_datetime(df["ZEIT_AB_E"], errors="coerce")
            - pd.to_datetime(df["ZEIT_AN_E"], errors="coerce")
        ).dt.total_seconds() / 60
        df = df[df["_dauer_ao_e"] > 1]
    
    # Response time (ZEIT_AN_E - ALARMIERT) <= 45 minutes
    if 'ZEIT_AN_E' in df.columns:
        df["_dauer_alarm_an_e"] = (
            pd.to_datetime(df["ZEIT_AN_E"], errors="coerce")
            - pd.to_datetime(df["ALARMIERT"], errors="coerce")
        ).dt.total_seconds() / 60
        df = df[df["_dauer_alarm_an_e"] <= 45]
    
    # Dispatch time (ALARMIERT - ZEIT_AB_D_1) <= 5 minutes
    if 'ZEIT_AB_D_1' in df.columns:
        df["_dauer_abd1_alarm"] = (
            pd.to_datetime(df["ALARMIERT"], errors="coerce")
            - pd.to_datetime(df["ZEIT_AB_D_1"], errors="coerce")
        ).dt.total_seconds() / 60
        df = df[df["_dauer_abd1_alarm"] <= 5]
    
    # Clean up helper columns
    helper_cols = ["_dauer_ao_e", "_dauer_einsatz", "_dauer_alarm_an_e", "_dauer_abd1_alarm"]
    df = df.drop(columns=[col for col in helper_cols if col in df.columns])
    
    # Drop duplicates by EINSATZ_NR, keep the smallest ZEIT_AN_E (first after sorting)
    if 'EINSATZ_NR' in df.columns:
        df = df.sort_values(["EINSATZ_NR", "ZEIT_AN_E"])
        df = df.drop_duplicates(subset=["EINSATZ_NR"], keep="first")
    
    return df