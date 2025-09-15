import pandas as pd


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
