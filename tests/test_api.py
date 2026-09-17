import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings  # noqa: E402
from backend.main import app  # noqa: E402


client = TestClient(app)


def test_health_endpoint_reports_static_mode_without_key():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_review_endpoint_returns_report():
    response = client.post(
        "/api/review",
        json={"code": "x = eval(user_input)\n", "filename": "sample.py"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "sample.py"
    assert body["issues"][0]["confidence"]


def test_review_endpoint_requires_configured_api_key():
    original = settings.API_AUTH_TOKEN
    settings.API_AUTH_TOKEN = "test-token"
    try:
        unauthorized = client.post("/api/review", json={"code": "x = 1", "filename": "a.py"})
        authorized = client.post(
            "/api/review",
            headers={"X-API-Key": "test-token"},
            json={"code": "x = 1", "filename": "a.py"},
        )
        assert unauthorized.status_code == 401
        assert authorized.status_code == 200
    finally:
        settings.API_AUTH_TOKEN = original