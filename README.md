# ApexAI — AI sim-racing coach (F1 telemetry)

Monorepo for an AI driving coach for sim racing. MVP scope: **F1 24/25 over UDP**, a
desktop capture client, a FastAPI backend, and a Next.js web cabinet. Market: CIS,
interface language Russian.

> Working name **ApexAI** — temporary, easy to rename.

## Layout

| Path        | Stack                                   | Status |
|-------------|-----------------------------------------|--------|
| `backend/`  | Python 3.12 · FastAPI · PostgreSQL · S3 | Slice 1 ✅ |
| `web/`      | Next.js 16 · TypeScript · Tailwind · uPlot | Slice 1 ✅ |
| `client/`   | C# / .NET 8 desktop capture (F1 UDP)    | Slice 2 (planned) |
| `infra/`    | docker-compose (Postgres, MinIO, Redis) | ✅ |

## Build order (vertical slices)

0. **Scaffold** — infra + backend/web boot. ✅
1. **Auth + lap ingestion + telemetry chart** — register, upload a lap, view its graphs. ✅ (current)
2. Desktop client: real F1 UDP capture → upload.
3. Layer-1 metrics (corner segmentation, deltas) + lap comparison.
4. AI coach (layer 2, paid) + billing + plan limits.
5. Dashboard + polish.

## Quick start (Slice 1)

Prerequisites: Docker Desktop, Node 18+ (for the web app).

### 1. Backend + infrastructure

```bash
docker compose -f infra/docker-compose.yml up --build
# API:            http://localhost:8000
# OpenAPI docs:   http://localhost:8000/docs
# MinIO console:  http://localhost:9001  (apexai / apexai-secret)
```

The API container applies database migrations on start. Seed a demo account with
synthetic F1 laps so the cabinet has data:

```bash
docker compose -f infra/docker-compose.yml run --rm backend python -m app.cli seed
# -> demo@apexai.dev / demo12345  (3 synthetic laps)
```

### 2. Web cabinet

```bash
cd web
cp .env.example .env.local        # points at http://localhost:8000
npm install
npm run dev                        # http://localhost:3000
```

Log in as `demo@apexai.dev` / `demo12345` and open a lap to see the telemetry charts.

## Tests

Backend tests run on in-memory SQLite — no services required:

```bash
docker compose -f infra/docker-compose.yml run --rm backend pytest -q
# or locally (Python 3.12): cd backend && pip install -r requirements-dev.txt && pytest -q
```

See `backend/README.md` and `web/README.md` for module-level details.
