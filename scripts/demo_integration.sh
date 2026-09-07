#!/usr/bin/env bash
# 联调小脚本：健康检查 + 开权前培训闸门（需本服务已启动且已 seed）。
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"
KEY="${API_KEY:-demo-key}"

echo "== GET /health =="
curl -sS "$BASE/health"
echo

echo "== POST /api/v1/integration/validate-training-before-grant (无培训媒体联络人) =="
curl -sS -X POST "$BASE/api/v1/integration/validate-training-before-grant" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"system_account_id":"sys3-media-1001","scopes":["wipe","outbound"]}'
echo

echo "== POST /api/v1/integration/validate-training-before-grant (已培训) =="
curl -sS -X POST "$BASE/api/v1/integration/validate-training-before-grant" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"system_account_id":"sys3-media-1002","scopes":["wipe","outbound"]}'
echo

echo "== GET /api/v1/integration/sync/status =="
curl -sS "$BASE/api/v1/integration/sync/status" -H "X-API-Key: $KEY"
echo
