import requests
import time
import logging
from typing import Dict, Any, List, Tuple
from psycopg2.extras import Json
from airflow.include.config import settings
from airflow.include.db import get_db_cursor

logger = logging.getLogger("sismowatch.ingestion")

def fetch_usgs_feed(feed_url: str = None, timeout: int = 30) -> Tuple[Dict[str, Any], float]:
    """
    Fetches GeoJSON feed from USGS with timeouts, validation and latency calculation.
    """
    url = feed_url or settings.USGS_REALTIME_FEED_URL
    start_time = time.time()
    logger.info(f"Connecting to USGS feed: {url}")
    
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "SismoWatch-DataPlatform/1.0 (+https://sismowatch.internal)"}
    )
    latency_ms = (time.time() - start_time) * 1000.0
    
    if response.status_code != 200:
        raise ValueError(f"USGS API error: HTTP {response.status_code} - {response.text[:200]}")
    
    payload = response.json()
    if payload.get("type") != "FeatureCollection" or "features" not in payload:
        raise ValueError("Invalid GeoJSON payload: missing 'FeatureCollection' or 'features'")
        
    logger.info(f"USGS feed fetched successfully in {latency_ms:.2f} ms ({len(payload['features'])} features)")
    return payload, latency_ms

def fetch_usgs_historical(
    start_date: str,
    end_date: str,
    min_magnitude: float = 2.5,
    timeout: int = 60
) -> Tuple[Dict[str, Any], float]:
    """
    Queries USGS FDSNWS event catalog for historical backfills.
    Dates format: YYYY-MM-DD
    """
    params = {
        "format": "geojson",
        "starttime": start_date,
        "endtime": end_date,
        "minmagnitude": min_magnitude,
        "orderby": "time-asc"
    }
    start_time = time.time()
    logger.info(f"Querying historical USGS data from {start_date} to {end_date} (min_mag: {min_magnitude})")
    
    response = requests.get(
        settings.USGS_HISTORICAL_QUERY_URL,
        params=params,
        timeout=timeout,
        headers={"User-Agent": "SismoWatch-Backfill/1.0"}
    )
    latency_ms = (time.time() - start_time) * 1000.0
    
    if response.status_code != 200:
        raise ValueError(f"USGS Historical query error: HTTP {response.status_code} - {response.text[:200]}")
        
    payload = response.json()
    if payload.get("type") != "FeatureCollection" or "features" not in payload:
        raise ValueError("Invalid GeoJSON payload from historical query")
        
    logger.info(f"Historical query completed in {latency_ms:.2f} ms ({len(payload['features'])} features)")
    return payload, latency_ms

def persist_raw_payloads(
    features: List[Dict[str, Any]],
    execution_id: str,
    source_feed: str,
    http_status: int = 200
) -> int:
    """
    Persists raw payloads idempotently into raw.usgs_earthquakes_raw using upsert on id.
    Uses 'ingest' role.
    """
    if not features:
        return 0

    inserted_or_updated = 0
    query = """
    INSERT INTO raw.usgs_earthquakes_raw (
        id, raw_payload, ingested_at, execution_id, source_feed, http_status
    )
    VALUES (%s, %s, NOW(), %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        raw_payload = EXCLUDED.raw_payload,
        ingested_at = NOW(),
        execution_id = EXCLUDED.execution_id,
        source_feed = EXCLUDED.source_feed,
        http_status = EXCLUDED.http_status;
    """
    
    with get_db_cursor(role="ingest", commit=True) as cur:
        for feature in features:
            event_id = feature.get("id")
            if not event_id:
                continue
            cur.execute(
                query,
                (event_id, Json(feature), execution_id, source_feed, http_status)
            )
            inserted_or_updated += 1
            
    logger.info(f"Persisted {inserted_or_updated} raw features into raw.usgs_earthquakes_raw")
    return inserted_or_updated

def record_ingestion_metric(
    execution_id: str,
    feed_url: str,
    status: str,
    events_extracted: int,
    response_time_ms: float,
    error_message: str = None
):
    """
    Records ingestion run telemetry into raw.ingestion_metrics using 'ingest' role.
    """
    query = """
    INSERT INTO raw.ingestion_metrics (
        execution_id, feed_url, status, events_extracted, response_time_ms, error_message, created_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, NOW());
    """
    try:
        with get_db_cursor(role="ingest", commit=True) as cur:
            cur.execute(
                query,
                (execution_id, feed_url, status, events_extracted, response_time_ms, error_message)
            )
    except Exception as e:
        logger.error(f"Failed to record ingestion metric: {e}")
