"""Actual SQLite read-scope reuse; each admission/policy check remains live."""
import pytest

from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.tutor_repository import TutorRepository
from tests.integration import test_tutor_runs as fixtures

tutor = fixtures.tutor

@pytest.mark.parametrize("operation", ["read", "events", "authorize"])
def test_one_service_snapshot_validates_each_owned_run_once(tutor, monkeypatch, operation):
    _, identity, service, _ = tutor
    _, _, ack = fixtures.started(tutor)
    original = TutorRepository._load_checked
    calls = []
    def checked(self, identifier):
        calls.append((self, identifier))
        return original(self, identifier)
    monkeypatch.setattr(TutorRepository, "_load_checked", checked)
    if operation == "read":
        assert service.read(identity, ack.run.id).run.id == ack.run.id
    elif operation == "events":
        assert [event.type for event in service.events(identity, ack.run.id, 0)] == ["queued"]
    else:
        service.authorize(identity, run_id=ack.run.id)
    assert len(calls) == 1

def test_new_service_read_revalidates_corrupted_original_message(tutor):
    database, identity, service, _ = tutor
    _, _, ack = fixtures.started(tutor)
    assert service.read(identity, ack.run.id).run.status == "queued"
    with database.transaction() as connection:
        connection.execute("UPDATE tutor_messages SET message_sha256=?", ("0" * 64,))
    with pytest.raises(ApiError) as error:
        service.read(identity, ack.run.id)
    assert error.value.code == "TUTOR_INTEGRITY_ERROR"

def test_local_write_invalidates_an_active_read_scope(tutor):
    database, identity, _, _ = tutor
    _, _, ack = fixtures.started(tutor)
    with database.transaction() as connection:
        repo = TutorRepository(connection, identity.workspace_id)
        with repo._read_snapshot():
            assert repo.view(ack.run.id).run.status == "queued"
            connection.execute("UPDATE tutor_events SET event_sha256=? WHERE run_id=?", ("0" * 64, ack.run.id))
            with pytest.raises(ApiError) as error:
                repo.view(ack.run.id)
            assert error.value.code == "TUTOR_INTEGRITY_ERROR"
