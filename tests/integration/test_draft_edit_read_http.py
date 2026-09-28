"""Exact browser read contract on real SQLite and the protected HTTP boundary."""
from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from packages.contracts.canonical import metadata_sha256, sha256_bytes
from services.api.app.application.draft_edit_models import EditDraftSnapshot
from services.api.app.main import create_app
from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.security import COOKIE_NAME, consume_bootstrap, issue_bootstrap_code
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_draft_edit_http import published_base
from tests.integration.test_edit_publication_http import ready
from tests.integration.test_review_http import prepared_review_http as prepared_review_http


def make_edit(case):
    base = published_base(case)
    created = case.client.post('/api/v1/drafts', json={
        'kind': 'block', 'base_ref': base.model_dump(mode='json'), 'title': 'Synthetic first title',
    }, headers=command(case.headers, 'read-create'))
    assert created.status_code == 201, created.text
    return base, created.json()['draft_id']


def test_exact_head_history_and_restart_read_have_no_database_writes(prepared_review_http):
    case = prepared_review_http
    base, identifier = make_edit(case)
    path = f'/api/v1/draft-edits/{identifier}'
    before = table_hashes(case.database)
    first_response = case.client.get(path)
    assert first_response.status_code == 200, first_response.text
    assert first_response.headers['cache-control'] == 'no-store'
    assert first_response.headers['vary'] == 'Cookie'
    first = EditDraftSnapshot.model_validate(first_response.json())
    assert set(first_response.json()) == {
        'owner', 'candidate', 'base_ref', 'base_material_sha256', 'payload', 'warnings', 'state'}
    assert first.owner == 'authoring_edit' and first.state == 'draft'
    assert first.candidate.draft_revision == 1 and first.base_ref == base
    assert first.payload.body_sha256 == sha256_bytes(first.payload.body_markdown.encode('utf-8'))
    assert first.candidate.candidate_sha256 == metadata_sha256(first.payload)
    assert table_hashes(case.database) == before

    changed = case.client.patch(f'/api/v1/drafts/{identifier}', json={'expected_revision': 1, 'patches': [
        {'field': 'title', 'value': 'Synthetic second title'},
        {'field': 'body_markdown', 'value': 'Synthetic second body.\n'},
    ]}, headers=command(case.headers, 'read-patch'))
    assert changed.status_code == 200, changed.text
    before = table_hashes(case.database)
    current = case.client.get(path)
    historical = case.client.get(path + '?revision=1')
    assert current.status_code == historical.status_code == 200
    assert current.json()['candidate']['draft_revision'] == 2
    assert current.json()['payload']['body_markdown'] == 'Synthetic second body.\n'
    assert historical.json() == first_response.json()
    assert case.client.get(path + '?revision=2').json() == current.json()
    assert case.client.get(path + '?revision=3').status_code == 412
    assert case.client.get(path + '?revision=12345678901234567').status_code == 412
    assert case.client.get(f'/api/v1/drafts/{identifier}').status_code == 404
    assert case.client.get(f'/api/v1/draft-edits/{case.candidate["draft_id"]}').status_code == 404

    fresh_app = create_app(case.database.settings)
    with TestClient(fresh_app, base_url=case.database.settings.origin) as fresh:
        fresh.cookies.update(case.client.cookies)
        owned_tables = ('draft_edit', 'draft_publication', 'content_', 'block_', 'object_')
        after_startup = {name: digest for name, digest in table_hashes(case.database).items()
                         if name.startswith(owned_tables)}
        reloaded = fresh.get(path)
        assert reloaded.status_code == 200 and reloaded.json() == current.json()
        assert {name: digest for name, digest in table_hashes(case.database).items()
                if name.startswith(owned_tables)} == after_startup


@pytest.mark.parametrize('query', [
    '?revision=0', '?revision=-1', '?revision=+1', '?revision=01', '?revision=1.0',
    '?revision=abc', '?revision=', '?revision=1&revision=1', '?unused=1',
    '?revision=1&unused=1',
])
def test_query_shape_rejects_without_mutation(prepared_review_http, query):
    case = prepared_review_http
    _, identifier = make_edit(case)
    before = table_hashes(case.database)
    response = case.client.get(f'/api/v1/draft-edits/{identifier}' + query)
    assert response.status_code == 422, response.text
    assert table_hashes(case.database) == before


