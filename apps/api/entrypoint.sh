#!/bin/sh
set -e

if [ -f alembic.ini ] && [ -d alembic/versions ] && [ "$(ls -A alembic/versions 2>/dev/null)" ]; then
  echo "[entrypoint] Running alembic upgrade head..."
  attempt=1
  max_attempts="${ALEMBIC_MAX_ATTEMPTS:-30}"
  until alembic upgrade head; do
    if [ "$attempt" -ge "$max_attempts" ]; then
      echo "[entrypoint] Alembic upgrade failed after ${attempt} attempts."
      exit 1
    fi
    attempt=$((attempt + 1))
    echo "[entrypoint] Alembic upgrade failed; retrying (${attempt}/${max_attempts})..."
    sleep 2
  done
else
  echo "[entrypoint] No migrations found, skipping alembic upgrade."
fi

echo "[entrypoint] Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 ${UVICORN_EXTRA:-}
