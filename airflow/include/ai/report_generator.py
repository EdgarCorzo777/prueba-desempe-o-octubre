"""
report_generator.py
Generates Daily Seismic Executive Summaries backed by Gold data.
Uses Ollama Local LLM with deterministic fallback.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from psycopg2.extras import Json
from airflow.include.config import settings
from airflow.include.db import get_db_cursor
from airflow.include.ai.ollama_client import generate_chat_completion, sanitize_user_input
from airflow.include.ai.prompting import load_prompt, validate_report_figures

logger = logging.getLogger("sismowatch.reports")

def calculate_daily_summary_metrics(target_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Computes exact mathematical figures from curated.events for the specified day.
    Uses 'transform' or 'api' role.
    """
    date_val = target_date or datetime.now(timezone.utc).date()
    start_dt = datetime(date_val.year, date_val.month, date_val.day, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)

    query_stats = """
    SELECT
        COUNT(*)::int as total_events,
        COALESCE(MAX(magnitude), 0.0)::float as max_magnitude,
        COALESCE(AVG(magnitude), 0.0)::float as avg_magnitude,
        COUNT(*) FILTER (WHERE tsunami = TRUE)::int as tsunami_alerts,
        COUNT(*) FILTER (WHERE severity_level = 'CRITICAL')::int as critical_events,
        COUNT(*) FILTER (WHERE severity_level = 'HIGH')::int as high_events,
        COUNT(*) FILTER (WHERE severity_level = 'MODERATE')::int as moderate_events,
        COUNT(*) FILTER (WHERE severity_level = 'LOW')::int as low_events
    FROM curated.events
    WHERE event_time >= %s AND event_time < %s;
    """

    query_top_regions = """
    SELECT 
        COALESCE(NULLIF(SPLIT_PART(place, ', ', 2), ''), place) as region,
        COUNT(*)::int as count,
        MAX(magnitude)::float as max_mag
    FROM curated.events
    WHERE event_time >= %s AND event_time < %s
    GROUP BY 1
    ORDER BY count DESC
    LIMIT 5;
    """

    query_notable_events = """
    SELECT event_id, place, magnitude, depth_km, event_time, tsunami
    FROM curated.events
    WHERE event_time >= %s AND event_time < %s
    ORDER BY magnitude DESC
    LIMIT 3;
    """

    with get_db_cursor(role="transform", commit=False) as cur:
        cur.execute(query_stats, (start_dt, end_dt))
        stats = cur.fetchone() or {}
        
        cur.execute(query_top_regions, (start_dt, end_dt))
        top_regions = cur.fetchall() or []
        
        cur.execute(query_notable_events, (start_dt, end_dt))
        notable = cur.fetchall() or []

    # Clean dates for JSON
    notable_cleaned = []
    for ev in notable:
        notable_cleaned.append({
            "event_id": ev["event_id"],
            "place": sanitize_user_input(ev["place"]),
            "magnitude": round(float(ev["magnitude"]), 2),
            "depth_km": round(float(ev["depth_km"]), 1),
            "time": ev["event_time"].isoformat(),
            "tsunami": ev["tsunami"]
        })

    return {
        "date": str(date_val),
        "total_events": stats.get("total_events", 0),
        "max_magnitude": round(stats.get("max_magnitude", 0.0), 2),
        "avg_magnitude": round(stats.get("avg_magnitude", 0.0), 2),
        "tsunami_alerts": stats.get("tsunami_alerts", 0),
        "critical_events": stats.get("critical_events", 0),
        "high_events": stats.get("high_events", 0),
        "moderate_events": stats.get("moderate_events", 0),
        "low_events": stats.get("low_events", 0),
        "top_regions": [
            {"region": sanitize_user_input(r["region"]), "count": r["count"], "max_mag": round(r["max_mag"], 2)}
            for r in top_regions
        ],
        "notable_events": notable_cleaned
    }

def generate_deterministic_report(metrics: Dict[str, Any]) -> str:
    """
    Deterministic analytical fallback template.
    Guarantees 100% availability even when Ollama is offline or times out.
    """
    date_str = metrics["date"]
    total = metrics["total_events"]
    max_m = metrics["max_magnitude"]
    avg_m = metrics["avg_magnitude"]
    tsunami = metrics["tsunami_alerts"]
    regions = metrics["top_regions"]
    
    reg_summary = "Sin regiones dominantes registradas."
    if regions:
        reg_lines = [f"• {r['region']}: {r['count']} sismos (Magnitud máxima: {r['max_mag']})" for r in regions]
        reg_summary = "\n".join(reg_lines)

    tsunami_text = "No se emitieron alertas de tsunami." if tsunami == 0 else f"ATENCIÓN: Se reportaron {tsunami} eventos con alerta de tsunami."

    summary = f"""### Reporte Ejecutivo Diario de Actividad Sísmica — {date_str}
*(Generado por el Motor Analítico Determinista de SismoWatch)*

**1. Resumen General:**
Durante el periodo evaluado del {date_str}, la red de monitoreo registró un total de **{total} sismos** a nivel global. La magnitud promedio fue de **{avg_m}**, alcanzando un valor pico de **{max_m}**. {tsunami_text}

**2. Distribución de Severidad:**
- Eventos Críticos (M >= 7.0): {metrics['critical_events']}
- Eventos Fuertes (M 6.0 - 6.9): {metrics['high_events']}
- Eventos Moderados (M 4.0 - 5.9): {metrics['moderate_events']}
- Eventos Menores / Microsismos (M < 4.0): {metrics['low_events']}

**3. Zonas con Mayor Frecuencia Sísmica:**
{reg_summary}

**4. Evaluación de Riesgo y Operaciones:**
La actividad sísmica global del periodo se encuentra dentro de los umbrales esperados. Se recomienda mantener monitorización activa en las regiones de mayor concentración.
"""
    return summary.strip()

