"""
chat_service.py
Motor conversacional inteligente con grounded data exclusivo de curated.events (Gold).
Previene alucinaciones calculando cifras matemáticas certificadas antes del prompt a Ollama.
Soporta resolución temporal precisa (zona horaria Colombia UTC-5: hoy, ayer, últimas 24h, semana).
"""

import re
import json
import logging
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timezone, timedelta
from api.app.database import db_cursor
from airflow.include.ai.ollama_client import generate_chat_completion, sanitize_user_input
from api.app.config import settings

logger = logging.getLogger("sismowatch.chat_service")

# ============================================================================
# Typos conversacionales auxiliares.
# Privacidad: el texto que NO sea del dominio jamás sale hacia un proveedor de
# IA — las respuestas off-topic y de cortesía son 100% deterministas.
# ============================================================================
SMALLTALK_KEYWORDS = [
    "hola", "buenas", "buenos días", "buenos dias", "buenas tardes", "buenas noches",
    "saludos", "gracias", "muchas gracias", "quién eres", "quien eres", "qué eres",
    "que eres", "cómo estás", "como estas", "qué puedes hacer", "que puedes hacer",
    "ayuda", "help", "presentate", "preséntate",
]

# Términos FUERTES del dominio (por sí solos habilitan la consulta).
SEISMIC_TERM_KEYWORDS = [
    "sismo", "sísmic", "sismic", "terremoto", "temblor", "earthquake", "quake",
    "tremor", "magnitud", "magnitude", "epicentro", "hipocentro", "tsunami",
    "maremoto", "enjambre", "anomal", "réplica", "replica", "aftershock", "telúric",
    "teluric", "volcan", "volcán", "sismógraf", "sismograf", "geolog",
    "medallion", "arquitectura", "orquesta", "pipeline", "dag", "dags", "airflow",
    "bronze", "silver", "cuarentena", "quarantine", "backfill", "sismowatch",
    "plataforma", "proyecto", "despliegu", "contenedor", "docker", "stack",
    "red global",
]

# Términos MODERADOS (solo acompañan; en esta app siempre son datos sísmicos).
MODERATE_TERM_KEYWORDS = [
    "kpi", "métric", "metric", "diagrama", "diagram", "grafic", "gráfic",
    "ranking", "tabla", "compar", "barras", "visual", "conteo", "cuánt", "cuant",
    "total", "cantidad", "telemetría", "telemetria", "alerta", "alertas", "aviso",
    "reporte", "reportes", "frecuencia", "actividad", "ocurri", "registrar",
    "registr", "histórico", "historico", "tendencia", "evolución", "region",
    "región", "regiones", "zona", "zonas", "profundidad", "calidad", "falla",
    "plan de emergencia",
]

PROJECT_KEYWORDS = [
    "arquitectura", "medallion", "bronze", "silver", "orquesta", "pipeline",
    "dag", "dags", "airflow", "tecnolog", "stack", "calidad de datos", "cuarentena",
    "quarantine", "backfill", "backfill histórico", "plataforma", "sismowatch", "proyecto",
    "reglas de calidad", "reglas de validación", "puntaje de calidad", "score de calidad",
    "calidad de datos", "calidad de los datos", "calidad del dato", "calidad del sistema",
    "infraestruct", "despliegu", "contenedor", "docker", "autenticación", "autenticacion",
    "roles", "notificac", "stream", "sse", "latencia", "cómo funciona", "como funciona",
    "funciona el sistema", "construido", "hecho con", "base de datos",
]

VISUAL_KEYWORDS = [
    "diagrama", "diagram", "grafic", "gráfic", "chart", "ranking", "tabla",
    "compar", "barras", "dibuj", "visual", "mejores", "más fuertes", "mas fuertes",
]

FAREWELL_KEYWORDS = [
    "chao", "chaito", "adiós", "adios", "hasta luego", "hasta pronto",
    "hasta mañana", "nos vemos", "bye", "goodbye", "me voy",
    "cuídate", "cuidate", "hasta la vista", "fin de la conversación",
]

