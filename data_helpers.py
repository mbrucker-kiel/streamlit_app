import pandas as pd
from bson import ObjectId
import datetime

def convert_objectid_to_str(data_list):
    """Convert ObjectId to string in a list of MongoDB documents"""
    for item in data_list:
        if '_id' in item and isinstance(item['_id'], ObjectId):
            item['_id'] = str(item['_id'])
    return data_list

def ja_nein_to_bool(val):
    """Convert 'ja'/'nein' or 'Ja'/'Nein' values to boolean"""
    if isinstance(val, str):
        return True if val.lower() in ["ja", "yes"] else False if val.lower() in ["nein", "no"] else None
    return val

def process_boolean_fields(df):
    """Process boolean fields that may be stored as 'ja'/'nein'"""
    bool_fields = ['flashingLights', 'transportFlashingLights', 'nachforderungNA']
    for field in bool_fields:
        if field in df.columns:
            df[field] = df[field].apply(ja_nein_to_bool)
    return df

def combine_date_time(date_val, time_val):
    """Combine date and time values into a datetime object"""
    if pd.notna(date_val) and pd.notna(time_val):
        try:
            date_str = str(date_val).strip()
            time_str = str(time_val).strip()
            if not date_str or not time_str:
                return None
            datetime_str = f"{date_str} {time_str}"
            return pd.to_datetime(datetime_str, errors='coerce')
        except Exception:
            return None
    return None

def combine_date_time_fields(df):
    """Combine date and time fields into datetime fields"""
    if df.empty:
        return df

    status_fields = [
        ("StatusAlarm", "content_dateStatusAlarm", "content_timeStatusAlarm"),
        ("Status3", "content_dateStatus3", "content_timeStatus3"),
        ("Status4", "content_dateStatus4", "content_timeStatus4"),
        ("Status4b", "content_dateStatus4b", "content_timeStatus4b"),
        ("Status7", "content_dateStatus7", "content_timeStatus7"),
        ("Status8", "content_dateStatus8", "content_timeStatus8"),
        ("Status8b", "content_dateStatus8b", "content_timeStatus8b"),
        ("Status1", "content_dateStatus1", "content_timeStatus1"),
        ("Status2", "content_dateStatus2", "content_timeStatus2"),
        ("StatusEnd", "content_dateStatusEnd", "content_timeStatusEnd"),
    ]

    for target_field, date_field, time_field in status_fields:
        if date_field in df.columns and time_field in df.columns:
            df[target_field] = df.apply(
                lambda row: combine_date_time(row[date_field], row[time_field]), axis=1
            )
    return df