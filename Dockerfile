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
RUN chmod +x /app/entrypoint.sh && chown -R app:app /app

USER app
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]

# -----------------------------------------------------------------------
FROM node:20-alpine AS web-builder
WORKDIR /app
RUN apk add --no-cache libc6-compat
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY apps/web ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# -----------------------------------------------------------------------
FROM node:20-alpine AS web-runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

COPY --from=web-builder /app/public ./public
COPY --from=web-builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=web-builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
