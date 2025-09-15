import streamlit as st
import pandas as pd
from pymongo import MongoClient
import datetime
from bson import ObjectId
from dotenv import load_dotenv
import os

from mongodb_connection import get_mongodb_connection, close_mongodb_connection


load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "einsatzdaten")



# ==============================================================
#   HELPERS
# ==============================================================

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


# ==============================================================
#   DATA LOADER FUNCTIONS
# ==============================================================

def get_index(db, filters=None, limit=10000):
    """
    Query data from MongoDB nida_index collection
    
    Parameters:
    - db: MongoDB database connection
    - filters: Dictionary containing filter conditions (e.g., year range)
    - limit: Maximum number of records to retrieve
    """
    query = {}
    
    # Apply year filter if provided
    if filters and 'year_range' in filters:
        year_start, year_end = filters['year_range']
        start_date = datetime.datetime(year_start, 1, 1)
        end_date = datetime.datetime(year_end, 12, 31, 23, 59, 59)
        
        query['missionDate'] = {
            '$gte': start_date,
            '$lte': end_date
        }
    
    # Apply protocol IDs filter if provided
    if filters and 'protocol_ids' in filters:
        query['protocolId'] = {'$in': filters['protocol_ids']}
    
    # Query the database
    docs = list(db.nida_index.find(query, limit=limit))
    
    # Convert ObjectId to string
    docs = convert_objectid_to_str(docs)
    
    # Convert to DataFrame
    if not docs:
        return pd.DataFrame()
    
    df = pd.DataFrame(docs)
    
    # Convert date fields to datetime
    date_fields = ['missionDate', 'createdAt', 'updatedAt']
    for field in date_fields:
        if field in df.columns:
            df[field] = pd.to_datetime(df[field], errors='coerce')
    
    return df

def get_details(db, filters=None, limit=10000):
    """
    Query data from MongoDB protocols_details collection
    
    Parameters:
    - db: MongoDB database connection
    - filters: Dictionary containing filter conditions
    - limit: Maximum number of records to retrieve
    """

    # Get details data
    nida_details_cursor = db.protocols_details.find(filters, limit=limit)
    nida_details_list = list(nida_details_cursor)
    nida_details_list = convert_objectid_to_str(nida_details_list)

    if nida_details_list and isinstance(nida_details_list[0], dict) and 'content' in nida_details_list[0]:
        nida_details_df = pd.json_normalize(nida_details_list, sep='_')
    else:
        nida_details_df = pd.DataFrame(nida_details_list)
    
    # Process date/time fields
    df = combine_date_time_fields(nida_details_df)

    # Process boolean fields
    df = process_boolean_fields(df)
    
    return df

def get_metric_from_findings(db, metric, limit=10000):
    """Load structured metrics like GCS, Schmerzen from protocols_findings"""
    query = {"data": {"$elemMatch": {"description": metric}}}
    docs = list(db.protocols_findings.find(query, limit=limit))
    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs).explode("data").reset_index(drop=True)
    flat = pd.json_normalize(df["data"])
    df = pd.concat([df.drop(columns=["data"]), flat], axis=1)
    df = df[df["description"] == metric]

    df["metric"] = metric
    df["value_num"] = pd.to_numeric(df.get("valueInteger"), errors="coerce")
    df["type"] = df.get("type")
    df["timestamp"] = df.get("timeStamp")
    df["source"] = df.get("source")
    df["collection"] = "protocols_findings"

    keep = ["protocolId","metric","value_num","type","timestamp","source","collection"]
    return df[keep]


