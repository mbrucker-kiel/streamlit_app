import pandas as pd
import datetime
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv

from data_helpers import (
    convert_objectid_to_str,
    combine_date_time_fields,
    process_boolean_fields,
)

load_dotenv()


def get_index(db, filters=None, limit=10000):
    """Query data from MongoDB nida_index collection"""
    query = {}

    # Apply year filter if provided
    if filters and "year_range" in filters:
        year_start, year_end = filters["year_range"]
        start_date = datetime.datetime(year_start, 1, 1)
        end_date = datetime.datetime(year_end, 12, 31, 23, 59, 59)

        query["missionDate"] = {"$gte": start_date, "$lte": end_date}

    # Apply protocol IDs filter if provided
    if filters and "protocol_ids" in filters:
        query["protocolId"] = {"$in": filters["protocol_ids"]}

    # Query the database
    docs = list(db.nida_index.find(query).sort("missionDate", -1).limit(limit))

    # Convert ObjectId to string
    docs = convert_objectid_to_str(docs)

    # Convert to DataFrame
    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs)

    # Convert date fields to datetime
    date_fields = ["missionDate", "createdAt", "updatedAt"]
    for field in date_fields:
        if field in df.columns:
            df[field] = pd.to_datetime(df[field], errors="coerce")

    return df


def get_details(db, filters=None, limit=10000):
    """Query data from MongoDB protocols_details collection"""
    # Get details data
    nida_details_cursor = (
        db.protocols_details.find(filters)
        .sort("content.dateStatusAlarm", -1)
        .limit(limit)
    )
    nida_details_list = list(nida_details_cursor)
    nida_details_list = convert_objectid_to_str(nida_details_list)

    if (
        nida_details_list
        and isinstance(nida_details_list[0], dict)
        and "content" in nida_details_list[0]
    ):
        nida_details_df = pd.json_normalize(nida_details_list, sep="_")
    else:
        nida_details_df = pd.DataFrame(nida_details_list)

    # Process date/time fields
    df = combine_date_time_fields(nida_details_df)

    # Process boolean fields
    df = process_boolean_fields(df)

    return df


def get_freetext(db, filters=None, limit=10000):
    """Query data from MongoDB free_text collection"""

    # Query the database
    docs = list(db.protocols_freetexts.find(filters, limit=limit))

    # Convert ObjectId to string
    docs = convert_objectid_to_str(docs)

    # Convert to DataFrame
    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs)

    return df


def get_etu(db, filters=None, limit=10000):
    query = {}
    if filters:
        query.update(filters)

    # Add filter for Schleswig-Flensburg district
    query["EO_LANDKREIS"] = "Schleswig-Flensburg"

    # Debug: Check if collection exists and get count
    try:
        collection_names = db.list_collection_names()
        if "etu_leitstelle" not in collection_names:
            return pd.DataFrame()

        docs = list(
            db.etu_leitstelle.find(query).sort("EINSATZBEGINN", -1).limit(limit)
        )

        docs = convert_objectid_to_str(docs)
        if not docs:
            return pd.DataFrame()

        df = pd.DataFrame(docs)
        return df

    except Exception as e:
        print(f"ERROR in get_etu: {str(e)}")
        return pd.DataFrame()


def get_rtm_vorhaltung(db, filters=None, limit=10000):
    """
    Load vehicle availability configuration from MongoDB into a DataFrame.

    Args:
        db: MongoDB database connection
        filters: Optional dict to filter (e.g. {"vehicle_type": "NEF"})
        limit: Max number of documents to retrieve

    Returns:
        pd.DataFrame with all vehicle configuration fields.
    """

    query = {}
    if filters:
        query.update(filters)

    try:
        # Check collection exists
        if "rtm_vorhaltung" not in db.list_collection_names():
            print("Collection 'vehicles' not found.")
            return pd.DataFrame()

        # Fetch data
        docs = list(db.rtm_vorhaltung.find(query).limit(limit))

        if not docs:
            print("No documents found in 'vehicles' for given filters.")
            return pd.DataFrame()

        # Convert ObjectId fields if necessary
        for doc in docs:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        # Convert to DataFrame
        df = pd.DataFrame(docs)

        # Optional: enforce column order / normalization
        expected_cols = [
            "_id",
            "vehicle_identifier",
            "vehicle_type",
            "station",
            "valid_from",
            "valid_to",
            "availability",
            "total_week_hours",
        ]

        for col in expected_cols:
            if col not in df.columns:
                df[col] = None

        return df[expected_cols]

    except Exception as e:
        print(f"ERROR in get_vehicle_config: {e}")
        return pd.DataFrame()
