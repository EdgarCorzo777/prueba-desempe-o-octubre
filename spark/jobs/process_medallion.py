"""
process_medallion.py
Core Medallion Pipeline Processor (Bronze -> Silver -> Quality -> Gold)
Supports running in PySpark or vectorized Python execution mode.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

# Ensure airflow/include is importable
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from airflow.include.config import settings
from airflow.include.db import get_db_cursor
from airflow.include.quality.quality_checker import (
    evaluate_batch_quality,
    persist_quarantine_records,
    persist_quality_metrics
)

logger = logging.getLogger("sismowatch.medallion")

def fetch_bronze_records(limit: Optional[int] = None, execution_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extracts raw features from Bronze (raw.usgs_earthquakes_raw).
    Uses 'transform' role.
    """
    query = """
    SELECT id, raw_payload, execution_id, ingested_at
    FROM raw.usgs_earthquakes_raw
    """
    params = []
    if execution_id:
        query += " WHERE execution_id = %s"
        params.append(execution_id)
        
    query += " ORDER BY ingested_at DESC"
    if limit:
        query += f" LIMIT {limit}"
        
    with get_db_cursor(role="transform", commit=False) as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        
    features = []
    for row in rows:
        payload = row["raw_payload"]
        if isinstance(payload, dict):
            features.append(payload)
    return features

def upsert_silver_records(valid_records: List[Dict[str, Any]]) -> int:
    """
    Upserts validated records into Silver (staging.usgs_earthquakes_staging).
    Uses 'transform' role.
    """
    if not valid_records:
        return 0
        
    query = """
    INSERT INTO staging.usgs_earthquakes_staging (
        event_id, magnitude, mag_type, place, event_time, updated_time,
        tsunami, sig, status, event_type, longitude, latitude, depth_km,
        url, source_execution_id, transformed_at
    )
    VALUES (
        %(event_id)s, %(magnitude)s, %(mag_type)s, %(place)s, %(event_time)s, %(updated_time)s,
        %(tsunami_int)s, %(sig)s, %(status)s, %(event_type)s, %(longitude)s, %(latitude)s, %(depth_km)s,
        %(url)s, %(source_execution_id)s, NOW()
    )
    ON CONFLICT (event_id) DO UPDATE SET
        magnitude = EXCLUDED.magnitude,
        mag_type = EXCLUDED.mag_type,
        place = EXCLUDED.place,
        event_time = EXCLUDED.event_time,
        updated_time = EXCLUDED.updated_time,
        tsunami = EXCLUDED.tsunami,
        sig = EXCLUDED.sig,
        status = EXCLUDED.status,
        event_type = EXCLUDED.event_type,
        longitude = EXCLUDED.longitude,
        latitude = EXCLUDED.latitude,
        depth_km = EXCLUDED.depth_km,
        url = EXCLUDED.url,
        source_execution_id = EXCLUDED.source_execution_id,
        transformed_at = NOW();
    """
    with get_db_cursor(role="transform", commit=True) as cur:
        for r in valid_records:
            cur.execute(query, r)
            
    logger.info(f"Upserted {len(valid_records)} records into staging.usgs_earthquakes_staging")
    return len(valid_records)

def publish_gold_records(valid_records: List[Dict[str, Any]]) -> int:
    """
    Publishes verified records to Gold (curated.events).
    Guarantees idempotency and revision ordering:
    Only updates if EXCLUDED.updated_time >= curated.events.updated_time.
    Uses 'transform' role.
    """
    if not valid_records:
        return 0

    query = """
    INSERT INTO curated.events (
        event_id, magnitude, mag_type, place, event_time, updated_time,
        tsunami, sig, status, event_type, longitude, latitude, depth_km,
        severity_level, url, ingestion_batch_id, published_at
    )
    VALUES (
        %(event_id)s, %(magnitude)s, %(mag_type)s, %(place)s, %(event_time)s, %(updated_time)s,
        %(tsunami)s, %(sig)s, %(status)s, %(event_type)s, %(longitude)s, %(latitude)s, %(depth_km)s,
        %(severity_level)s, %(url)s, %(source_execution_id)s, NOW()
    )
    ON CONFLICT (event_id) DO UPDATE SET
        magnitude = EXCLUDED.magnitude,
        mag_type = EXCLUDED.mag_type,
        place = EXCLUDED.place,
        event_time = EXCLUDED.event_time,
        updated_time = EXCLUDED.updated_time,
        tsunami = EXCLUDED.tsunami,
        sig = EXCLUDED.sig,
        status = EXCLUDED.status,
        event_type = EXCLUDED.event_type,
        longitude = EXCLUDED.longitude,
        latitude = EXCLUDED.latitude,
        depth_km = EXCLUDED.depth_km,
        severity_level = EXCLUDED.severity_level,
        url = EXCLUDED.url,
        ingestion_batch_id = EXCLUDED.ingestion_batch_id,
        published_at = NOW()
    WHERE EXCLUDED.updated_time >= curated.events.updated_time;
    """
    published_count = 0
    with get_db_cursor(role="transform", commit=True) as cur:
        for r in valid_records:
            cur.execute(query, r)
            published_count += cur.rowcount
            
    logger.info(f"Published/Refreshed {published_count} records into curated.events")
    return published_count

