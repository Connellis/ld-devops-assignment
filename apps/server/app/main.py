"""App2 - the server.

Exposes exactly one business endpoint (/work), logs every incoming request,
and returns HTTP 200 - as specified in the assignment. Also exposes /healthz
(for Kubernetes liveness/readiness probes) and a minimal hand-rolled /metrics
endpoint (no prometheus_client dependency - kept intentionally small; a real
production version would use prometheus_client or OpenTelemetry instead).
"""

from __future__ import annotations

import os
import time
import uuid

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.logging_config import configure_logging

SERVICE_NAME = "app2-server"
SHARED_SECRET = os.environ.get("SHARED_SECRET")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

logger = configure_logging(SERVICE_NAME, LOG_LEVEL)

app = FastAPI(title="App2 Server")

# Counter for the /metrics endpoint. Resets on restart;
# a real deployment would use a proper metrics
# library that survives scrapes correctly across multiple replicas.
_request_count = 0


@app.get("/healthz")
async def healthz() -> dict:
    """Liveness/readiness target. Intentionally requires no auth - the
    kubelet, not a human or another service, calls this."""
    return {"status": "ok"}


@app.get("/work")
async def work(
    request: Request,
    x_request_id: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> JSONResponse:
    global _request_count

    start = time.perf_counter()
    request_id = x_request_id or str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"

    if not SHARED_SECRET:
        # An unconfigured secret must never be treated as "auth disabled".
        logger.error(
            "SHARED_SECRET is not configured on the server",
            extra={"request_id": request_id},
        )
        raise HTTPException(status_code=500, detail="server misconfigured")

    if x_api_key != SHARED_SECRET:
        logger.warning(
            "Rejected request with invalid or missing API key",
            extra={
                "request_id": request_id,
                "http_status_code": 401,
                "client_ip": client_ip,
                "path": str(request.url.path),
            },
        )
        raise HTTPException(status_code=401, detail="invalid API key")

    _request_count += 1
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "Handled incoming request",
        extra={
            "request_id": request_id,
            "http_status_code": 200,
            "client_ip": client_ip,
            "latency_ms": latency_ms,
            "path": str(request.url.path),
        },
    )
    return JSONResponse(status_code=200, content={"status": "ok", "request_id": request_id})


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    body = (
        "# HELP app2_requests_total Total number of successfully authenticated requests\n"
        "# TYPE app2_requests_total counter\n"
        f"app2_requests_total {_request_count}\n"
    )
    return PlainTextResponse(body)
