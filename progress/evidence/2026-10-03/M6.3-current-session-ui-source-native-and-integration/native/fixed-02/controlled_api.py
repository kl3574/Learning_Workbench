"""Explicit synthetic bootstrap test port; all turn HTTP/SQLite paths are real."""
from pathlib import Path

from services.api.app.config import Settings
from services.api.app.main import create_app as application
from tests.integration.test_codex_bootstrap_http import ControlledRuntime


class NativeControlledBootstrap(ControlledRuntime):
    def execute(self, frozen, permit_id):
        outcome = super().execute(frozen, permit_id)
        with (Settings.from_env().data_dir / 'synthetic-bootstrap-count.txt').open('a') as record:
            record.write('synthetic-bootstrap\n')
        return outcome


def create_app():
    settings = Settings.from_env()
    app = application(settings, codex_bootstrap_runtime=NativeControlledBootstrap())
    app.state.database.initialize()
    app.state.provider_service.secret_store.initialize()
    return app
