"""App1 - the client.

Continuously polls App2 in a background loop, logging the target address and
the HTTP response code on every attempt, as specified in the assignment.

Also runs a tiny FastAPI app exposing /healthz - Kubernetes liveness/
readiness probes need *something* to hit inside the pod, and running a real
HTTP server for that (rather than a bespoke TCP check) keeps the client
symmetric with the server's tech stack.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
import uuid

import httpx
from fastapi import FastAPI

from app.logging_config import configure_logging

SERVICE_NAME = "app1-client"
TARGET_URL = os.environ.get(
    "TARGET_URL", "http://app2-server.server.svc.cluster.local:8000/work"
)
SHARED_SECRET = os.environ.get("SHARED_SECRET")
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "5"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

logger = configure_logging(SERVICE_NAME, LOG_LEVEL)

_stop_event = asyncio.Event()


async def poll_loop() -> None:
    if not SHARED_SECRET:
        logger.warning(
            "SHARED_SECRET is not set - requests to the target will be sent "
            "without an X-API-Key header and will be rejected with 401",
            extra={"target_address": TARGET_URL},
        )

    headers = {"X-API-Key": SHARED_SECRET} if SHARED_SECRET else {}

    async with httpx.AsyncClient(timeout=5.0) as http_client:
        while not _stop_event.is_set():
            request_id = str(uuid.uuid4())
            start = time.perf_counter()
            try:
                response = await http_client.get(
                    TARGET_URL,
                    headers={**headers, "X-Request-ID": request_id},
                )
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.info(
                    "Polled target",
                    extra={
                        "target_address": TARGET_URL,
                        "http_status_code": response.status_code,
                        "request_id": request_id,
                        "latency_ms": latency_ms,
                    },
                )
            except httpx.HTTPError as exc:
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.error(
                    "Failed to reach target",
                    extra={
                        "target_address": TARGET_URL,
                        "request_id": request_id,
                        "latency_ms": latency_ms,
                    },
                    exc_info=exc,
                )

            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(_stop_event.wait(), timeout=POLL_INTERVAL_SECONDS)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting poll loop",
        extra={"target_address": TARGET_URL},
    )
    task = asyncio.create_task(poll_loop())
    yield
    _stop_event.set()
    await task


app = FastAPI(title="App1 Client", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
