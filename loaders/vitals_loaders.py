import pandas as pd
from typing import Dict, List, Any, Optional

# Flipped vitals dictionary - collection names to API shortcodes
VITALS = {
    "af": "af",
    "bd": "bd",
    "bz": "bz",
    "co2": "co2",
    "co": "co",
    "hb": "hb",
    "hf": "hf",
    "puls": "puls",
    "spo2": "spo2",
    "temp": "temp",
}


def get_vitals(db, vital, limit=10000):
    """Load vital signs from vitals collection"""
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
        for col in [
            "protocolId",
            "metric",
            "value",
            "unit",
            "o2Administration",
            "description",
            "timestamp",
            "source",
            "collection",
        ]:
            if col not in df.columns:
                df[col] = None

        keep = [
            "protocolId",
            "metric",
            "value",
            "unit",
            "o2Administration",
            "description",
            "timestamp",
            "source",
            "collection",
        ]
        return df[keep]

    except Exception as e:
        print(
            f"Error loading vital {vital} from collection vitals_{collection_name}: {e}"
        )
        return pd.DataFrame()
