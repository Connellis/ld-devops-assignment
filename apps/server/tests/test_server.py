import os

# Must be set before `app.main` is imported, since SHARED_SECRET is read at
# module import time.
os.environ["SHARED_SECRET"] = "test-secret"

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_work_rejects_missing_api_key():
    response = client.get("/work")
    assert response.status_code == 401


def test_work_rejects_wrong_api_key():
    response = client.get("/work", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_work_accepts_correct_api_key():
    response = client.get("/work", headers={"X-API-Key": "test-secret"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "request_id" in body


def test_work_echoes_request_id():
    response = client.get(
        "/work",
        headers={"X-API-Key": "test-secret", "X-Request-ID": "abc-123"},
    )
    assert response.json()["request_id"] == "abc-123"


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "app2_requests_total" in response.text
