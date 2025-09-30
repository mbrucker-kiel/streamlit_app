import pandas as pd
from typing import Dict, List, Any, Optional


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

    keep = [
        "protocolId",
        "metric",
        "value_num",
        "type",
        "timestamp",
        "source",
        "collection",
    ]
    return df[keep]


def get_neurological_signs(db, limit=10000):
    """Load neurological signs (Seitenzeichen/Sprachstörung) from protocol_findings"""
    query = {"data": {"$elemMatch": {"description": "Auffäligkeiten"}}}
    docs = list(db.protocols_findings.find(query, limit=limit))


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
                    left_records.append(
                        {
                            "protocolId": protocol_id,
                            "left_reaction": data_item.get("valueString"),
                            "timeStamp": data_item.get("timeStamp"),
                            "source": data_item.get("source"),
                        }
                    )

        # Convert to DataFrame and ensure unique protocol IDs
        if left_records:
            left_clean = pd.DataFrame(left_records)
            left_clean = left_clean.drop_duplicates(subset=["protocolId"]).reset_index(
                drop=True
            )
        else:
            left_clean = pd.DataFrame(
                columns=["protocolId", "left_reaction", "timeStamp", "source"]
            )
    else:
        left_clean = pd.DataFrame(
            columns=["protocolId", "left_reaction", "timeStamp", "source"]
        )

    # Process right pupil data
    right_records = []
    if right_docs:
        for doc in right_docs:
            protocol_id = doc.get("protocolId")
            for data_item in doc.get("data", []):
                if data_item.get("description") == "Lichtreaktion rechts":
                    right_records.append(
                        {
                            "protocolId": protocol_id,
                            "right_reaction": data_item.get("valueString"),
                        }
                    )

        # Convert to DataFrame and ensure unique protocol IDs
        if right_records:
            right_clean = pd.DataFrame(right_records)
            right_clean = right_clean.drop_duplicates(
                subset=["protocolId"]
            ).reset_index(drop=True)
        else:
            right_clean = pd.DataFrame(columns=["protocolId", "right_reaction"])
    else:
        right_clean = pd.DataFrame(columns=["protocolId", "right_reaction"])

    # Combine the data using a safer approach
    # Start with all unique protocol IDs
    all_protocol_ids = pd.concat(
        [
            left_clean["protocolId"] if not left_clean.empty else pd.Series(dtype=str),
            (
                right_clean["protocolId"]
                if not right_clean.empty
                else pd.Series(dtype=str)
            ),
        ]
    ).unique()

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
        keep = [
            "protocolId",
            "metric",
            "left_reaction",
            "right_reaction",
            "timestamp",
            "source",
            "collection",
        ]

        # Ensure all columns exist
        for col in keep:
            if col not in result_df.columns:
                result_df[col] = None

        return result_df[keep]
    else:
        # Return empty dataframe with correct columns
        return pd.DataFrame(
            columns=[
                "protocolId",
                "metric",
                "left_reaction",
                "right_reaction",
                "timestamp",
                "source",
                "collection",
            ]
        )
