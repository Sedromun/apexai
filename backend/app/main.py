from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.storage.object_store import get_object_store


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Best-effort bucket creation for dev/MinIO; per-request calls surface real errors.
    try:
        await get_object_store().ensure_ready()
    except Exception:
        pass
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        # In dev, accept any localhost port (preview servers, alternate ports); prod stays strict.
        allow_origin_regex=(
            None if settings.is_production else r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
