"""Actual HTTP, restricted worker, immutable bytes and application-lifespan recovery."""

from contextlib import contextmanager
from hashlib import sha256
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.security import COOKIE_NAME, issue_bootstrap_code
from tests.document_fixtures import (
    docx_fixture, docx_malformed_fixture, pdf_encrypted_fixture,
    pdf_malformed_fixture, pdf_scan_fixture, pdf_text_fixture,
)


@contextmanager
def application_client(settings, cookie=None):
    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        if cookie is None:
            response = client.post('/api/v1/session/bootstrap',
                json={'one_time_code': issue_bootstrap_code(app.state.database)}, headers={'Origin': settings.origin})
            assert response.status_code == 200
        else:
            client.cookies.set(COOKIE_NAME, cookie)
        yield app, client
    assert not app.state.import_worker.is_alive()


def mutation_headers(client, settings):
    response = client.get('/api/v1/session')
    assert response.status_code == 200
    return {'Origin': settings.origin, 'X-CSRF-Token': response.json()['csrf_token'], 'Idempotency-Key': uuid4().hex}


def change_role(client, settings, role):
    response = client.post('/api/v1/session/role', json={'role': role}, headers=mutation_headers(client, settings))
    assert response.status_code == 200, response.text


def staged_document(client, settings, data, kind):
    response = client.post('/api/v1/imports', data={'kind': kind},
        files={'file': ('synthetic.' + kind, data)}, headers=mutation_headers(client, settings))
    assert response.status_code == 202, response.text
    staged = response.json()
    assert staged['input_sha256'] == sha256(data).hexdigest()
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        response = client.get('/api/v1/imports/' + staged['import_id'])
        assert response.status_code == 200, response.text
        preview = response.json()
        if preview['status'] not in {'staged', 'parsing'}:
            return staged, preview
        time.sleep(0.05)
    pytest.fail('Restricted document worker did not reach a visible decision within20s')


def confirm(client, settings, preview, *, acknowledge):
    return client.post('/api/v1/imports/' + preview['id'] + '/commit', json={
        'expected_input_sha256': preview['input_sha256'],
        'accepted_warning_codes': sorted({w['code'] for w in preview['warnings'] if w['severity'] == 'warning'}) if acknowledge else [],
        'id_mapping': [],
    }, headers=mutation_headers(client, settings))


@pytest.mark.parametrize('kind,factory,visible', [
    ('pdf', pdf_text_fixture, 'PDF page two beta'),
    ('docx', docx_fixture, 'DOCX paragraph alpha'),
])
def test_document_http_preserves_locators_hashes_original_permission_and_restart(tmp_path, kind, factory, visible):
    settings = Settings(data_dir=tmp_path / 'data')
    original = factory()
    with application_client(settings) as (app, client):
        staged, preview = staged_document(client, settings, original, kind)
        assert preview['status'] == 'preview_ready', preview
        assert client.get('/api/v1/courses').json()['items'] == []
        assert confirm(client, settings, preview, acknowledge=False).status_code == 409
        drafts = []
        for id in preview['preview_refs']:
            response = client.get('/api/v1/drafts/' + id)
            assert response.status_code == 200, response.text
            if response.json()['kind'] == 'block':
                drafts.append(response.json())
        assert drafts
        text = '\n'.join(draft['payload']['body_markdown'] for draft in drafts)
        assert visible in text and 'Cell A' in text and 'Cell B' in text
        assert '\\frac' not in text and '<m:oMath' not in text
        locators = []
        for draft in drafts:
            payload = draft['payload']
            block = dm.ContentBlock.model_validate(payload['metadata'])
            assert metadata_sha256(block) == draft['candidate_sha256']
            assert sha256(payload['body_markdown'].encode()).hexdigest() == block.body_sha256
            assert block.body_sha256 != staged['input_sha256']
            assert payload['citations'] and {c['id'] for c in payload['citations']} == set(block.citations)
            for citation in payload['citations']:
                assert citation['source_sha256'] == staged['input_sha256'] and citation['verification'] == 'user_supplied'
                assert payload['source_id'] in citation['locator']
                locators.append(citation['locator'])
        if kind == 'pdf':
            assert any('pdf:page:1' in loc for loc in locators)
            assert any('pdf:page:2' in loc for loc in locators)
        else:
            assert all('docx:' in loc and 'word/document.xml' in loc for loc in locators)
            assert all('pdf:page:' not in loc for loc in locators)
            assert any('tbl' in loc or 'table' in loc for loc in locators)
        source_path = '/api/v1/sources/' + drafts[0]['payload']['source_id']
        if kind == 'docx':
            assert client.get(source_path).status_code == 403
            assert client.get('/api/v1/drafts/' + drafts[0]['id']).status_code == 200
            change_role(client, settings, 'author')
        source_response = client.get(source_path)
        assert source_response.status_code == 200, source_response.text
        source = source_response.json()
        assert source['sha256'] == staged['input_sha256'] and source['size'] == len(original)
        artifact = source['artifact']
        download = client.get(artifact['download_path'])
        assert download.content == original and download.headers['etag'] == '"' + staged['input_sha256'] + '"'
        assert download.headers['content-type'] == 'application/octet-stream'
        assert download.headers['content-disposition'].startswith('attachment;')
        if kind == 'docx':
            change_role(client, settings, 'learner')
            assert client.get(artifact['download_path']).status_code == 403
        accepted = confirm(client, settings, preview, acknowledge=True)
        assert accepted.status_code == 200, accepted.text
        refs = accepted.json()['course_refs']
        assert refs
        for draft in drafts:
            block = draft['payload']['metadata']
            response = client.get(f"/api/v1/blocks/{block['id']}/body?revision={block['revision']}")
            assert response.status_code == 200 and response.text == draft['payload']['body_markdown']
        cookie = client.cookies[COOKIE_NAME]
        with app.state.database.connect() as connection:
            assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
            assert connection.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND type IN ('completed','cancelled','failed')", (staged['job']['id'],)).fetchone()[0] == 1
    # First application's lifespan and worker have ended before the second begins.
    with application_client(settings, cookie) as (_, restarted):
        assert restarted.get('/api/v1/imports/' + preview['id']).json()['status'] == 'committed'
        assert restarted.get('/api/v1/jobs/' + staged['job']['id']).json()['result_refs'] == refs
        for draft in drafts:
            assert restarted.get('/api/v1/drafts/' + draft['id']).json()['payload']['citations'] == draft['payload']['citations']
        if kind == 'docx':
            assert restarted.get(artifact['download_path']).status_code == 403
            change_role(restarted, settings, 'author')
        assert restarted.get(artifact['download_path']).content == original