def get_medikamente(db, med_name=None, limit=10000):
    """
    Load medications from protocols_measures
    
    Parameters:
    - db: MongoDB database connection
    - med_name: Optional name of medication to filter by (can be in value_2 or value_6)
    - limit: Maximum number of records to return
    """
    query = {"data": {"$elemMatch": {"value_1": "Medikamente"}}}
    
    # If a specific medication is requested, add to query
    if med_name:
        query = {
            "data": {
                "$elemMatch": {
                    "value_1": "Medikamente",
                    "$or": [
                        {"value_2": {"$regex": med_name, "$options": "i"}},  # Case-insensitive search in value_2
                        {"value_6": {"$regex": med_name, "$options": "i"}}   # Case-insensitive search in value_6
                    ]
                }
            }
        }
        
    docs = list(db.protocols_measures.find(query, limit=limit))
    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs).explode("data").reset_index(drop=True)
    flat = pd.json_normalize(df["data"])
    df = pd.concat([df.drop(columns=["data"]), flat], axis=1)

    df = df[df["value_1"] == "Medikamente"]
    
    # If a medication name was specified, filter the results
    if med_name:
        med_name_lower = med_name.lower()
        mask = (
            df["value_2"].str.lower().str.contains(med_name_lower, na=False) | 
            df["value_6"].str.lower().str.contains(med_name_lower, na=False)
        )
        df = df[mask]

    df["metric"] = "Medikamente"
    df["med_name"] = df.get("value_2")
    df["route"] = df.get("value_3")
    df["dose"] = pd.to_numeric(df.get("value_4"), errors="coerce")
    df["dose_unit"] = df.get("value_5")
    df["substance"] = df.get("value_6")
    df["timestamp"] = df.get("timeStamp")
    df["source"] = df.get("source")
    df["collection"] = "protocols_measures"

    keep = ["protocolId","metric","med_name","route","dose","dose_unit","substance","timestamp","source","collection"]
    return df[keep]

def get_metric_from_results(db, limit=10000):
    """Load NACA score from protocols_results"""
    query = {"data": {"$elemMatch": {"value_1": "NACA"}}}
    docs = list(db.protocols_results.find(query, limit=limit))
    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs).explode("data").reset_index(drop=True)
    flat = pd.json_normalize(df["data"])
    df = pd.concat([df.drop(columns=["data"]), flat], axis=1)

    df = df[df["value_1"] == "NACA"]

    df["metric"] = "NACA"
    df["NACA-Score"] = df.get("value_2")
    df["timestamp"] = df.get("timeStamp")
    df["source"] = df.get("source")
    df["collection"] = "protocols_results"

    keep = ["protocolId","metric","NACA-Score","source","collection"]
    return df[keep]

# Flipped vitals dictionary - collection names to API shortcodes
VITALS = {
    "af": "af",
    "bd": "bd",
    "bz": "bz",
    "co2": "co2",
    "co": "co",  # ???? rly?
    "hb": "hb",
    "hf": "hf",
    "puls": "puls",
    "spo2": "spo2",
    "temp": "temp",
}

def get_vitals(db, vital, limit=10000):
    """
    Load vital signs from vitals collection
    
    Parameters:
    - db: MongoDB database connection
    - vital: Short code for the vital sign (e.g., 'af', 'bd', 'spo2')
    - limit: Maximum number of records to return
    """
    # Find the collection name for the given vital shortcode
    collection_name = None
    for coll, code in VITALS.items():
        if code == vital:
            collection_name = coll
            break
    
    if not collection_name:
        return pd.DataFrame()
    
    # Query the appropriate vitals collection
    query = {}  # No specific query filter needed
    try:
        collection = db[f"vitals_{collection_name}"]
        docs = list(collection.find(query, limit=limit))
        
        if not docs:
            return pd.DataFrame()
        
        # Process the documents
        df = pd.DataFrame(docs)
        
        # Ensure the dataframe has the expected columns
        if df.empty:
            return pd.DataFrame()
        
        # Extract data - handle both direct fields and nested data structure
        if "data" in df.columns:
            # Handle nested data structure
            df = df.explode("data").reset_index(drop=True)
            flat = pd.json_normalize(df["data"])
            df = pd.concat([df.drop(columns=["data"]), flat], axis=1)
        
        # Create standardized output
        df["metric"] = vital
        df["value"] = df.get("value", None)
        df["unit"] = df.get("unit", df.get("%", None))
        df["o2Administration"] = df.get("o2Administration", None)
        df["description"] = df.get("description", None)
        df["timestamp"] = df.get("timeStamp", df.get("timestamp", None))
        df["source"] = df.get("source", None)
        df["collection"] = f"vitals_{collection_name}"
        
        # Ensure all expected columns exist
        for col in ["protocolId", "metric", "value", "unit", "o2Administration", "description", "timestamp", "source", "collection"]:
            if col not in df.columns:
                df[col] = None
        
        keep = ["protocolId", "metric", "value", "unit", "o2Administration", "description", "timestamp", "source", "collection"]
        return df[keep]
    
    except Exception as e:
        print(f"Error loading vital {vital} from collection vitals_{collection_name}: {e}")
        return pd.DataFrame()


