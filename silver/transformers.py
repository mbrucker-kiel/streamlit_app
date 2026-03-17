"""
Data transformers for the Bronze → Silver cleaning step.

All transformation functions are plain Python – no Streamlit dependency – so
they can be used both from the Silver pipeline and from within the Streamlit app.

The existing ``data_filtering.py`` helpers are imported directly so that the
cleaning logic is defined in exactly one place.
"""

import hashlib
import re
from typing import Optional

import pandas as pd

# Reuse the existing Eckpunktevereinbarung filter that already lives in
# data_filtering.py – no duplication.
from data_filtering import reduce_etu_eckpunktevereinbarung

# ---------------------------------------------------------------------------
# LST / Dispatch transformers
# ---------------------------------------------------------------------------

# Prefix that appears on LST callsigns but not on NIDA rufname
_FLO_SL_PREFIX = re.compile(r"^Flo\s+SL\s*", re.IGNORECASE)


def normalize_lst_callsign(callsign: str) -> Optional[str]:
    """
    Strip the "Flo SL" prefix from a raw LST callsign.

    Examples
    --------
    >>> normalize_lst_callsign("Flo SL RTW 1")
    'RTW 1'
    >>> normalize_lst_callsign("Flo SL S-KTW 2")
    'S-KTW 2'
    >>> normalize_lst_callsign("RTW 1")
    'RTW 1'
    """
    if pd.isna(callsign):
        return None
    return _FLO_SL_PREFIX.sub("", str(callsign)).strip()


def clean_lst(
    df_lst: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Apply the full LST Silver transformation:

    1. Normalise callsigns (strip "Flo SL" prefix from ``EINSATZMITTEL``).
    2. Apply :func:`~data_filtering.reduce_etu_eckpunktevereinbarung` when
       *start_date* / *end_date* are given.
    3. Deduplicate on ``EINSATZ_NR`` (keep first occurrence after sorting by
       alarm time).

    Parameters
    ----------
    df_lst : pd.DataFrame
        Raw Bronze LST data.
    start_date : str or datetime-like, optional
        Lower bound for the Eckpunktevereinbarung filter.  If omitted the
        entire date range is kept.
    end_date : str or datetime-like, optional
        Upper bound (exclusive) for the filter.

    Returns
    -------
    pd.DataFrame
        Cleaned LST data.
    """
    if df_lst.empty:
        return df_lst

    df = df_lst.copy()

    # 1. Normalise callsign
    if "EINSATZMITTEL" in df.columns:
        df["EINSATZMITTEL"] = df["EINSATZMITTEL"].apply(normalize_lst_callsign)

    # 2. Eckpunktevereinbarung filter (requires date bounds)
    if start_date is not None and end_date is not None:
        df = reduce_etu_eckpunktevereinbarung(df, start_date, end_date)

    # 3. Deduplicate – reduce_etu_eckpunktevereinbarung already does this
    #    when start/end dates are provided; apply it here as a safety net
    #    for the no-date path too.
    if "EINSATZ_NR" in df.columns and not df.empty:
        if "ALARMIERT" in df.columns:
            df = df.sort_values("ALARMIERT")
        df = df.drop_duplicates(subset=["EINSATZ_NR"], keep="first")

    return df


# ---------------------------------------------------------------------------
# NIDA transformers
# ---------------------------------------------------------------------------


def combine_nida_alarm_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge the split ``datum_alarm`` and ``zeit_alarm`` fields into a single
    ``alarm_datetime`` column.

    Parameters
    ----------
    df : pd.DataFrame
        Raw NIDA index data containing ``datum_alarm`` and ``zeit_alarm``.

    Returns
    -------
    pd.DataFrame
        DataFrame with an additional ``alarm_datetime`` column (datetime64).
    """
    if df.empty:
        return df

    df = df.copy()

    if "datum_alarm" in df.columns and "zeit_alarm" in df.columns:
        df["alarm_datetime"] = pd.to_datetime(
            df["datum_alarm"].astype(str) + " " + df["zeit_alarm"].astype(str),
            dayfirst=True,
            errors="coerce",
        )

    return df


def clean_nida(df_nida: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the full NIDA Silver transformation:

    1. Combine split date/time alarm fields into ``alarm_datetime``.
    2. Deduplicate on ``ein_nr_lst`` (keeping the most recent alarm_datetime).
    3. Mask PII fields (see :func:`mask_pii`).

    Parameters
    ----------
    df_nida : pd.DataFrame
        Raw Bronze NIDA index data.

    Returns
    -------
    pd.DataFrame
        Cleaned NIDA data.
    """
    if df_nida.empty:
        return df_nida

    df = combine_nida_alarm_datetime(df_nida)

    # Deduplicate on mission-link field – keep the most recent protocol
    if "ein_nr_lst" in df.columns:
        if "alarm_datetime" in df.columns:
            df = df.sort_values("alarm_datetime", ascending=False)
        df = df.drop_duplicates(subset=["ein_nr_lst"], keep="first")

    df = mask_pii(df)

    return df


# ---------------------------------------------------------------------------
# PII masking
# ---------------------------------------------------------------------------

# Fields known to contain personal data that must be masked for contractor use
_PII_FIELDS = [
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
    """SHA-256 hash of a value, returning None for missing/empty inputs."""
    if pd.isna(value) or value == "":
        return None
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def mask_pii(df: pd.DataFrame, extra_fields: Optional[list] = None) -> pd.DataFrame:
    """
    Replace PII fields with a one-way hash (first 16 hex chars of SHA-256).

    Parameters
    ----------
    df : pd.DataFrame
        Input data that may contain PII columns.
    extra_fields : list[str], optional
        Additional column names to mask beyond the default list.

    Returns
    -------
    pd.DataFrame
        DataFrame with PII columns replaced by hashed values.
    """
    fields_to_mask = _PII_FIELDS + (extra_fields or [])
    df = df.copy()
    for col in fields_to_mask:
        if col in df.columns:
            df[col] = df[col].apply(_hash_value)
    return df


# ---------------------------------------------------------------------------
# Linking LST ↔ NIDA
# ---------------------------------------------------------------------------


def link_lst_nida(
    df_lst: pd.DataFrame,
    df_nida: pd.DataFrame,
    lst_key: str = "EINSATZ_NR",
    nida_key: str = "ein_nr_lst",
) -> pd.DataFrame:
    """
    Join cleaned LST and NIDA DataFrames on their shared mission identifier.

    Parameters
    ----------
    df_lst : pd.DataFrame
        Cleaned LST data (output of :func:`clean_lst`).
    df_nida : pd.DataFrame
        Cleaned NIDA data (output of :func:`clean_nida`).
    lst_key : str
        Join key column in the LST frame.
    nida_key : str
        Join key column in the NIDA frame.

    Returns
    -------
    pd.DataFrame
        Left-joined result: all LST rows enriched with NIDA attributes.
        Returns an empty DataFrame if either input is empty.
    """
    if df_lst.empty or df_nida.empty:
        return pd.DataFrame()

    linked = pd.merge(
        df_lst,
        df_nida.rename(columns={nida_key: lst_key}),
        on=lst_key,
        how="left",
        suffixes=("_lst", "_nida"),
    )
    return linked
