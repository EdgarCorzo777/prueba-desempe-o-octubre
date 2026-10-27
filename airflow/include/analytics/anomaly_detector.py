"""
anomaly_detector.py
Statistical Seismic Anomaly Detection (Z-Score & Regional Swarms).
Operates exclusively on curated.events (Gold layer).
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import numpy as np
from airflow.include.db import get_db_cursor

logger = logging.getLogger("sismowatch.anomaly_detector")

DISCLAIMER_TEXT = "Nota geofísica: Una anomalía estadística representa una variación inusual en la tasa de eventos o energía sísmica detectada, pero NO constituye una predicción determinista de terremotos futuros."

def detect_seismic_anomalies(hours_window: int = 48, z_threshold: float = 2.5) -> List[Dict[str, Any]]:
    """
    Detects statistical anomalies in recent seismic activity:
    1. Seismic Swarms: Abnormal concentration of earthquakes in a specific region.
    2. Magnitude Spikes: Unusual high-energy events exceeding statistical baselines.
    Persists findings to curated.anomaly_alerts.
    Uses 'transform' role.
    """
    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(hours=hours_window)
    
    query = """
    SELECT
        COALESCE(NULLIF(SPLIT_PART(place, ', ', 2), ''), place) as region,
        COUNT(*)::int as event_count,
        MAX(magnitude)::float as max_mag,
        AVG(magnitude)::float as avg_mag,
        STDDEV(magnitude)::float as std_mag
    FROM curated.events
    WHERE event_time >= %s
    GROUP BY 1
    HAVING COUNT(*) >= 2;
    """
    
    with get_db_cursor(role="transform", commit=False) as cur:
        cur.execute(query, (window_start,))
        region_stats = cur.fetchall() or []
        
    if not region_stats:
        logger.info("No seismic events available in window to evaluate anomalies.")
        return []

    counts = [row["event_count"] for row in region_stats]
    mean_count = float(np.mean(counts))
    std_count = float(np.std(counts)) if len(counts) > 1 and np.std(counts) > 0 else 1.0

    detected_alerts = []
    
    insert_alert_query = """
    INSERT INTO curated.anomaly_alerts (
        alert_type, region, period_start, period_end, z_score,
        event_count, avg_magnitude, explanation, is_dismissed, created_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, NOW())
    RETURNING alert_id;
    """

    with get_db_cursor(role="transform", commit=True) as cur:
        for row in region_stats:
            region = row["region"]
            cnt = row["event_count"]
            max_m = row["max_mag"]
            avg_m = row["avg_mag"]
            
            # Compute Z-Score on frequency
            z_score = (cnt - mean_count) / std_count
            
            # Check for Seismic Swarm
            if z_score >= z_threshold and cnt >= 4:
                explanation = (
                    f"Enjambre sísmico detectado en {region}: Se registraron {cnt} eventos "
                    f"(Z-Score: {z_score:.2f}) con magnitud promedio de {avg_m:.2f} y máxima de {max_m:.2f} "
                    f"en las últimas {hours_window} horas. {DISCLAIMER_TEXT}"
                )
                alert_type = "SEISMIC_SWARM"
                cur.execute(
                    insert_alert_query,
                    (alert_type, region, window_start, now_utc, round(z_score, 2), cnt, round(avg_m, 2), explanation)
                )
                alert_id = cur.fetchone()["alert_id"]
                detected_alerts.append({
                    "alert_id": alert_id,
                    "alert_type": alert_type,
                    "region": region,
                    "z_score": round(z_score, 2),
                    "event_count": cnt,
                    "avg_magnitude": round(avg_m, 2),
                    "explanation": explanation
                })
                
            # Check for Magnitude Spike
            elif max_m >= 6.0:
                explanation = (
                    f"Pico de magnitud significativo en {region}: Evento sísmico destacado de magnitud {max_m:.2f}. "
                    f"Nivel de severidad elevado. {DISCLAIMER_TEXT}"
                )
                alert_type = "MAGNITUDE_SPIKE"
                cur.execute(
                    insert_alert_query,
                    (alert_type, region, window_start, now_utc, round(max(z_score, 3.0), 2), cnt, round(avg_m, 2), explanation)
                )
                alert_id = cur.fetchone()["alert_id"]
                detected_alerts.append({
                    "alert_id": alert_id,
                    "alert_type": alert_type,
                    "region": region,
                    "z_score": round(max(z_score, 3.0), 2),
                    "event_count": cnt,
                    "avg_magnitude": round(avg_m, 2),
                    "explanation": explanation
                })

    logger.info(f"Anomaly detection complete. Identified {len(detected_alerts)} alerts.")
    return detected_alerts