def get_intubation(db, limit=10000):
    """Load intubation data from protocols_measures"""
    query = {"data": {"$elemMatch": {"value_1": "Atemweg"}}}
    docs = list(db.protocols_measures.find(query, limit=limit))
    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs).explode("data").reset_index(drop=True)
    flat = pd.json_normalize(df["data"])
    df = pd.concat([df.drop(columns=["data"]), flat], axis=1)

    # Fixed the boolean operation with proper parentheses
    df = df[(df["value_2"] == "Intubation") & (df["value_3"].notna())]

    df["metric"] = "Intubation"
    df["type"] = df.get("value_3")
    df["size"] = df.get("value_4")
    df["applicant"] = df.get("value_8") # if done by one self or someone else prior
    df["timestamp"] = df.get("timeStamp")
    df["source"] = df.get("source")
    df["collection"] = "protocols_measures"

    keep = ["protocolId","metric","type","size","applicant","timestamp","source","collection"]
    return df[keep]

def get_reanimation(db, limit=10000):
    """Load reanimation data - NACA 6 or explicit reanimation field"""
    # First get all NACA 6 cases
    naca_query = {"data": {"$elemMatch": {"value_1": "NACA", "value_2": "6"}}}
    naca_docs = list(db.protocols_results.find(naca_query, limit=limit))
    
    # Get explicit reanimation field
    rea_query = {"data": {"$elemMatch": {"value_1": "Rea durchgeführt"}}}
    rea_docs = list(db.protocols_results.find(rea_query, limit=limit))
    
    # Combine and process
    if not naca_docs and not rea_docs:
        return pd.DataFrame()
        
    # Process NACA 6 data
    naca_df = pd.DataFrame()
    if naca_docs:
        naca_df = pd.DataFrame(naca_docs).explode("data").reset_index(drop=True)
        naca_flat = pd.json_normalize(naca_df["data"])
        naca_df = pd.concat([naca_df.drop(columns=["data"]), naca_flat], axis=1)
        naca_df = naca_df[naca_df["value_1"] == "NACA"]
        naca_df = naca_df[naca_df["value_2"] == "6"]
        naca_df["source_metric"] = "NACA 6"
        
    # Process reanimation data
    rea_df = pd.DataFrame()
    if rea_docs:
        rea_df = pd.DataFrame(rea_docs).explode("data").reset_index(drop=True)
        rea_flat = pd.json_normalize(rea_df["data"])
        rea_df = pd.concat([rea_df.drop(columns=["data"]), rea_flat], axis=1)
        rea_df = rea_df[rea_df["value_1"] == "Rea durchgeführt"]
        rea_df["source_metric"] = "Reanimation field"
        
    # Combine both sources
    combined_dfs = []
    if not naca_df.empty:
        combined_dfs.append(naca_df)
    if not rea_df.empty:
        combined_dfs.append(rea_df)
        
    if not combined_dfs:
        return pd.DataFrame()
        
    df = pd.concat(combined_dfs, ignore_index=True)
    
    df["metric"] = "Reanimation"
    df["rea_status"] = df.apply(
        lambda row: "Ja" if row["source_metric"] == "NACA 6" or (row["source_metric"] == "Reanimation field" and row.get("value_2") == "ja") else "Nein", 
        axis=1
    )
    df["rea_status"] = df["rea_status"].apply(ja_nein_to_bool)  # Explicitly convert "Ja"/"Nein" to boolean
    df["timestamp"] = df.get("timeStamp")
    df["source"] = df.get("source")
    df["collection"] = "protocols_results"

    keep = ["protocolId", "metric", "rea_status", "source_metric", "timestamp", "source", "collection"]
    return df[keep]

