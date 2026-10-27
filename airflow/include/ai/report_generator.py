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
    Tries Ollama with validated prompt grounding; falls back to deterministic template if needed.
    """
    metrics = calculate_daily_summary_metrics(target_date)
    date_str = metrics["date"]
    report_id = f"REP_{date_str.replace('-', '')}"
    
    # Prompt for Ollama
    system_prompt = (
        "Eres un analista geofísico senior de SismoWatch. Redacta un reporte ejecutivo en español "
        "con base EXCLUSIVA en los datos certificados que se te proporcionan. "
        "REGLA CRÍTICA: NO inventes cifras ni porcentajes. Utiliza exactamente los números calculados."
    )
    
    user_prompt = f"""
DATOS SÍSMICOS CERTIFICADOS DEL DÍA {date_str}:
- Total de sismos: {metrics['total_events']}
- Magnitud máxima: {metrics['max_magnitude']}
- Magnitud promedio: {metrics['avg_magnitude']}
- Alertas de tsunami: {metrics['tsunami_alerts']}
- Sismos críticos (>=7.0): {metrics['critical_events']}
- Sismos fuertes (6.0-6.9): {metrics['high_events']}
- Sismos moderados (4.0-5.9): {metrics['moderate_events']}
- Sismos menores (<4.0): {metrics['low_events']}
- Regiones más activas: {json.dumps(metrics['top_regions'], ensure_ascii=False)}
- Eventos más destacados: {json.dumps(metrics['notable_events'], ensure_ascii=False)}

Redacta un informe ejecutivo conciso de 3 a 4 párrafos que incluya:
1. Resumen de actividad sísmica y magnitudes.
2. Zonas geográficas más activas.
3. Eventos destacados y alertas de tsunami si las hubo.
4. Recomendación operativa.
"""

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

    if ai_result["status"] == "SUCCESS" and len(ai_result["content"]) > 80:
        summary_text = ai_result["content"]
        executive_summary = summary_text
    else:
        logger.info(f"Ollama unavailable or response too short ({ai_result.get('error')}). Using deterministic report.")
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
        "metrics": metrics
    }
