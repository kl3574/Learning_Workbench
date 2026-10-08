"""Only RestartRuntime's explicit E2E opt-in selects this app factory."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from server_stage_observer import Boundary, Collector, OwnedBindings


def observed_lifespan(original: Any, bindings: OwnedBindings, collector: Collector, output: Path) -> Any:
    @asynccontextmanager
    async def lifespan(application: Any):
        returned = False
        try:
            async with original(application):
                yield
            returned = True
        finally:
            # Original shutdown owns all existing stop/join/wait behavior.
            # No per-event file writes; failed/SIGKILL cleanup can remain absent.
            try:
                bindings.restore()
            except BaseException:  # noqa: BLE001, S110 - Never log private diagnostic exceptions or replace the original outcome.
                pass
            try:
                collector.save(output, boundary=Boundary.LIFESPAN_RETURNED if returned else Boundary.LIFESPAN_RAISED)
            except BaseException:  # noqa: BLE001, S110 - Never log private diagnostic exceptions or replace the original outcome.
                pass
    return lifespan


def create_app():
    # No environment opt-in exists in the ordinary production create_app.
    from services.api.app.main import create_app as production_create_app
    application = production_create_app()
    if os.environ.get("LEARNING_E2E_SERVER_STAGE_OBSERVER") != "1":
        return application
    generation = os.environ.get("LEARNING_E2E_SERVER_STAGE_GENERATION", "")
    if generation not in ("0", "1", "2", "3"):
        return application
    try:
        from services.api.app.application.grading import GradingService
        from services.api.app.infrastructure.grading_repository import GradingRepository
        collector = Collector()
        bindings = OwnedBindings(collector, application.state.database,
                                 application.state.import_worker, GradingService, GradingRepository)
        bindings.install()
        output = application.state.settings.data_dir / f"e2e-server-stages-{generation}.json"
        application.router.lifespan_context = observed_lifespan(
            application.router.lifespan_context, bindings, collector, output)
    except BaseException:  # noqa: BLE001 - Never log private diagnostic exceptions or replace the original outcome.
        # Construction/installation is diagnostic, never an app-start condition.
        if "bindings" in locals():
            try:
                bindings.restore()
            except BaseException:  # noqa: BLE001, S110 - Never log private diagnostic exceptions or replace the original outcome.
                pass
    return application
