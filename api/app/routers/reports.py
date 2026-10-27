from fastapi import APIRouter, Depends, Query, HTTPException, Response
from typing import List, Optional
from api.app.schemas.api_models import ReportItem
from api.app.auth.dependencies import require_role
from api.app.database import db_cursor
from api.app.services.report_exporter import export_events_to_csv, export_report_to_html

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("", response_model=List[ReportItem])
def list_daily_reports(
    user: dict = Depends(require_role("viewer")),
    search: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100)
):
    """
    Returns the history of daily seismic reports.
    """
    query = """
    SELECT 
        report_id, report_date, executive_summary, metrics_json,
        ai_model, generation_status, tokens_used, latency_ms, created_at
    FROM curated.daily_reports
    """
    params = []
    if search and search.strip():
        query += " WHERE executive_summary ILIKE %s OR report_id ILIKE %s"
        params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])
        
    query += " ORDER BY report_date DESC LIMIT %s;"
    params.append(limit)

    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall() or []

    return [
        ReportItem(
            report_id=r["report_id"],
            report_date=r["report_date"],
            executive_summary=r["executive_summary"],
            metrics=r["metrics_json"],
            ai_model=r["ai_model"],
            generation_status=r["generation_status"],
            tokens_used=r["tokens_used"],
            latency_ms=r["latency_ms"],
            created_at=r["created_at"]
        )
        for r in rows
    ]

@router.get("/export")
def export_data(
    user: dict = Depends(require_role("viewer")),
    format: str = Query("csv", pattern="^(csv|html)$"),
    report_id: Optional[str] = Query(None)
):
    """
    Exports data to CSV or HTML printable report.
    """
    if format == "html":
        # Export single report or latest report to HTML
        with db_cursor(as_admin=False, commit=False) as cur:
            if report_id:
                cur.execute(
                    "SELECT report_id, report_date, executive_summary, metrics_json, ai_model, generation_status FROM curated.daily_reports WHERE report_id = %s;",
                    (report_id,)
                )
            else:
                cur.execute(
                    "SELECT report_id, report_date, executive_summary, metrics_json, ai_model, generation_status FROM curated.daily_reports ORDER BY report_date DESC LIMIT 1;"
                )
            report = cur.fetchone()
            
        if not report:
            raise HTTPException(status_code=404, detail="No hay reportes disponibles para exportar.")
            
        html_str = export_report_to_html({
            "report_id": report["report_id"],
            "report_date": str(report["report_date"]),
            "executive_summary": report["executive_summary"],
            "metrics": report["metrics_json"],
            "ai_model": report["ai_model"],
            "generation_status": report["generation_status"]
        })
        return Response(content=html_str, media_type="text/html")

    else: # CSV format for events
        with db_cursor(as_admin=False, commit=False) as cur:
            cur.execute(
                """
                SELECT event_id, magnitude, mag_type, place, event_time, latitude, longitude, depth_km, severity_level, tsunami, url
                FROM curated.events
                ORDER BY event_time DESC
                LIMIT 1000;
                """
            )
            events = cur.fetchall() or []
            
        csv_str = export_events_to_csv(events)
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sismowatch_events_export.csv"}
        )

@router.get("/{report_id}", response_model=ReportItem)
def get_single_report(report_id: str, user: dict = Depends(require_role("viewer"))):
    """
    Returns single report by ID.
    """
    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute(
            """
            SELECT report_id, report_date, executive_summary, metrics_json,
                   ai_model, generation_status, tokens_used, latency_ms, created_at
            FROM curated.daily_reports
            WHERE report_id = %s;
            """,
            (report_id,)
        )
        r = cur.fetchone()

    if not r:
        raise HTTPException(status_code=404, detail="Reporte no encontrado.")

    return ReportItem(
        report_id=r["report_id"],
        report_date=r["report_date"],
        executive_summary=r["executive_summary"],
        metrics=r["metrics_json"],
        ai_model=r["ai_model"],
        generation_status=r["generation_status"],
        tokens_used=r["tokens_used"],
        latency_ms=r["latency_ms"],
        created_at=r["created_at"]
    )