def get_12lead_ecg(db, limit=10000):
    """Load 12-lead ECG data from protocols_measures"""
    query = {"data": {"$elemMatch": {"value_1": "Monitoring", "value_2": "12-Kanal-EKG"}}}
    docs = list(db.protocols_measures.find(query, limit=limit))
    
    if not docs:
        return pd.DataFrame()
        
    df = pd.DataFrame(docs).explode("data").reset_index(drop=True)
    flat = pd.json_normalize(df["data"])
    df = pd.concat([df.drop(columns=["data"]), flat], axis=1)
    
    df = df[(df["value_1"] == "Monitoring") & (df["value_2"] == "12-Kanal-EKG")]
    
    df["metric"] = "12-Kanal-EKG"
    df["performed"] = True  # If it's in the database, it was performed
    df["result"] = df.get("value_3")  # May contain diagnostic info
    df["timestamp"] = df.get("timeStamp")
    df["source"] = df.get("source")
    df["collection"] = "protocols_measures"
    
    keep = ["protocolId", "metric", "performed", "result", "timestamp", "source", "collection"]
    return df[keep]

def get_symptom_onset(db, limit=10000):
    """
    Load symptom onset time data from protocol_results
    
    Special handling for the unique data structure where:
    - Date and time are stored in separate records with the same value_1
    - One record has the date in value_2 (e.g., "01.01.2023")
    - Another record has the time in value_2 (e.g., "00:50:00")
    
    Note: The timeStamp field in the database is often null for these entries.

    """
    onset_query = {"data": {"$elemMatch": {"value_1": "Symptombeginn"}}}
    spec_query = {"data": {"$elemMatch": {"value_1": "Spezifikation Symptombeginn"}}}
    
    onset_docs = list(db.protocols_results.find(onset_query, limit=limit))
    spec_docs = list(db.protocols_results.find(spec_query, limit=limit))
    
    if not onset_docs and not spec_docs:
        return pd.DataFrame()
    
    # Extract and group onset data by protocolId
    onset_data_by_protocol = {}
    if onset_docs:
        for doc in onset_docs:
            protocol_id = doc.get("protocolId")
            
            if protocol_id not in onset_data_by_protocol:
                onset_data_by_protocol[protocol_id] = {
                    "date": None,
                    "time": None,
                    "timeStamp": None,  # Initialize timeStamp
                    "source": doc.get("source")
                }
                
            for data_item in doc.get("data", []):
                if data_item.get("value_1") == "Symptombeginn":
                    value = data_item.get("value_2")
                    source = data_item.get("source", doc.get("source"))
                    # Get the timeStamp, which may be null
                    time_stamp = data_item.get("timeStamp")
                    
                    if value:
                        # Check if this is a date or time format
                        if "." in value and len(value) >= 8:  # Likely a date like DD.MM.YYYY
                            onset_data_by_protocol[protocol_id]["date"] = value
                        elif ":" in value:  # Likely a time like HH:MM:SS
                            onset_data_by_protocol[protocol_id]["time"] = value
                        
                    # Update source if available
                    if source:
                        onset_data_by_protocol[protocol_id]["source"] = source
                        
                    # Update timeStamp if available
                    if time_stamp:
                        onset_data_by_protocol[protocol_id]["timeStamp"] = time_stamp
    
    # Extract specification data by protocolId
    spec_data_by_protocol = {}
    if spec_docs:
        for doc in spec_docs:
            protocol_id = doc.get("protocolId")
            
            for data_item in doc.get("data", []):
                if data_item.get("value_1") == "Spezifikation Symptombeginn":
                    value = data_item.get("value_2")
                    source = data_item.get("source", doc.get("source"))
                    # Get the timeStamp, which may be null
                    time_stamp = data_item.get("timeStamp")
                    
                    if value:
                        spec_data_by_protocol[protocol_id] = {
                            "specification": value,
                            "source": source or doc.get("source"),
                            "timeStamp": time_stamp
                        }
    
    # Combine all unique protocol IDs
    all_protocol_ids = set(list(onset_data_by_protocol.keys()) + list(spec_data_by_protocol.keys()))
    
    # Create result records
    result_records = []
    for pid in all_protocol_ids:
        record = {"protocolId": pid}
        
        # Add onset date/time if available
        if pid in onset_data_by_protocol:
            onset_data = onset_data_by_protocol[pid]
            
            record["date"] = onset_data.get("date")
            record["time"] = onset_data.get("time")
            record["source"] = onset_data.get("source")
            record["timeStamp"] = onset_data.get("timeStamp")  # May be null
            
            # Combine date and time if both are available
            if onset_data.get("date") and onset_data.get("time"):
                record["onset_time"] = f"{onset_data.get('date')} {onset_data.get('time')}"
            elif onset_data.get("date"):
                record["onset_time"] = onset_data.get("date")
            elif onset_data.get("time"):
                record["onset_time"] = onset_data.get("time")
            else:
                record["onset_time"] = None
        else:
            record["date"] = None
            record["time"] = None
            record["onset_time"] = None
            record["source"] = None
            record["timeStamp"] = None
            
        # Add specification if available
        if pid in spec_data_by_protocol:
            spec_data = spec_data_by_protocol[pid]
            record["specification"] = spec_data.get("specification")
            
            # Use spec source if onset source is not available
            if not record["source"] and spec_data.get("source"):
                record["source"] = spec_data.get("source")
                
            # Use spec timeStamp if onset timeStamp is not available
            if not record["timeStamp"] and spec_data.get("timeStamp"):
                record["timeStamp"] = spec_data.get("timeStamp")
        else:
            record["specification"] = None
            
        # Add to results
        result_records.append(record)
    
    # Create final dataframe
    if result_records:
        result_df = pd.DataFrame(result_records)
        
        # Add remaining fields
        result_df["metric"] = "Symptombeginn"
        # Use the database timeStamp field for timestamp (may be null)
        result_df["timestamp"] = result_df["timeStamp"]
        result_df["collection"] = "protocols_results"
        
        # Reorder columns for consistency
        keep = ["protocolId", "metric", "onset_time", "date", "time", "specification", "timestamp", "source", "collection"]
        
        # Ensure all columns exist
        for col in keep:
            if col not in result_df.columns:
                result_df[col] = None
                
        return result_df[keep]
    else:
        # Return empty dataframe with correct columns
        return pd.DataFrame(columns=["protocolId", "metric", "onset_time", "date", "time", "specification", "timestamp", "source", "collection"])
    
