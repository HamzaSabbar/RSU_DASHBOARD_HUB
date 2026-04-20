# RSU Dashboard Hub

Authenticated web workspace hosting analytical boards. The first board, **Macro National**, reproduces the RSU weekly tracking dashboard: KPI cards, line/bar/stacked-bar charts, and ranking tables. Data is uploaded by admins as Excel/CSV, parsed server-side, and rendered from a persisted snapshot.

## Stack

- **Web**: Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui + Recharts
- **API**: FastAPI + Pandas + SQLAlchemy 2 + Alembic + Pydantic v2
- **DB**: PostgreSQL 16
- **Auth**: NextAuth v5 (Credentials) with a shared-secret JWT verified by the API
- **Infra**: Docker Compose (3 services: `db`, `api`, `web`)

## Running locally

```bash
cp .env.example .env
# edit .env: set NEXTAUTH_SECRET (openssl rand -base64 32), ADMIN_EMAIL, ADMIN_PASSWORD
docker compose up --build
```

Then open:

- Web: http://localhost:3000
- API: http://localhost:8000/health (sanity check)
- API docs: http://localhost:8000/docs

To reset the database and uploaded files:

```bash
docker compose down -v   # drops the dbdata volume
rm -rf data/uploads/*    # drops uploaded files
```

Dev mode (hot reload) is active automatically because `docker-compose.override.yml` is picked up by `docker compose up`. The override bind-mounts `apps/api` and `apps/web` and runs `uvicorn --reload` / `next dev`. To start without hot reload (prod-like image):

```bash
docker compose -f docker-compose.yml up --build
```

## Status

Step 1 complete: monorepo scaffolded, three-service compose, Dockerfiles, Next.js and FastAPI boot to placeholder pages. Auth, board registry, analytics, and the Macro National dashboard are the following steps. See `/Users/omar/.claude/plans/build-prompt-rsu-indexed-matsumoto.md` for the full plan.
