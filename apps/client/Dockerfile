# syntax=docker/dockerfile:1

# Builder must match the Python version baked into the distroless runtime
# (Debian 12 ships 3.11). Compiled deps like pydantic-core are version-specific
# wheels, and we don't copy a venv across stages.
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --no-cache-dir --target=/dependencies -r requirements.txt

COPY app ./app

FROM gcr.io/distroless/python3-debian12:nonroot AS runtime

WORKDIR /app

COPY --from=builder /dependencies /dependencies
COPY --from=builder /build/app ./app

ENV PYTHONPATH=/dependencies \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]