def generate_daily_executive_report(target_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Generates and persists the daily executive report.
    Without an explicit date, covers the LAST COMPLETED UTC day (T-1): the DAG runs
    at a fixed time and the report must be of a full day's data, never a partially
    started day. Tries the LLM with validated prompt grounding; falls back to the
    deterministic template if needed.
    """
    effective_date = target_date or (datetime.now(timezone.utc) - timedelta(days=1)).date()
    metrics = calculate_daily_summary_metrics(effective_date)
    date_str = metrics["date"]
    report_id = f"REP_{date_str.replace('-', '')}"

    # Prompts versionados (airflow/include/ai/prompts/) — el LLM solo redacta
    system_prompt = load_prompt("daily_report_system.md")
    user_prompt = load_prompt(
        "daily_report_user.md",
        {
            "DATE": date_str,
            "TOTAL": metrics['total_events'],
            "MAX_MAG": metrics['max_magnitude'],
            "AVG_MAG": metrics['avg_magnitude'],
            "TSUNAMI": metrics['tsunami_alerts'],
            "CRITICAL": metrics['critical_events'],
            "HIGH": metrics['high_events'],
            "MODERATE": metrics['moderate_events'],
            "LOW": metrics['low_events'],
            "REGIONS_JSON": json.dumps(metrics['top_regions'], ensure_ascii=False),
            "NOTABLE_JSON": json.dumps(metrics['notable_events'], ensure_ascii=False),
        },
    )

    ai_result = generate_chat_completion(
        prompt=user_prompt,
        system_prompt=system_prompt,
        timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        options={"num_predict": 250, "temperature": 0.2}
    )
    
    generation_status = "AI_GENERATED"
    model_used = ai_result["model"]
    tokens = ai_result["tokens"]
    latency = ai_result["latency_ms"]
    executive_summary = ""
    figure_validation = {"status": "NOT_APPLICABLE", "missing": []}

    if ai_result["status"] == "SUCCESS" and len(ai_result["content"]) > 80:
        summary_text = ai_result["content"]
        # Control anti-alucinación: las cifras del texto DEBEN coincidir con las calculadas.
        figure_validation = validate_report_figures(summary_text, metrics)
        if figure_validation["status"] == "VERIFIED":
            executive_summary = summary_text
        else:
            logger.warning(
                f"Reporte descartado por cifras inconsistente con Gold (faltantes: "
                f"{figure_validation['missing']}). Se usa el reporte determinista."
            )
            executive_summary = generate_deterministic_report(metrics)
            generation_status = "DETERMINISTIC_FALLBACK"
    else:
        logger.info(f"LLM unavailable or response too short ({ai_result.get('error')}). Using deterministic report.")
        executive_summary = generate_deterministic_report(metrics)
        generation_status = "DETERMINISTIC_FALLBACK"

    # Persist into curated.daily_reports
    upsert_query = """
    INSERT INTO curated.daily_reports (
        report_id, report_date, executive_summary, metrics_json,
        ai_model, generation_status, tokens_used, latency_ms, created_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (report_id) DO UPDATE SET
        executive_summary = EXCLUDED.executive_summary,
        metrics_json = EXCLUDED.metrics_json,
        ai_model = EXCLUDED.ai_model,
        generation_status = EXCLUDED.generation_status,
        tokens_used = EXCLUDED.tokens_used,
        latency_ms = EXCLUDED.latency_ms,
        created_at = NOW();
    """
    
    with get_db_cursor(role="transform", commit=True) as cur:
        cur.execute(
            upsert_query,
            (
                report_id,
                metrics["date"],
                executive_summary,
                Json(metrics),
                model_used,
                generation_status,
                tokens,
                round(latency, 2)
            )
        )
        
    logger.info(f"Daily report persisted for {date_str} (status: {generation_status})")
    return {
        "report_id": report_id,
        "date": date_str,
        "generation_status": generation_status,
        "model": model_used,
        "latency_ms": latency,
        "tokens_used": tokens,
        "executive_summary": executive_summary,
        "metrics": metrics,
        "figure_validation": figure_validation
    }
