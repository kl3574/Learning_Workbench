"""Actual named HTTP endpoints and SQLite, with a test-only loopback model."""
import asyncio
from dataclasses import replace

from fastapi.testclient import TestClient
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import COOKIE_NAME, consume_bootstrap, issue_bootstrap_code, expires_after
from services.api.app.main import create_app
from services.api.app.provider_dto import ProviderConfigWrite, ProviderSecretWrite
from tests.integration.test_authoring_context import request
from tests.integration.test_authoring_provider import payload
from tests.integration.test_retrieval import all_rows
from tests.provider_protocol_fixture import MODEL, local_provider, test_preparer


def session(tmp_path, preparer=None):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    database.initialize()
    token, learner = consume_bootstrap(database, issue_bootstrap_code(database))
    SessionService(database).switch_role(learner, RoleRequest(role='author'), 'author')
    identity = replace(learner, role='author')
    app = create_app(database.settings, request_preparer=preparer)
    client = TestClient(app, base_url=database.settings.origin)
    client.cookies.set(COOKIE_NAME, token)
    headers = {'Origin':database.settings.origin, 'X-CSRF-Token':identity.csrf_token}
    return database, identity, app, client, headers


def command(headers, key):
    return {**headers, 'Idempotency-Key':key}


def test_http_safe_discovery_cancel_survives_role_change_and_rejects_unknown_query(tmp_path):
    database, identity, app, client, headers = session(tmp_path)
    try:
        result = client.post('/api/v1/authoring/jobs', json=request().model_dump(mode='json'), headers=command(headers,'prepare'))
        assert result.status_code == 202, result.text
        identifier = result.json()['id']
        view = client.get('/api/v1/authoring/jobs/'+identifier)
        assert view.status_code == 200 and view.json()['summary']['job_revision'] == 1
        assert client.get('/api/v1/authoring/jobs?limit=1&limit=1').status_code == 422
        assert client.get('/api/v1/authoring/jobs?unexpected=value').status_code == 422
        assert client.get('/api/v1/authoring/jobs/'+identifier+'?revision=1').status_code == 422
        switched = client.post('/api/v1/session/role', json={'role':'learner'}, headers=command(headers,'learner'))
        assert switched.status_code == 200
        before = all_rows(database)
        assert client.get('/api/v1/authoring/jobs/'+identifier).status_code == 403
        page = client.get('/api/v1/authoring/jobs')
        assert page.status_code == 200 and len(page.json()['items']) == 1
        assert request().topic not in page.text
        assert all_rows(database) == before
        cancelled = client.post('/api/v1/jobs/'+identifier+'/cancel',json={'expected_revision':1},headers=command(headers,'cancel'))
        assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'
        assert not app.state.authoring_worker.run_once()
    finally:
        client.close()


def test_http_real_generation_separate_numeric_decisions_and_actual_environment_result(tmp_path):
    async def run():
        async with local_provider(text=canonical_bytes(payload()).decode()) as server:
            database, identity, app, client, headers = session(tmp_path, test_preparer(server.base_url))
            try:
                app.state.provider_service.secret_store.initialize()
                app.state.provider_service.save_config(identity,'test_provider',ProviderConfigWrite(expected_revision=0,
                    adapter='compatible_chat',base_url=server.base_url,model=MODEL,embedding_model=None,
                    endpoint_policy='explicit_loopback',pricing=None),'config')
                app.state.provider_service.save_secret(identity,'test_provider',ProviderSecretWrite(expected_revision=1,
                    secret='synthetic-http-authoring-key'),'secret')
                original = client.post('/api/v1/authoring/jobs',json=request().model_dump(mode='json'),headers=command(headers,'prepare'))
                assert original.status_code == 202, original.text
                job_id = original.json()['id']
                preview = client.post('/api/v1/consents/preview',json={'job_id':job_id,'expected_job_revision':1,
                    'provider_id':'test_provider','expected_provider_revision':2,'expires_at':expires_after(300),
                    'budget':{'max_input_tokens':20000,'max_output_tokens':5000,'max_provider_calls':1,
                        'max_search_calls':0,'max_tool_calls':0,'timeout_seconds':10,'max_cost_usd':None}},headers=command(headers,'preview'))
                assert preview.status_code == 201, preview.text
                grant = client.post('/api/v1/consents',json={'proposal_id':preview.json()['id'],
                    'proposal_sha256':preview.json()['proposal_sha256']},headers=command(headers,'grant'))
                assert grant.status_code == 201, grant.text
                assert await asyncio.to_thread(app.state.authoring_worker.run_once)
                generated = client.get('/api/v1/authoring/jobs/'+job_id)
                assert generated.status_code == 200, generated.text
                candidate = generated.json()['summary']['candidate']
                draft_path = '/api/v1/authoring/drafts/'+candidate['draft_id']
                draft = client.get(draft_path)
                assert draft.status_code == 200 and draft.json()['state'] == 'draft'
                assert client.get('/api/v1/drafts/'+candidate['draft_id']).status_code == 404
                preview_path = draft_path+'/numeric-checks'
                first = client.post(preview_path,json={'candidate':candidate},headers=command(headers,'numeric-preview-1'))
                assert first.status_code == 201, first.text
                assert first.json()['job'] is None and not app.state.numeric_worker.run_once()
                check_path = '/api/v1/authoring/numeric-checks/'+first.json()['id']
                declined = client.post(check_path+'/decision',json={'expected_revision':1,'operation_sha256':first.json()['operation_sha256'],
                    'decision':'decline'},headers=command(headers,'decline'))
                assert declined.status_code == 200 and declined.json()['job'] is None
                second = client.post(preview_path,json={'candidate':candidate},headers=command(headers,'numeric-preview-2'))
                assert second.status_code == 201, second.text
                second_path = '/api/v1/authoring/numeric-checks/'+second.json()['id']
                approved = client.post(second_path+'/decision',json={'expected_revision':1,'operation_sha256':second.json()['operation_sha256'],
                    'decision':'approve_once'},headers=command(headers,'approve'))
                assert approved.status_code == 202, approved.text
                safe = client.get('/api/v1/authoring/jobs').json()['items']
                assert {item['kind'] for item in safe} == {'authoring','authoring_numeric_check'}
                assert await asyncio.to_thread(app.state.numeric_worker.run_once)
                checked = client.get(second_path)
                assert checked.status_code == 200, checked.text
                result = checked.json()['result']
                # Actual trusted sandbox either evaluates the original plan or
                # reports this host's explicit isolation unavailability. The
                # latter is BLOCKED, never counted as successful arithmetic.
                assert result['outcome'] in {'passed','environment_unavailable'}, result
                assert result['verdict'] == ('PASS' if result['outcome']=='passed' else 'BLOCKED')
                assert client.get(draft_path).json()['state'] == 'draft'
                assert client.get(draft_path).json()['candidate'] == candidate
                assert len(server.requests) == 1
            finally:
                client.close()
    asyncio.run(run())
