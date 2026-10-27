import pytest
from api.app.auth.jwt_handler import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hashing():
    raw_pass = "SecurePass123!*"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_flow():
    payload = {"sub": "test@sismowatch.internal", "role": "viewer"}
    token = create_access_token(payload)
    assert isinstance(token, str)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "test@sismowatch.internal"
    assert decoded["role"] == "viewer"

def test_unauthenticated_request_rejected(client):
    """
    Verifies that unauthenticated requests to protected endpoints return 401 Unauthorized.
    """
    endpoints = [
        "/api/kpis",
        "/api/events",
        "/api/stats/timeseries",
        "/api/reports",
        "/api/pipeline/status",
        "/api/quality/quarantine",
        "/api/anomalies"
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 401, f"Expected 401 on {ep}, got {resp.status_code}"