def get_neurological_signs(db, limit=10000):
    """Load neurological signs (Seitenzeichen/Sprachstörung) from protocol_findings"""
    query = {"data": {"$elemMatch": {"description": "Auffäligkeiten"}}}
    docs = list(db.protocols_findings.find(query, limit=limit))
    
    if not docs:
        return pd.DataFrame()
    
    df = pd.DataFrame(docs).explode("data").reset_index(drop=True)
    flat = pd.json_normalize(df["data"])
    df = pd.concat([df.drop(columns=["data"]), flat], axis=1)
    
    df = df[df["description"] == "Auffäligkeiten"]
    
    df["metric"] = "Neurologische Auffälligkeiten"
    df["finding"] = df.get("valueString")
    df["timestamp"] = df.get("timeStamp")
    df["source"] = df.get("source")
    df["collection"] = "protocols_findings"
    
    keep = ["protocolId", "metric", "finding", "timestamp", "source", "collection"]
    return df[keep]

def get_pupil_status(db, limit=10000):
    """Load pupil status data from protocol_findings"""
    left_query = {"data": {"$elemMatch": {"description": "Lichtreaktion links"}}}
    right_query = {"data": {"$elemMatch": {"description": "Lichtreaktion rechts"}}}
    
    left_docs = list(db.protocols_findings.find(left_query, limit=limit))
    right_docs = list(db.protocols_findings.find(right_query, limit=limit))
    
    if not left_docs and not right_docs:
        return pd.DataFrame()
    
    # Process left pupil data
    left_records = []
    if left_docs:
        for doc in left_docs:
            protocol_id = doc.get("protocolId")
            for data_item in doc.get("data", []):
                if data_item.get("description") == "Lichtreaktion links":
                    left_records.append({
                        "protocolId": protocol_id,
                        "left_reaction": data_item.get("valueString"),
                        "timeStamp": data_item.get("timeStamp"),
                        "source": data_item.get("source")
                    })
        
        # Convert to DataFrame and ensure unique protocol IDs
        if left_records:
            left_clean = pd.DataFrame(left_records)
            left_clean = left_clean.drop_duplicates(subset=["protocolId"]).reset_index(drop=True)
        else:
            left_clean = pd.DataFrame(columns=["protocolId", "left_reaction", "timeStamp", "source"])
    else:
        left_clean = pd.DataFrame(columns=["protocolId", "left_reaction", "timeStamp", "source"])
    
    # Process right pupil data
    right_records = []
    if right_docs:
        for doc in right_docs:
            protocol_id = doc.get("protocolId")
            for data_item in doc.get("data", []):
                if data_item.get("description") == "Lichtreaktion rechts":
                    right_records.append({
                        "protocolId": protocol_id,
                        "right_reaction": data_item.get("valueString")
                    })
        
        # Convert to DataFrame and ensure unique protocol IDs
        if right_records:
            right_clean = pd.DataFrame(right_records)
            right_clean = right_clean.drop_duplicates(subset=["protocolId"]).reset_index(drop=True)
        else:
            right_clean = pd.DataFrame(columns=["protocolId", "right_reaction"])
    else:
        right_clean = pd.DataFrame(columns=["protocolId", "right_reaction"])
    
    # Combine the data using a safer approach
    # Start with all unique protocol IDs
    all_protocol_ids = pd.concat([
        left_clean["protocolId"] if not left_clean.empty else pd.Series(dtype=str),
        right_clean["protocolId"] if not right_clean.empty else pd.Series(dtype=str)
    ]).unique()
    
    # Create result dataframe with all protocol IDs
    result_records = []
    for pid in all_protocol_ids:
        record = {"protocolId": pid}
        
        # Add left eye data if available
        if not left_clean.empty and pid in left_clean["protocolId"].values:
            left_row = left_clean[left_clean["protocolId"] == pid].iloc[0]
            record["left_reaction"] = left_row["left_reaction"]
            record["timeStamp"] = left_row["timeStamp"]
            record["source"] = left_row["source"]
        else:
            record["left_reaction"] = None
            record["timeStamp"] = None
            record["source"] = None
            
        # Add right eye data if available
        if not right_clean.empty and pid in right_clean["protocolId"].values:
            right_row = right_clean[right_clean["protocolId"] == pid].iloc[0]
            record["right_reaction"] = right_row["right_reaction"]
        else:
            record["right_reaction"] = None
            
        result_records.append(record)
    
    # Create final dataframe
    if result_records:
        result_df = pd.DataFrame(result_records)
        
        # Add remaining fields
        result_df["metric"] = "Pupillenstatus"
        result_df["timestamp"] = result_df["timeStamp"]
        result_df["collection"] = "protocols_findings"
        
        # Reorder columns for consistency
        keep = ["protocolId", "metric", "left_reaction", "right_reaction", "timestamp", "source", "collection"]
        
        # Ensure all columns exist
        for col in keep:
            if col not in result_df.columns:
                result_df[col] = None
                
        return result_df[keep]
    else:
        # Return empty dataframe with correct columns
        return pd.DataFrame(columns=["protocolId", "metric", "left_reaction", "right_reaction", "timestamp", "source", "collection"])

