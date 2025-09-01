import streamlit as st
import pandas as pd
from pymongo import MongoClient
import datetime
from bson import ObjectId

# MongoDB connection setup
MONGO_URL = "mongodb://root:example@192.168.100.217:27017/"
DATABASE_NAME = "einsatzdaten"

def get_mongodb_connection():
    """Establish connection to MongoDB and return the database object"""
    client = MongoClient(MONGO_URL)
    db = client[DATABASE_NAME]
    return db, client

def close_mongodb_connection(client):
    """Close the MongoDB connection"""
    if client:
        client.close()

def get_data(filters=None, limit=10000):
    """
    Query data from MongoDB and merge nida_index with protocols_details
    
    Parameters:
    - filters: Dictionary containing filter conditions for nida_index
    - limit: Maximum number of records to retrieve
    
    Returns:
    - Pandas DataFrame with the merged data
    """
    # Generate a cache key based on the function parameters
    cache_key = f"df_{str(filters)}_{str(limit)}"
    
    # Check if data is already in session state
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    
    # Connect to MongoDB
    db, client = get_mongodb_connection()
    
    try:
        # Default empty filters if none provided
        if filters is None:
            filters = {}
            
        # Get data from nida_index collection
        nida_cursor = db.nida_index.find(filters, limit=limit)
        nida_list = list(nida_cursor)
        # Convert ObjectId to string
        nida_list = convert_objectid_to_str(nida_list)
        nida_df = pd.DataFrame(nida_list)
        
        # Get details data
        nida_details_cursor = db.protocols_details.find(filters, limit=limit)
        nida_details_list = list(nida_details_cursor)
        # Convert ObjectId to string
        nida_details_list = convert_objectid_to_str(nida_details_list)
        nida_details_df = pd.DataFrame(nida_details_list)

        # If 'content' column exists and contains dicts, expand its fields
        if not nida_details_df.empty and 'content' in nida_details_df.columns:
            content_expanded = nida_details_df['content'].apply(lambda x: x if isinstance(x, dict) else {})
            content_df = pd.json_normalize(content_expanded)
            # Merge expanded content fields into nida_details_df
            nida_details_df = pd.concat([nida_details_df.drop(columns=['content']), content_df], axis=1)

        # If no data found, return empty DataFrame
        if nida_df.empty:
            st.session_state[cache_key] = pd.DataFrame()
            return st.session_state[cache_key]

        # Combine date/time fields in each dataframe before merging
        nida_df = combine_date_time_fields(nida_df)
        if not nida_details_df.empty:
            nida_details_df = combine_date_time_fields(nida_details_df)

        # Merge nida_df and nida_details_df
        if not nida_details_df.empty:
            # When merging, you can explicitly exclude the _id columns
            if '_id' in nida_df.columns and '_id' in nida_details_df.columns:
                merged_df = pd.merge(
                    nida_df.drop(columns=['_id']), 
                    nida_details_df.drop(columns=['_id']), 
                    on='protocolId', 
                    how='outer',
                    suffixes=('', '_y')  # Avoid duplicate column names
                )
            else:
                merged_df = pd.merge(
                    nida_df, 
                    nida_details_df, 
                    on='protocolId', 
                    how='outer',
                    suffixes=('', '_y')  # Avoid duplicate column names
                )
            nida_df = merged_df
        
        # Process boolean fields
        nida_df = process_boolean_fields(nida_df)
        
        # Store in session state
        st.session_state[cache_key] = nida_df
        return nida_df
        
    finally:
        close_mongodb_connection(client)


def convert_objectid_to_str(data_list):
    """Convert ObjectId to string in a list of MongoDB documents"""
    for item in data_list:
        if '_id' in item and isinstance(item['_id'], ObjectId):
            item['_id'] = str(item['_id'])
    return data_list

def combine_date_time(date_val, time_val):
    """Combine date and time values into a datetime object"""
    if pd.notna(date_val) and pd.notna(time_val):
        try:
            # Convert to string if not already
            date_str = str(date_val).strip()
            time_str = str(time_val).strip()
            
            # Check if we have valid values
            if not date_str or not time_str:
                return None
                
            # Format the datetime string and convert
            datetime_str = f"{date_str} {time_str}"
            return pd.to_datetime(datetime_str, errors='coerce')
        except Exception as e:
            print(f"Error combining date {date_val} and time {time_val}: {e}")
            return None
    return None

def combine_date_time_fields(df):
    """
    Combine date and time fields into datetime fields
    """
    if df.empty:
        return df
        
    # Define the status fields mapping (target field, date field, time field)
    status_fields = [
        ("StatusAlarm", "dateStatusAlarm", "timeStatusAlarm"),
        ("Status3", "dateStatus3", "timeStatus3"),
        ("Status4", "dateStatus4", "timeStatus4"),
        ("Status4b", "dateStatus4b", "timeStatus4b"),
        ("Status7", "dateStatus7", "timeStatus7"),
        ("Status8", "dateStatus8", "timeStatus8"),
        ("Status8b", "dateStatus8b", "timeStatus8b"),
        ("Status1", "dateStatus1", "timeStatus1"),
        ("Status2", "dateStatus2", "timeStatus2"),
        ("StatusEnd", "dateStatusEnd", "timeStatusEnd"),
    ]
    
    # Process each field pair
    for target_field, date_field, time_field in status_fields:
        # Check if both date and time fields exist in dataframe
        if date_field in df.columns and time_field in df.columns:
            # Combine date and time into the target field
            df[target_field] = df.apply(
                lambda row: combine_date_time(row[date_field], row[time_field]), 
                axis=1
            )
            
            # For debugging
            if not df.empty:
                sample_idx = df.index[0]
                print(f"Combined {date_field} + {time_field} -> {target_field}")
    
    return df

def ja_nein_to_bool(val):
    """Convert 'ja'/'nein' values to boolean"""
    if isinstance(val, str):
        return True if val.lower() == "ja" else False if val.lower() == "nein" else None
    return val

def process_boolean_fields(df):
    """Process boolean fields that may be stored as 'ja'/'nein'"""
    bool_fields = ['flashingLights', 'transportFlashingLights', 'nachforderungNA']
    
    for field in bool_fields:
        if field in df.columns:
            df[field] = df[field].apply(ja_nein_to_bool)
    
    return df