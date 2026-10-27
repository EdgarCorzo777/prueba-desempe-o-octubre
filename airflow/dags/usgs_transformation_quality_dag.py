"""
usgs_transformation_quality_dag.py
DAG 2: Cleanses, validates and promotes records from Bronze to Silver and Gold.
Executes blocking quality checks, quarantines invalid records, and detects anomalies.
"""

import sys
import os
from datetime import datetime, timedelta
import logging

# Ensure include directory is in sys.path
for p in ["/opt/airflow", "/opt/airflow/include", os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))]:
    if p not in sys.path:
        sys.path.insert(0, p)

from airflow import DAG

# Airflow 3 & Airflow 2 dual compatibility
try:
    from airflow.providers.standard.operators.python import PythonOperator
except ImportError:
    from airflow.operators.python import PythonOperator

try:
    from include.transformations.spark_transformer import execute_medallion_transformations
    from include.analytics.anomaly_detector import detect_seismic_anomalies
except ImportError:
    from airflow.include.transformations.spark_transformer import execute_medallion_transformations
    from airflow.include.analytics.anomaly_detector import detect_seismic_anomalies

logger = logging.getLogger("airflow.dag.usgs_transformation")

def failure_alert_callback(context):
    task_id = context.get("task_instance").task_id
    dag_id = context.get("dag").dag_id
    exec_date = context.get("execution_date")
    error = context.get("exception")
    logger.error(f"ALERT: Transformation/Quality task {task_id} failed in {dag_id} on {exec_date}: {error}")

default_args = {
    "owner": "sismowatch_data_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(seconds=20),
    "execution_timeout": timedelta(minutes=5),
    "on_failure_callback": failure_alert_callback
}

with DAG(
    dag_id="usgs_transformation_quality",
    default_args=default_args,
    description="Procesamiento Medallion, validación de calidad y promoción Silver/Gold",
    schedule=None, # Triggered exclusively by DAG 1
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["sismowatch", "transformation", "silver", "gold", "quality"],
    doc_md="""
    # DAG de Transformación y Calidad (Medallion)
    - Consume datos desde `raw.usgs_earthquakes_raw`.
    - Ejecuta validaciones geofísicas bloqueantes.
    - Registra anomalías o violaciones en `staging.quarantine_events`.
    - Publica únicamente datos aprobados en `curated.events`.
    - Dispara detector de enjambres y picos de magnitud.
    """
) as dag:

    def transform_task(**context):
        run_id = context.get("run_id", f"trans_{int(datetime.now().timestamp())}")
        result = execute_medallion_transformations(run_id)
        return {
            "processed": result.get("valid_count", 0),
            "quarantined": result.get("quarantined_count", 0),
            "score": result.get("quality_score", 100.0)
        }

    def anomaly_task(**context):
        alerts = detect_seismic_anomalies(hours_window=48, z_threshold=2.5)
        return {"detected_alerts_count": len(alerts)}

    transform_op = PythonOperator(
        task_id="medallion_silver_gold_processing",
        python_callable=transform_task
    )

    anomaly_op = PythonOperator(
        task_id="seismic_anomaly_detection",
        python_callable=anomaly_task
    )

    transform_op >> anomaly_op
