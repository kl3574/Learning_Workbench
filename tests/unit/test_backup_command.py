import hashlib
import json
import sqlite3
import zipfile

import pytest

from backup import create_backup
from services.api.app.config import Settings
from services.api.app.database import Database
from services.api.app.security import consume_bootstrap, issue_bootstrap_code


def test_online_backup_retains_committed_wal_and_excludes_session_material(tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    db = Database(settings)
    workspace_id = db.initialize()
    token, _ = consume_bootstrap(db, issue_bootstrap_code(db))
    (settings.data_dir / "provider.key").write_text("synthetic-key-must-never-be-copied")
    with db.connect() as source:
        source.execute("PRAGMA wal_autocheckpoint=0")
        source.execute("UPDATE workspace SET title='committed in WAL' WHERE id=?", (workspace_id,))
        archive = create_backup(settings)
    with zipfile.ZipFile(archive) as reader:
        manifest = json.loads(reader.read("manifest.json"))
        assert reader.namelist() == ["workspace.sqlite3", "manifest.json"]
        snapshot = reader.read("workspace.sqlite3")
        assert token.encode() not in snapshot
        assert b"synthetic-key-must-never-be-copied" not in snapshot
        assert hashlib.sha256(snapshot).hexdigest() == manifest["files"][0]["sha256"]
        restored = tmp_path / "check.sqlite3"
        restored.write_bytes(snapshot)
    with sqlite3.connect(restored) as connection:
        assert connection.execute("SELECT title FROM workspace").fetchone()[0] == "committed in WAL"
        assert connection.execute("SELECT count(*) FROM local_sessions").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM bootstrap_codes").fetchone()[0] == 0
    with db.connect() as original:
        assert original.execute("SELECT count(*) FROM local_sessions").fetchone()[0] == 1


@pytest.mark.parametrize("symlink", [False, True])
def test_corrupt_blob_reference_cannot_export_key_file(tmp_path, symlink):
    settings = Settings(data_dir=tmp_path / "data")
    db = Database(settings)
    db.initialize()
    secret = b"synthetic-key-for-backup-boundary"
    digest = hashlib.sha256(secret).hexdigest()
    key = settings.data_dir / "provider.key"
    key.write_bytes(secret)
    relative = "provider.key"
    if symlink:
        relative = f"blobs/{digest[:2]}/{digest}"
        link = settings.data_dir / relative
        link.parent.mkdir(parents=True)
        link.symlink_to(key)
    with db.transaction() as connection:
        connection.execute("INSERT INTO content_blobs VALUES(?,?,?,?)", (digest, relative, len(secret), "2026-09-14T00:00:00Z"))
    with pytest.raises(ValueError, match="unsafe path|symbolic links"):
        create_backup(settings)
    assert not list((settings.data_dir / "backups").glob("*.zip"))


def test_exported_zip_retains_provider_history_and_partial_artifacts_without_authentication(tmp_path):
    from packages.contracts.canonical import sha256_bytes
    from services.api.app.application.errors import ApiError
    from services.api.app.application.provider_models import CheckedProviderError, UsageSnapshot
    from services.api.app.infrastructure.consent_repository import ConsentRepository
    from services.api.app.infrastructure.database import utc_now
    from services.api.app.infrastructure.provider_repository import ProviderRepository, historical_scope_digest
    from services.api.app.provider_dto import ConsentCreate
    from tests.integration.test_provider_consents import consent_setup

    database, identity, _, service, request = consent_setup(tmp_path)
    proposal = service.preview(identity, request, 'backup-preview')
    grant = service.grant(identity, ConsentCreate(proposal_id=proposal.id,
        proposal_sha256=proposal.proposal_sha256), 'backup-grant')
    # An explicitly synthetic persisted partial result tests export, not HTTP or
    # model execution. The protocol's real transport is covered separately.
    answer, refusal = '合成个人草稿\n'.encode(), '合成部分拒答'.encode()
    with database.transaction() as connection:
        repo = ConsentRepository(connection, identity.workspace_id)
        summary, material, body = repo.dispatch_material(grant.id)
        record, created = repo.begin_dispatch(grant.id, request.job_id, sha256_bytes(body), utc_now())
        assert created
        receipt = repo.finish_dispatch(record.id, CheckedProviderError(type='error',
            error_code='PROVIDER_OUTCOME_UNKNOWN', provider_outcome='unknown', output_state='partial',
            usage=UsageSnapshot(input_tokens=None, output_tokens=None)), answer, refusal, utc_now())
        history_hash = historical_scope_digest(connection, identity.workspace_id)
        config = ProviderRepository(connection, identity.workspace_id).config('provider_test')
        authentication = [row[0].encode() for row in connection.execute('SELECT fingerprint FROM provider_private_commands')]
        authentication.extend(row[0].encode() for row in connection.execute('SELECT locator FROM provider_private_references'))
        assert authentication
    archive = create_backup(database.settings)
    with zipfile.ZipFile(archive) as reader:
        manifest = json.loads(reader.read('manifest.json'))
        assert manifest['consent_dispatch_disabled'] is True
        assert manifest['sensitive_personal_data'] is True and manifest['restore_acceptance'] == 'NOT_RUN'
        assert manifest['provider_backup']['workspaces_downgraded'] == 1
        assert all(not any(secret in reader.read(name) for secret in authentication) for name in reader.namelist())
        assert all(b'synthetic-controlled-provider-key' not in reader.read(name) for name in reader.namelist())
        assert not any('provider-secrets' in name for name in reader.namelist())
        snapshot = tmp_path / 'exported-provider.sqlite3'
        snapshot.write_bytes(reader.read('workspace.sqlite3'))
    with sqlite3.connect(snapshot) as copied:
        copied.row_factory = sqlite3.Row
        assert copied.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert copied.execute('PRAGMA foreign_key_check').fetchall() == []
        providers = ProviderRepository(copied, identity.workspace_id)
        assert providers.backup_disabled() and providers.config('provider_test') == config
        assert historical_scope_digest(copied, identity.workspace_id) == history_hash
        repo = ConsentRepository(copied, identity.workspace_id)
        assert repo.dispatch_material(grant.id) == (summary, material, body)
        assert repo.read_terminal(record.id) == receipt
        assert {row['channel']: row['bytes'] for row in copied.execute('SELECT channel,bytes FROM provider_artifacts')} == {
            'answer': answer, 'refusal': refusal}
        assert copied.execute('SELECT status FROM provider_consent_history').fetchone()[0] == 'active'
        copied.execute('BEGIN IMMEDIATE')
        with pytest.raises(ApiError) as blocked:
            repo.check_dispatch(record.id, utc_now())
        assert blocked.value.code == 'CONSENT_REVOKED'
        copied.rollback()
    with database.connect() as original:
        assert historical_scope_digest(original, identity.workspace_id) == history_hash
        assert not ProviderRepository(original, identity.workspace_id).backup_disabled()
        assert original.execute('SELECT count(*) FROM provider_private_commands').fetchone()[0] > 0
        assert original.execute('SELECT count(*) FROM local_sessions').fetchone()[0] == 1
