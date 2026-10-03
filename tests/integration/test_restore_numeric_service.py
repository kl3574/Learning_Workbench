"""Actual Restore/SQLite/Jobs/Review protocol; synthetic numeric runtime is labelled.

These service cases never assert physical isolation or academic approval.
"""
from dataclasses import dataclass
import sqlite3
import pytest
from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.restore_numeric_dto import RestoreNumericCheckPreviewWrite
from tests.integration.test_authoring_http import session, command
from tests.integration.test_authoring_numeric_service import LedgerRuntime, decision
from tests.integration.test_content_restore_http import create
from tests.integration.test_authoring_numeric_provider_history import table_hashes


BODY = '😀 未审合成例题 e\u0301；原样 $x$\n输入 x = 2；公式 x * x；期望 4。\n'


def material(body=BODY):
    def span(quote):
        start = body.index(quote)
        return dict(start_codepoint=start, end_codepoint=start + len(quote), quote=quote)
    return dict(version='restore-numeric-material-v1', symbols=[dict(name='x', tex='x', domain='finite real', dimension='length')],
        plan=dict(version='finite-arithmetic-v1', seed=None, variables=[dict(name='x', value=2.0, unit='m')],
            assertions=[dict(id='square', expression='x*x', expected=4.0, atol=0.0, rtol=0.0, unit='m^2')]),
        variable_bindings=[dict(variable_name='x', value_source=span('2'))],
        assertion_bindings=[dict(assertion_id='square', expression_source=span('x * x'), expected_source=span('4'))],
        reason='明确提供合成计划；软件验收不是学术批准。')


@dataclass(repr=False)
class Case:
    database: object
    identity: object
    app: object
    client: object
    headers: dict
    identifier: str = ''
    snapshot: dict | None = None
    request: object = None
    block: object = None
    current: object = None

    @property
    def service(self):
        return self.app.state.restore_numeric_service


@pytest.fixture
def restored(tmp_path):
    case = Case(*session(tmp_path))
    raw = BODY.encode()
    block = dm.ContentBlock(id='restore_numbers', revision=1, kind='worked_example', title='Synthetic numeric original',
        body_path='content/restore_numbers.md', body_sha256=sha256_bytes(raw), concepts=[], citations=[], depends_on=[])
    content = ContentService(case.database)
    old = content.publish(case.identity.workspace_id, [block], {block.body_path: raw})[0]
    current = content.publish(case.identity.workspace_id, [block.model_copy(update={'revision': 2, 'title': 'Current distinct title'})], {block.body_path: raw})[0]
    case.identifier, _, case.snapshot = create(case, old, current)
    case.block, case.current = block, current
    case.request = RestoreNumericCheckPreviewWrite.model_validate(dict(candidate=case.snapshot['candidate'], material=material()))
    case.service.runtime = LedgerRuntime()
    try:
        yield case
    finally:
        case.client.close()


def preview(case, key='preview'):
    return case.service.preview(case.identity, case.identifier, case.request, key)


def test_preview_discovery_is_exact_zero_execution_and_replay_is_original(restored, monkeypatch):
    case = restored
    import subprocess
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('preview must not spawn'))
    before = table_hashes(case.database)
    view = preview(case)
    assert view.owner == 'authoring_restore' and view.job is view.result is None
    stable = table_hashes(case.database)
    assert stable != before
    read = case.client.get('/api/v1/content/restore-drafts/' + case.identifier)
    assert read.status_code == 200, read.text
    assert read.json()['numeric_material']['material'] == material()
    assert read.json()['body_markdown'] == BODY
    assert read.json()['candidate'] == case.snapshot['candidate']
    assert read.json()['numeric_check_ids'] == [view.id]
    assert case.service.read(case.identity, view.id) == view
    assert preview(case) == view
    assert table_hashes(case.database) == stable
    ack = case.service.decide(case.identity, view.id, decision(view, 'decline'), 'decline')
    assert ack.job is None and ack.revision == 2
    assert preview(case) == view
    assert case.service.read(case.identity, view.id).decision == 'decline'


def test_approval_job_safe_control_and_restart(restored):
    case = restored
    view = preview(case)
    ack = case.service.decide(case.identity, view.id, decision(view), 'approve')
    assert ack.job.status == 'queued' and ack.applied
    assert case.service.decide(case.identity, view.id, decision(view), 'approve') == ack
    with pytest.raises(ApiError) as error:
        case.service.decide(case.identity, view.id, decision(view), 'another')
    assert error.value.code == 'NUMERIC_DECISION_EXISTS'
    listed = case.client.get('/api/v1/authoring/jobs')
    assert listed.status_code == 200, listed.text
    assert ack.job.id in [item['id'] for item in listed.json()['items']]
    safe = case.client.get('/api/v1/jobs/' + ack.job.id)
    assert safe.status_code == 200 and BODY not in safe.text and 'plan' not in safe.text
    from services.api.app.main import create_app
    restarted = create_app(case.database.settings)
    assert restarted.state.restore_numeric_service.read(case.identity, view.id).job.id == ack.job.id
    cancelled = case.client.post(f'/api/v1/jobs/{ack.job.id}/cancel', json={'expected_revision': 1}, headers=command(case.headers, 'cancel'))
    assert cancelled.status_code == 200, cancelled.text
    result = case.service.read(case.identity, view.id)
    assert result.result.outcome == 'cancelled' and result.result.started_at is None
    assert result.job.status == 'cancelled'


