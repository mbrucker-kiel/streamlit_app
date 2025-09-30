import pandas as pd
import datetime
from typing import Dict, List, Any, Optional

from db_connection import get_mongodb_connection, close_mongodb_connection
from data_helpers import (
    convert_objectid_to_str,
    combine_date_time_fields,
    process_boolean_fields,
)


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

        collection_count = db.etu_leitstelle.count_documents(query)

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