FAREWELL_ANSWER = (
    "¡Hasta pronto! 👋 Fue un gusto ayudarte con el monitoreo sísmico.\n\n"
    "Recuerda que estoy disponible 24/7 para consultas de actividad sísmica "
    "reciente, alertas de tsunami y el estado de la plataforma SismoWatch."
)

OFF_TOPIC_ANSWER = (
    "Lo siento, esa consulta está fuera de mi alcance. Solo puedo ayudarte con:\n\n"
    "1. **Actividad sísmica:** conteos, magnitudes, regiones, alertas de tsunami y anomalías.\n"
    "2. **La plataforma SismoWatch:** su arquitectura, calidad de datos, reportes y alertas.\n\n"
    "Reformula tu pregunta sobre sismicidad o sobre el sistema y te respondo con las cifras "
    "certificadas del monitoreo."
)

SMALLTALK_ANSWER = (
    "¡Hola! Soy **SismoWatch AI**, el asistente analítico de la plataforma de monitoreo sísmico. "
    "Puedo ayudarte con:\n\n"
    "• Estadísticas de sismos (hoy, últimas 24/48 horas, 30 días…)\n"
    "• Magnitudes máximas, promedios y rankings por región\n"
    "• Alertas de tsunami y anomalías (enjambres, picos M≥6.0)\n"
    "• La plataforma en sí: arquitectura, calidad de datos, reportes diarios\n\n"
    "Pregúntame sobre actividad sísmica reciente y te respondo con cifras certificadas."
)

# Ficha técnica certera para preguntas sobre la plataforma. Facts del repositorio —
# sin credenciales, sin nombres de proveedores IA, con pilares de la solución.
PROJECT_KNOWLEDGE = {
    "propósito": (
        "SismoWatch es la plataforma de monitoreo de riesgo sísmico global: convierte los feeds "
        "públicos del USGS en un producto de datos certificado y consumible."
    ),
    "arquitectura (Medallion)": (
        "Patrón de 3 capas: crudo inmutable (payload íntegro tal como lo entregó el USGS) → "
        "conformado (normalizado, tipado, con control de calidad) → curada certificada (los "
        "sismos válidos y sus métricas agregadas). Los registros que fallan las reglas van a "
        "cuarentena auditable, nunca se descartan en silencio."
    ),
    "orquestación": (
        "Apache Airflow con 3 flujos: ingesta automática cada 5 minutos, transformación+calidad "
        "encadenada al término de la ingesta, y reporte ejecutivo diario a las 07:00 hora Colombia."
    ),
    "calidad de datos": (
        "7 reglas de validación por lote (ID obligatorio, timestamp válido, coordenadas válidas, "
        "latitud [-90,90], longitud [-180,180], magnitud [-2,10], profundidad [-5,1000] km), con "
        "puntaje de calidad por lote y cuarentena con payload original y motivo de rechazo."
    ),
    "tiempo real": (
        "Notificaciones en vivo vía Server-Sent Events (~2-3 s desde la entrada del sismo al "
        "sistema hasta la pantalla), refresco silencioso de KPIs y gráficas sin recargar, y "
        "efecto visual de grietas para M≥2.5 o alertas de tsunami."
    ),
    "IA confiable": (
        "El asistente (este chat) y los reportes diarios son generados con IA que SOLO redacta "
        "sobre cifras calculadas por el sistema; el texto se valida contra los números "
        "certificados y si no coincide se usa un motor determinista de respaldo."
    ),
    "anomalías": (
        "Detector estadístico Z-Score sobre ventanas móviles por región: enjambres sísmicos "
        "(Z>2.5) y picos de magnitud M≥6.0, cada alerta queda registrada con su explicación."
    ),
    "histórico (backfill)": (
        "Carga histórica idempotente de 1 a 60 días con filtro de magnitud mínima: re-lanzarla "
        "dos veces produce exactamente los mismos datos, sin duplicados ni notificaciones fantasma."
    ),
    "seguridad": (
        "Acceso por roles (admin/viewer) con sesiones JWT firmadas; el rol de consulta solo "
        "tiene permisos de lectura sobre los datos certificados, verificado con pruebas "
        "automatizadas (403 para viewers en endpoints de administración)."
    ),
}


