"""
Silver-layer data interface backed by DuckDB.

Provides a single, stable entry-point for loading *prepared* (Silver) data
from MinIO.  Contractors and ML engineers only need to know the dataset
name and optional column filters -- no knowledge of S3 folder structure,
Parquet layout, or database credentials is required.

All functions are pure Python (no Streamlit dependency) and work from:
  * Streamlit pages
  * Jupyter notebooks
  * ML training scripts
  * External contractor tooling

Query modes
-----------
1. Dict filter  (simple equality / list-in filter):

       df = query_silver("etu", filter={"EINSATZMITTELTYP": "RTW"})

2. Raw SQL  (full DuckDB SQL, table name is the dataset name):

       df = query_silver("linked", sql="SELECT * FROM linked LIMIT 100")

How it works
------------
Each call to query_silver:
  1. Downloads the requested Silver Parquet file from MinIO into memory via
     the existing minio_client (boto3).
  2. Registers the in-memory DataFrame as a DuckDB virtual table.
  3. Executes the filter/SQL predicate entirely inside DuckDB.
  4. Returns the result as a pandas DataFrame.

The DuckDB approach gives contractors the full power of SQL (window
functions, aggregations, JOINs across datasets) without exposing raw
S3 credentials or requiring any local file system setup.

Usage example::

    from silver.data_interface import query_silver

    # Simple filter
    df = query_silver("etu", filter={"EINSATZMITTELTYP": "Rettungswagen (RTW)"})

    # Multiple values in filter
    df = query_silver("etu", filter={"EINSATZMITTELTYP": ["RTW", "NEF"]})

    # Raw SQL across a dataset
    df = query_silver("linked", sql=\"\"\"
        SELECT EINSATZ_NR, EINSATZMITTELTYP, COUNT(*) AS n
        FROM   linked
        GROUP  BY 1, 2
        ORDER  BY 3 DESC
    \"\"\")

    # Cross-dataset analysis: join ETU matches with NIDA data
    df = query_silver_sql(\"\"\"
        SELECT m.unique_mission_id,
               m.match_probability,
               e.EINSATZMITTELTYP,
               n.missionType
        FROM   matches  m
        JOIN   etu      e ON e.EINSATZ_NR  = m.einsatz_nr
        JOIN   nida     n ON n.ein_nr_lst  = m.einsatz_nr
        WHERE  m.match_probability >= 0.9
    \"\"\")
"""

from __future__ import annotations

from typing import Optional

import duckdb
import pandas as pd

from silver.minio_client import SILVER_BUCKET, read_parquet

# Object keys -- must stay in sync with silver/pipeline.py
_DATASETS: dict = {
    "nida": "nida/nida_silver.parquet",
    "etu": "etu/etu_silver.parquet",
    "linked": "linked/etu_nida_silver.parquet",
    "matches": "matches/etu_nida_matches.parquet",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_dataset(name: str) -> pd.DataFrame:
    """Read a Silver Parquet file from MinIO into a DataFrame."""
    if name not in _DATASETS:
        raise ValueError(
            f"Unknown Silver dataset '{name}'. "
            f"Valid options: {sorted(_DATASETS.keys())}"
        )
    key = _DATASETS[name]
    df = read_parquet(key, bucket=SILVER_BUCKET)
    if df.empty:
        print(
            f"[data_interface] Silver dataset '{name}' not found at "
            f"s3://{SILVER_BUCKET}/{key}. "
            "Run silver.pipeline.run_pipeline() first."
        )
    return df


def _build_where_clause(filters: dict) -> tuple:
    """
    Convert a filter dict into a DuckDB parameterised WHERE clause.

    Supports scalar equality (col = ?) and list membership (col IN (?,...)).
    Returns (where_sql, params_list).
    """
    clauses = []
    params = []
    for col, value in filters.items():
        if isinstance(value, (list, tuple, set)):
            placeholders = ", ".join(["?"] * len(value))
            clauses.append(f'"{col}" IN ({placeholders})')
            params.extend(list(value))
        else:
            clauses.append(f'"{col}" = ?')
            params.append(value)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def query_silver(
    dataset: str,
    filter: Optional[dict] = None,  # noqa: A002
    sql: Optional[str] = None,
) -> pd.DataFrame:
    """
    Query a Silver dataset using DuckDB.

    Parameters
    ----------
    dataset : {"etu", "nida", "linked", "matches"}
        Which Silver dataset to query.
    filter : dict, optional
        Column equality filters.  Supports scalar and list values, e.g.::

            {"EINSATZMITTELTYP": "Rettungswagen (RTW)"}
            {"EINSATZMITTELTYP": ["Rettungswagen (RTW)", "NEF"]}

    sql : str, optional
        Full DuckDB SQL statement.  The dataset is available as a virtual
        table with the same name as the *dataset* argument.  When *sql* is
        provided, *filter* is ignored.

    Returns
    -------
    pd.DataFrame
        Query results.

    Raises
    ------
    ValueError
        If *dataset* is not a known name.
    """
    df_source = _load_dataset(dataset)
    if df_source.empty:
        return df_source

    conn = duckdb.connect()
    conn.register(dataset, df_source)

    if sql:
        return conn.execute(sql).df()

    if filter:
        where, params = _build_where_clause(filter)
        stmt = f'SELECT * FROM "{dataset}" {where}'
        return conn.execute(stmt, params).df()

    return conn.execute(f'SELECT * FROM "{dataset}"').df()


def query_silver_sql(sql: str) -> pd.DataFrame:
    """
    Execute arbitrary DuckDB SQL across *all* Silver datasets simultaneously.

    All datasets are pre-registered as virtual tables:
      * ``etu``     -- ETU/LST dispatch data
      * ``nida``    -- NIDA protocol data
      * ``linked``  -- ETU left-joined with NIDA
      * ``matches`` -- Splink match table with unique_mission_id

    Datasets that are not yet available in MinIO are registered as empty
    DataFrames so the SQL still runs (rows simply won't appear).

    Parameters
    ----------
    sql : str
        DuckDB SQL statement that may reference any of the four table names.

    Returns
    -------
    pd.DataFrame
    """
    conn = duckdb.connect()

    for name in _DATASETS:
        df = read_parquet(_DATASETS[name], bucket=SILVER_BUCKET)
        conn.register(name, df if not df.empty else pd.DataFrame())

    return conn.execute(sql).df()


def get_silver_etu(filter: Optional[dict] = None) -> pd.DataFrame:  # noqa: A002
    """Return the prepared Silver ETU dataset, optionally filtered."""
    return query_silver("etu", filter=filter)


def get_silver_nida(filter: Optional[dict] = None) -> pd.DataFrame:  # noqa: A002
    """Return the prepared Silver NIDA dataset, optionally filtered."""
    return query_silver("nida", filter=filter)


def get_silver_linked(filter: Optional[dict] = None) -> pd.DataFrame:  # noqa: A002
    """Return the Silver ETU + NIDA linked dataset, optionally filtered."""
    return query_silver("linked", filter=filter)


def get_silver_matches(filter: Optional[dict] = None) -> pd.DataFrame:  # noqa: A002
    """Return the Splink match table (unique_mission_id, match_probability)."""
    return query_silver("matches", filter=filter)


def list_silver_datasets() -> list:
    """Return the known Silver dataset names."""
    return sorted(_DATASETS.keys())
