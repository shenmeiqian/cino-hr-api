# Production-ish image for local / demo use.
# Multi-stage: install deps in a venv, run as non-root.
#
# Base images use official names (python:3.12-slim) so THIS MACHINE's
# Docker daemon registry-mirrors apply. Do not prefix a country-specific
# registry — that changes when you change country.
#
# pip: optional PIP_INDEX_URL / PIP_EXTRA_INDEX_URL / PIP_TRUSTED_HOST
# build-args (empty = official PyPI). scripts/compose.sh forwards this
# machine's pip.conf into those args.

FROM python:3.12-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
ARG PIP_INDEX_URL=""
ARG PIP_EXTRA_INDEX_URL=""
ARG PIP_TRUSTED_HOST=""
RUN set -- \
    && if [ -n "$PIP_INDEX_URL" ]; then set -- "$@" --index-url "$PIP_INDEX_URL"; fi \
    && if [ -n "$PIP_EXTRA_INDEX_URL" ]; then set -- "$@" --extra-index-url "$PIP_EXTRA_INDEX_URL"; fi \
    && if [ -n "$PIP_TRUSTED_HOST" ]; then \
         for host in $PIP_TRUSTED_HOST; do \
           set -- "$@" --trusted-host "$host"; \
         done; \
       fi \
    && pip install --no-cache-dir --upgrade pip "$@" \
    && pip install --no-cache-dir "$@" -r requirements.txt

FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_KEY=demo-key \
    DATABASE_URL=sqlite:////data/cino_hr.db \
    FILE_LOCAL_DIR=/data/files

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
    && mkdir -p /app /data/files \
    && chown -R appuser:appuser /app /data

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser docker/entrypoint.sh /entrypoint.sh
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser requirements.txt ./

RUN chmod 755 /entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

ENTRYPOINT ["/entrypoint.sh"]
