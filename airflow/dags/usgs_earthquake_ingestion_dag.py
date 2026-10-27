"""
usgs_earthquake_ingestion_dag.py
DAG 1: Ingests USGS Realtime Feed every 5 minutes into Bronze (raw).
Triggers DAG 2 upon successful extraction.
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
    from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
except ImportError:
    from airflow.operators.python import PythonOperator
    from airflow.operators.trigger_dagrun import TriggerDagRunOperator

try:
    from include.ingestion.usgs_client import (
        fetch_usgs_feed,
        persist_raw_payloads,
        record_ingestion_metric
    )
    from include.config import settings
except ImportError:
    from airflow.include.ingestion.usgs_client import (
        fetch_usgs_feed,
        persist_raw_payloads,
        record_ingestion_metric
    )
    from airflow.include.config import settings

logger = logging.getLogger("airflow.dag.usgs_ingestion")

def failure_alert_callback(context):
    task_id = context.get("task_instance").task_id
    dag_id = context.get("dag").dag_id
    exec_date = context.get("execution_date")
    error = context.get("exception")
    logger.error(f"ALERT: Task {task_id} in {dag_id} failed on {exec_date}. Exception: {error}")

default_args = {
    "owner": "sismowatch_data_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=30),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=3),
    "on_failure_callback": failure_alert_callback
}

with DAG(
    dag_id="usgs_earthquake_ingestion",
    default_args=default_args,
    description="Ingesta continua del feed USGS GeoJSON hacia la capa Bronze (raw) cada 5 min",
    schedule="*/5 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["sismowatch", "ingestion", "bronze", "usgs"],
    doc_md="""
    # DAG de Ingesta USGS (Bronze)
    - Extrae el feed oficial de USGS: `all_hour.geojson`
    - Inserta idempotentemente en `raw.usgs_earthquakes_raw` mediante upsert por `id`.
    - Registra latencia y métricas en `raw.ingestion_metrics`.
    - Dispara DAG de transformación y calidad.
    """
) as dag:

    def ingest_task(**context):
        run_id = context.get("run_id", f"manual_{int(datetime.now().timestamp())}")
        try:
            payload, latency_ms = fetch_usgs_feed(timeout=30)
            features = payload.get("features", [])

            # Persist raw GeoJSON response to MinIO Object Lakehouse (Non-relational Bronze)
            s3_uri = None
            try:
                try:
                    from include.storage.minio_lake import persist_raw_feed_to_lake
                except ImportError:
                    from airflow.include.storage.minio_lake import persist_raw_feed_to_lake
                s3_uri = persist_raw_feed_to_lake(feed_data=payload, execution_id=run_id)
            except Exception as minio_err:
                logger.warning(f"Could not archive to MinIO Bronze lake: {minio_err}")

            persisted = persist_raw_payloads(
                features=features,
                execution_id=run_id,
                source_feed=settings.USGS_REALTIME_FEED_URL,
                http_status=200
            )
            record_ingestion_metric(
                execution_id=run_id,
                feed_url=settings.USGS_REALTIME_FEED_URL,
                status="SUCCESS" if persisted > 0 else "EMPTY",
                events_extracted=persisted,
                response_time_ms=latency_ms
            )
            return {"persisted_count": persisted, "run_id": run_id}
        except Exception as e:
            record_ingestion_metric(
                execution_id=run_id,
                feed_url=settings.USGS_REALTIME_FEED_URL,
                status="ERROR",
                events_extracted=0,
                response_time_ms=0.0,
                error_message=str(e)
            )
            raise

    ingest_op = PythonOperator(
        task_id="ingest_usgs_feed_to_bronze",
        python_callable=ingest_task
    )

    trigger_transform_op = TriggerDagRunOperator(
        task_id="trigger_transformation_dag",
        trigger_dag_id="usgs_transformation_quality",
        wait_for_completion=False,
        reset_dag_run=True
    )

    ingest_op >> trigger_transform_op
