#!/usr/bin/env bash
# Generates .env (gitignored) with a random shared secret.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
  echo ".env already exists at $ENV_FILE - leaving it untouched."
  exit 0
fi

TOKEN="$(openssl rand -hex 32)"
echo "SHARED_SECRET=${TOKEN}" > "$ENV_FILE"
echo "Generated a new SHARED_SECRET and wrote it to $ENV_FILE (gitignored, never commit it)."
