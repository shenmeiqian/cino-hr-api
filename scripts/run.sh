#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export API_KEY="${API_KEY:-demo-key}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///./cino_hr.db}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
