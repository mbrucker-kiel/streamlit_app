"""
Schema validator: parse the einsatzdaten Data Contract YAML and enforce
column types, validate presence, and identify classified/PII fields.

The contract lives at silver/schema/einsatzdaten_contract.yaml and follows
the Open Data Contract Standard (ODCS) format.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import yaml

_CONTRACT_PATH = Path(__file__).parent / "schema" / "einsatzdaten_contract.yaml"

# ---------------------------------------------------------------------------
# logicalType → pandas cast
# ---------------------------------------------------------------------------
# Timestamps are always coerced to UTC-aware datetime64 so that the Silver
# layer has a single, unambiguous time representation.
# String caster: convert to str while preserving NaN/None as pd.NA
# (s.astype(str) alone would turn NaN into the literal string "nan").
_CASTERS = {
    "string": lambda s: s.astype(str).where(s.notna()),
    "timestamp": lambda s: pd.to_datetime(s, errors="coerce", utc=True),
    "boolean": lambda s: s.astype("boolean"),
    "integer": lambda s: pd.to_numeric(s, errors="coerce").astype("Int64"),
    "number": lambda s: pd.to_numeric(s, errors="coerce"),
}

# Columns with tag "classified" that hold addresses / precise locations and
# must be masked with a one-way hash.  Primary key columns (EINSATZ_NR,
# EINSATZMITTEL) are excluded from masking even though they carry the tag,
# because they are needed for linking and aggregation.
_MASKING_EXCLUDED_PRIMARY_KEYS = {"EINSATZ_NR", "OBER_EINSATZ_NR", "EINSATZMITTEL"}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def load_contract(path: Optional[Path] = None) -> dict:
    """Load and parse the YAML data contract."""
    with open(path or _CONTRACT_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_field_specs(contract: Optional[dict] = None) -> List[dict]:
    """Return the list of field-spec dicts from the first schema entry."""
    if contract is None:
        contract = load_contract()
    schemas = contract.get("schema", [])
    return schemas[0].get("properties", []) if schemas else []


def get_classified_fields(contract: Optional[dict] = None) -> List[str]:
    """
    Return columns tagged *classified* in the contract that should be masked.

    Primary-key columns are excluded because they are required for record
    linkage even though they appear in the classified list.
    """
    return [
        f["name"]
        for f in get_field_specs(contract)
        if "classified" in f.get("tags", [])
        and f["name"] not in _MASKING_EXCLUDED_PRIMARY_KEYS
    ]


def get_timestamp_fields(contract: Optional[dict] = None) -> List[str]:
    """Return columns declared as *timestamp* in the contract."""
    return [
        f["name"]
        for f in get_field_specs(contract)
        if f.get("logicalType") == "timestamp"
    ]


# ---------------------------------------------------------------------------
# Schema enforcement
# ---------------------------------------------------------------------------


def enforce_schema(
    df: pd.DataFrame,
    contract: Optional[dict] = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Cast each column that is present in *df* to the type declared in the
    data contract.

    Columns absent from *df* are silently skipped (the contract may describe
    columns that are optional or not yet populated).

    Parameters
    ----------
    df : pd.DataFrame
        Input data – typically the raw output of a loader or transformer.
    contract : dict, optional
        Pre-parsed YAML contract.  Loaded from the default path when *None*.

    Returns
    -------
    (df_enforced, errors)
        *df_enforced* has columns cast to their contract types.
        *errors* is a list of warning strings for columns that could not be
        cast; these are logged but do not abort the pipeline.
    """
    if contract is None:
        contract = load_contract()

    errors: List[str] = []
    df = df.copy()

    for field in get_field_specs(contract):
        col = field["name"]
        logical = field.get("logicalType", "string")

        if col not in df.columns:
            continue  # optional – not an error

        caster = _CASTERS.get(logical)
        if caster is None:
            errors.append(
                f"No caster registered for logicalType '{logical}' "
                f"(column '{col}') – column left as-is."
            )
            continue

        try:
            df[col] = caster(df[col])
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Cast failed for '{col}' → {logical}: {exc}")

    return df, errors
