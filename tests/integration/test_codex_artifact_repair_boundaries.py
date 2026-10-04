"""Real HTTP-created source facts and post-transaction download admission."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
import shutil
from threading import Event

import pytest

from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.infrastructure.database import Database
from tests.integration.test_codex_artifact_import_http import selected, consent_case, base_consent_case
from tests.integration.test_codex_artifact_manifest import execute
from tests.integration.test_assessment_learning_port import assessment_learning_state

__all__ = ['consent_case', 'base_consent_case']
assessment_state = assessment_learning_state


@pytest.mark.parametrize('table', ['codex_import_batches', 'codex_import_bindings', 'codex_import_previews'])
@pytest.mark.parametrize('mutation', ['update', 'delete', 'replace', 'upsert'])
def test_original_import_source_rows_reject_normal_mutation_and_preserve_full_http_readback(consent_case, table, mutation):
    case, sid, _, body = selected(consent_case)
    created = case.post(f'sessions/{sid}/artifacts/import', body, 'original-import')
    assert created.status_code == 202
    identifier = created.json()['id']
    assert ImportWorker(case.app.state.database).run_once() is True
    original = case.get('artifact-imports/'+identifier)
    assert original.status_code == 200
    item = original.json()['items'][0]
    preview = case.client.get('/api/v1/imports/'+item['import_id'])
    assert preview.status_code == 200 and preview.json()['status'] == 'preview_ready'
    before = case.dump()
    with case.app.state.database.transaction() as conn:
        row = dict(conn.execute(f'SELECT * FROM {table}').fetchone())
        columns = ','.join(row)
        placeholders = ','.join('?' for _ in row)
        statement = f'INSERT OR REPLACE INTO {table}({columns}) VALUES({placeholders})'
        args = tuple(row.values())
        if mutation == 'update':
            statement, args = f'UPDATE {table} SET record_json=record_json', ()
        elif mutation == 'delete':
            statement, args = f'DELETE FROM {table}', ()
        elif mutation == 'upsert':
            statement = f'INSERT INTO {table}({columns}) VALUES({placeholders}) ON CONFLICT DO UPDATE SET record_json=excluded.record_json'
        with pytest.raises(sqlite3.IntegrityError, match='immutable Codex Import'):
            conn.execute(statement, args)
    assert case.dump() == before
    assert case.get('artifact-imports/'+identifier).content == original.content
    assert case.client.get('/api/v1/imports/'+item['import_id']).content == preview.content
    assert case.post(f'sessions/{sid}/artifacts/import', body, 'original-import').content == created.content
    assert len(case.app.state.synthetic_transport_calls) == 1


def pause_after_download_transaction(database, monkeypatch):
    """Pause only after the real first transaction commits and closes its connection."""
    transaction = database.transaction
    entered, release = Event(), Event()
    armed = True

    @contextmanager
    def held(*args, **kwargs):
        nonlocal armed
        pause = armed
        armed = False
        with transaction(*args, **kwargs) as conn:
            yield conn
        if pause:
            entered.set()
            assert release.wait(10), 'The controlled HTTP race was not released'

    monkeypatch.setattr(database, 'transaction', held)
    return entered, release


@pytest.mark.parametrize('change,expected', [('learner', 403), ('logout', 401)])
def test_download_rechecks_actor_after_original_transaction_has_closed(consent_case, monkeypatch, change, expected):
    case, sid, prep, _, _, _ = execute(consent_case)
    manifest = case.get(f'sessions/{sid}/turns/{prep["turn_id"]}/artifacts').json()['manifest']
    path = '/api/v1/artifacts/'+manifest['entries'][0]['artifact_id']+'/download'
    original = case.client.get(path)
    assert original.status_code == 200 and original.content == 'Synthetic exact answer α\n'.encode()
    entered, release = pause_after_download_transaction(case.app.state.database, monkeypatch)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(case.client.get, path)
        try:
            assert entered.wait(10)
            changed = case.client.post('/api/v1/session/'+('role' if change == 'learner' else 'logout'),
                json={'role':'learner'} if change == 'learner' else {},
                headers={**case.headers, 'Idempotency-Key':'late-download-access'})
            assert changed.status_code == 200
            before = case.dump()
        finally:
            release.set()
        response = future.result(timeout=10)
    assert response.status_code == expected
    assert original.content not in response.content
    assert response.json()['error']['code'] in {'POLICY_DENIED', 'SESSION_REQUIRED'}
    assert case.dump() == before
    assert len(case.app.state.synthetic_transport_calls) == 1


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_download_rechecks_real_policy_started_after_original_transaction(assessment_state, monkeypatch, mode):
    from services.api.app.infrastructure.content_repository import reference
    from tests.integration.test_codex_turn_consent_http import make_consent_case
    from tests.integration.test_codex_turn_dispatch_http import make_dispatch_case
    database, _, fixture, _ = assessment_state
    for original in make_consent_case(database.settings.data_dir):
        for values in make_dispatch_case(original):
            case, sid, prep, _, _, _ = execute(values)
            manifest = case.get(f'sessions/{sid}/turns/{prep["turn_id"]}/artifacts').json()['manifest']
            path = '/api/v1/artifacts/'+manifest['entries'][0]['artifact_id']+'/download'
            entered, release = pause_after_download_transaction(case.app.state.database, monkeypatch)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(case.client.get, path)
                try:
                    assert entered.wait(10)
                    started = case.client.post('/api/v1/assessments/'+fixture.assessment.id+'/attempts',
                        json={'assessment_ref':reference(fixture.assessment).model_dump(), 'mode':mode},
                        headers={**case.headers, 'Idempotency-Key':'late-policy'})
                    assert started.status_code == 201
                    before = case.dump()
                finally:
                    release.set()
                response = future.result(timeout=10)
            assert response.status_code == 409
            assert response.json()['error']['code'] == 'ASSESSMENT_ACTIVE'
            assert b'Synthetic exact answer' not in response.content
            assert case.dump() == before
            assert len(case.app.state.synthetic_transport_calls) == 1


@pytest.mark.parametrize('identity', ['import_id', 'source_id', 'import_job_id', 'ordinal'])
def test_replace_cannot_evict_any_existing_binding_conflict_identity(consent_case, identity):
    case, sid, _, body = selected(consent_case)
    created = case.post(f'sessions/{sid}/artifacts/import', body, 'original-import')
    assert created.status_code == 202
    before = case.dump()
    with case.app.state.database.transaction() as conn:
        original = dict(conn.execute('SELECT * FROM codex_import_bindings').fetchone())
        incoming = {**original, 'import_id':'import_other', 'source_id':'source_other',
            'import_job_id':'job_other', 'aggregate_job_id':'aggregate_other', 'ordinal':1}
        incoming[identity] = original[identity]
        if identity == 'ordinal':
            incoming['aggregate_job_id'] = original['aggregate_job_id']
        # The immutable conflict guard must reject before SQLite's later FK
        # validation. Each candidate matches exactly one existing unique key.
        with pytest.raises(sqlite3.IntegrityError, match='immutable Codex Import'):
            conn.execute('INSERT OR REPLACE INTO codex_import_bindings('+','.join(incoming)+') VALUES('
                +','.join('?' for _ in incoming)+')', tuple(incoming.values()))
    assert case.dump() == before
    assert case.post(f'sessions/{sid}/artifacts/import', body, 'original-import').content == created.content


def test_forward_guards_preserve_existing_source_rows_rowids_and_original_http_acks(tmp_path, monkeypatch):
    from tests.integration import test_codex_bootstrap_http as bootstrap_fixture
    from tests.integration.test_codex_turn_consent_http import make_consent_case
    from tests.integration.test_codex_turn_dispatch_http import make_dispatch_case
    settings_type = bootstrap_fixture.Settings
    installed = settings_type(data_dir=tmp_path/'data')
    prior = tmp_path/'prior-migrations'
    prior.mkdir()
    for path in installed.migrations_dir.glob('*.sql'):
        if path.name < '0035':
            shutil.copyfile(path, prior/path.name)
    # Install the real previous catalog while creating the normal HTTP fixture;
    # no source rows, migration receipts or owner histories are fabricated.
    monkeypatch.setattr(bootstrap_fixture, 'Settings',
        lambda **kwargs: replace(settings_type(**kwargs), migrations_dir=prior))
    for original in make_consent_case(installed.data_dir):
        for values in make_dispatch_case(original):
            case, sid, _, body = selected(values)
            created = case.post(f'sessions/{sid}/artifacts/import', body, 'before-upgrade')
            assert created.status_code == 202
            assert ImportWorker(case.app.state.database).run_once() is True
            view = case.get('artifact-imports/'+created.json()['id'])
            assert view.status_code == 200
            tables = ['codex_import_batches', 'codex_import_bindings', 'codex_import_previews']
            with case.app.state.database.connect() as conn:
                rows = {table:[tuple(row) for row in conn.execute(f'SELECT rowid,* FROM {table} ORDER BY rowid')]
                    for table in tables}
                assert all(rows.values())
            upgraded = Database(replace(case.app.state.settings, migrations_dir=installed.migrations_dir))
            upgraded.initialize()
            with upgraded.connect() as conn:
                assert {table:[tuple(row) for row in conn.execute(f'SELECT rowid,* FROM {table} ORDER BY rowid')]
                    for table in tables} == rows
                assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
                for table in tables:
                    with pytest.raises(sqlite3.IntegrityError, match='immutable Codex Import'):
                        conn.execute(f'UPDATE {table} SET record_json=record_json')
            assert case.get('artifact-imports/'+created.json()['id']).content == view.content
            assert case.post(f'sessions/{sid}/artifacts/import', body, 'before-upgrade').content == created.content
            assert len(case.app.state.synthetic_transport_calls) == 1


def test_ordinary_import_download_remains_available_to_current_learner(tmp_path):
    from tests.integration.test_codex_bootstrap_http import make_case
    from tests.integration.test_import_http import upload
    case = make_case(tmp_path)
    raw = b'# Ordinary learner Import\n\nOriginal bytes.\n'
    staged = upload(case.client, case.app.state.settings, raw)
    assert ImportWorker(case.app.state.database).run_once() is True
    preview = case.client.get('/api/v1/imports/'+staged['import_id'])
    assert preview.status_code == 200
    draft = case.client.get('/api/v1/drafts/'+preview.json()['preview_refs'][0])
    assert draft.status_code == 200
    source = case.client.get('/api/v1/sources/'+draft.json()['payload']['source_id'])
    assert source.status_code == 200
    changed = case.client.post('/api/v1/session/role', json={'role':'learner'},
        headers={**case.headers, 'Idempotency-Key':'ordinary-learner'})
    assert changed.status_code == 200
    before = case.dump()
    downloaded = case.client.get(source.json()['artifact']['download_path'])
    assert downloaded.status_code == 200 and downloaded.content == raw
    assert case.dump() == before
