# syntax=docker/dockerfile:1

# Builder must match the Python version baked into the distroless runtime
# (Debian 12 ships 3.11). Compiled deps like pydantic-core are version-specific
# wheels, and we don't copy a venv across stages.
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

COPY requirements.txt .

# Install to a plain dir, not a venv: venv symlinks point back at the builder's
# Python path, which doesn't exist in the distroless runtime image.
RUN pip install --no-cache-dir --target=/dependencies -r requirements.txt

COPY app ./app

# Distroless: no shell, no package manager. Runs as non-root already. We use
# the Python interpreter that ships inside it and point PYTHONPATH at our deps.
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime

WORKDIR /app

COPY --from=builder /dependencies /dependencies
COPY --from=builder /build/app ./app

ENV PYTHONPATH=/dependencies \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]