def refresh_curated_kpis() -> Dict[str, Any]:
    """
    Aggregates metrics for the last 24 hours into curated.daily_kpis.
    Calculates total events, max magnitude, avg magnitude, tsunami count,
    magnitude distribution, and top active regions.
    Uses 'transform' role.
    """
    today_date = datetime.now(timezone.utc).date()
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)

    agg_query = """
    SELECT
        COUNT(*)::int as total_events,
        COALESCE(MAX(magnitude), 0.0)::float as max_magnitude,
        COALESCE(AVG(magnitude), 0.0)::float as avg_magnitude,
        COUNT(*) FILTER (WHERE tsunami = TRUE)::int as tsunami_alerts_count
    FROM curated.events
    WHERE event_time >= %s;
    """
    
    regions_query = """
    SELECT 
        COALESCE(NULLIF(SPLIT_PART(place, ', ', 2), ''), place) as region_name,
        COUNT(*)::int as count,
        MAX(magnitude)::float as max_mag
    FROM curated.events
    WHERE event_time >= %s
    GROUP BY 1
    ORDER BY count DESC
    LIMIT 5;
    """
    
    dist_query = """
    SELECT
        severity_level,
        COUNT(*)::int as count
    FROM curated.events
    WHERE event_time >= %s
    GROUP BY severity_level;
    """
    
    with get_db_cursor(role="transform", commit=True) as cur:
        cur.execute(agg_query, (yesterday,))
        agg_res = cur.fetchone() or {}
        
        cur.execute(regions_query, (yesterday,))
        regions_res = cur.fetchall() or []
        
        cur.execute(dist_query, (yesterday,))
        dist_res = cur.fetchall() or []
        
        mag_dist = {row["severity_level"]: row["count"] for row in dist_res}
        
        upsert_kpi = """
        INSERT INTO curated.daily_kpis (
            kpi_date, total_events, max_magnitude, avg_magnitude,
            tsunami_alerts_count, active_regions_json, mag_distribution_json, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (kpi_date) DO UPDATE SET
            total_events = EXCLUDED.total_events,
            max_magnitude = EXCLUDED.max_magnitude,
            avg_magnitude = EXCLUDED.avg_magnitude,
            tsunami_alerts_count = EXCLUDED.tsunami_alerts_count,
            active_regions_json = EXCLUDED.active_regions_json,
            mag_distribution_json = EXCLUDED.mag_distribution_json,
            updated_at = NOW();
        """
        import json
        cur.execute(
            upsert_kpi,
            (
                today_date,
                agg_res.get("total_events", 0),
                round(agg_res.get("max_magnitude", 0.0), 2),
                round(agg_res.get("avg_magnitude", 0.0), 2),
                agg_res.get("tsunami_alerts_count", 0),
                json.dumps(regions_res),
                json.dumps(mag_dist)
            )
        )
        
    return {
        "date": str(today_date),
        "total_events": agg_res.get("total_events", 0),
        "max_magnitude": agg_res.get("max_magnitude", 0.0),
        "avg_magnitude": agg_res.get("avg_magnitude", 0.0),
        "tsunami_alerts_count": agg_res.get("tsunami_alerts_count", 0),
        "active_regions": regions_res,
        "mag_distribution": mag_dist
    }

def run_medallion_pipeline(execution_id: str, raw_features: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Executes the complete Medallion transformation & quality pipeline:
    1. Extract from Bronze (or accept in-memory features).
    2. Evaluate quality rules & calculate score.
    3. Persist quarantined records with rejection reasons.
    4. Persist quality metrics.
    5. Block publication if quality criteria fails.
    6. Upsert valid records to Silver (staging).
    7. Publish valid records to Gold (curated).
    8. Refresh Gold KPIs.
    """
    logger.info(f"Starting Medallion processing run for execution_id: {execution_id}")
    
    if raw_features is None:
        raw_features = fetch_bronze_records(limit=2000, execution_id=execution_id)
        if not raw_features:
            # Fallback to recent Bronze records
            raw_features = fetch_bronze_records(limit=500)
            
    # Step 2: Quality evaluation
    valid_records, quarantined_records, metrics = evaluate_batch_quality(raw_features, execution_id)
    
    # Step 3: Persist quarantine records
    if quarantined_records:
        persist_quarantine_records(quarantined_records)
        
    # Step 4: Persist quality metrics
    metric_id = persist_quality_metrics(metrics)
    
    # Step 5: Blocking check: An invalid record must never reach Gold
    if metrics["status"] == "BLOCKED":
        error_msg = f"Medallion pipeline BLOCKED for execution {execution_id}: 0 valid records from {len(raw_features)} raw features"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    # Step 6: Upsert to Silver
    upsert_silver_records(valid_records)
    
    # Step 7: Publish to Gold
    published_count = publish_gold_records(valid_records)
    
    # Step 8: Refresh KPIs in Gold
    kpi_summary = refresh_curated_kpis()
    
    summary = {
        "execution_id": execution_id,
        "raw_count": len(raw_features),
        "valid_count": len(valid_records),
        "quarantined_count": len(quarantined_records),
        "published_to_gold": published_count,
        "quality_score": metrics["quality_score"],
        "metric_id": metric_id,
        "kpis": kpi_summary
    }
    logger.info(f"Medallion processing completed: {summary}")
    return summary

if __name__ == "__main__":
    exec_id = f"manual_{int(datetime.now().timestamp())}"
    res = run_medallion_pipeline(exec_id)
    print("Pipeline result:", res)
