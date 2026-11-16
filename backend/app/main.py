from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging
from app.database.session import SessionLocal, engine, init_db
from app.services import application_service, compute_service

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        yield
    finally:
        try:
            with SessionLocal() as db:
                compute_service.stop_all_active(db)
                application_service.stop_all_active(db)
        except Exception:
            logger.exception("Could not stop managed workers during shutdown")
        finally:
            engine.dispose()


app = FastAPI(
    title="Mini AWS Local Cloud API",
    version="0.1.0",
    description="Educational local cloud lab API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
