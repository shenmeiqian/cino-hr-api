#!/usr/bin/env bash
set -euo pipefail

cd /app

mkdir -p "${DATA_DIR:-/data}" "${FILE_LOCAL_DIR:-/data/files}" || true

wait_for_postgres() {
  case "${DATABASE_URL:-}" in
    postgresql*|postgres*) ;;
    *) return 0 ;;
  esac

  echo "==> Waiting for PostgreSQL..."
  python - <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
last = None
for attempt in range(1, 41):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("PostgreSQL is ready")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        last = exc
        print(f"  attempt {attempt}/40: {exc}")
        time.sleep(1.5)
print(f"PostgreSQL did not become ready: {last}", file=sys.stderr)
sys.exit(1)
PY
}

wait_for_postgres

echo "==> Creating tables and seeding demo data if empty..."
python -m app.seed

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
