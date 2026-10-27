from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone, timedelta
from api.app.schemas.api_models import KPIResponse
from api.app.auth.dependencies import require_role
from api.app.database import db_cursor

router = APIRouter(prefix="/api/kpis", tags=["KPIs"])

@router.get("", response_model=KPIResponse)
def get_dashboard_kpis(
    user: dict = Depends(require_role("viewer")),
    hours: int = Query(720, ge=1, le=1440)
):
    """
    Returns core operational KPIs for the SismoWatch dashboard:
    - Total Events in period (default 30 days / 720h)
    - Max Magnitude in period
    - Average Magnitude in period
    - Tsunami Alerts in period
    - Latest Data Quality Score
    - Last Ingestion/Publication Timestamp
    - Data Freshness Delay in minutes
    """
    now_utc = datetime.now(timezone.utc)
    since_dt = now_utc - timedelta(hours=hours)
    
    with db_cursor(as_admin=False, commit=False) as cur:
        # 1. Event stats from curated.events for the requested timeframe
        cur.execute(
            """
            SELECT
                COUNT(*)::int as total_24h,
                COALESCE(MAX(magnitude), 0.0)::float as max_mag_24h,
                COALESCE(AVG(magnitude), 0.0)::float as avg_mag_24h,
                COUNT(*) FILTER (WHERE tsunami = TRUE)::int as tsunami_24h,
                MAX(event_time) as latest_event_time,
                MAX(published_at) as latest_published_time
            FROM curated.events
            WHERE event_time >= %s;
            """,
            (since_dt,)
        )
        stats = cur.fetchone() or {}
        
        # 2. Latest quality score from curated.quality_metrics
        cur.execute(
            """
            SELECT quality_score, freshness_delay_minutes, created_at
            FROM curated.quality_metrics
            ORDER BY created_at DESC
            LIMIT 1;
            """
        )
        quality_row = cur.fetchone() or {}

    latest_time = stats.get("latest_published_time") or stats.get("latest_event_time")
    freshness = 0.0
    if latest_time:
        freshness = max(0.0, (now_utc - latest_time).total_seconds() / 60.0)

    quality_score = float(quality_row.get("quality_score", 100.0))

    return KPIResponse(
        total_events_24h=stats.get("total_24h", 0),
        max_magnitude_24h=round(stats.get("max_mag_24h", 0.0), 2),
        avg_magnitude_24h=round(stats.get("avg_mag_24h", 0.0), 2),
        tsunami_alerts_24h=stats.get("tsunami_24h", 0),
        quality_score=quality_score,
        last_data_update=latest_time,
        freshness_delay_minutes=round(freshness, 1)
    )
