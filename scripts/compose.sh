#!/usr/bin/env bash
# docker compose wrapper: forward this machine's pip index into the image build.
# Hub/Postgres pulls already use the daemon registry-mirrors; do not hardcode
# a country-specific registry in the repo.
set -euo pipefail
cd "$(dirname "$0")/.."

pip_get() {
  local key="$1"
  python3 -m pip config get "$key" 2>/dev/null \
    || pip3 config get "$key" 2>/dev/null \
    || pip config get "$key" 2>/dev/null \
    || true
}

trim() {
  printf '%s' "$1" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

if [ -z "${PIP_INDEX_URL:-}" ]; then
  detected="$(trim "$(pip_get global.index-url)")"
  if [ -n "$detected" ]; then
    export PIP_INDEX_URL="$detected"
  fi
fi
if [ -z "${PIP_EXTRA_INDEX_URL:-}" ]; then
  detected="$(trim "$(pip_get global.extra-index-url)")"
  if [ -n "$detected" ]; then
    export PIP_EXTRA_INDEX_URL="$detected"
  fi
fi
if [ -z "${PIP_TRUSTED_HOST:-}" ]; then
  detected="$(trim "$(pip_get global.trusted-host)")"
  if [ -n "$detected" ]; then
    export PIP_TRUSTED_HOST="$detected"
  fi
fi

if [ -n "${PIP_INDEX_URL:-}" ]; then
  echo "==> docker build pip index: ${PIP_INDEX_URL}"
else
  echo "==> docker build pip index: official PyPI (no host pip index-url)"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found in PATH" >&2
  exit 127
fi

exec docker compose "$@"
