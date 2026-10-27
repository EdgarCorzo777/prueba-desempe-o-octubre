import pytest
import sys
import os
from fastapi.testclient import TestClient

# Ensure project root in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.app.main import app
from api.app.auth.jwt_handler import create_access_token

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def admin_headers():
    token = create_access_token({"sub": "admin@sismowatch.internal", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def viewer_headers():
    token = create_access_token({"sub": "viewer@sismowatch.internal", "role": "viewer"})
    return {"Authorization": f"Bearer {token}"}
