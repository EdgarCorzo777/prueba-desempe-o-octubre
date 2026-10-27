"""
test_dag_integrity.py
Unit tests to ensure DAGs have valid syntax, no import errors, and follow standards.
Supports both containerized execution with Airflow DagBag and AST parsing.
"""

import ast
import glob
import os
import pytest

try:
    from airflow.models import DagBag
    AIRFLOW_INSTALLED = True
except ImportError:
    AIRFLOW_INSTALLED = False

def test_dag_files_exist_and_syntax_valid():
    """
    Validates that all SismoWatch Airflow DAG files exist and have 0 syntax errors.
    """
    dag_files = glob.glob("airflow/dags/*.py")
    assert len(dag_files) >= 3, f"Expected at least 3 DAG files, found {len(dag_files)}"
    
    expected_dags = [
        "usgs_earthquake_ingestion_dag.py",
        "usgs_transformation_quality_dag.py",
        "sismowatch_daily_ai_report_dag.py"
    ]
    file_basenames = [os.path.basename(f) for f in dag_files]
    for exp in expected_dags:
        assert exp in file_basenames, f"Missing DAG file: {exp}"

    for f_path in dag_files:
        with open(f_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=f_path)
        assert tree is not None, f"Failed to parse AST for {f_path}"

def test_dagbag_imports():
    """
    If Airflow is installed in the active environment (e.g. inside Airflow container),
    validates that DagBag loads with 0 import errors.
    """
    if not AIRFLOW_INSTALLED:
        pytest.skip("Airflow package is installed inside Docker container; syntax verified via AST.")
        
    dagbag = DagBag(dag_folder="airflow/dags", include_examples=False)
    assert len(dagbag.import_errors) == 0, f"DAG import errors: {dagbag.import_errors}"
    assert "usgs_earthquake_ingestion" in dagbag.dags
    assert "usgs_transformation_quality" in dagbag.dags
    assert "sismowatch_daily_ai_report" in dagbag.dags
