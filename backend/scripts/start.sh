#!/usr/bin/env bash
# Production-ish container entrypoint: apply migrations, then serve.
set -euo pipefail

echo "Applying database migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
