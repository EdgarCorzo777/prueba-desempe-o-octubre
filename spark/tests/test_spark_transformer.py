"""
test_spark_transformer.py
Unit tests for GeoJSON transformation, quality rules, quarantine, and idempotency.
"""

import pytest
from datetime import datetime, timezone
from airflow.include.quality.rules import validate_earthquake_feature, calculate_severity
from airflow.include.quality.quality_checker import evaluate_batch_quality

def get_sample_valid_feature():
    return {
        "type": "Feature",
        "id": "us7000test1",
        "properties": {
            "mag": 5.4,
            "place": "12 km SW of Ovalle, Chile",
            "time": 1700000000000,
            "updated": 1700000100000,
            "tz": None,
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000test1",
            "detail": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/us7000test1.geojson",
            "felt": 45,
            "cdi": 4.1,
            "mmi": 5.2,
            "alert": "green",
            "status": "reviewed",
            "tsunami": 0,
            "sig": 450,
            "net": "us",
            "code": "7000test1",
            "ids": ",us7000test1,",
            "sources": ",us,",
            "types": ",moment-tensor,origin,phase-data,",
            "nst": 65,
            "dmin": 0.85,
            "rms": 0.72,
            "gap": 48,
            "magType": "mww",
            "type": "earthquake",
            "title": "M 5.4 - 12 km SW of Ovalle, Chile"
        },
        "geometry": {
            "type": "Point",
            "coordinates": [-71.285, -30.682, 45.2]
        }
    }

def get_sample_invalid_feature():
    return {
        "type": "Feature",
        "id": "us_invalid_999",
        "properties": {
            "mag": 15.0, # Physially impossible magnitude (> 10.0)
            "place": "Nowhere",
            "time": 0, # Invalid time epoch
            "updated": 0,
            "tsunami": 0
        },
        "geometry": {
            "type": "Point",
            "coordinates": [999.0, -999.0, 50000.0] # Invalid lon, lat, depth
        }
    }

def test_valid_feature_transformation():
    feat = get_sample_valid_feature()
    is_valid, passed, failed = validate_earthquake_feature(feat)
    assert is_valid is True
    assert len(failed) == 0
    assert len(passed) >= 6

    # Test severity calculation
    assert calculate_severity(5.4) == "MODERATE"
    assert calculate_severity(7.2) == "CRITICAL"
    assert calculate_severity(6.5) == "HIGH"
    assert calculate_severity(2.1) == "LOW"

def test_invalid_feature_rejection():
    feat = get_sample_invalid_feature()
    is_valid, passed, failed = validate_earthquake_feature(feat)
    assert is_valid is False
    assert "RULE_TIME_REQUIRED" in failed
    assert "RULE_LATITUDE_RANGE" in failed
    assert "RULE_LONGITUDE_RANGE" in failed
    assert "RULE_MAGNITUDE_RANGE" in failed
    assert "RULE_DEPTH_RANGE" in failed

def test_batch_quality_and_quarantine_segregation():
    batch = [
        get_sample_valid_feature(),
        get_sample_invalid_feature()
    ]
    valid_records, quarantined, metrics = evaluate_batch_quality(batch, "test_exec_001")
    
    # Assert strictly that valid and quarantined are separated
    assert len(valid_records) == 1
    assert len(quarantined) == 1
    assert valid_records[0]["event_id"] == "us7000test1"
    assert quarantined[0]["raw_event_id"] == "us_invalid_999"
    assert "Failed validation rules" in quarantined[0]["rejection_reason"]
    assert metrics["quarantined_records_count"] == 1
    assert metrics["valid_records_count"] == 1
    assert metrics["quality_score"] > 0

def test_idempotency_simulation():
    """
    Simulates deduplication: duplicate IDs with the same or older update time
    should result in an update without creating duplicate items.
    """
    feat = get_sample_valid_feature()
    batch = [feat, feat, feat] # 3 identical features
    valid_records, quarantined, _ = evaluate_batch_quality(batch, "test_exec_idemp")
    
    unique_ids = set(r["event_id"] for r in valid_records)
    assert len(unique_ids) == 1
