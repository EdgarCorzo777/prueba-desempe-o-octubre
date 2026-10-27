import json
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from psycopg2.extras import Json
from airflow.include.quality.rules import validate_earthquake_feature, calculate_severity
from airflow.include.config import settings
from airflow.include.db import get_db_cursor

logger = logging.getLogger("sismowatch.quality")

def evaluate_batch_quality(
    raw_features: List[Dict[str, Any]],
    execution_id: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Evaluates quality rules on a batch of raw earthquake features.
    Separates valid records from quarantined records.
    Returns:
      - valid_records: list of cleaned records ready for Silver/Gold
      - quarantined_records: list of invalid records with failure details
      - quality_metrics: summary metrics dictionary
    """
    valid_records = []
    quarantined_records = []
    
    total_rules_evaluated = 0
    total_rules_passed = 0
    total_rules_failed = 0

    latest_event_time = None

    for feature in raw_features:
        is_valid, passed, failed = validate_earthquake_feature(feature)
        total_rules_evaluated += (len(passed) + len(failed))
        total_rules_passed += len(passed)
        total_rules_failed += len(failed)

        if is_valid:
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [0, 0, 0])
            
            event_epoch_ms = props.get("time")
            updated_epoch_ms = props.get("updated") or event_epoch_ms
            
            event_dt = datetime.fromtimestamp(event_epoch_ms / 1000.0, tz=timezone.utc)
            updated_dt = datetime.fromtimestamp(updated_epoch_ms / 1000.0, tz=timezone.utc)
            
            if latest_event_time is None or event_dt > latest_event_time:
                latest_event_time = event_dt
                
            mag = float(props.get("mag", 0.0))
            
            record = {
                "event_id": feature.get("id"),
                "magnitude": mag,
                "mag_type": props.get("magType"),
                "place": props.get("place") or "Unknown location",
                "event_time": event_dt,
                "updated_time": updated_dt,
                "tsunami": bool(props.get("tsunami") == 1 or props.get("tsunami") is True),
                "tsunami_int": 1 if props.get("tsunami") in (1, True) else 0,
                "sig": props.get("sig"),
                "status": props.get("status"),
                "event_type": props.get("type", "earthquake"),
                "longitude": float(coords[0]),
                "latitude": float(coords[1]),
                "depth_km": float(coords[2]),
                "severity_level": calculate_severity(mag),
                "url": props.get("url"),
                "source_execution_id": execution_id
            }
            valid_records.append(record)
        else:
            reason = f"Failed validation rules: {', '.join(failed)}"
            quarantine_item = {
                "raw_event_id": feature.get("id"),
                "execution_id": execution_id,
                "raw_payload": feature,
                "rejection_reason": reason,
                "failed_rules": failed
            }
            quarantined_records.append(quarantine_item)

    # Calculate Quality Score
    quality_score = 100.0
    if total_rules_evaluated > 0:
        quality_score = round((total_rules_passed / total_rules_evaluated) * 100.0, 2)

    # Check Data Freshness Delay
    freshness_delay_minutes = 0.0
    if latest_event_time is not None:
        now_utc = datetime.now(timezone.utc)
        freshness_delay_minutes = max(0.0, (now_utc - latest_event_time).total_seconds() / 60.0)

    # Determine Status (Blocking Rule: If score is 0 and records were present, or critical schema failure)
    status = "PASSED"
    if len(raw_features) > 0 and len(valid_records) == 0:
        status = "BLOCKED"

    metrics = {
        "execution_id": execution_id,
        "rules_evaluated": total_rules_evaluated,
        "rules_passed": total_rules_passed,
        "rules_failed": total_rules_failed,
        "quality_score": quality_score,
        "total_records_processed": len(raw_features),
        "valid_records_count": len(valid_records),
        "quarantined_records_count": len(quarantined_records),
        "freshness_delay_minutes": round(freshness_delay_minutes, 2),
        "status": status,
        "details": {
            "freshness_ok": freshness_delay_minutes <= settings.DATA_FRESHNESS_THRESHOLD_MINUTES,
            "quarantined_reasons": [q["rejection_reason"] for q in quarantined_records[:10]]
        }
    }

    return valid_records, quarantined_records, metrics

def persist_quarantine_records(quarantined_records: List[Dict[str, Any]]) -> int:
    """
    Persists invalid records to staging.quarantine_events using 'transform' role.
    """
    if not quarantined_records:
        return 0

    query = """
    INSERT INTO staging.quarantine_events (
        raw_event_id, execution_id, raw_payload, rejection_reason, failed_rules, quarantined_at
    )
    VALUES (%s, %s, %s, %s, %s, NOW());
    """
    count = 0
    with get_db_cursor(role="transform", commit=True) as cur:
        for q in quarantined_records:
            cur.execute(
                query,
                (
                    q["raw_event_id"],
                    q["execution_id"],
                    Json(q["raw_payload"]),
                    q["rejection_reason"],
                    Json(q["failed_rules"])
                )
            )
            count += 1
            
    logger.warning(f"Quarantined {count} records in staging.quarantine_events")
    return count

def persist_quality_metrics(metrics: Dict[str, Any]) -> int:
    """
    Persists batch quality score and evaluation summary into curated.quality_metrics.
    Uses 'transform' role.
    """
    query = """
    INSERT INTO curated.quality_metrics (
        execution_id, rules_evaluated, rules_passed, rules_failed,
        quality_score, total_records_processed, valid_records_count,
        quarantined_records_count, freshness_delay_minutes, status, details, created_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    RETURNING metric_id;
    """
    with get_db_cursor(role="transform", commit=True) as cur:
        cur.execute(
            query,
            (
                metrics["execution_id"],
                metrics["rules_evaluated"],
                metrics["rules_passed"],
                metrics["rules_failed"],
                metrics["quality_score"],
                metrics["total_records_processed"],
                metrics["valid_records_count"],
                metrics["quarantined_records_count"],
                metrics["freshness_delay_minutes"],
                metrics["status"],
                Json(metrics["details"])
            )
        )
        res = cur.fetchone()
        return res["metric_id"] if res else 0