def test_get_body_current_role_and_base_corruption_fail_closed(prepared_review_http):
    case = prepared_review_http
    _, identifier = make_edit(case)
    path = f'/api/v1/draft-edits/{identifier}'
    before = table_hashes(case.database)
    assert case.client.request('GET', path, content=b'not allowed').status_code == 422
    assert case.client.get('/api/v1/draft-edits/draft_unknown').status_code == 404
    assert table_hashes(case.database) == before

    changed = case.client.post('/api/v1/session/role', json={'role': 'learner'},
        headers=command(case.headers, 'read-learner'))
    assert changed.status_code == 200
    before = table_hashes(case.database)
    assert case.client.get(path).status_code == 403
    assert table_hashes(case.database) == before


def test_exact_base_body_corruption_refuses_snapshot_without_database_mutation(prepared_review_http):
    case = prepared_review_http
    base, identifier = make_edit(case)
    digest = case.app.state.draft_edit_service.read(case.identity, identifier, 1).base.metadata.body_sha256
    blob = case.database.settings.data_dir / 'blobs' / digest[:2] / digest
    blob.write_bytes(b'Synthetic corrupt bytes')
    before = table_hashes(case.database)
    response = case.client.get(f'/api/v1/draft-edits/{identifier}')
    assert response.status_code == 409 and response.json()['error']['code'] == 'CONTENT_HASH_MISMATCH'
    assert table_hashes(case.database) == before


def test_foreign_workspace_and_changed_policy_cannot_read_current_edit(prepared_review_http):
    case = prepared_review_http
    _, identifier = make_edit(case)
    path = f'/api/v1/draft-edits/{identifier}'
    token, learner = consume_bootstrap(case.database, issue_bootstrap_code(case.database))
    SessionService(case.database).switch_role(learner, RoleRequest(role='author'), 'second-author')
    foreign = replace(learner, role='author', workspace_id='workspace_foreign_edit_read')
    with case.database.transaction() as conn:
        conn.execute("INSERT INTO workspace(id,title,created_at) VALUES(?,'Synthetic other','2026-09-28T00:00:00Z')",
                     (foreign.workspace_id,))
        conn.execute('UPDATE local_sessions SET workspace_id=? WHERE id=?', (foreign.workspace_id, foreign.id))
    other = TestClient(case.app, base_url=case.database.settings.origin)
    try:
        other.cookies.set(COOKIE_NAME, token)
        before = table_hashes(case.database)
        assert other.get(path).status_code == 404
        assert table_hashes(case.database) == before
    finally:
        other.close()

    from services.api.app.application.assessment import AssessmentService
    from services.api.app.assessment_dto import AssessmentAttemptCreate
    from services.api.app.infrastructure.content_repository import reference
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture
    fixture = assessment_fixture('editreadpolicy')
    import_fixture(case.database, case.identity, fixture, 'read-policy-material')
    AssessmentService(case.database).create_attempt(case.identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode='independent'), 'read-attempt')
    before = table_hashes(case.database)
    denied = case.client.get(path)
    assert denied.status_code == 409 and denied.json()['error']['code'] == 'ASSESSMENT_ACTIVE'
    assert table_hashes(case.database) == before


def test_published_state_is_bound_to_exact_candidate_and_patch_is_terminal(prepared_review_http):
    case = prepared_review_http
    _, identifier, text, body = ready(case)
    path = f'/api/v1/draft-edits/{identifier}'
    before = table_hashes(case.database)
    draft = case.client.get(path)
    assert draft.status_code == 200 and draft.json()['state'] == 'draft'
    assert draft.json()['payload']['body_markdown'] == text
    assert table_hashes(case.database) == before
    published = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=body,
        headers=command(case.headers, 'read-publish'))
    assert published.status_code == 201, published.text
    before = table_hashes(case.database)
    current = case.client.get(path)
    original = case.client.get(path + '?revision=1')
    assert current.status_code == original.status_code == 200
    assert current.json()['state'] == 'published'
    assert original.json()['state'] == 'draft'
    assert current.json()['candidate']['draft_revision'] == 2
    assert case.client.patch(f'/api/v1/drafts/{identifier}', json={
        'expected_revision': 2, 'patches': [{'field': 'title', 'value': 'Forbidden after publication'}],
    }, headers=command(case.headers, 'read-after-publication')).status_code == 409
    assert table_hashes(case.database) == before