# Registry
LOADERS = {
    "Index": get_index,
    "Details": get_details,
    "GCS": get_metric_from_findings,
    "Schmerzen": get_metric_from_findings,
    "Medikamente": get_medikamente,
    "NACA": get_metric_from_results,
    "af": get_vitals,  # Short codes for vitals
    # "bd": get_vitals_bd, # false implementation needs special handling since sys and dia values
    "bz": get_vitals,
    "co2": get_vitals,
    "co": get_vitals,
    "hb": get_vitals,
    "hf": get_vitals,
    "puls": get_vitals,
    "spo2": get_vitals,
    "temp": get_vitals,
    "Intubation": get_intubation,
    "Reanimation": get_reanimation,
    "12-Kanal-EKG": get_12lead_ecg,
    "Symptombeginn": get_symptom_onset,
    "Neurologische_Auffälligkeiten": get_neurological_signs,
    "Pupillenstatus": get_pupil_status,
}

def filter_data_by_year(year_start, year_end, limit=10000):
    """
    Filter data by year range from missionDate in nida_index
    
    Parameters:
    - year_start: Start year for filtering
    - year_end: End year for filtering
    - limit: Maximum number of records to return
    
    Returns:
    - DataFrame with filtered index data
    - List of protocol IDs that can be used to filter other collections
    """
    db, client = get_mongodb_connection()
    try:
        filters = {'year_range': (year_start, year_end)}
        index_df = get_index(db, filters=filters, limit=limit)
        
        if index_df.empty:
            return index_df, []
            
        protocol_ids = index_df['protocolId'].unique().tolist()
        return index_df, protocol_ids
    finally:
        close_mongodb_connection(client)

