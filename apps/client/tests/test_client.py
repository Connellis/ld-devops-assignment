import os

# Point the poll loop at an address that will simply fail fast, and set the
# interval very high so the background task doesn't spam retries during the
# test run.
os.environ.setdefault("SHARED_SECRET", "test-secret")
os.environ.setdefault("TARGET_URL", "http://127.0.0.1:9/work")
os.environ.setdefault("POLL_INTERVAL_SECONDS", "3600")

from app.main import app
from fastapi.testclient import TestClient


def test_healthz():
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
