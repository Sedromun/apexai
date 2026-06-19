from fastapi import APIRouter
from sqlalchemy import text

from app.core.deps import DbDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness — no dependencies, so it answers even if the DB is down."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(db: DbDep) -> dict[str, str]:
    """Readiness — verifies the database connection."""
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}
