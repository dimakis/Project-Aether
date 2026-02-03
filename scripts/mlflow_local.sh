#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ARTIFACT_ROOT="${MLFLOW_ARTIFACT_ROOT:-$ROOT_DIR/mlruns}"
BACKEND_URI="${MLFLOW_BACKEND_STORE_URI:-postgresql://aether:aether@localhost:5432/aether}"
HOST="${MLFLOW_HOST:-0.0.0.0}"
PORT="${MLFLOW_PORT:-5000}"

mkdir -p "$ARTIFACT_ROOT"

exec uv run mlflow server \
  --host "$HOST" \
  --port "$PORT" \
  --backend-store-uri "$BACKEND_URI" \
  --default-artifact-root "$ARTIFACT_ROOT"
