from fastapi import APIRouter, Depends, Query
from typing import List
from datetime import datetime, timezone, timedelta
from api.app.schemas.api_models import TimeSeriesPoint, MagnitudeDistItem, RegionCountItem
from api.app.auth.dependencies import require_role
from api.app.database import db_cursor

router = APIRouter(prefix="/api/stats", tags=["Statistics"])

@router.get("/timeseries", response_model=List[TimeSeriesPoint])
def get_timeseries_stats(
    user: dict = Depends(require_role("viewer")),
    hours: int = Query(720, ge=1, le=1440)
):
    """
    Returns seismic activity aggregated by hour or day for charts (events count and max magnitude).
    """
    since_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # If timeframe is larger than 48 hours, aggregate by day for visual clarity
    trunc_unit = 'day' if hours > 48 else 'hour'
    time_format = 'YYYY-MM-DD' if hours > 48 else 'YYYY-MM-DD HH24:00'
    
    query = f"""
    SELECT
        TO_CHAR(DATE_TRUNC('{trunc_unit}', event_time), '{time_format}') as hour_label,
        COUNT(*)::int as count,
        COALESCE(MAX(magnitude), 0.0)::float as max_mag
    FROM curated.events
    WHERE event_time >= %s
    GROUP BY 1
    ORDER BY hour_label ASC;
    """
    
    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute(query, (since_time,))
        rows = cur.fetchall() or []
        
    return [
        TimeSeriesPoint(
            hour=r["hour_label"],
            count=r["count"],
            max_magnitude=round(r["max_mag"], 2)
        )
        for r in rows
    ]

@router.get("/magnitude-distribution", response_model=List[MagnitudeDistItem])
def get_magnitude_distribution(
    user: dict = Depends(require_role("viewer")),
    hours: int = Query(720, ge=1, le=1440)
):
    """
    Returns earthquake counts categorized by severity level.
    """
    since_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    query = """
    SELECT
        severity_level,
        COUNT(*)::int as count
    FROM curated.events
    WHERE event_time >= %s
    GROUP BY severity_level
    ORDER BY count DESC;
    """
    
    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute(query, (since_time,))
        rows = cur.fetchall() or []
        
    return [
        MagnitudeDistItem(
            severity=r["severity_level"],
            count=r["count"]
        )
        for r in rows
    ]

@router.get("/top-regions", response_model=List[RegionCountItem])
def get_top_regions(
    user: dict = Depends(require_role("viewer")),
    hours: int = Query(720, ge=1, le=1440),
    limit: int = Query(5, ge=1, le=20)
):
    """
    Returns regions with the highest number of recorded seismic events.
    """
    since_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    query = """
    SELECT
        COALESCE(NULLIF(SPLIT_PART(place, ', ', 2), ''), place) as region_name,
        COUNT(*)::int as count,
        COALESCE(MAX(magnitude), 0.0)::float as max_mag
    FROM curated.events
    WHERE event_time >= %s
    GROUP BY 1
    ORDER BY count DESC
    LIMIT %s;
    """
    
    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute(query, (since_time, limit))
        rows = cur.fetchall() or []
        
    return [
        RegionCountItem(
            region=r["region_name"],
            count=r["count"],
            max_magnitude=round(r["max_mag"], 2)
        )
        for r in rows
    ]
