# ApexAI backend (Python · FastAPI · PostgreSQL · S3)

Auth, lap ingestion + storage, layer-1 metrics, lap comparison, layer-2 AI coach, billing & plan
limits. Layered: `api` (thin routers) → `services` (business logic) → `repositories` (DB access).

## Layout

```
app/
  api/v1/        routers: auth, account, sessions, laps, coach, billing, health
  services/      auth, lap, coach, billing, account
  repositories/  user, session, lap, coach_report, subscription
  models/        SQLAlchemy ORM (portable GUID/JSON types → runs on SQLite in tests)
  schemas/       pydantic request/response models
  telemetry/     trace format, synthetic generator, layer-1 metrics, delta compare
  coach/         provider-agnostic LLM (stub + OpenAI/Anthropic) + payload/validation
  billing/       payment provider interface + stub adapter
  core/          config, security (argon2/JWT), db, deps, errors
  cli.py         `seed`, `recompute-metrics`
alembic/         migrations
tests/           pytest (in-memory SQLite + in-memory object store — no services needed)
```

## Run (Docker)

```bash
docker compose -f ../infra/docker-compose.yml up --build
# API http://localhost:8000 · docs /docs · MinIO console http://localhost:9001
docker compose -f ../infra/docker-compose.yml run --rm backend python -m app.cli seed
```

The API container runs `alembic upgrade head` on start.

## Tests

```bash
docker compose -f ../infra/docker-compose.yml run --rm --no-deps backend pytest -q
# or locally with Python 3.12: pip install -r requirements-dev.txt && pytest -q
```

## Configuration (`.env`, see `.env.example`)

Secrets have no production-safe defaults. Key vars: `DATABASE_URL`, `JWT_SECRET`, `S3_*`,
`CORS_ORIGINS`, plan limits (`FREE_MONTHLY_LAP_LIMIT`, `FREE_AI_TRIAL`).

**AI coach** — `COACH_PROVIDER=stub|openai|anthropic`. The deterministic **stub** is the default and
works fully offline; set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` to use a real model (the provider is
swappable without touching service code). Advice is always validated against the computed metrics.

**Billing** — `BILLING_PROVIDER=stub` for now; a ЮKassa/CloudPayments adapter implements the same
`PaymentProvider` interface. The webhook is signature-verified.

## Migrations

```bash
docker compose -f ../infra/docker-compose.yml run --rm backend alembic revision --autogenerate -m "msg"
docker compose -f ../infra/docker-compose.yml run --rm backend alembic upgrade head
```

## Key endpoints

`POST /auth/{register,login,refresh}` · `GET /me` · `POST /laps` ·
`GET /sessions` · `GET /sessions/{id}/laps` · `GET /laps/{id}` · `GET /laps/{id}/trace` ·
`GET /laps/compare?a=&b=` · `POST /coach/analyze` · `GET /laps/{id}/coach` ·
`GET /billing/plans` · `POST /billing/subscribe` · `POST /billing/webhook`.
