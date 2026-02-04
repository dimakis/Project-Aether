#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ARTIFACT_ROOT="${MLFLOW_ARTIFACT_ROOT:-$ROOT_DIR/mlruns}"
# Default to local SQLite unless an explicit backend is provided.
BACKEND_URI="${MLFLOW_BACKEND_STORE_URI:-sqlite:///$ROOT_DIR/mlflow.db}"
HOST="${MLFLOW_HOST:-0.0.0.0}"
PORT="${MLFLOW_PORT:-5002}"

mkdir -p "$ARTIFACT_ROOT"

# Ensure backend schema is up to date (idempotent).
case "$BACKEND_URI" in
  sqlite:*|postgresql:*|mysql:*|mssql:*)
    echo "Ensuring MLflow DB schema is up to date for $BACKEND_URI"
    uv run mlflow db upgrade "$BACKEND_URI"
    ;;
  *)
    echo "Skipping MLflow DB upgrade for backend: $BACKEND_URI"
    ;;
esac

exec uv run mlflow server \
  --host "$HOST" \
  --port "$PORT" \
  --backend-store-uri "$BACKEND_URI" \
  --default-artifact-root "$ARTIFACT_ROOT"
