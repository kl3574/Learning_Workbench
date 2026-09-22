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
from .application.tutor import TutorService
from .application.tutor_context import ContextService
from .application.tutor_source import TutorOutboundSource, build_outbound
from .application.tutor_worker import TutorWorker
from .application.authoring import AuthoringService
from .application.authoring_context import AuthoringContext
from .application.authoring_source import AuthoringOutboundSource
from .application.authoring_worker import AuthoringWorker
from .application.authoring_numeric_service import NumericService
from .application.authoring_numeric_worker import NumericWorker
from .application.authoring_group import AuthoringGroupService
from .application.authoring_group_context import AuthoringGroupContext
from .application.authoring_group_source import AuthoringGroupOutboundSource
from .application.authoring_group_worker import AuthoringGroupWorker
from .application.authoring_group_numeric_service import GroupNumericService
from .application.authoring_group_numeric_worker import GroupNumericWorker
from .application.authoring_routing import AuthoringSourceRouter
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
from .interfaces.retrieval_http import create_retrieval_router
from .interfaces.route_http import create_route_router
from .interfaces.tutor_http import create_tutor_router
from .interfaces.authoring_http import create_authoring_router
from .interfaces.authoring_group_http import create_authoring_group_router
from .infrastructure.import_worker import ImportWorker
from .infrastructure.provider_secret_store import preferred_secret_store
from .infrastructure.authoring_numeric_runtime import NumericRuntime


def create_app(settings: Settings | None = None, *,
               outbound_sources: OutboundSourceRegistry | None = None,
               request_preparer: ProviderRequestPreparer | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings)
    import_service = ImportService(database)
    import_worker = ImportWorker(database)
    tutor_context = ContextService(database)
    tutor_service = TutorService(database, tutor_context)
    authoring_context = AuthoringContext(database)
    authoring_group_context = AuthoringGroupContext(database)
    # Registrations are explicit trusted Python composition, never HTTP or
    # environment data. The production Tutor source owns real jobs; production
    # model proofs remain unavailable until their separate verification.
    provider_sources = (outbound_sources if outbound_sources is not None else OutboundSourceRegistry()).with_source(
        'tutor', TutorOutboundSource(tutor_context)).with_source('authoring', AuthoringSourceRouter(
            AuthoringOutboundSource(authoring_context), AuthoringGroupOutboundSource(authoring_group_context)))
    provider_preparer = request_preparer if request_preparer is not None else RequestPreparer(ProofRegistry())
    provider_secrets = preferred_secret_store(settings.provider_secret_dir)
    providers = ProviderService(database, provider_secrets, provider_preparer)
    consents = ConsentsService(database, provider_secrets, provider_sources, provider_preparer)
    provider_dispatch = CheckedDispatch(database, provider_secrets, provider_sources, provider_preparer)
    tutor_worker = TutorWorker(database, tutor_context, provider_dispatch, build_outbound)
    authoring_service = AuthoringService(database, authoring_context, provider_dispatch)
    authoring_worker = AuthoringWorker(database, authoring_context, provider_dispatch)
    authoring_group_service = AuthoringGroupService(database, authoring_group_context, provider_dispatch)
    authoring_group_worker = AuthoringGroupWorker(database, authoring_group_context, provider_dispatch)
    numeric_runtime = NumericRuntime()
    numeric_service = NumericService(database, authoring_context, numeric_runtime, authoring=authoring_service)
    numeric_worker = NumericWorker(database, authoring_context, numeric_runtime, authoring=authoring_service)
    group_numeric_runtime = NumericRuntime()
    group_numeric_service = GroupNumericService(database, authoring_group_context, group_numeric_runtime, authoring=authoring_group_service)
    group_numeric_worker = GroupNumericWorker(database, authoring_group_context, group_numeric_runtime, authoring=authoring_group_service)

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
        tutor_worker.start()
        authoring_worker.start()
        authoring_group_worker.start()
        numeric_worker.start()
        group_numeric_worker.start()
        try:
            yield
        finally:
            group_numeric_worker.stop()
            numeric_worker.stop()
            authoring_group_worker.stop()
            authoring_worker.stop()
            tutor_worker.stop()
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
    application.state.tutor_service = tutor_service
    application.state.tutor_worker = tutor_worker
    application.state.authoring_service = authoring_service
    application.state.authoring_worker = authoring_worker
    application.state.authoring_group_service = authoring_group_service
    application.state.authoring_group_worker = authoring_group_worker
    application.state.numeric_service = numeric_service
    application.state.numeric_runtime = numeric_runtime
    application.state.numeric_worker = numeric_worker
    application.state.group_numeric_service = group_numeric_service
    application.state.group_numeric_runtime = group_numeric_runtime
    application.state.group_numeric_worker = group_numeric_worker
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
    application.include_router(create_retrieval_router(database))
    application.include_router(create_tutor_router(tutor_service))
    application.include_router(create_authoring_router(authoring_service, numeric_service, authoring_group_service))
    application.include_router(create_authoring_group_router(authoring_group_service, group_numeric_service))
    if settings.static_dir.is_dir():
        application.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="workbench")
    return application
