"""Private diagnosis only. Real synthetic fixtures, explicit local clock fault.
Never changes host time; +120s is injected only after real work reaches finish.
The unmodified original fixture completion assertion is the RED oracle.
"""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path

import pytest

from services.api.app.infrastructure import database as db_module, security
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.application.authoring_group_worker import AuthoringGroupWorker
from tests.integration import test_authoring_group_numeric_service as group_fixture
from tests.integration import test_authoring_group_provider as generation
from tests.integration import test_assessment_attempts as assessment_fixture

EVIDENCE = Path(__file__).parent


def instrument(monkeypatch, target, expire):
    capture = {'offset': 0, 'finish_calls': 0, 'run_once_returns': []}
    class ControlledDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) + timedelta(seconds=capture['offset'])
    monkeypatch.setattr(db_module, 'datetime', ControlledDatetime)
    monkeypatch.setattr(security, 'datetime', ControlledDatetime)
    worker_type = AuthoringGroupWorker if target == 'group' else ImportWorker
    original_run = worker_type.run_once
    def run(worker):
        capture['worker'] = worker
        capture['database'] = worker.database
        result = original_run(worker)
        capture['run_once_returns'].append(result)
        return result
    monkeypatch.setattr(worker_type, 'run_once', run)
    if target == 'group':
        original_configured = generation.configured
        def configured(*args, **kwargs):
            state = original_configured(*args, **kwargs)
            capture['state'] = state
            return state
        monkeypatch.setattr(generation, 'configured', configured)
        original_finish = worker_type._finish
        def finish(worker, *args, **kwargs):
            capture['finish_calls'] += 1
            if expire and capture['finish_calls'] == 1:
                capture['offset'] = 120
            return original_finish(worker, *args, **kwargs)
        monkeypatch.setattr(worker_type, '_finish', finish)
    else:
        original_parse = worker_type._parse
        def parse(worker, *args, **kwargs):
            parsed = original_parse(worker, *args, **kwargs)
            capture['finish_calls'] += 1
            if expire and capture['finish_calls'] == 1:
                capture['offset'] = 120
            return parsed
        monkeypatch.setattr(worker_type, '_parse', parse)
    return capture


def original_fixture(target, tmp_path):
    return (group_fixture.generated_group(tmp_path, 'assessment') if target == 'group'
            else assessment_fixture.storage.__wrapped__(tmp_path))


def safe_state(capture):
    with capture['database'].connect() as conn:
        return {'jobs': [dict(r) for r in conn.execute('SELECT kind,status,revision,cancel_requested,lease_until,created_at,updated_at FROM jobs')],
                'events': [dict(r) for r in conn.execute('SELECT seq,type,occurred_at FROM job_events ORDER BY seq')],
                'run_once_returns': capture['run_once_returns'], 'finish_calls': capture['finish_calls'],
                'clock_offset_seconds': capture['offset']}


def terminal_digest(database):
    with database.connect() as conn:
        rows = [list(r) for r in conn.execute('SELECT receipt_sha256 FROM provider_terminals ORDER BY dispatch_id')]
        return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


@pytest.mark.parametrize('target', ['group', 'import'])
@pytest.mark.parametrize('expire', [False, True], ids=['valid', 'expired'])
def test_original_fixture_completion_oracle(tmp_path, monkeypatch, target, expire):
    capture = instrument(monkeypatch, target, expire)
    try:
        original_fixture(target, tmp_path)
    finally:
        (EVIDENCE / f'05-original-{target}-{expire}-state.json').write_text(json.dumps(safe_state(capture), indent=2)+'\n')


@pytest.mark.parametrize('target', ['group', 'import'])
def test_expired_owner_refuses_then_fresh_owner_recovers(tmp_path, monkeypatch, target):
    capture = instrument(monkeypatch, target, True)
    with pytest.raises(AssertionError):
        original_fixture(target, tmp_path)
    first = safe_state(capture)
    assert first['run_once_returns'] == [True]
    assert first['jobs'][0]['status'] == 'running'
    assert first['jobs'][0]['cancel_requested'] == 0
    database = capture['database']
    if target == 'group':
        _, identity, service, old_worker, _, dispatch = capture['state']
        before = terminal_digest(database)
        async def forbidden_dispatch(*args, **kwargs):
            raise AssertionError('Recovery must not issue a second Provider dispatch')
            yield
        monkeypatch.setattr(dispatch, 'dispatch', forbidden_dispatch)
        fresh = AuthoringGroupWorker(database, service.context, dispatch)
        assert fresh.run_once()
        with database.connect() as conn:
            job = conn.execute("SELECT id,status FROM jobs WHERE kind='authoring'").fetchone()
            assert job['status'] == 'completed'
            assert conn.execute('SELECT COUNT(*) FROM provider_dispatches').fetchone()[0] == 1
            assert conn.execute('SELECT COUNT(*) FROM authoring_group_candidates').fetchone()[0] == 1
        assert service.read(identity, job['id']).summary.status == 'completed'
        assert terminal_digest(database) == before
    else:
        fresh = ImportWorker(database)
        assert fresh.run_once()
        with database.connect() as conn:
            assert conn.execute('SELECT status FROM ingestion_imports').fetchone()[0] == 'preview_ready'
            assert conn.execute('SELECT status FROM jobs').fetchone()[0] == 'awaiting_approval'
            assert conn.execute('SELECT count(*) FROM drafts').fetchone()[0] > 0
    assert fresh.run_once() is False
    after = safe_state(capture)
    (EVIDENCE / f'06-recovery-{target}.json').write_text(json.dumps({'before':first,'after':after}, indent=2)+'\n')
