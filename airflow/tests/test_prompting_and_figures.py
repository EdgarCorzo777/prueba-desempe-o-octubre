"""
test_prompting_and_figures.py
Prueba el control anti-alucinación:
1. Todos los prompts versionados existen y sustituyen tokens.
2. validate_report_figures(): reporte fiel -> VERIFIED; reporte con cifras
   inventadas/ausentes -> MISMATCH (se descarta y va a fallback determinista).
Solo stdlib: no requiere Airflow ni psycopg2 instalados.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from airflow.include.ai.prompting import (  # noqa: E402
    load_prompt,
    validate_report_figures,
    list_versioned_prompts,
)


def test_versioned_prompts_exist():
    prompts = list_versioned_prompts()
    for expected in ["daily_report_system.md", "daily_report_user.md", "chat_system.md", "chat_user.md"]:
        assert expected in prompts, f"Prompt versionado faltante: {expected}"


def test_load_prompt_substitutes_tokens():
    text = load_prompt("daily_report_user.md", {"DATE": "2026-10-25", "TOTAL": 1924})
    assert "{{DATE}}" not in text
    assert "2026-10-25" in text
    assert "1924" in text


def test_validate_figures_verified():
    metrics = {"total_events": 1924, "max_magnitude": 7.7, "avg_magnitude": 3.92, "tsunami_alerts": 6}
    text = (
        "Se registraron 1924 sismos con magnitud promedio de 3,92 y máxima de 7.7. "
        "Se emitieron 6 alertas de tsunami."
    )
    assert validate_report_figures(text, metrics)["status"] == "VERIFIED"


def test_validate_figures_mismatch_missing_total():
    metrics = {"total_events": 1924, "max_magnitude": 7.7, "avg_magnitude": 3.92, "tsunami_alerts": 6}
    text = "Se registraron 999 sismos con magnitud promedio 3.9 y máxima 7.7. Hubo 6 alertas de tsunami."
    result = validate_report_figures(text, metrics)
    assert result["status"] == "MISMATCH"
    assert any("total events" in m for m in result["missing"])


def test_validate_figures_zero_tsunami_optional():
    # tsunami_alerts = 0 -> el texto puede describirlo verbalmente; la cifra no es obligatoria
    metrics = {"total_events": 10, "max_magnitude": 4.6, "avg_magnitude": 2.1, "tsunami_alerts": 0}
    text = "Se registraron 10 sismos, con promedio 2,1 y máxima 4,6. No se emitieron alertas de tsunami."
    result = validate_report_figures(text, metrics)
    assert result["status"] == "VERIFIED"
    assert result["missing"] == []


def test_validate_figures_empty_text():
    metrics = {"total_events": 5, "max_magnitude": 4.0, "avg_magnitude": 2.0}
    assert validate_report_figures("", metrics)["status"] == "MISMATCH"
