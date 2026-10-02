"""Real HTTP composition/restart with controlled original Provider and synthetic ledger."""
from dataclasses import replace

from fastapi.testclient import TestClient
from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.security import COOKIE_NAME, consume_bootstrap, issue_bootstrap_code
from services.api.app.main import create_app
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_single_publication import ready_single


def test_named_http_publication_then_fresh_app_get_is_no_store_readonly_and_current_guarded(tmp_path):
    case, _, _, intent = ready_single(tmp_path)
    token, learner = consume_bootstrap(case.database, issue_bootstrap_code(case.database))
    SessionService(case.database).switch_role(learner, RoleRequest(role='author'), 'http-author')
    identity = replace(learner, role='author')
    headers = {'Origin': case.database.settings.origin, 'X-CSRF-Token': identity.csrf_token}
    path = '/api/v1/authoring/drafts/' + case.candidate.draft_id
    publish_path = '/api/v1/drafts/' + case.candidate.draft_id + '/publish'
    original = case.authoring.draft(case.identity, case.candidate.draft_id)
    for restart in (False, True):
        app = create_app(case.database.settings)
        client = TestClient(app, base_url=case.database.settings.origin)
        client.cookies.set(COOKIE_NAME, token)
        try:
            before = table_hashes(case.database)
            draft = client.get(path)
            assert draft.status_code == 200 and draft.headers['cache-control'] == 'no-store'
            assert table_hashes(case.database) == before
            assert draft.json()['state'] == ('published' if restart else 'draft')
            assert (draft.json()['published_ref'] is not None) == restart
            response = client.post(publish_path, json=intent.model_dump(), headers=command(headers, 'http-publish'))
            assert response.status_code == 201, response.text
            assert response.headers['cache-control'] == 'no-store'
            result = response.json()
            current = client.get(path)
            assert current.status_code == 200 and current.json()['published_ref'] == result
            assert current.json()['payload'] == original.payload.model_dump(mode='json')
            assert current.json()['validation'] == original.validation.model_dump(mode='json')
            assert client.get('/api/v1/drafts/' + case.candidate.draft_id).status_code == 404
            body = client.get(f"/api/v1/blocks/{result['id']}/body?revision=1")
            assert body.status_code == 200 and body.content == original.payload.body_markdown.encode()
            before = table_hashes(case.database)
            refused = client.post(path + '/numeric-checks', json={'candidate': case.candidate.model_dump()},
                                  headers=command(headers, 'new-after-publication'))
            assert refused.status_code == 409 and refused.json()['error']['code'] == 'DRAFT_ALREADY_PUBLISHED'
            assert table_hashes(case.database) == before
        finally:
            client.close()
    SessionService(case.database).switch_role(identity, RoleRequest(role='learner'), 'return-to-learner')
    app = create_app(case.database.settings)
    client = TestClient(app, base_url=case.database.settings.origin)
    client.cookies.set(COOKIE_NAME, token)
    try:
        before = table_hashes(case.database)
        denied = client.get(path)
        assert denied.status_code == 403 and 'published_ref' not in denied.text
        assert original.payload.title not in denied.text
        assert table_hashes(case.database) == before
    finally:
        client.close()
