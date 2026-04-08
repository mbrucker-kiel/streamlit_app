"""
Data transformers for the Bronze to Silver cleaning step.

All transformation functions are pure Python (no Streamlit dependency) and
can be used from the Silver pipeline, Jupyter notebooks, or ML scripts.

Design principle
----------------
Each prepare_* function uses the same loaders the Streamlit dashboard uses
(loaders.LOADERS), applies the same merging/cleaning the pages perform,
enforces the einsatzdaten Data Contract schema, and returns a
fully-prepared DataFrame.  The Silver pipeline calls these functions once,
stores the result in MinIO, and future consumers simply read the pre-cleaned
Parquet files - no re-transformation needed.
"""

import hashlib
import re
from typing import Optional

import pandas as pd

# Reuse the existing Eckpunktevereinbarung filter - single source of truth.
from data_filtering import reduce_etu_eckpunktevereinbarung
from loaders import LOADERS

# Schema contract for type enforcement and classified-field identification.
from silver.schema_validator import (
    enforce_schema,
    get_classified_fields,
    load_contract,
)

# ---------------------------------------------------------------------------
# PII / classified field masking
# ---------------------------------------------------------------------------

# Hard-coded fallback list - used when the contract file is unavailable.
# The contract-derived list always takes precedence.
_PII_FALLBACK = [
    "vorname",
    "nachname",
    "name",
    "geburtsdatum",
    "patient_name",
    "patient_vorname",
    "patient_nachname",
    "address",
    "strasse",
    "hausnummer",
]


def _hash_value(value) -> Optional[str]:
    """One-way SHA-256 hash of a PII value; returns None for missing inputs.

    PII hashes use 32 hex chars (128 bits) for strong collision resistance:
    the same real-world person must never hash to the same token as another.
    This is intentionally longer than the 24-char unique_mission_id used in
    matcher.py, which links records (not people) and has a much smaller
    collision universe.
    """
    if pd.isna(value) or value == "":
        return None
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:32]


def mask_pii(df: pd.DataFrame, extra_fields: Optional[list] = None) -> pd.DataFrame:
    """
    Replace classified/PII columns with a one-way SHA-256 hash (32 hex chars).

    The list of columns to mask is taken from the einsatzdaten Data Contract
    (silver/schema/einsatzdaten_contract.yaml), falling back to a
    hard-coded list if the contract cannot be loaded.  Primary-key columns
    (e.g. EINSATZ_NR) are excluded from masking even if tagged classified.

    Parameters
    ----------
    df : pd.DataFrame
        Input data that may contain classified/PII columns.
    extra_fields : list, optional
        Additional column names to mask beyond the contract list.

    Returns
    -------
    pd.DataFrame
        DataFrame with classified columns replaced by hashed values.
    """
    try:
        contract_fields = get_classified_fields()
    except Exception:  # noqa: BLE001
        contract_fields = _PII_FALLBACK

    fields_to_mask = list(set(contract_fields + _PII_FALLBACK + (extra_fields or [])))
    df = df.copy()
    for col in fields_to_mask:
        if col in df.columns:
            df[col] = df[col].apply(_hash_value)
    return df


# ---------------------------------------------------------------------------
# NIDA preparation  (mirrors the Index + Details merge every page performs)
# ---------------------------------------------------------------------------


def prepare_nida_silver(db, limit: int = 999999) -> pd.DataFrame:
    """
    Build the prepared NIDA Silver dataset from a live MongoDB connection.

    This reproduces exactly what the Streamlit pages do:

    1. Load Index via LOADERS["Index"] (nida_index collection).
    2. Load Details via LOADERS["Details"] (protocols_details).
    3. Merge on protocolId (outer join, same as in the pages).
    4. Drop the internal _id column from both sides.
    5. Remove duplicate columns (same guard as data_loading.py).
    6. Mask PII/classified fields.

    Parameters
    ----------
    db : pymongo.database.Database
        An open MongoDB database handle (from get_mongodb_connection()).
    limit : int
        Maximum documents to fetch from each collection.

    Returns
    -------
    pd.DataFrame
        Merged, cleaned, PII-masked NIDA dataset.
    """
    print("[transformers] Loading NIDA Index ...")
    index_df = LOADERS["Index"](db, limit=limit)

    print("[transformers] Loading NIDA Details ...")
    details_df = LOADERS["Details"](db, limit=limit)

    if index_df.empty and details_df.empty:
        return pd.DataFrame()

    # Merge exactly as the Streamlit pages do
    if not index_df.empty and not details_df.empty:
        merged = pd.merge(
            index_df.drop(columns=["_id"], errors="ignore"),
            details_df.drop(columns=["_id"], errors="ignore"),
            on="protocolId",
            how="outer",
            suffixes=("", "_details"),
        )
    elif not index_df.empty:
        merged = index_df.drop(columns=["_id"], errors="ignore")
    else:
        merged = details_df.drop(columns=["_id"], errors="ignore")

    # Remove duplicate columns (same guard used in data_loading.cached_db_query)
    merged = merged.loc[:, ~merged.columns.duplicated()]

    merged = mask_pii(merged)
    return merged


