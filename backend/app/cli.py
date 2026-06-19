"""Developer CLI.

Seed a demo user with synthetic F1 laps so the web cabinet has data before the
desktop client exists::

    python -m app.cli seed --email demo@apexai.dev --password demo12345 --laps 3

Idempotent: laps use stable client ids, so re-running does not duplicate them.
Run after migrations are applied (``alembic upgrade head`` / docker compose up).
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.lap import Lap
from app.repositories.user_repo import UserRepository
from app.schemas.lap import LapMeta
from app.services.lap_service import LapService
from app.storage.object_store import get_object_store
from app.telemetry.metrics import compute_lap_metrics
from app.telemetry.synth import SIM_CIRCUIT, generate_lap, lap_time_ms
from app.telemetry.trace import LapTrace


async def _seed(email: str, password: str, laps: int) -> None:
    email = email.lower()
    store = get_object_store()
    await store.ensure_ready()

    async with SessionLocal() as db:
        users = UserRepository(db)
        user = await users.get_by_email(email)
        if user is None:
            user = await users.create(email, hash_password(password))
            await db.commit()
            print(f"Created user {email} (password: {password})")
        else:
            print(f"Using existing user {email}")

        service = LapService(db, store)
        session_uuid = f"seed-session-{user.id}"
        for i in range(laps):
            trace = generate_lap(SIM_CIRCUIT.name, seed=i)
            meta = LapMeta(
                client_lap_uuid=f"seed-{user.id}-{i}",
                client_session_uuid=session_uuid,
                game="f1_25",
                track=SIM_CIRCUIT.name,
                car_or_team="Demo Car",
                session_type="practice",
                weather="dry",
                lap_time_ms=lap_time_ms(trace),
                valid=True,
                recorded_at=datetime.now(timezone.utc),
                sample_count=trace.points,
            )
            lap = await service.ingest(user, meta, trace.to_gzip())
            print(f"  lap {i}: {meta.lap_time_ms / 1000:.3f}s ({trace.points} pts) -> {lap.id}")

    print(f"Done. Log in as {email} and open the cabinet.")


async def _recompute_metrics() -> None:
    """Backfill / refresh layer-1 metrics for every stored lap (e.g. after a metrics change)."""
    store = get_object_store()
    async with SessionLocal() as db:
        laps = (await db.execute(select(Lap).options(selectinload(Lap.trace)))).scalars().all()
        updated = 0
        for lap in laps:
            if lap.trace is None:
                continue
            blob = await store.get(lap.trace.storage_key)
            lap.metrics = compute_lap_metrics(LapTrace.from_gzip(blob))
            updated += 1
        await db.commit()
        print(f"Recomputed metrics for {updated} lap(s).")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    seed_p = sub.add_parser("seed", help="Seed a demo user with synthetic F1 laps")
    seed_p.add_argument("--email", default="demo@apexai.dev")
    seed_p.add_argument("--password", default="demo12345")
    seed_p.add_argument("--laps", type=int, default=3)

    sub.add_parser("recompute-metrics", help="Recompute layer-1 metrics for all stored laps")

    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(_seed(args.email, args.password, args.laps))
    elif args.command == "recompute-metrics":
        asyncio.run(_recompute_metrics())


if __name__ == "__main__":
    main()
