"""Application composition; imports and factory calls never initialize user data."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from packages.contracts.domain_models import ErrorEnvelope

from .application.imports import ImportService
from .application.reader import backfill_provenance
from .config import Settings
from .database import Database
from .interfaces.boundary import install_boundary
from .interfaces.assessment_http import create_assessment_router
from .interfaces.content_http import create_content_router
from .interfaces.concept_state_http import create_concept_state_router
from .interfaces.http import create_router
from .interfaces.import_http import create_import_router
from .interfaces.learning_http import create_learning_router
from .interfaces.practice_http import create_practice_router
from .interfaces.profile_http import create_profile_router
from .interfaces.recommendation_http import create_recommendation_router
from .interfaces.route_http import create_route_router
from .infrastructure.import_worker import ImportWorker


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings)
    import_service = ImportService(database)
    import_worker = ImportWorker(database)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database.initialize()
        application.state.provenance_backfill = backfill_provenance(database)
        import_worker.start()
        try:
            yield
        finally:
            import_worker.stop()

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
    application.state.import_worker = import_worker
    install_boundary(application, settings, database)
    application.include_router(create_router(settings, database, worker_ready=import_worker.is_alive))
    application.include_router(create_content_router(database))
    application.include_router(create_import_router(settings, import_service))
    application.include_router(create_learning_router(database))
    application.include_router(create_practice_router(database))
    application.include_router(create_assessment_router(database))
    application.include_router(create_route_router(database))
    application.include_router(create_profile_router(database))
    application.include_router(create_concept_state_router(database))
    application.include_router(create_recommendation_router(database))
    if settings.static_dir.is_dir():
        application.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="workbench")
    return application
