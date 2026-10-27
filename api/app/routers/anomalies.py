from fastapi import APIRouter, Depends, Query
from typing import List
from api.app.schemas.api_models import AnomalyAlertItem
from api.app.auth.dependencies import require_role
from api.app.database import db_cursor

router = APIRouter(prefix="/api/anomalies", tags=["Anomalies"])

@router.get("", response_model=List[AnomalyAlertItem])
def get_anomaly_alerts(
    user: dict = Depends(require_role("viewer")),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Returns detected statistical seismic anomalies (Z-Score spikes and swarms).
    """
    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute(
            """
            SELECT alert_id, alert_type, region, period_start, period_end,
                   z_score, event_count, avg_magnitude, explanation, created_at
            FROM curated.anomaly_alerts
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (limit,)
        )
        rows = cur.fetchall() or []

    return [
        AnomalyAlertItem(
            alert_id=r["alert_id"],
            alert_type=r["alert_type"],
            region=r["region"],
            period_start=r["period_start"],
            period_end=r["period_end"],
            z_score=r["z_score"],
            event_count=r["event_count"],
            avg_magnitude=r["avg_magnitude"],
            explanation=r["explanation"],
            created_at=r["created_at"]
        )
        for r in rows
    ]
