"""
Probabilistic record linkage between ETU (LST/Dispatch) and NIDA (Protocol)
datasets using Splink 4.

Matching keys
-------------
Both datasets are projected onto a common schema before Splink sees them:

  ETU column         NIDA column        Comparison
  -----------------  -----------------  ------------------------------------
  EINSATZ_NR         ein_nr_lst         Exact match (primary blocker)
  EINSATZMITTEL      rufname            Jaro-Winkler >= 0.88 / 0.70
  ALARMIERT          alarm_datetime     (used as UTC ts for context)

Output columns
--------------
  unique_mission_id   Stable SHA-256-based identifier linking one ETU mission
                      to one NIDA protocol.  Deterministic: same inputs ->
                      same ID across pipeline runs.
  einsatz_nr          The matched ETU mission number.
  protocol_id         The matched NIDA protocolId.
  match_probability   Splink posterior match probability (0-1).

Graceful degradation
--------------------
If splink is not installed the module falls back to a deterministic exact
join on EINSATZ_NR / ein_nr_lst with match_probability = 1.0.
"""

from __future__ import annotations

import hashlib

import pandas as pd

try:
    import splink.comparison_library as cl
    from splink import DuckDBAPI, Linker, SettingsCreator, block_on

    _SPLINK_AVAILABLE = True
except ImportError:
    _SPLINK_AVAILABLE = False

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Column mapping: ETU column name -> common schema name used during matching
_ETU_COL_MAP: dict = {
    "EINSATZ_NR": "einsatz_nr",
    "EINSATZMITTEL": "callsign",
    "ALARMIERT": "alarm_ts",
}

# Column mapping: NIDA column name -> common schema name
_NIDA_COL_MAP: dict = {
    "ein_nr_lst": "einsatz_nr",
    "rufname": "callsign",
    "alarm_datetime": "alarm_ts",
}

