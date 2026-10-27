from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
from api.app.schemas.api_models import PaginatedEventsResponse, EventItem
from api.app.auth.dependencies import require_role
from api.app.database import db_cursor

router = APIRouter(prefix="/api/events", tags=["Events"])

@router.get("", response_model=PaginatedEventsResponse)
def get_events(
    user: dict = Depends(require_role("viewer")),
    min_magnitude: Optional[float] = Query(None, description="Filtro de magnitud mínima"),
    max_magnitude: Optional[float] = Query(None, description="Filtro de magnitud máxima"),
    region: Optional[str] = Query(None, description="Filtro por nombre de región o lugar"),
    tsunami_only: Optional[bool] = Query(False, description="Solo eventos con alerta de tsunami"),
    event_category: Optional[str] = Query(None, description="'all', 'sismo' o 'tsunami'"),
    start_date: Optional[str] = Query(None, description="Fecha inicial YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Fecha final YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=500)
):
    """
    Returns filterable, paginated reliable seismic events from Gold (curated.events).
    """
    conditions = []
    params = []

    if min_magnitude is not None:
        conditions.append("magnitude >= %s")
        params.append(min_magnitude)

    if max_magnitude is not None:
        conditions.append("magnitude <= %s")
        params.append(max_magnitude)

    if region and region.strip():
        conditions.append("place ILIKE %s")
        params.append(f"%{region.strip()}%")

    if event_category == 'tsunami' or tsunami_only:
        conditions.append("tsunami = TRUE")
    elif event_category == 'sismo':
        conditions.append("tsunami = FALSE")

    if start_date:
        conditions.append("event_time >= %s")
        params.append(f"{start_date} 00:00:00+00")

    if end_date:
        conditions.append("event_time <= %s")
        params.append(f"{end_date} 23:59:59+00")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    count_query = f"SELECT COUNT(*)::int as total FROM curated.events {where_clause};"  # nosec B608
    
    offset = (page - 1) * page_size
    data_query = f"""
    SELECT 
        event_id, magnitude, mag_type, place, event_time, updated_time,
        tsunami, sig, status, event_type, longitude, latitude, depth_km,
        severity_level, url
    FROM curated.events
    {where_clause}
    ORDER BY event_time DESC
    LIMIT %s OFFSET %s;
    """  # nosec B608
    data_params = list(params) + [page_size, offset]

    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute(count_query, tuple(params))
        total = cur.fetchone()["total"]

        cur.execute(data_query, tuple(data_params))
        rows = cur.fetchall() or []

    events = [
        EventItem(
            event_id=r["event_id"],
            magnitude=r["magnitude"],
            mag_type=r["mag_type"],
            place=r["place"],
            event_time=r["event_time"],
            updated_time=r["updated_time"],
            tsunami=r["tsunami"],
            sig=r["sig"],
            status=r["status"],
            event_type=r["event_type"],
            longitude=r["longitude"],
            latitude=r["latitude"],
            depth_km=r["depth_km"],
            severity_level=r["severity_level"],
            url=r["url"]
        )
        for r in rows
    ]

    return PaginatedEventsResponse(
        total=total,
        page=page,
        page_size=page_size,
        events=events
    )
