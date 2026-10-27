"""
chat_service.py
Motor conversacional inteligente con grounded data exclusivo de curated.events (Gold).
Previene alucinaciones calculando cifras matemáticas certificadas antes del prompt a Ollama.
Soporta resolución temporal precisa (zona horaria Colombia UTC-5: hoy, ayer, últimas 24h, semana).
"""

import re
import json
import logging
from typing import Dict, Any, Tuple, List
from datetime import datetime, timezone, timedelta
from api.app.database import db_cursor
from airflow.include.ai.ollama_client import generate_chat_completion, sanitize_user_input
from api.app.config import settings

logger = logging.getLogger("sismowatch.chat_service")

def resolve_time_window(query: str) -> Tuple[datetime, datetime, str]:
    """
    Resolves start time, end time, and label.
    Supports Colombia timezone (UTC-5) for "hoy", "ayer", etc.
    """
    now_utc = datetime.now(timezone.utc)
    cot_tz = timezone(timedelta(hours=-5))
    now_cot = now_utc.astimezone(cot_tz)
    lower = query.lower()

    if "hoy" in lower or "el día de hoy" in lower or "dia de hoy" in lower:
        start_cot = now_cot.replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = start_cot.astimezone(timezone.utc)
        period_label = f"Hoy {start_cot.strftime('%Y-%m-%d')} (desde 00:00 COT / {start_utc.strftime('%H:%M')} UTC hasta {now_cot.strftime('%H:%M')} COT)"
        return start_utc, now_utc, period_label

    if "ayer" in lower:
        yesterday_cot = now_cot - timedelta(days=1)
        start_cot = yesterday_cot.replace(hour=0, minute=0, second=0, microsecond=0)
        end_cot = yesterday_cot.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_utc = start_cot.astimezone(timezone.utc)
        end_utc = end_cot.astimezone(timezone.utc)
        period_label = f"Ayer {yesterday_cot.strftime('%Y-%m-%d')} (00:00 a 23:59 COT)"
        return start_utc, end_utc, period_label

    if "semana" in lower or "7 d" in lower or "últimos días" in lower or "ultimos dias" in lower:
        start_utc = now_utc - timedelta(days=7)
        period_label = f"Últimos 7 días ({start_utc.strftime('%Y-%m-%d')} a {now_utc.strftime('%Y-%m-%d')} UTC)"
        return start_utc, now_utc, period_label

    if "mes" in lower or "30 d" in lower:
        start_utc = now_utc - timedelta(days=30)
        period_label = f"Últimos 30 días"
        return start_utc, now_utc, period_label

    # Default: last 24 hours
    start_utc = now_utc - timedelta(hours=24)
    period_label = f"Últimas 24 horas ({start_utc.strftime('%Y-%m-%d %H:%M')} a {now_utc.strftime('%Y-%m-%d %H:%M')} UTC)"
    return start_utc, now_utc, period_label

def resolve_intent(query: str) -> str:
    """
    Identifies analytical intent with strict priority for geographic queries.
    """
    lower = query.lower()

    # 1. Geographic / Region-based queries take highest precedence
    region_keywords = [
        "region", "región", "regiones", "zona", "zonas", "lugar", "lugares",
        "país", "pais", "paises", "países", "dónde", "donde", "ubicación", "ubicacion"
    ]
    if any(k in lower for k in region_keywords):
        return "top_regions"

    # 2. Tsunami alerts
    if "tsunami" in lower or "maremoto" in lower:
        return "tsunami"

    # 3. Statistical anomalies
    if "anomal" in lower or "enjambre" in lower or "atípico" in lower or "atipico" in lower:
        return "anomalies"

    # 4. Trends / historical
    if "tendencia" in lower or "histórico" in lower or "historico" in lower or "evolución" in lower:
        return "weekly_trend"

    # 5. Maximum magnitude
    max_keywords = ["máxim", "maxim", "más fuerte", "mas fuerte", "mayor magnitud", "más grande", "mas grande"]
    if any(k in lower for k in max_keywords) or ("fuerte" in lower and "sismo" in lower):
        return "max_magnitude"

    # 6. Event counts
    count_keywords = ["cuánt", "cuant", "total", "cantidad", "número", "numero"]
    if any(k in lower for k in count_keywords):
        return "count_events"

    return "general_kpis"