# ---------------------------------------------------------------------------
# LST / ETU preparation  (mirrors ETU loading + Eckpunktevereinbarung)
# ---------------------------------------------------------------------------

# "Flo SL" prefix present on raw LST callsigns but absent from NIDA rufname
_FLO_SL_PREFIX = re.compile(r"^Flo\s+SL\s*", re.IGNORECASE)


def normalize_lst_callsign(callsign: str) -> Optional[str]:
    """
    Strip the "Flo SL" prefix from a raw LST callsign.

    Examples
    --------
    >>> normalize_lst_callsign("Flo SL RTW 1")
    'RTW 1'
    >>> normalize_lst_callsign("RTW 1")
    'RTW 1'
    """
    if pd.isna(callsign):
        return None
    return _FLO_SL_PREFIX.sub("", str(callsign)).strip()


def prepare_etu_silver(
    mariadb_conn,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Build the prepared ETU/LST Silver dataset from a live MariaDB connection.

    Steps (same logic as the Streamlit pages that use ETU data):

    1. Load the full einsatzdaten table via LOADERS["ETU"].
    2. Normalise callsigns: strip the "Flo SL" prefix from EINSATZMITTEL.
    3. Apply reduce_etu_eckpunktevereinbarung when start_date/end_date given.
    4. Deduplicate on EINSATZ_NR.
    5. Enforce the einsatzdaten Data Contract schema (type casting +
       validation of each column declared in the YAML contract).
    6. Remove duplicate columns.
    7. Mask classified/PII fields.

    Parameters
    ----------
    mariadb_conn
        An open MariaDB connection (from get_mariadb_connection()).
    start_date : str or datetime-like, optional
        Lower bound for the Eckpunktevereinbarung date filter (ALARMIERT).
    end_date : str or datetime-like, optional
        Upper bound (exclusive) for the date filter.

    Returns
    -------
    pd.DataFrame
        Schema-validated, deduplicated, PII-masked ETU dataset.
    """
    print("[transformers] Loading ETU data from MariaDB ...")
    df = LOADERS["ETU"](mariadb_conn)

    if df.empty:
        return df

    # 1. Normalise callsigns
    if "EINSATZMITTEL" in df.columns:
        df["EINSATZMITTEL"] = df["EINSATZMITTEL"].apply(normalize_lst_callsign)

    # 2. Eckpunktevereinbarung filter / deduplication
    if start_date is not None and end_date is not None:
        df = reduce_etu_eckpunktevereinbarung(df, start_date, end_date)
    else:
        if "EINSATZ_NR" in df.columns:
            if "ALARMIERT" in df.columns:
                df = df.sort_values("ALARMIERT")
            df = df.drop_duplicates(subset=["EINSATZ_NR"], keep="first")

    # 3. Enforce Data Contract schema (cast types, collect warnings)
    try:
        contract = load_contract()
        df, schema_errors = enforce_schema(df, contract)
        if schema_errors:
            for err in schema_errors:
                print(f"[transformers] Schema warning: {err}")
    except Exception as exc:  # noqa: BLE001
        print(f"[transformers] Schema enforcement skipped: {exc}")

    # 4. Remove duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]

    # 5. Mask classified/PII fields
    df = mask_pii(df)
    return df


# ---------------------------------------------------------------------------
# Linking LST <-> NIDA
# ---------------------------------------------------------------------------


def link_lst_nida(
    df_etu: pd.DataFrame,
    df_nida: pd.DataFrame,
    etu_key: str = "EINSATZ_NR",
    nida_key: str = "ein_nr_lst",
) -> pd.DataFrame:
    """
    Join the prepared ETU and NIDA Silver DataFrames on their shared mission ID.

    The result has one row per ETU mission, enriched with NIDA protocol
    attributes where a matching protocol exists.

    Parameters
    ----------
    df_etu : pd.DataFrame
        Output of prepare_etu_silver.
    df_nida : pd.DataFrame
        Output of prepare_nida_silver.
    etu_key : str
        Join key in the ETU frame (default: EINSATZ_NR).
    nida_key : str
        Join key in the NIDA frame (default: ein_nr_lst).

    Returns
    -------
    pd.DataFrame
        Left-joined result enriched with NIDA attributes.
        Returns an empty DataFrame if either input is empty.
    """
    if df_etu.empty or df_nida.empty:
        return pd.DataFrame()

    linked = pd.merge(
        df_etu,
        df_nida.rename(columns={nida_key: etu_key}),
        on=etu_key,
        how="left",
        suffixes=("_etu", "_nida"),
    )
    # Remove any duplicate columns introduced by the merge
    linked = linked.loc[:, ~linked.columns.duplicated()]
    return linked
