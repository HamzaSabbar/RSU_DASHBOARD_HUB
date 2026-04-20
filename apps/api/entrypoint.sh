#!/bin/sh
set -e

if [ -f alembic.ini ] && [ -d alembic/versions ] && [ "$(ls -A alembic/versions 2>/dev/null)" ]; then
  echo "[entrypoint] Running alembic upgrade head..."
  alembic upgrade head
else
  echo "[entrypoint] No migrations found, skipping alembic upgrade."
fi

echo "[entrypoint] Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 ${UVICORN_EXTRA:-}
