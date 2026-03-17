"""
silver – Bronze → Silver data pipeline.

Public API::

    from silver import run_pipeline
    from silver.data_interface import query_silver, get_silver_linked
"""

from silver.pipeline import run_pipeline
from silver.data_interface import (
    get_silver_linked,
    get_silver_lst,
    get_silver_nida,
    list_silver_datasets,
    query_silver,
)

__all__ = [
    "run_pipeline",
    "query_silver",
    "get_silver_lst",
    "get_silver_nida",
    "get_silver_linked",
    "list_silver_datasets",
]