def resolve_time_window(query: str) -> Tuple[datetime, datetime, str]:
    """
    Resolves start time, end time, and label.
    Supports Colombia timezone (UTC-5) for "hoy", "ayer", etc.,
    plus explicit numeric windows ("48 horas", "3 días", "12 h").
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

    # Ventanas numéricas explícitas: "48 horas", "12 h", "3 días", "7 dias"
    # Topes alineados con la capacidad de datos (60 días = 1440 h).
    m_hours = re.search(r"(\d+(?:\.\d+)?)\s*(?:horas|hora|hrs?|hs?|h)\b", lower)
    m_days = re.search(r"(\d+(?:\.\d+)?)\s*(?:d[ií]as|d[ií]a|ds?|d)\b", lower)
    if m_hours:
        n_hours = min(int(float(m_hours.group(1))), 1440) or 24
        start_utc = now_utc - timedelta(hours=n_hours)
        period_label = f"Últimas {n_hours} horas ({start_utc.strftime('%Y-%m-%d %H:%M')} a {now_utc.strftime('%Y-%m-%d %H:%M')} UTC)"
        return start_utc, now_utc, period_label
    if m_days:
        n_days = min(int(float(m_days.group(1))), 60) or 7
        start_utc = now_utc - timedelta(days=n_days)
        period_label = f"Últimos {n_days} días ({start_utc.strftime('%Y-%m-%d')} a {now_utc.strftime('%Y-%m-%d')} UTC)"
        return start_utc, now_utc, period_label

    if "semana" in lower or "últimos días" in lower or "ultimos dias" in lower:
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

# Umbral de magnitud escrito de formas naturales: "M>=6", "M≥4.5", "M > 2.5",
# "magnitud mayor a 6", "magnitud superior a 4.5", "5 o mayor".
MAGNITUDE_THRESHOLD_PATTERNS = [
    r"\bm\s*[≥>][=>]?\s*(\d+(?:\.\d+)?)",
    r"magnitud(?:es)?\s*(?:de\s*)?(?:mayor(?:es)?\s*(?:a|que)|superior(?:es)?\s*(?:a|que)|al\s*menos|m[ií]nimo(?:\s*de)?)\s*(\d+(?:\.\d+)?)",
    r"(\d+(?:\.\d+)?)\s*(?:o\s*mayor(?:es)?|o\s*más)",
]

def extract_magnitude_threshold(query: str) -> Optional[float]:
    """
    Extracts an explicit magnitude floor (e.g. "M>=6.0") if the user asked for one,
    so the chat answers with EXACTLY those events instead of the general KPIs.
    """
    for pattern in MAGNITUDE_THRESHOLD_PATTERNS:
        m = re.search(pattern, query)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None

def _is_project_query(lower: str) -> bool:
    return any(k in lower for k in PROJECT_KEYWORDS)

def _is_topical_query(lower: str) -> bool:
    """True si la pregunta pertenece al dominio (sismología / plataforma)."""
    if any(k in lower for k in SEISMIC_TERM_KEYWORDS):
        return True
    if any(k in lower for k in MODERATE_TERM_KEYWORDS):
        return True
    if extract_magnitude_threshold(lower) is not None:
        return True
    # "M6.5", "m 4.2" símbolos sueltos
    return bool(re.search(r"\bm\s*\d", lower))

def resolve_intent(query: str) -> str:
    """
    Identifies analytical intent with priority:
    smalltalk > specific phenomena > magnitude threshold > geographic/magnitude
    combos > generic analytics > platform questions > off-topic guard.
    """
    lower = query.lower()
    is_topical = _is_topical_query(lower)
    is_project = _is_project_query(lower)

    # 0. Cortesía (sin términos del dominio): NO se envía al LLM.
    # La despedida primero: "bye" o "adiós" no deben caer en el mensaje genérico.
    if (any(k in lower for k in FAREWELL_KEYWORDS)
            and not is_topical and not is_project
            and len(lower.split()) <= 8):
        return "farewell"

    if (any(k in lower for k in SMALLTALK_KEYWORDS)
            and not is_topical and not is_project
            and len(lower.split()) <= 8):
        return "smalltalk"

    # 1. Tsunami alerts
    if "tsunami" in lower or "maremoto" in lower:
        return "tsunami"

    # 2. Statistical anomalies
    if "anomal" in lower or "enjambre" in lower or "atípico" in lower or "atipico" in lower:
        return "anomalies"

    # 3. Explicit magnitude floor: the query is about M>=X events only
    if extract_magnitude_threshold(lower) is not None:
        return "magnitude_threshold"

    # 4. Maximum magnitude combined with geography: "¿Dónde fue el sismo más fuerte?"
    #    asks for THE place of the strongest event, not a regions ranking.
    max_keywords = ["máxim", "maxim", "más fuerte", "mas fuerte", "mayor magnitud", "más grande", "mas grande"]
    region_keywords = [
        "region", "región", "regiones", "zona", "zonas", "lugar", "lugares",
        "país", "pais", "paises", "países", "dónde", "donde", "ubicación", "ubicacion"
    ]
    is_max_query = any(k in lower for k in max_keywords) or ("fuerte" in lower and "sismo" in lower)
    is_geo_query = any(k in lower for k in region_keywords)

    if is_geo_query and is_max_query:
        return "max_magnitude"

    # 5. Pure geographic / Region-based queries
    if is_geo_query:
        return "top_regions"

    # 6. Trends / historical
    if "tendencia" in lower or "histórico" in lower or "historico" in lower or "evolución" in lower:
        return "weekly_trend"

    # 7. Maximum magnitude
    if is_max_query:
        return "max_magnitude"

    # 8. Event counts
    count_keywords = ["cuánt", "cuant", "total", "cantidad", "número", "numero"]
    if any(k in lower for k in count_keywords):
        return "count_events"

    # 9. Preguntas sobre la plataforma (arquitectura, calidad, pipeline…)
    if is_project:
        return "project_info"

    # 10. Consulta de dominio sin intención específica
    if is_topical:
        return "general_kpis"

    # 11. Fuera de alcance (privacidad: texto ajeno no viaja al LLM)
    return "off_topic"

def wants_visual(lower_query: str) -> bool:
    """True si el usuario pidió diagrama, tabla, ranking o comparación."""
    return any(k in lower_query for k in VISUAL_KEYWORDS)

def _build_comparison_table(intent: str, d: Dict[str, Any]) -> Optional[str]:
    """
    Construye una tabla markdown con las filas del lote de datos certificados,
    para que comparaciones y rankings se rendericen correctamente en la UI.
    """
    if not isinstance(d, dict):
        return None

    if intent in ("count_events", "max_magnitude", "magnitude_threshold", "general_kpis"):
        lst = d.get("sismos_mas_fuertes") or []
        if not lst:
            return None
        rows = [
            "| # | Lugar | Magnitud | Profundidad (km) | Hora (UTC) |",
            "|---|-------|----------|------------------|------------|",
        ]
        for i, e in enumerate(lst[:5], 1):
            rows.append(
                f"| {i} | {str(e.get('lugar', 'N/A'))[:40]} | M{e.get('magnitud')} | "
                f"{e.get('profundidad_km')} | {e.get('fecha_utc')} |"
            )
        return "\n".join(rows)

    if intent == "top_regions":
        lst = d.get("regiones_con_mayor_actividad") or []
        if not lst:
            return None
        rows = [
            "| Región | Sismos | Magnitud máxima | Magnitud promedio |",
            "|--------|--------|-----------------|-------------------|",
        ]
        for r in lst[:5]:
            rows.append(
                f"| {str(r['region'])[:38]} | {r['total_sismos']} | M{r['magnitud_maxima']} | M{r['magnitud_promedio']} |"
            )
        return "\n".join(rows)

    if intent == "weekly_trend":
        lst = d.get("tendencia_diaria") or []
        if not lst:
            return None
        rows = [
            "| Fecha (UTC) | Sismos | Magnitud máxima |",
            "|-------------|--------|-----------------|",
        ]
        for t in lst[:30]:
            rows.append(f"| {t['fecha']} | {t['sismos']} | M{t['magnitud_maxima']} |")
        return "\n".join(rows)

    if intent == "anomalies":
        lst = d.get("alertas_recientes") or []
        if not lst:
            return None
        rows = [
            "| Tipo | Región | Z-Score | Eventos | Magnitud promedio |",
            "|------|--------|---------|---------|-------------------|",
        ]
        for a in lst[:5]:
            rows.append(
                f"| {a['tipo']} | {str(a['region'])[:32]} | {a['z_score']} | {a['conteo_eventos']} | M{a['magnitud_promedio']} |"
            )
        return "\n".join(rows)

    if intent == "tsunami":
        lst = d.get("detalle_eventos") or []
        if not lst:
            return None
        rows = [
            "| Lugar | Magnitud | Profundidad (km) | Hora (UTC) |",
            "|-------|----------|------------------|------------|",
        ]
        for e in lst[:10]:
            rows.append(
                f"| {str(e.get('lugar', 'N/A'))[:40]} | M{e.get('magnitud')} | {e.get('profundidad_km')} | {e.get('hora')} |"
            )
        return "\n".join(rows)

    return None

def answer_user_query_grounded_in_gold(question: str) -> Dict[str, Any]:
    """
    Executes grounded conversational workflow:
    1. Sanitizes question.
    2. Resolves intent and exact time window.
    3. Runs parameterized query on curated.events.
    4. Prompts the LLM with certified figures.
    5. Returns grounded answer with fallbacks.
    Off-topic and courtesy queries are answered deterministically WITHOUT
    calling any external AI provider (privacy by design).
    """
    clean_q = sanitize_user_input(question)
    start_utc, end_utc, period_label = resolve_time_window(clean_q)
    intent = resolve_intent(clean_q)

    # --- Guardas de conversación (deterministas, sin LLM) ---
    if intent == "off_topic":
        return {
            "question": clean_q,
            "answer": OFF_TOPIC_ANSWER,
            "data_points": {},
            "period_consulted": "No aplica (consulta fuera de alcance)",
            "ai_model": "determinista",
            "latency_ms": 0.0,
            "is_fallback": True,
        }

    if intent == "farewell":
        return {
            "question": clean_q,
            "answer": FAREWELL_ANSWER,
            "data_points": {},
            "period_consulted": "No aplica",
            "ai_model": "determinista",
            "latency_ms": 0.0,
            "is_fallback": True,
        }

    if intent == "smalltalk":
        return {
            "question": clean_q,
            "answer": SMALLTALK_ANSWER,
            "data_points": {},
            "period_consulted": "No aplica",
            "ai_model": "determinista",
            "latency_ms": 0.0,
            "is_fallback": True,
        }

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

        elif intent == "magnitude_threshold":
            min_mag = extract_magnitude_threshold(clean_q.lower()) or 0.0
            cur.execute(
                """
                SELECT event_id, place, magnitude, depth_km, event_time, tsunami, url
                FROM curated.events
                WHERE magnitude >= %s AND event_time >= %s AND event_time <= %s
                ORDER BY magnitude DESC
                LIMIT 10;
                """,
                (min_mag, start_utc, end_utc)
            )
            threshold_events = cur.fetchall() or []
            cur.execute(
                """
                SELECT COUNT(*)::int as tot
                FROM curated.events
                WHERE magnitude >= %s AND event_time >= %s AND event_time <= %s;
                """,
                (min_mag, start_utc, end_utc)
            )
            total_threshold = cur.fetchone()["tot"]
            data_points = {
                "periodo": period_label,
                "umbral_magnitud": min_mag,
                "total_sismos_igual_o_mayores": total_threshold,
                "sismos_mas_fuertes": [
                    {
                        "lugar": e.get("place", "N/A"),
                        "magnitud": round(float(e["magnitude"]), 2),
                        "profundidad_km": round(float(e["depth_km"]), 1),
                        "fecha_utc": e["event_time"].strftime("%Y-%m-%d %H:%M UTC") if e.get("event_time") else "N/A",
                        "tsunami": e.get("tsunami", False)
                    }
                    for e in threshold_events
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

        elif intent == "project_info":
            pass  # No requiere consulta: se llena con la ficha técnica después del bloque.

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

    # Ficha técnica para preguntas sobre la plataforma (sin datos sísmicos)
    if intent == "project_info":
        data_points = {
            "ficha_tecnica_plataforma": PROJECT_KNOWLEDGE,
            "periodo": "Pregunta sobre la plataforma SismoWatch (sin ventana temporal)",
        }

    # Tabla comparativa: si el usuario pidió diagrama/tabla/ranking/comparación,
    # se ancla una tabla markdown al JSON para que el LLM la cite tal cual.
    tabla_certificada = _build_comparison_table(intent, data_points) if wants_visual(clean_q.lower()) else None
    if tabla_certificada:
        data_points["tabla_markdown"] = tabla_certificada

    # Prompts versionados (airflow/include/ai/prompts/) — el LLM solo redacta
    from airflow.include.ai.prompting import load_prompt

    system_prompt = load_prompt("chat_system.md")

    prompt = load_prompt(
        "chat_user.md",
        {
            "QUESTION": clean_q,
            "PERIOD": period_label,
            "INTENT": intent,
            "DATA_JSON": json.dumps(data_points, ensure_ascii=False, indent=2),
        },
    )

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

        elif intent == "magnitude_threshold":
            thr = data_points.get("umbral_magnitud", 0.0)
            cnt = data_points.get("total_sismos_igual_o_mayores", 0)
            if cnt > 0:
                strongest = data_points.get("sismos_mas_fuertes", [])
                top_str = f" El más fuerte fue de M{strongest[0]['magnitud']} en {strongest[0]['lugar']}." if strongest else ""
                answer_text = f"Durante {period_label} se registraron {cnt} sismos de magnitud M≥{thr:g} en los registros certificados.{top_str}"
            else:
                answer_text = f"Durante {period_label} no se registraron sismos de magnitud M≥{thr:g} en los registros certificados."

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

        elif intent == "project_info":
            answer_text = (
                "SismoWatch es la plataforma de monitoreo de riesgo sísmico global: convierte los feeds "
                "públicos del USGS en un producto de datos certificado. Sus pilares:\n\n"
                "1. **Arquitectura Medallion:** capa cruda inmutable → conformado con control de calidad → "
                "capa curada certificada; los rechazos van a cuarentena auditable.\n"
                "2. **Orquestación con Apache Airflow:** ingesta cada 5 minutos, transformación encadenada y "
                "reporte ejecutivo diario a las 07:00 Colombia.\n"
                "3. **Calidad:** 7 reglas geofísicas por lote con puntaje y cuarentena trazable.\n"
                "4. **Tiempo real:** notificaciones en vivo (~2-3 s) con refresco silencioso de estadísticas.\n"
                "5. **IA confiable:** este asistente y los reportes solo redactan sobre cifras certificadas, "
                "con motor determinista de respaldo.\n"
                "6. **Anomalías:** detector Z-Score (enjambres por región, picos M≥6.0)."
            )

        else:
            tot = data_points.get("total_sismos", 0)
            max_m = data_points.get("magnitud_maxima", 0.0)
            avg_m = data_points.get("magnitud_promedio", 0.0)
            top_ev = data_points.get("sismo_mas_fuerte")
            top_str = f" El evento más fuerte fue de M{top_ev['magnitud']} en {top_ev['lugar']}." if top_ev else ""
            answer_text = f"En {period_label} se registraron un total de {tot} sismos certificados, con una magnitud promedio de {avg_m} y una magnitud máxima de {max_m}.{top_str}"

    # Tabla comparativa garantizada: si el LLM no la incluyó (o es fallback),
    # se adjunta la tabla certificada construida desde los datos certificados.
    if tabla_certificada and "|" not in answer_text:
        answer_text += "\n\n**Tabla comparativa (datos certificados):**\n\n" + tabla_certificada

    # Las preguntas de plataforma no tienen ventana temporal: no decir "últimas 24 h".
    if intent == "project_info":
        period_label = "Pregunta sobre la plataforma (sin ventana temporal)"

    return {
        "question": clean_q,
        "answer": answer_text,
        "data_points": data_points,
        "period_consulted": period_label,
        "ai_model": llm_res.get("model", settings.OLLAMA_MODEL),
        "latency_ms": round(llm_res.get("latency_ms", 0.0), 2),
        "is_fallback": is_fallback
    }
