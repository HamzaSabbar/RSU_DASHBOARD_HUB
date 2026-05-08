FROM python:3.11-slim AS api-builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

COPY apps/api /app
ENV PATH="/opt/venv/bin:$PATH"
RUN chmod +x /app/entrypoint.sh

# -----------------------------------------------------------------------
FROM python:3.11-slim AS api-runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --create-home --uid 1001 app

WORKDIR /app
COPY --from=api-builder /opt/venv /opt/venv
COPY --from=api-builder /app /app
RUN mkdir -p /data/uploads /data/storage \
 && chmod +x /app/entrypoint.sh \
 && chown -R app:app /app /data

USER app
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]

# -----------------------------------------------------------------------
FROM mcr.microsoft.com/playwright:v1.59.1-noble AS web-builder
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY apps/web ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# -----------------------------------------------------------------------
FROM mcr.microsoft.com/playwright:v1.59.1-noble AS web-runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=3000 \
    HOSTNAME=0.0.0.0

COPY --from=web-builder /app/public ./public
COPY --from=web-builder --chown=pwuser:pwuser /app/.next/standalone ./
COPY --from=web-builder --chown=pwuser:pwuser /app/.next/static ./.next/static

USER pwuser
EXPOSE 3000
CMD ["node", "server.js"]
