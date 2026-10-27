from fastapi import APIRouter, Depends, HTTPException
from api.app.schemas.api_models import BackfillRequest, BackfillResponse, ReportItem
from api.app.auth.dependencies import require_role
from airflow.include.ingestion.backfill import execute_historical_backfill
from airflow.include.ai.report_generator import generate_daily_executive_report

router = APIRouter(prefix="/api/admin", tags=["Admin Actions"])

@router.post("/backfill", response_model=BackfillResponse)
def trigger_historical_backfill(
    req: BackfillRequest,
    user: dict = Depends(require_role("admin")) # STRICTLY ADMIN ONLY
):
    """
    Executes a historical backfill from the USGS earthquake catalog.
    STRICTLY RESTRICTED TO ADMIN USERS. Returns 403 Forbidden for Viewers.
    """
    try:
        res = execute_historical_backfill(days=req.days, min_magnitude=req.min_magnitude)
        return BackfillResponse(
            message=f"Backfill de {req.days} días completado exitosamente con 0 duplicados.",
            execution_id=res["execution_id"],
            period=res["period"],
            raw_events_fetched=res["raw_events_fetched"],
            valid_promoted_to_gold=res["valid_promoted_to_gold"],
            quarantined=res["quarantined"],
            quality_score=res["quality_score"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante backfill: {str(e)}")

@router.post("/reports/regenerate", response_model=ReportItem)
def regenerate_ai_report(
    user: dict = Depends(require_role("admin")) # STRICTLY ADMIN ONLY
):
    """
    Regenerates the daily AI executive report on-demand.
    STRICTLY RESTRICTED TO ADMIN USERS. Returns 403 Forbidden for Viewers.
    """
    try:
        report = generate_daily_executive_report()
        return ReportItem(
            report_id=report["report_id"],
            report_date=report["date"],
            executive_summary=report["executive_summary"],
            metrics=report["metrics"],
            ai_model=report["model"],
            generation_status=report["generation_status"],
            tokens_used=report["tokens_used"],
            latency_ms=report["latency_ms"],
            created_at=report.get("created_at", report["date"])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al regenerar reporte: {str(e)}")
