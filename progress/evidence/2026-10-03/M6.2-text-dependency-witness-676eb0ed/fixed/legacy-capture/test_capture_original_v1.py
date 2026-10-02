"""Private original-316 capture only; synthetic HTTP/SQLite, no server/model/key reads."""
import hashlib
import json
from pathlib import Path

from packages.contracts.canonical import canonical_bytes
from tests.integration.test_edit_publication_http import prepared_review_http as prepared_review_http, ready
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_edit_publication_dependencies import source, draft

OUTPUT = Path(__file__).parent / 'captured'
SOURCE = '316bf693e52f1ca08a675fc7671f4d9cebad3e8b'


def store(directory, name, raw):
    assert isinstance(raw, bytes)
    assert not any(marker in raw.lower() for marker in (b'csrf_token', b'x-csrf', b'cookie', b'bootstrap='))
    path = directory / name
    path.write_bytes(raw)
    return {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def extract(case, label, identifier, publish_response=None):
    destination = OUTPUT / label
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {'source_commit': SOURCE, 'synthetic': True, 'draft_id': identifier,
                'workspace_id': case.identity.workspace_id, 'versions': [], 'commands': [], 'files': []}
    with case.database.connect() as connection:
        versions = connection.execute('SELECT * FROM draft_edit_versions WHERE draft_id=? ORDER BY revision', (identifier,)).fetchall()
        commands = connection.execute('SELECT * FROM draft_edit_commands WHERE draft_id=? ORDER BY revision', (identifier,)).fetchall()
        results = connection.execute('SELECT r.* FROM draft_publication_results r JOIN draft_publications p ON p.id=r.publication_id WHERE p.draft_id=?', (identifier,)).fetchall()
    assert len(versions) == len(commands) == 2
    before = table_hashes(case.database)
    for row in versions:
        raw = row['record_json'].encode('utf-8')
        assert canonical_bytes(json.loads(raw)) == raw
        assert hashlib.sha256(raw).hexdigest() == row['record_sha256']
        info = store(destination, f'version-r{row["revision"]}.json', raw)
        manifest['files'].append(info)
        manifest['versions'].append({key: row[key] for key in ('revision', 'candidate_sha256', 'record_sha256', 'parent_sha256')})
    for row in commands:
        raw = row['record_json'].encode('utf-8')
        assert canonical_bytes(json.loads(raw)) == raw
        assert hashlib.sha256(raw).hexdigest() == row['record_sha256']
        data = json.loads(raw)
        manifest['files'].append(store(destination, f'command-r{row["revision"]}.json', raw))
        method, route = row['route'].split(' ', 1)
        response = case.client.request(method, '/api/v1' + route, json=data['request'], headers=command(case.headers, row['command_key']))
        assert response.status_code == (201 if method == 'POST' else 200)
        assert response.json() == data['ack']
        manifest['files'].append(store(destination, f'http-{method.lower()}-ack.bin', response.content))
        manifest['commands'].append({'revision': row['revision'], 'route': row['route'], 'command_key': row['command_key'], 'record_sha256': row['record_sha256'], 'http_status': response.status_code})
    assert len(results) == (1 if publish_response is not None else 0)
    if results:
        raw = results[0]['record_json'].encode('utf-8')
        assert canonical_bytes(json.loads(raw)) == raw
        assert hashlib.sha256(raw).hexdigest() == results[0]['sha256']
        manifest['files'].append(store(destination, 'publication-record.json', raw))
        manifest['publication'] = {'record_sha256': results[0]['sha256'], 'publication_id': results[0]['publication_id']}
        manifest['files'].append(store(destination, 'http-publication-ack.bin', publish_response.content))
    assert table_hashes(case.database) == before
    (destination / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')


def test_capture_genuine_empty_dependency_v1_published_history(prepared_review_http):
    case = prepared_review_http
    base, identifier, _, body = ready(case)
    result = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=body, headers=command(case.headers, 'publish-edit'))
    assert result.status_code == 201
    assert result.json()['id'] == base.id and result.json()['revision'] == 2
    replay = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=body, headers=command(case.headers, 'publish-edit'))
    assert replay.status_code == 201 and replay.content == result.content
    extract(case, 'empty-dependencies-published', identifier, result)


def test_capture_genuine_no_witness_dependency_v1_history(prepared_review_http):
    case = prepared_review_http
    _, _, base, _, ordered, _ = source(case)
    identifier, _, _, _, _, snapshot = draft(case, base)
    assert len(ordered) == 2 and snapshot['state'] == 'draft'
    extract(case, 'dependencies-no-witness-unpublished', identifier)
