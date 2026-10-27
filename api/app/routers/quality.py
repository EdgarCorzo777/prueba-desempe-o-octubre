from fastapi import APIRouter, Depends, Query
from api.app.schemas.api_models import PaginatedQuarantineResponse, QuarantineItem
from api.app.auth.dependencies import require_role
from api.app.database import db_cursor

router = APIRouter(prefix="/api/quality", tags=["Data Quality & Quarantine"])

@router.get("/quarantine", response_model=PaginatedQuarantineResponse)
def get_quarantined_records(
    user: dict = Depends(require_role("admin")), # STRICTLY ADMIN ONLY
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    Returns quarantined records rejected by data quality rules.
    STRICTLY RESTRICTED TO ADMIN USERS. Returns 403 Forbidden for Viewers.
    """
    offset = (page - 1) * page_size
    
    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute("SELECT COUNT(*)::int as total FROM staging.quarantine_events;")
        total = cur.fetchone()["total"]
        
        cur.execute(
            """
            SELECT quarantine_id, raw_event_id, execution_id, rejection_reason,
                   failed_rules, raw_payload, quarantined_at
            FROM staging.quarantine_events
            ORDER BY quarantined_at DESC
            LIMIT %s OFFSET %s;
            """,
            (page_size, offset)
        )
        rows = cur.fetchall() or []

    records = [
        QuarantineItem(
            quarantine_id=r["quarantine_id"],
            raw_event_id=r["raw_event_id"],
            execution_id=r["execution_id"],
            rejection_reason=r["rejection_reason"],
            failed_rules=r["failed_rules"] if isinstance(r["failed_rules"], list) else [],
            raw_payload=r["raw_payload"],
            quarantined_at=r["quarantined_at"]
        )
        for r in rows
    ]

    return PaginatedQuarantineResponse(
        total=total,
        page=page,
        page_size=page_size,
        records=records
    )

@router.get("/metrics")
def get_quality_metrics(
    user: dict = Depends(require_role("admin")),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Returns latest data quality audit history. Restricted to Admin.
    """
    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute(
            """
            SELECT metric_id, execution_id, rules_evaluated, rules_passed,
                   rules_failed, quality_score, total_records_processed,
                   valid_records_count, quarantined_records_count,
                   freshness_delay_minutes, status, details, created_at
            FROM curated.quality_metrics
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (limit,)
        )
        rows = cur.fetchall() or []
    return {"metrics": rows}

