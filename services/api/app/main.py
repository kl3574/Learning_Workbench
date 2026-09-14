"""Application composition; imports and factory calls never initialize user data."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from packages.contracts.domain_models import ErrorEnvelope

from .config import Settings
from .database import Database
from .interfaces.boundary import install_boundary
from .interfaces.content_http import create_content_router
from .interfaces.http import create_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database.initialize()
        yield

    application = FastAPI(
        title="知径 Learning Workbench",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        responses={status: {"model": ErrorEnvelope} for status in (400, 401, 403, 404, 405, 409, 412, 413, 422, 500, 503)},
    )
    application.state.database = database
    application.state.settings = settings
    install_boundary(application, settings, database)
    application.include_router(create_router(settings, database))
    application.include_router(create_content_router(database))
    if settings.static_dir.is_dir():
        application.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="workbench")
    return application
