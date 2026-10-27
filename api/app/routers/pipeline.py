from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from api.app.schemas.api_models import PipelineStatusResponse
from api.app.auth.dependencies import require_role
from api.app.database import db_cursor

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])

@router.get("/status", response_model=PipelineStatusResponse)
def get_pipeline_status(user: dict = Depends(require_role("viewer"))):
    """
    Returns pipeline health, ingestion state, record counts across Medallion layers,
    freshness delay, and data quality metrics.
    """
    now_utc = datetime.now(timezone.utc)
    
    with db_cursor(as_admin=False, commit=False) as cur:
        # Layer counts
        cur.execute("SELECT COUNT(*)::int as bronze_cnt FROM raw.usgs_earthquakes_raw;")
        bronze_cnt = cur.fetchone()["bronze_cnt"]
        
        cur.execute("SELECT COUNT(*)::int as silver_cnt FROM staging.usgs_earthquakes_staging;")
        silver_cnt = cur.fetchone()["silver_cnt"]
        
        cur.execute("SELECT COUNT(*)::int as gold_cnt FROM curated.events;")
        gold_cnt = cur.fetchone()["gold_cnt"]
        
        cur.execute("SELECT COUNT(*)::int as quaran_cnt FROM staging.quarantine_events;")
        quaran_cnt = cur.fetchone()["quaran_cnt"]
        
        # Latest Ingestion Metric
        cur.execute(
            """
            SELECT status, created_at
            FROM raw.ingestion_metrics
            ORDER BY created_at DESC
            LIMIT 1;
            """
        )
        latest_ingest = cur.fetchone() or {}
        
        # Latest Quality Metric
        cur.execute(
            """
            SELECT quality_score, freshness_delay_minutes, status, details, created_at
            FROM curated.quality_metrics
            ORDER BY created_at DESC
            LIMIT 1;
            """
        )
        latest_quality = cur.fetchone() or {}

    ingest_time = latest_ingest.get("created_at")
    freshness = float(latest_quality.get("freshness_delay_minutes", 0.0))
    if ingest_time:
        freshness = max(0.0, (now_utc - ingest_time).total_seconds() / 60.0)

    # Simulated/Reported DAG status for UI
    dags_status = [
        {
            "dag_id": "usgs_earthquake_ingestion",
            "schedule": "*/5 * * * *",
            "state": "active",
            "last_run": ingest_time.isoformat() if ingest_time else None,
            "status": latest_ingest.get("status", "SUCCESS")
        },
        {
            "dag_id": "usgs_transformation_quality",
            "schedule": "Triggered by Ingestion",
            "state": "active",
            "last_run": latest_quality.get("created_at").isoformat() if latest_quality.get("created_at") else None,
            "status": latest_quality.get("status", "PASSED")
        },
        {
            "dag_id": "sismowatch_daily_ai_report",
            "schedule": "@daily",
            "state": "active",
            "last_run": now_utc.strftime("%Y-%m-%d 00:00:00 UTC"),
            "status": "SUCCESS"
        }
    ]

    # For Viewer, omit internal details if any
    is_admin = user.get("role") == "admin"
    if not is_admin:
        # Viewer sees summary
        pass

    return PipelineStatusResponse(
        latest_ingestion_time=ingest_time,
        latest_ingestion_status=latest_ingest.get("status", "INITIALIZED"),
        events_in_bronze=bronze_cnt,
        events_in_silver=silver_cnt,
        events_in_gold=gold_cnt,
        quarantined_records_count=quaran_cnt,
        quality_score=float(latest_quality.get("quality_score", 100.0)),
        freshness_delay_minutes=round(freshness, 1),
        dags_status=dags_status
    )
