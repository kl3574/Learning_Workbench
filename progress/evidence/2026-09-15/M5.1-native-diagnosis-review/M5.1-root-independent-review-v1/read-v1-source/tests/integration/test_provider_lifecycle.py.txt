"""Actual app restart recovery of synthetic durable starts; never a provider call."""

import socket

from fastapi.testclient import TestClient

from services.api.app.infrastructure.consent_repository import ConsentRepository
from services.api.app.infrastructure.database import utc_now
from services.api.app.main import create_app
from tests.provider_protocol_fixture import authorized_source


def test_app_startup_skips_live_owner_then_recovers_abandoned_allowance_without_network(tmp_path, monkeypatch):
    db, identity, _, _, job, _, _, _, grant, _ = authorized_source(tmp_path, 'http://127.0.0.1:1/v1')
    with db.transaction() as connection:
        repo = ConsentRepository(connection, identity.workspace_id)
        summary, _, _ = repo.dispatch_material(grant.id)
        record, created = repo.begin_dispatch(grant.id, job,
            summary.input_token_assurance.request_body_sha256, utc_now())
        assert created
        live_job = tuple(connection.execute('SELECT * FROM jobs WHERE id=?', (job,)).fetchone())
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Startup recovery must not resolve or call a provider.')
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    app = create_app(db.settings)
    with TestClient(app, base_url=db.settings.origin) as client:
        assert client.get('/health').status_code == 200
        assert app.state.provider_recovered_count == 0
        with db.transaction() as connection:
            assert ConsentRepository(connection, identity.workspace_id).read_terminal(record.id) is None
            assert tuple(connection.execute('SELECT * FROM jobs WHERE id=?', (job,)).fetchone()) == live_job
    # Explicit test-only clock precondition simulates the old owner lease having
    # expired. The production recovery never edits the source job or claims it.
    with db.transaction() as connection:
        connection.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00Z' WHERE id=?", (job,))
        expired_job = tuple(connection.execute('SELECT * FROM jobs WHERE id=?', (job,)).fetchone())
    restarted = create_app(db.settings)
    with TestClient(restarted, base_url=db.settings.origin):
        assert restarted.state.provider_recovered_count == 1
        with db.transaction() as connection:
            repo = ConsentRepository(connection, identity.workspace_id)
            receipt = repo.read_terminal(record.id)
            assert receipt.terminal.type == 'error'
            assert receipt.terminal.error_code == 'PROVIDER_OUTCOME_UNKNOWN'
            assert receipt.terminal.provider_outcome == 'unknown'
            assert receipt.terminal.usage.input_tokens is None
            assert receipt.answer_artifact_id is receipt.refusal_artifact_id is None
            assert tuple(connection.execute('SELECT * FROM jobs WHERE id=?', (job,)).fetchone()) == expired_job
    again = create_app(db.settings)
    with TestClient(again, base_url=db.settings.origin):
        assert again.state.provider_recovered_count == 0
        with db.transaction() as connection:
            repo = ConsentRepository(connection, identity.workspace_id)
            assert repo.read_terminal(record.id) == receipt
            assert connection.execute('SELECT count(*) FROM provider_dispatches').fetchone()[0] == 1
    assert attempts == []
