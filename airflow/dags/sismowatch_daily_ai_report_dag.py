"""
sismowatch_daily_ai_report_dag.py
DAG 3: Generates Daily Seismic Executive Summaries with Ollama Local AI.
Includes deterministic fallback.
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
    from include.ai.report_generator import generate_daily_executive_report
except ImportError:
    from airflow.include.ai.report_generator import generate_daily_executive_report

logger = logging.getLogger("airflow.dag.daily_ai_report")

def failure_alert_callback(context):
    task_id = context.get("task_instance").task_id
    dag_id = context.get("dag").dag_id
    error = context.get("exception")
    logger.error(f"ALERT: AI Report task {task_id} in {dag_id} failed: {error}")

default_args = {
    "owner": "sismowatch_data_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(seconds=30),
    "execution_timeout": timedelta(minutes=5),
    "on_failure_callback": failure_alert_callback
}

with DAG(
    dag_id="sismowatch_daily_ai_report",
    default_args=default_args,
    description="Generación diaria de informe ejecutivo con IA local anclada a Gold",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["sismowatch", "analytics", "ai", "gold"],
    doc_md="""
    # DAG de Reporte Diario Asistido por IA
    - Lee exclusivamente de `curated.events`.
    - Calcula métricas analíticas exactas (SQL/Python).
    - Solicita redacción ejecutiva al LLM local (Ollama).
    - Valida consistencia numérica contra alucinaciones.
    - Aplica generador determinista si Ollama falla o no responde.
    """
) as dag:

    def report_task(**context):
        res = generate_daily_executive_report()
        return {
            "report_id": res.get("report_id"),
            "status": res.get("generation_status"),
            "model": res.get("model")
        }

    report_op = PythonOperator(
        task_id="generate_grounded_executive_report",
        python_callable=report_task
    )
