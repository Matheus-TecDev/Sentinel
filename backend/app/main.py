import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.errors import http_exception_handler, validation_exception_handler
from app.core.logging import configure_logging
from app.db.init_db import seed_initial_admin
from app.db.session import SessionLocal
from app.workers.healthcheck_worker import start_healthcheck_scheduler, stop_healthcheck_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    settings = get_settings()
    with SessionLocal() as db:
        seed_initial_admin(db)
    if settings.ENABLE_HEALTHCHECK_WORKER:
        start_healthcheck_scheduler()
    logger.info("Sentinel API started environment=%s", settings.ENVIRONMENT)
    yield
    stop_healthcheck_scheduler()
    logger.info("Sentinel API stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    app.include_router(api_router, prefix=settings.API_PREFIX)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "sentinel-backend"}

    return app


app = create_app()