_OUTPUT_COLS = ["unique_mission_id", "einsatz_nr", "protocol_id", "match_probability"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mission_id(einsatz_nr, protocol_id) -> str:
    """
    Return a stable, unique mission identifier derived from the matched pair.

    The ID is the first 24 hex characters of SHA-256(einsatz_nr::protocol_id).
    Deterministic: re-running the pipeline with the same data produces the
    same IDs, enabling idempotent writes to the Silver bucket.
    """
    key = f"{einsatz_nr}::{protocol_id}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def _to_utc(series: pd.Series) -> pd.Series:
    """Coerce a series to timezone-aware UTC datetime, ignoring errors."""
    return pd.to_datetime(series, errors="coerce", utc=True)


def _deterministic_match(
    df_etu: pd.DataFrame,
    df_nida: pd.DataFrame,
) -> pd.DataFrame:
    """
    Fallback: exact inner join on EINSATZ_NR / ein_nr_lst.

    Used when splink is not installed or when Splink training fails.
    All matched pairs receive match_probability = 1.0.
    """
    if "EINSATZ_NR" not in df_etu.columns or "ein_nr_lst" not in df_nida.columns:
        return pd.DataFrame(columns=_OUTPUT_COLS)

    nida_sub = df_nida[["ein_nr_lst", "protocolId"]].copy()
    nida_sub["ein_nr_lst"] = nida_sub["ein_nr_lst"].astype(str)
    etu_sub = df_etu[["EINSATZ_NR"]].copy()
    etu_sub["EINSATZ_NR"] = etu_sub["EINSATZ_NR"].astype(str)

    merged = pd.merge(
        etu_sub,
        nida_sub,
        left_on="EINSATZ_NR",
        right_on="ein_nr_lst",
        how="inner",
    )
    merged["match_probability"] = 1.0
    merged["unique_mission_id"] = merged.apply(
        lambda r: _make_mission_id(r["EINSATZ_NR"], r["protocolId"]), axis=1
    )
    merged = merged.rename(
        columns={"EINSATZ_NR": "einsatz_nr", "protocolId": "protocol_id"}
    )
    return merged[_OUTPUT_COLS].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def match_etu_nida(
    df_etu: pd.DataFrame,
    df_nida: pd.DataFrame,
    threshold: float = 0.7,
    training_recall: float = 0.8,
    training_max_pairs: int = 1_000_000,
) -> pd.DataFrame:
    """
    Probabilistically link ETU missions to NIDA protocols using Splink 4.

    The function projects both DataFrames onto a common two-column schema
    (einsatz_nr, callsign), runs Splink with DuckDB as the compute backend,
    trains model parameters using unsupervised EM, and returns all candidate
    pairs whose match_probability >= threshold.

    A stable unique_mission_id is generated for every returned pair so that
    downstream consumers can reference a specific ETU<->NIDA match without
    embedding raw IDs.

    Parameters
    ----------
    df_etu : pd.DataFrame
        Output of prepare_etu_silver.
    df_nida : pd.DataFrame
        Output of prepare_nida_silver.
    threshold : float
        Minimum match_probability to include (default 0.7).
    training_recall : float
        Recall estimate for ``estimate_probability_two_random_records_match``.
        Represents the proportion of true matches captured by the blocking
        rule on ``einsatz_nr``.  0.8 is a conservative starting point;
        increase toward 1.0 if the EINSATZ_NR values are clean and
        consistent across both sources (default 0.8).
    training_max_pairs : int
        Maximum record pairs sampled for ``estimate_u_using_random_sampling``.
        Higher values give more accurate u-probability estimates at the cost
        of compute time.  1 000 000 is appropriate for datasets up to ~100 k
        records; reduce for faster iteration during development (default
        1_000_000).

    Returns
    -------
    pd.DataFrame
        Columns: unique_mission_id, einsatz_nr, protocol_id,
        match_probability.  Empty DataFrame if either input is empty.
    """
    if df_etu.empty or df_nida.empty:
        return pd.DataFrame(columns=_OUTPUT_COLS)

    if not _SPLINK_AVAILABLE:
        print("[matcher] splink not available -- using deterministic fallback")
        return _deterministic_match(df_etu, df_nida)

    # ------------------------------------------------------------------ #
    # 1.  Project to common schema
    # ------------------------------------------------------------------ #
    etu_present = [c for c in _ETU_COL_MAP if c in df_etu.columns]
    nida_present = [c for c in _NIDA_COL_MAP if c in df_nida.columns]

    # Left table  (ETU)
    etu_extra = ["protocolId"] if "protocolId" in df_etu.columns else []
    df_l = df_etu[etu_present + etu_extra].copy()
    df_l = df_l.rename(columns={k: v for k, v in _ETU_COL_MAP.items() if k in df_l})
    df_l["unique_id"] = "etu_" + df_l["einsatz_nr"].astype(str)
    if "alarm_ts" in df_l.columns:
        df_l["alarm_ts"] = _to_utc(df_l["alarm_ts"])

    # Right table  (NIDA)
    nida_proto = ["protocolId"] if "protocolId" in df_nida.columns else []
    df_r = df_nida[nida_present + nida_proto].copy()
    df_r = df_r.rename(columns={k: v for k, v in _NIDA_COL_MAP.items() if k in df_r})
    df_r["unique_id"] = "nida_" + df_r["protocolId"].astype(str)
    if "alarm_ts" in df_r.columns:
        df_r["alarm_ts"] = _to_utc(df_r["alarm_ts"])

    # ------------------------------------------------------------------ #
    # 2.  Build Splink comparisons (only for columns present in both)
    # ------------------------------------------------------------------ #
    comparisons = [
        cl.ExactMatch("einsatz_nr").configure(term_frequency_adjustments=True)
    ]
    if "callsign" in df_l.columns and "callsign" in df_r.columns:
        comparisons.append(cl.JaroWinklerAtThresholds("callsign", [0.88, 0.7]))

    settings = SettingsCreator(
        link_type="link_only",
        blocking_rules_to_generate_predictions=[block_on("einsatz_nr")],
        comparisons=comparisons,
        retain_intermediate_calculation_columns=False,
    )

    # ------------------------------------------------------------------ #
    # 3.  Train and predict
    # ------------------------------------------------------------------ #
    try:
        linker = Linker([df_l, df_r], settings, db_api=DuckDBAPI())

        # Unsupervised training -- no labelled data required.
        # recall=training_recall: estimated share of true matches captured by
        # the einsatz_nr blocking rule; used to set the match prior.
        linker.training.estimate_probability_two_random_records_match(
            [block_on("einsatz_nr")], recall=training_recall
        )
        # max_pairs controls the random sample used to estimate u-probabilities
        # (non-match rate for each feature level).
        linker.training.estimate_u_using_random_sampling(
            max_pairs=training_max_pairs
        )
        linker.training.estimate_parameters_using_expectation_maximisation(
            block_on("einsatz_nr"), estimate_without_term_frequencies=True
        )

        preds = linker.inference.predict(threshold_match_probability=threshold)
        pred_df = preds.as_pandas_dataframe()

    except Exception as exc:  # noqa: BLE001
        print(f"[matcher] Splink error ({exc}) -- using deterministic fallback")
        return _deterministic_match(df_etu, df_nida)

    # ------------------------------------------------------------------ #
    # 4.  Build output with unique_mission_id
    # ------------------------------------------------------------------ #
    # Splink link_only output: einsatz_nr_l, einsatz_nr_r, protocolId_r,
    # match_probability
    proto_col = "protocolId_r" if "protocolId_r" in pred_df.columns else None

    rows = []
    for _, row in pred_df.iterrows():
        enr = row.get("einsatz_nr_l", row.get("einsatz_nr", ""))
        proto = row.get(proto_col) if proto_col else None
        rows.append(
            {
                "unique_mission_id": _make_mission_id(enr, proto or ""),
                "einsatz_nr": enr,
                "protocol_id": proto,
                "match_probability": float(row.get("match_probability", 0.0)),
            }
        )

    result = pd.DataFrame(rows, columns=_OUTPUT_COLS)
    return result.reset_index(drop=True)
