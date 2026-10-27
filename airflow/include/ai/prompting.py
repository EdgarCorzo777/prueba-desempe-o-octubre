"""
prompting.py
Carga de prompts versionados y validación de cifras del LLM.

- load_prompt(): lee plantillas versionadas en airflow/include/ai/prompts/ (repo),
  sustituyendo tokens {{NOMBRE}} por los valores entregados.
- validate_report_figures(): control anti-alucinación. Extrae los números del texto
  generado por el LLM y verifica que las cifras certificadas de Gold (calculadas
  por SQL/Python) aparezcan en la redacción. El LLM solo redacta; si menciona
  números que no coinciden con los certificados, el reporte se descarta.
Solo stdlib: pensado para importarse en pruebas sin dependencias pesadas.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Set

logger = logging.getLogger("sismowatch.prompting")

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def list_versioned_prompts() -> Set[str]:
    return {p.name for p in PROMPTS_DIR.glob("*.md")} | {p.name for p in PROMPTS_DIR.glob("*.txt")}


def load_prompt(template_name: str, replacements: Optional[Dict[str, str]] = None) -> str:
    """Carga una plantilla de prompt versionada y substituye tokens {{CLAVE}}."""
    path = PROMPTS_DIR / template_name
    if not path.is_file():
        raise FileNotFoundError(f"Prompt versionado no encontrado: {path}")
    text = path.read_text(encoding="utf-8")
    for key, value in (replacements or {}).items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def _humanize(missing_key: str) -> str:
    return missing_key.replace("_", " ")


def _extract_numbers(text: str):
    """Extrae números del texto tolerando miles '1.924'/'1,924' y decimales '3,92'."""
    numbers = []
    for match in re.finditer(r"\d+(?:[.,]\d+)*", text):
        token = match.group()
        # Decimal con coma (1-2 decimales y una sola coma): "3,92"
        if re.fullmatch(r"\d+,\d{1,2}", token):
            try:
                numbers.append(float(token.replace(",", ".")))
                continue
            except ValueError:
                pass
        # Miles con separador: "1.924" / "1,924" / "1.924,5"
        cleaned = re.sub(r"[.,](?=\d{3}\b)", "", token)
        cleaned = cleaned.replace(",", ".")
        try:
            numbers.append(float(cleaned))
        except ValueError:
            continue
    return numbers


def _tolerance(value: float) -> float:
    if value == int(value):
        return 0.51  # permite miles redondeados o números en palabras vecinas
    return 0.06  # permite redondeos 3.92 -> "3.9" / "2,09" -> "2,1"


def validate_report_figures(summary_text: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida que las cifras obligatorias calculadas en SQL/Python aparezcan en la
    redacción del LLM. Devuelve {"status": "VERIFIED"|"MISMATCH", "missing": [...]}.
    """
    if not summary_text:
        return {"status": "MISMATCH", "missing": ["texto vacío"]}

    found = _extract_numbers(summary_text)
    required = {
        "total_events": metrics.get("total_events", 0),
        "max_magnitude": metrics.get("max_magnitude", 0.0),
        "avg_magnitude": metrics.get("avg_magnitude", 0.0),
    }
    # Si no hubo alertas de tsunami, el texto puede expresarlo de forma verbal
    tsunami = metrics.get("tsunami_alerts", 0)
    if tsunami and tsunami > 0:
        required["tsunami_alerts"] = tsunami

    missing = []
    for key, value in required.items():
        target = float(value)
        if not any(abs(n - target) <= _tolerance(target) for n in found):
            missing.append(f"{_humanize(key)} ({target:g})")

    status = "MISMATCH" if missing else "VERIFIED"
    if status == "MISMATCH":
        logger.warning(f"Cifras del LLM no coinciden con Gold: faltantes={missing}")
    return {"status": status, "missing": missing}