@pytest.mark.parametrize('fault', ['codepoint', 'quote', 'expected', 'lexical', 'expression'])
def test_unverifiable_material_rejects_without_binding(restored, fault):
    case = restored
    body = case.request.model_dump(mode='json')
    if fault == 'codepoint':
        body['material']['variable_bindings'][0]['value_source']['start_codepoint'] += 1
        body['material']['variable_bindings'][0]['value_source']['end_codepoint'] += 1
    elif fault == 'quote':
        body['material']['variable_bindings'][0]['value_source']['quote'] = '3'
    elif fault == 'expected':
        body['material']['plan']['assertions'][0]['expected'] = 5.0
    elif fault == 'lexical':
        span = body['material']['variable_bindings'][0]['value_source']
        span.update(start_codepoint=span['start_codepoint'] - 1, quote=' 2')
    else:
        body['material']['plan']['assertions'][0]['expression'] = '__import__("os")'
    request = RestoreNumericCheckPreviewWrite.model_validate(body)
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as error:
        case.service.preview(case.identity, case.identifier, request, 'bad')
    assert error.value.code == 'NUMERIC_PLAN_UNSUPPORTED'
    assert table_hashes(case.database) == before


def test_material_immutable_and_current_race_keep_original_ack(restored):
    case = restored
    view = preview(case)
    body = case.request.model_dump(mode='json')
    body['material']['reason'] += ' 改变'
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as error:
        case.service.preview(case.identity, case.identifier, RestoreNumericCheckPreviewWrite.model_validate(body), 'different')
    assert error.value.code == 'RESTORE_NUMERIC_MATERIAL_CONFLICT' and table_hashes(case.database) == before
    ContentService(case.database).publish(case.identity.workspace_id, [case.block.model_copy(update={'revision': 3})], {case.block.body_path: BODY.encode()})
    assert preview(case) == view
    with pytest.raises(ApiError) as error:
        preview(case, 'new')
    assert error.value.status == 412
    with pytest.raises(ApiError) as error:
        case.service.decide(case.identity, view.id, decision(view), 'approve')
    assert error.value.status == 412
    assert case.service.decide(case.identity, view.id, decision(view, 'decline'), 'decline').job is None


@pytest.mark.parametrize('table', ['materials', 'heads', 'events', 'checks', 'commands', 'jobs'])
def test_restore_numeric_immutable_rows_reject_replace_delete_and_update(restored, table):
    case = restored
    view = preview(case)
    case.service.decide(case.identity, view.id, decision(view), 'approve')
    name = 'restore_numeric_' + table
    with case.database.transaction() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(f'INSERT OR REPLACE INTO {name} SELECT * FROM {name}')
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(f'DELETE FROM {name}')
        column = 'sequence' if table == 'heads' else 'workspace_id'
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(f'UPDATE {name} SET {column}={column}')
    assert case.service.read(case.identity, view.id).decision == 'approve_once'


def test_expiry_runtime_changed_old_ack_and_preview_quota(restored, monkeypatch):
    case = restored
    first = preview(case)
    from services.api.app.application import restore_numeric_service as service_module
    from services.api.app.infrastructure import restore_numeric_repository as repo_module
    monkeypatch.setattr(service_module, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    monkeypatch.setattr(repo_module, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    assert case.service.read(case.identity, first.id).expired
    with pytest.raises(ApiError) as error:
        case.service.decide(case.identity, first.id, decision(first), 'expired')
    assert error.value.code == 'NUMERIC_APPROVAL_EXPIRED'
    ack = case.service.decide(case.identity, first.id, decision(first, 'decline'), 'decline')
    case.service.runtime.changed = True
    assert case.service.decide(case.identity, first.id, decision(first, 'decline'), 'decline') == ack
    assert preview(case) == first
    monkeypatch.undo()
    for index in range(1, 100):
        preview(case, f'preview_{index}')
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as error:
        preview(case, 'over_limit')
    assert error.value.status == 413 and error.value.code == 'NUMERIC_PREVIEW_LIMIT'
    assert preview(case) == first and table_hashes(case.database) == before
    assert len(case.app.state.content_restore_service.read(case.identity, case.identifier).numeric_check_ids) == 100
