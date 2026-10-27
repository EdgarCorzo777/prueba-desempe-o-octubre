"""
backfill.py
Parametrized historical backfill utility for USGS earthquake data.
Loads past N days (default 30 days) and promotes through Medallion layers idempotently.
"""

import sys
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# Ensure project root in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from airflow.include.config import settings
from airflow.include.ingestion.usgs_client import fetch_usgs_historical, persist_raw_payloads, record_ingestion_metric
from spark.jobs.process_medallion import run_medallion_pipeline

logger = logging.getLogger("sismowatch.backfill")

def execute_historical_backfill(
    days: int = 30,
    min_magnitude: float = 2.5,
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes an end-to-end historical backfill:
    1. Queries USGS historical catalog.
    2. Persists raw payloads to Bronze (raw.usgs_earthquakes_raw).
    3. Promotes through Medallion pipeline (Bronze -> Silver -> Gold).
    4. Upsert ensures complete idempotency with zero duplicate records.
    """
    now = datetime.now(timezone.utc)
    if custom_start and custom_end:
        start_str = custom_start
        end_str = custom_end
    else:
        start_date = now - timedelta(days=days)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = now.strftime("%Y-%m-%d")

    exec_id = f"backfill_{start_str}_to_{end_str}_{int(now.timestamp())}"
    logger.info(f"Initiating historical backfill {exec_id} (days={days}, min_mag={min_magnitude})")

    # Step 1: Fetch USGS historical data
    payload, latency_ms = fetch_usgs_historical(
        start_date=start_str,
        end_date=end_str,
        min_magnitude=min_magnitude,
        timeout=90
    )
    features = payload.get("features", [])
    logger.info(f"Retrieved {len(features)} historical features from USGS")

    # Step 2: Persist to Bronze (MinIO Lakehouse + Raw Metadata)
    try:
        from airflow.include.storage.minio_lake import persist_raw_feed_to_lake
        persist_raw_feed_to_lake(feed_data=payload, execution_id=exec_id)
    except Exception as minio_err:
        logger.warning(f"Could not persist historical feed to MinIO lake: {minio_err}")

    feed_label = f"USGS_QUERY_BACKFILL_{start_str}_to_{end_str}"
    persisted_raw = persist_raw_payloads(
        features=features,
        execution_id=exec_id,
        source_feed=feed_label,
        http_status=200
    )
    record_ingestion_metric(
        execution_id=exec_id,
        feed_url=feed_label,
        status="SUCCESS",
        events_extracted=persisted_raw,
        response_time_ms=latency_ms
    )

    # Step 3: Run Medallion transformations & Quality checks
    pipeline_result = run_medallion_pipeline(execution_id=exec_id, raw_features=features)

    return {
        "execution_id": exec_id,
        "period": f"{start_str} to {end_str}",
        "raw_events_fetched": len(features),
        "persisted_to_bronze": persisted_raw,
        "valid_promoted_to_gold": pipeline_result.get("published_to_gold", 0),
        "quarantined": pipeline_result.get("quarantined_count", 0),
        "quality_score": pipeline_result.get("quality_score", 100.0)
    }

if __name__ == "__main__":
    days_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    min_mag_arg = float(sys.argv[2]) if len(sys.argv) > 2 else 2.5
    res = execute_historical_backfill(days=days_arg, min_magnitude=min_mag_arg)
    print("Backfill executed successfully:", res)
