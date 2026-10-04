"""Real backup CLI over synthetic owner history; this is not M7 restore acceptance."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import zipfile

from fastapi.testclient import TestClient

from packages.contracts import domain_models as dm
from services.api.app.application.content import ContentService
from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import COOKIE_NAME, consume_bootstrap, issue_bootstrap_code
from services.api.app.main import create_app
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_content_restore_http import approve, create
from tests.integration.test_edit_publication_http import ready
from tests.integration.test_review_http import prepared_review_http as prepared_review_http


ROOT = Path(__file__).resolve().parents[2]


def file_hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob('*')) if path.is_file() and 'backups' not in path.relative_to(directory).parts}


def cli_backup(database, temporary):
    """Only fixture data and a minimal, non-secret child environment cross this seam."""
    before = table_hashes(database)
    files_before = file_hashes(database.settings.data_dir)
    uv = shutil.which('uv')
    assert uv is not None
    result = subprocess.run(['make', 'backup', f'PY={uv} run --frozen --no-sync python'], cwd=ROOT,
        env={'PATH': '/usr/bin:/bin', 'LEARNING_DATA_DIR': str(database.settings.data_dir),
             'UV_OFFLINE': '1', 'TMPDIR': str(temporary)},
        capture_output=True, timeout=45)
    (temporary / 'backup-cli.stdout').write_bytes(result.stdout)
    (temporary / 'backup-cli.stderr').write_bytes(result.stderr)
    after = table_hashes(database)
    files_after = file_hashes(database.settings.data_dir)
    receipt = {'command': 'make backup PY=<uv> run --frozen --no-sync python',
        'exit_code': result.returncode, 'source_tables_unchanged': before == after,
        'source_files_unchanged': files_before == files_after,
        'changed_source_paths': sorted(name for name in files_before.keys() | files_after.keys()
                                       if files_before.get(name) != files_after.get(name)),
        'external_model_calls': 0, 'restore_acceptance': 'NOT_RUN'}
    (temporary / 'backup-cli-receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    assert before == after, 'backup must not change any source table'
    assert files_before == files_after, 'this quiescent fixture must keep source file bytes'
    assert result.returncode == 0, 'real backup CLI failed; original stderr remains private in pytest basetemp'
    archives = list((database.settings.data_dir / 'backups').glob('workspace-*.zip'))
    assert len(archives) == 1
    target = temporary / 'readback'
    target.mkdir()
    with zipfile.ZipFile(archives[0]) as reader:
        manifest = json.loads(reader.read('manifest.json'))
        assert manifest['restore_acceptance'] == 'NOT_RUN'
        assert set(reader.namelist()) == {'manifest.json', *(item['path'] for item in manifest['files'])}
        for item in manifest['files']:
            raw = reader.read(item['path'])
            assert len(raw) == item['size'] and hashlib.sha256(raw).hexdigest() == item['sha256']
            if item['path'] == 'workspace.sqlite3':
                (target / item['path']).write_bytes(raw)
            else:
                assert item['path'].startswith('blobs/') and item['path'].count('/') == 1
                digest = item['path'].split('/')[1]
                assert len(digest) == 64 and digest == hashlib.sha256(raw).hexdigest()
                destination = target / 'blobs' / digest[:2] / digest
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
    copied = Database(replace(database.settings, data_dir=target))
    with copied.connect() as conn:
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    return copied, manifest


def fresh_author(database):
    token, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    SessionService(database).switch_role(identity, RoleRequest(role='author'), 'read-backup-history')
    app = create_app(database.settings)
    client = TestClient(app, base_url=database.settings.origin)
    client.cookies.set(COOKIE_NAME, token)
    return replace(identity, role='author'), client


def test_actual_cli_retains_published_edit_restore_and_review_history_without_old_login(prepared_review_http, tmp_path):
    case = prepared_review_http
    base, edit_id, _, publish_body = ready(case)
    content = ContentService(case.database)
    parent = dm.Lesson(id='backup_parent', revision=1, title='Synthetic pinned parent', objectives=[], block_refs=[base])
    content.publish(case.identity.workspace_id, [parent], {})
    published = case.client.post(f'/api/v1/drafts/{edit_id}/publish', json=publish_body,
        headers=command(case.headers, 'backup-edit-publish'))
    assert published.status_code == 201
    current = dm.ContentRef.model_validate_json(published.content)
    restore_id, _, snapshot = create(case, base, current)
    restoration = approve(case, restore_id, snapshot, math='NOT_APPLICABLE')
    restored = case.client.post(f'/api/v1/drafts/{restore_id}/publish', json=restoration,
        headers=command(case.headers, 'backup-restore-publish'))
    assert restored.status_code == 201
    paths = [f'/api/v1/draft-edits/{edit_id}', f'/api/v1/content/restore-drafts/{restore_id}',
             f'/api/v1/reviews/{publish_body["review_receipt_id"]}', f'/api/v1/reviews/{restoration["review_receipt_id"]}',
             f'/api/v1/blocks/{base.id}/body?revision=1', '/api/v1/lessons/backup_parent?revision=1']
    originals = {path: case.client.get(path).content for path in paths}
    before = table_hashes(case.database)
    copied, manifest = cli_backup(case.database, tmp_path)
    copied_tables = table_hashes(copied)
    allowed = {'local_sessions', 'bootstrap_codes', 'idempotency', 'provider_backup_projections'}
    assert {name for name in before if before[name] != copied_tables[name]} <= allowed
    assert manifest['consent_dispatch_disabled'] is True
    old_cookie = TestClient(create_app(copied.settings), base_url=copied.settings.origin)
    try:
        old_cookie.cookies.update(case.client.cookies)
        assert old_cookie.get('/api/v1/session').status_code == 401
        assert old_cookie.get(paths[1]).status_code == 401
    finally:
        old_cookie.close()
    author, client = fresh_author(copied)
    try:
        assert author.id != case.identity.id
        for path, expected in originals.items():
            response = client.get(path)
            assert response.status_code == 200 and response.content == expected
        # A new actor may inspect history but does not inherit the old command key.
        response = client.post(f'/api/v1/drafts/{edit_id}/publish', json=publish_body,
            headers=command({'Origin': copied.settings.origin, 'X-CSRF-Token': author.csrf_token}, 'backup-edit-publish'))
        assert response.status_code in {409, 412}
    finally:
        client.close()
    assert table_hashes(case.database) == before