@pytest.mark.parametrize('kind,factory,scan', [
    ('pdf', pdf_scan_fixture, True), ('pdf', pdf_malformed_fixture, False),
    ('pdf', pdf_encrypted_fixture, False), ('docx', docx_malformed_fixture, False),
])
def test_failed_documents_report_safe_failure_and_retain_exact_original_without_formal_content(tmp_path, kind, factory, scan):
    settings = Settings(data_dir=tmp_path / 'data')
    original = factory()
    with application_client(settings) as (app, client):
        staged, preview = staged_document(client, settings, original, kind)
        assert preview['status'] == 'failed', preview
        assert preview['preview_refs'] == []
        denied = confirm(client, settings, preview, acknowledge=True)
        assert denied.status_code == (403 if kind == 'docx' else 409), denied.text
        job = client.get('/api/v1/jobs/' + staged['job']['id']).json()
        assert job['status'] == 'failed' and job['result_refs'] == []
        assert job['error']['code'] != 'IMPORT_PARSE_FAILED', job
        assert not any(part in job['error']['message'] for part in ['Traceback', str(tmp_path), 'synthetic-password'])
        if scan:
            assert any('OCR' in warning['message'] or 'OCR' in warning['code'] for warning in preview['warnings'])
            assert any('pdf:page:1' in (warning['locator'] or '') for warning in preview['warnings'])
        with app.state.database.connect() as connection:
            row = connection.execute('SELECT source_id FROM ingestion_imports WHERE id=?', (staged['import_id'],)).fetchone()
            source_id = row['source_id']
            assert connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0] == 0
            assert connection.execute('SELECT COUNT(*) FROM revisions').fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND type IN ('completed','cancelled','failed')", (staged['job']['id'],)).fetchone()[0] == 1
        # This DB lookup is an integration audit, not a claim that failure DTOs expose source_id.
        change_role(client, settings, 'author')
        source = client.get('/api/v1/sources/' + source_id).json()
        assert client.get(source['artifact']['download_path']).content == original
        cookie = client.cookies[COOKIE_NAME]
    with application_client(settings, cookie) as (_, restarted):
        assert restarted.get('/api/v1/imports/' + staged['import_id']).json()['input_sha256'] == sha256(original).hexdigest()
        assert restarted.get('/api/v1/jobs/' + staged['job']['id']).json()['status'] == 'failed'
        assert restarted.get(source['artifact']['download_path']).content == original
        assert restarted.get('/api/v1/courses').json()['items'] == []
