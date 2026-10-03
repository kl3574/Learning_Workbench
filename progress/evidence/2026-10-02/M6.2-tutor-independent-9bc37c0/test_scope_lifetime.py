from collections import Counter
import pytest
from services.api.app.infrastructure.tutor_repository import TutorRepository
from tests.integration.test_tutor_runs import started, tutor


def test_return_and_exception_both_force_next_read_to_check_again(tmp_path, monkeypatch):
    database, identity, _, _ = values = tutor.__wrapped__(tmp_path)
    _, _, ack = started(values)
    scans = Counter()
    with database.transaction(immediate=False) as connection:
        connection.set_trace_callback(lambda sql: scans.update([sql]) if sql.startswith('SELECT * FROM tutor_events WHERE run_id=') else None)
        repo = TutorRepository(connection, identity.workspace_id)
        assert repo.source_state(ack.run.id).status == 'queued'
        assert repo.source_state(ack.run.id).status == 'queued'
        assert list(scans.values()) == [2]
        original = repo.thread
        def fail_thread(*args, **kwargs):
            raise RuntimeError('synthetic nested-read interruption after complete run validation')
        monkeypatch.setattr(repo, 'thread', fail_thread)
        with pytest.raises(RuntimeError):
            repo.view(ack.run.id)
        assert list(scans.values()) == [3]
        monkeypatch.setattr(repo, 'thread', original)
        assert repo.view(ack.run.id).run.status == 'queued'
        assert list(scans.values()) == [4]