def get_data_for_protocols(metric, protocol_ids, limit=10000, med_name=None):
    """
    Get data for specific protocols
    
    Parameters:
    - metric: The type of data to load
    - protocol_ids: List of protocol IDs to filter by
    - limit: Maximum number of records to return
    - med_name: Optional name of medication to filter by (only used with 'Medikamente' metric)
    """
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



@st.cache_data(ttl=3600, show_spinner="Loading data...")  # Cache for 1 hour
def cached_db_query(metric: str, limit: int = 10000, med_name: Optional[str] = None, 
                   protocol_ids: Optional[List[str]] = None):
    """
    Cached database query function that handles the actual data retrieval
    
    Parameters:
    - metric: The type of data to load
    - limit: Maximum number of records to return
    - med_name: Optional name of medication to filter by
    - protocol_ids: Optional list of protocol IDs to filter by
    
    Returns:
    - DataFrame containing the requested data
    """
    db, client = get_mongodb_connection()
    try:
        if metric not in LOADERS:
            raise ValueError(f"Unknown metric: {metric}")

        # Handle different metric types
        if metric in ["GCS", "Schmerzen"]:
            df = LOADERS[metric](db, metric=metric, limit=limit)
        elif metric in ["af", "bd", "bz", "co2", "co", "hb", "hf", "puls", "spo2", "temp"]:
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

@st.cache_data(ttl=3600, show_spinner="Filtering data by year...")
def cached_year_filter(start_year: int, end_year: int, limit: int = 10000):
    """Cached function to filter data by year range"""
    return filter_data_by_year(start_year, end_year, limit)

def data_loading(metric: str, limit: int = 10000, med_name: Optional[str] = None, 
                year_filter: Optional[Tuple[int, int]] = None):
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
        _, protocol_ids = cached_year_filter(start_year, end_year, limit)
        
        if not protocol_ids:
            # Return empty DataFrame if no protocols found for the year range
            return pd.DataFrame()
            
        # Get data for the filtered protocol IDs
        return cached_db_query(metric, limit, med_name, protocol_ids)
    
    # If no year filter, proceed with normal data loading
    return cached_db_query(metric, limit, med_name)