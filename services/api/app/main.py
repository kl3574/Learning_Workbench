"""Application composition; imports and factory calls never initialize user data."""

from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from packages.contracts.domain_models import ErrorEnvelope

from .application.imports import ImportService
from .application.consents import ConsentsService
from .application.provider_budget import ProofRegistry, RequestPreparer
from .application.provider_dispatch import CheckedDispatch
from .application.provider_ports import OutboundSourceRegistry, ProviderRequestPreparer
from .application.providers import ProviderService
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
from .interfaces.provider_http import create_provider_router
from .interfaces.recommendation_http import create_recommendation_router
from .interfaces.route_http import create_route_router
from .infrastructure.import_worker import ImportWorker
from .infrastructure.provider_secret_store import preferred_secret_store


def create_app(settings: Settings | None = None, *,
               outbound_sources: OutboundSourceRegistry | None = None,
               request_preparer: ProviderRequestPreparer | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings)
    import_service = ImportService(database)
    import_worker = ImportWorker(database)
    # Registrations are explicit trusted Python composition, never HTTP or
    # environment data. M5.1 has no production source or model proof entry.
    provider_sources = outbound_sources if outbound_sources is not None else OutboundSourceRegistry()
    provider_preparer = request_preparer if request_preparer is not None else RequestPreparer(ProofRegistry())
    provider_secrets = preferred_secret_store(settings.provider_secret_dir)
    providers = ProviderService(database, provider_secrets, provider_preparer)
    consents = ConsentsService(database, provider_secrets, provider_sources, provider_preparer)
    provider_dispatch = CheckedDispatch(database, provider_secrets, provider_sources, provider_preparer)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        workspace_id = database.initialize()
        provider_secrets.initialize()
        # Only consumed, abandoned records are terminated. Recovery cannot make
        # another HTTP attempt and must skip a still-live source owner lease.
        recovered = await asyncio.to_thread(provider_dispatch.recover_unfinished, workspace_id)
        application.state.provider_recovered_count = len(recovered)
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
    application.state.provider_service = providers
    application.state.consent_service = consents
    application.state.provider_dispatch = provider_dispatch
    application.state.outbound_sources = provider_sources
    application.state.request_preparer = provider_preparer
    install_boundary(application, settings, database)
    application.include_router(create_router(settings, database, worker_ready=import_worker.is_alive))
    application.include_router(create_content_router(database))
    application.include_router(create_import_router(settings, import_service))
    application.include_router(create_learning_router(database))
    application.include_router(create_practice_router(database))
    application.include_router(create_assessment_router(database))
    application.include_router(create_route_router(database))
    application.include_router(create_profile_router(database))
    application.include_router(create_provider_router(providers, consents))
    application.include_router(create_concept_state_router(database))
    application.include_router(create_recommendation_router(database))
    if settings.static_dir.is_dir():
        application.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="workbench")
    return application
