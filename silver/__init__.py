"""
silver -- database -> Silver data pipeline and query interface.

Pipeline (run once after the daily Airbyte sync)::

    from silver import run_pipeline
    run_pipeline(start_date="2024-01-01", end_date="2025-01-01")

Query interface (for contractors and ML engineers)::

    from silver.data_interface import query_silver, query_silver_sql

    # Simple filter
    df = query_silver("etu", filter={"EINSATZMITTELTYP": "Rettungswagen (RTW)"})

    # Full SQL across all Silver datasets
    df = query_silver_sql(\"\"\"
        SELECT m.unique_mission_id, m.match_probability, e.EINSATZMITTELTYP
        FROM   matches m
        JOIN   etu     e ON e.EINSATZ_NR = m.einsatz_nr
        WHERE  m.match_probability >= 0.9
    \"\"\")
"""

from silver.pipeline import run_pipeline
from silver.data_interface import (
    get_silver_etu,
    get_silver_linked,
    get_silver_matches,
    get_silver_nida,
    list_silver_datasets,
    query_silver,
    query_silver_sql,
)

__all__ = [
    "run_pipeline",
    "query_silver",
    "query_silver_sql",
    "get_silver_etu",
    "get_silver_nida",
    "get_silver_linked",
    "get_silver_matches",
    "list_silver_datasets",
]
