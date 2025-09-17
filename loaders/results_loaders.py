import pandas as pd
from data_helpers import ja_nein_to_bool
import data_loading

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



def get_reanimation_with_targetDestination(db, limit=10000):
    """
    Load reanimation data and merge with index data to get target destination
    Only returns cases where reanimation was performed (rea_status = True)
    Handles duplicate protocol IDs by keeping only the most recent entry
    """
    # Get reanimation data
    df_rea = get_reanimation(db, limit=limit)
    
    if df_rea.empty:
        # Return empty DataFrame with expected columns if no reanimation data
        return pd.DataFrame(columns=["protocolId", "metric", "rea_status", "source_metric", 
                                     "timestamp", "source", "collection", "targetDestination"])
    
    # Filter to only keep positive reanimation cases
    df_rea = df_rea[df_rea['rea_status'] == True]
    
    # Check for any NaN values in protocolId and drop them
    if df_rea['protocolId'].isna().any():
        df_rea = df_rea.dropna(subset=['protocolId'])
    
    # Ensure protocolId is a string type for consistent comparison
    df_rea['protocolId'] = df_rea['protocolId'].astype(str)
    
    # Handle duplicate protocol IDs - keep the most recent entry
    if 'timestamp' in df_rea.columns and not df_rea['timestamp'].isna().all():
        # Sort by timestamp (descending) and keep first occurrence of each protocolId
        df_rea = df_rea.sort_values('timestamp', ascending=False)
        df_rea = df_rea.drop_duplicates(subset=['protocolId'], keep='first')
    else:
        # If no timestamp, just keep the first occurrence
        df_rea = df_rea.drop_duplicates(subset=['protocolId'], keep='first')
    
    # Reset index to ensure clean indexing
    df_rea = df_rea.reset_index(drop=True)
    
    # Final check for duplicates
    if df_rea['protocolId'].duplicated().any():
        # If still duplicated, force uniqueness
        df_rea = df_rea.groupby('protocolId', as_index=False).first()
    
    # If no positive reanimation cases remain, return empty DataFrame
    if df_rea.empty:
        return pd.DataFrame(columns=["protocolId", "metric", "rea_status", "source_metric", 
                                     "timestamp", "source", "collection", "targetDestination"])
    
    # Import directly in function to avoid circular imports
    from data_loading import data_loading
    
    # Get index data which contains target destination
    df_index = data_loading("Index")
    
    if df_index.empty:
        # If no index data, just add empty targetDestination column
        df_rea["targetDestination"] = None
        keep = ["protocolId", "metric", "rea_status", "source_metric", "timestamp", 
                "source", "collection", "targetDestination"]
        return df_rea[keep]
    
    # Ensure protocolId is a string type in index data
    df_index['protocolId'] = df_index['protocolId'].astype(str)
    
    # Drop any NaN values in protocolId
    if df_index['protocolId'].isna().any():
        df_index = df_index.dropna(subset=['protocolId'])
    
    # Handle duplicate protocol IDs in index data if they exist
    if df_index['protocolId'].duplicated().any():
        df_index = df_index.drop_duplicates(subset=['protocolId'], keep='first')
    
    # Reset index in index data
    df_index = df_index.reset_index(drop=True)
    
    # Perform the merge using a more controlled approach
    # First, extract only the needed columns from df_index
    df_index_subset = df_index[["protocolId", "targetDestination"]].copy()
    
    # Merge reanimation data with index data on protocolId
    df_merged = pd.merge(
        df_rea,
        df_index_subset,
        on="protocolId",
        how="left",
        validate="1:1"  # Ensures a one-to-one merge
    )
    
    # Select required columns
    keep = ["protocolId", "metric", "rea_status", "source_metric", "timestamp", 
            "source", "collection", "targetDestination"]
    
    # Ensure all required columns exist
    for col in keep:
        if col not in df_merged.columns:
            df_merged[col] = None
    
    return df_merged[keep]