def answer_user_query_grounded_in_gold(question: str) -> Dict[str, Any]:
    """
    Executes grounded conversational workflow:
    1. Sanitizes question.
    2. Resolves intent and exact time window.
    3. Runs parameterized query on curated.events.
    4. Prompts Ollama with certified figures.
    5. Returns grounded answer with fallbacks.
    """
    clean_q = sanitize_user_input(question)
    start_utc, end_utc, period_label = resolve_time_window(clean_q)
    intent = resolve_intent(clean_q)

    data_points: Dict[str, Any] = {}

    with db_cursor(as_admin=False, commit=False) as cur:
        if intent == "anomalies":
            cur.execute(
                """
                SELECT alert_type, region, z_score, event_count, avg_magnitude, explanation, created_at
                FROM curated.anomaly_alerts
                ORDER BY created_at DESC
                LIMIT 5;
                """
            )
            alerts = cur.fetchall() or []
            data_points = {
                "periodo": period_label,
                "total_alertas_anomalias": len(alerts),
                "alertas_recientes": [
                    {
                        "tipo": a["alert_type"],
                        "region": a["region"],
                        "z_score": round(float(a["z_score"]), 2),
                        "conteo_eventos": a["event_count"],
                        "magnitud_promedio": round(float(a["avg_magnitude"]), 2),
                        "explicacion": a["explanation"]
                    }
                    for a in alerts
                ]
            }

        elif intent == "tsunami":
            cur.execute(
                """
                SELECT event_id, place, magnitude, depth_km, event_time, url
                FROM curated.events
                WHERE tsunami = TRUE AND event_time >= %s AND event_time <= %s
                ORDER BY event_time DESC
                LIMIT 10;
                """,
                (start_utc, end_utc)
            )
            tsunami_events = cur.fetchall() or []
            data_points = {
                "periodo": period_label,
                "eventos_con_alerta_tsunami": len(tsunami_events),
                "detalle_eventos": [
                    {
                        "lugar": e["place"],
                        "magnitud": float(e["magnitude"]),
                        "profundidad_km": float(e["depth_km"]),
                        "hora": e["event_time"].strftime("%Y-%m-%d %H:%M UTC")
                    }
                    for e in tsunami_events
                ]
            }

        elif intent == "top_regions":
            cur.execute(
                """
                SELECT 
                    COALESCE(NULLIF(SPLIT_PART(place, ', ', 2), ''), place) as region,
                    COUNT(*)::int as count,
                    COALESCE(MAX(magnitude), 0.0)::float as max_mag,
                    COALESCE(ROUND(AVG(magnitude)::numeric, 2), 0.0)::float as avg_mag
                FROM curated.events
                WHERE event_time >= %s AND event_time <= %s
                GROUP BY 1
                ORDER BY count DESC
                LIMIT 5;
                """,
                (start_utc, end_utc)
            )
            regions = cur.fetchall() or []

            # Also get total events in window
            cur.execute(
                "SELECT COUNT(*)::int as tot FROM curated.events WHERE event_time >= %s AND event_time <= %s;",
                (start_utc, end_utc)
            )
            total_in_window = cur.fetchone()["tot"]

            data_points = {
                "periodo": period_label,
                "total_sismos_en_periodo": total_in_window,
                "regiones_con_mayor_actividad": [
                    {
                        "region": r["region"],
                        "total_sismos": r["count"],
                        "magnitud_maxima": round(r["max_mag"], 2),
                        "magnitud_promedio": round(r["avg_mag"], 2)
                    }
                    for r in regions
                ]
            }

        elif intent == "weekly_trend":
            cur.execute(
                """
                SELECT
                    DATE(event_time) as day,
                    COUNT(*)::int as count,
                    COALESCE(MAX(magnitude), 0.0)::float as max_mag
                FROM curated.events
                WHERE event_time >= %s AND event_time <= %s
                GROUP BY 1
                ORDER BY day ASC;
                """,
                (start_utc, end_utc)
            )
            daily_trend = cur.fetchall() or []
            data_points = {
                "periodo": period_label,
                "tendencia_diaria": [
                    {"fecha": str(d["day"]), "sismos": d["count"], "magnitud_maxima": round(d["max_mag"], 2)}
                    for d in daily_trend
                ]
            }

        else:  # count_events, max_magnitude, general_kpis
            cur.execute(
                """
                SELECT
                    COUNT(*)::int as total_events,
                    COALESCE(MAX(magnitude), 0.0)::float as max_magnitude,
                    COALESCE(ROUND(AVG(magnitude)::numeric, 2), 0.0)::float as avg_magnitude,
                    COUNT(*) FILTER (WHERE tsunami = TRUE)::int as tsunami_alerts
                FROM curated.events
                WHERE event_time >= %s AND event_time <= %s;
                """,
                (start_utc, end_utc)
            )
            kpi_res = cur.fetchone() or {}

            cur.execute(
                """
                SELECT place, magnitude, depth_km, event_time, tsunami
                FROM curated.events
                WHERE event_time >= %s AND event_time <= %s
                ORDER BY magnitude DESC
                LIMIT 5;
                """,
                (start_utc, end_utc)
            )
            top_events = cur.fetchall() or []
            max_event = top_events[0] if top_events else None

            notable_list = [
                {
                    "lugar": ev.get("place", "N/A"),
                    "magnitud": round(float(ev.get("magnitude", 0.0)), 2),
                    "profundidad_km": round(float(ev.get("depth_km", 0.0)), 1),
                    "fecha_utc": ev.get("event_time").strftime("%Y-%m-%d %H:%M UTC") if ev.get("event_time") else "N/A",
                    "tsunami": ev.get("tsunami", False)
                }
                for ev in top_events
            ]

            data_points = {
                "periodo": period_label,
                "total_sismos": kpi_res.get("total_events", 0),
                "magnitud_maxima": round(kpi_res.get("max_magnitude", 0.0), 2),
                "magnitud_promedio": round(kpi_res.get("avg_magnitude", 0.0), 2),
                "alertas_tsunami": kpi_res.get("tsunami_alerts", 0),
                "sismos_mas_fuertes": notable_list,
                "sismo_mas_fuerte": notable_list[0] if notable_list else None
            }

    # Prompt Ollama Local AI
    system_prompt = (
        "Eres SismoWatch AI, el asistente analítico oficial y científico de monitoreo sísmico. "
        "Tu función es responder preguntas informativas sobre eventos telúricos y actividad geológica natural registrada. "
        "Todas las consultas se refieren exclusivamente a fenómenos naturales (terremotos y sismos). "
        "Responde siempre en español de forma amable, directa y profesional con base en las cifras certificadas. "
        "REGLA MANDATORIA: Cita las cifras numéricas del JSON sin inventar datos ni fechas. "
        "Si el usuario pide un diagrama, gráfico o ranking, incluye una representación visual clara."
    )

    prompt = f"""
PREGUNTA DEL USUARIO: "{clean_q}"
PERIODO CONSULTADO: {period_label}
INTENCIÓN DETECTADA: {intent}

DATOS CERTIFICADOS (CAPA GOLD):
{json.dumps(data_points, ensure_ascii=False, indent=2)}

Instrucción: Redacta una respuesta de 1 a 2 párrafos concisos que responda directamente a la pregunta con los datos anteriores.
"""

    llm_res = generate_chat_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        timeout=75
    )

    is_fallback = False
    answer_text = ""

    refusal_patterns = [
        "no puedo proporcionar", "no puedo responder", "actividades ilegales",
        "como modelo de lenguaje", "as an ai language model", "cannot fulfill"
    ]

    candidate_text = llm_res.get("content", "").strip()
    is_refusal = any(pat in candidate_text.lower() for pat in refusal_patterns)

    if llm_res["status"] == "SUCCESS" and len(candidate_text) > 15 and not is_refusal:
        answer_text = candidate_text
    else:
        # Deterministic analytical fallback tailored to intent
        is_fallback = True
        logger.info(f"Using deterministic fallback for intent '{intent}' (reason: {llm_res.get('error')})")

        if intent == "top_regions":
            regs = data_points.get("regiones_con_mayor_actividad", [])
            tot = data_points.get("total_sismos_en_periodo", 0)
            if regs:
                top_str = "; ".join([f"{r['region']} ({r['total_sismos']} sismos, máx M{r['magnitud_maxima']})" for r in regs])
                answer_text = f"Durante {period_label} se registraron {tot} sismos en total. Las regiones con mayor actividad fueron: {top_str}."
            else:
                answer_text = f"Durante {period_label} no se registraron concentraciones sísmicas significativas en la base de datos."

        elif intent == "anomalies":
            cnt = data_points.get("total_alertas_anomalias", 0)
            if cnt > 0:
                alerts_str = "; ".join([f"{a['tipo']} en {a['region']} (Z-Score {a['z_score']})" for a in data_points["alertas_recientes"][:3]])
                answer_text = f"Se detectaron {cnt} alertas de anomalía estadística: {alerts_str}."
            else:
                answer_text = f"No se han detectado anomalías estadísticas ni enjambres sísmicos durante {period_label}."

        elif intent == "tsunami":
            cnt = data_points.get("eventos_con_alerta_tsunami", 0)
            if cnt > 0:
                answer_text = f"Durante {period_label} se registraron {cnt} eventos con alerta de tsunami activa en la red de monitoreo."
            else:
                answer_text = f"Durante {period_label} no se registraron eventos con alerta de tsunami."

        elif intent == "weekly_trend":
            trend = data_points.get("tendencia_diaria", [])
            tot = sum(t["sismos"] for t in trend)
            answer_text = f"En {period_label} se registraron {tot} sismos en total a lo largo de {len(trend)} días monitoreados."

        elif intent == "max_magnitude":
            max_ev = data_points.get("sismo_mas_fuerte")
            if max_ev:
                answer_text = f"Durante {period_label}, el sismo de mayor magnitud fue de M{max_ev['magnitud']} ocurrido en {max_ev['lugar']} a las {max_ev['fecha_utc']} con una profundidad de {max_ev['profundidad_km']} km."
            else:
                answer_text = f"No se registraron sismos durante {period_label}."

        else:
            tot = data_points.get("total_sismos", 0)
            max_m = data_points.get("magnitud_maxima", 0.0)
            avg_m = data_points.get("magnitud_promedio", 0.0)
            top_ev = data_points.get("sismo_mas_fuerte")
            top_str = f" El evento más fuerte fue de M{top_ev['magnitud']} en {top_ev['lugar']}." if top_ev else ""
            answer_text = f"En {period_label} se registraron un total de {tot} sismos certificados, con una magnitud promedio de {avg_m} y una magnitud máxima de {max_m}.{top_str}"

    requests_diagram = any(w in clean_q.lower() for w in ["diagrama", "grafic", "gráfic", "chart", "ranking", "barras", "dibuj", "visual"])
    if requests_diagram and "```" not in answer_text:
        # Append guaranteed structured visual diagram
        if data_points.get("sismos_mas_fuertes"):
            events_to_show = data_points.get("sismos_mas_fuertes", [])[:5]
            diag = "\n\n📊 **Diagrama de Sismos Más Fuertes (Ranking):**\n```text\n"
            for ev in events_to_show:
                mag = ev['magnitud']
                bars = "█" * int(mag * 4)
                place_short = ev['lugar'][:26]
                diag += f"M {mag:3.1f} | {bars:<24} | {place_short}\n"
            diag += "```\n"
            answer_text += diag
        elif data_points.get("regiones_con_mayor_actividad"):
            regs = data_points.get("regiones_con_mayor_actividad", [])[:5]
            diag = "\n\n📊 **Diagrama de Frecuencia por Región:**\n```text\n"
            for r in regs:
                cnt = r['total_sismos']
                bars = "█" * min(25, max(1, int(cnt * 2)))
                diag += f"{r['region'][:12]:<12} | {bars:<25} ({cnt} sismos)\n"
            diag += "```\n"
            answer_text += diag

    return {
        "question": clean_q,
        "answer": answer_text,
        "data_points": data_points,
        "period_consulted": period_label,
        "ai_model": llm_res.get("model", settings.OLLAMA_MODEL),
        "latency_ms": round(llm_res.get("latency_ms", 0.0), 2),
        "is_fallback": is_fallback
    }
