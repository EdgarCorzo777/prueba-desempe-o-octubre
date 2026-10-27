"""
spark_transformer.py
Airflow Task Wrapper for Spark/Medallion processing.
"""

import logging
from typing import Dict, Any, Optional
from spark.jobs.process_medallion import run_medallion_pipeline

logger = logging.getLogger("sismowatch.transformer")

def execute_medallion_transformations(execution_id: str) -> Dict[str, Any]:
    """
    Executes the Silver & Gold Medallion transformations and quality validation.
    Called from Airflow DAG 2.
    """
    logger.info(f"Triggering Medallion transformation task for execution {execution_id}")
    result = run_medallion_pipeline(execution_id)
    return result
