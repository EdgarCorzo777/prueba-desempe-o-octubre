import pytest
from unittest.mock import patch

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"

def test_viewer_forbidden_on_admin_endpoints(client, viewer_headers):
    """
    CRITICAL ACCEPTANCE CRITERIA:
    A viewer role MUST receive HTTP 403 Forbidden on all admin endpoints.
    """
    # 1. Quarantine access
    res = client.get("/api/quality/quarantine", headers=viewer_headers)
    assert res.status_code == 403, f"Viewer must get 403 on quarantine, got {res.status_code}"

    # 2. Backfill trigger
    res = client.post("/api/admin/backfill", json={"days": 7, "min_magnitude": 3.0}, headers=viewer_headers)
    assert res.status_code == 403, f"Viewer must get 403 on backfill, got {res.status_code}"

    # 3. Report regenerate
    res = client.post("/api/admin/reports/regenerate", headers=viewer_headers)
    assert res.status_code == 403, f"Viewer must get 403 on report regenerate, got {res.status_code}"

def test_chat_ai_fallback_on_ollama_failure(client, viewer_headers):
    """
    Verifies that when Ollama is offline or times out, the chat endpoint generates
    a robust deterministic analytical answer without throwing a 500 error.
    """
    with patch("api.app.services.chat_service.generate_chat_completion") as mock_gen:
        mock_gen.return_value = {
            "content": "",
            "model": "llama3.2:1b",
            "latency_ms": 100.0,
            "tokens": 0,
            "status": "ERROR",
            "error": "Connection refused"
        }
        res = client.post(
            "/api/chat",
            json={"question": "¿Cuántos sismos se registraron en las últimas 24 horas?"},
            headers=viewer_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_fallback"] is True
        assert "sismos" in data["answer"].lower()
