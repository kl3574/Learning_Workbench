"""Native migration and a separate sensitive backup, not a public export."""

from pathlib import Path
import sqlite3

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.consent_repository import ConsentRepository
from services.api.app.infrastructure.provider_repository import ProviderRepository
from services.api.app.provider_dto import ConsentCreate
from tests.integration.test_provider_consents import consent_setup


def test_backup_retains_original_history_and_body_but_never_revives_permission(tmp_path):
    from services.api.app.application.provider_backup import sanitize_provider_backup

    database, identity, _, service, request = consent_setup(tmp_path)
    proposal = service.preview(identity, request, 'preview')
    ack = service.grant(identity, ConsentCreate(proposal_id=proposal.id,
        proposal_sha256=proposal.proposal_sha256), 'grant')
    with database.transaction() as connection:
        original_config = ProviderRepository(connection, identity.workspace_id).config('provider_test')
        authentication_bytes = [row[0].encode() for row in connection.execute('SELECT locator FROM provider_private_references')]
        authentication_bytes += [row[0].encode() for row in connection.execute('SELECT fingerprint FROM provider_private_commands')]
        _, original_material, original_body = ConsentRepository(connection, identity.workspace_id).dispatch_material(ack.id)
        with pytest.raises(ApiError) as rejected:
            sanitize_provider_backup(connection, live_database_path=database.path)
        assert rejected.value.code == 'PROVIDER_BACKUP_TARGET_INVALID'
    backup_path = database.online_backup()
    with sqlite3.connect(backup_path, isolation_level=None) as copy:
        copy.row_factory = sqlite3.Row
        # Match the export owner's closed standalone-file boundary, not an
        # uncheckpointed WAL main file that still predates sanitization.
        assert copy.execute('PRAGMA journal_mode=DELETE').fetchone()[0] == 'delete'
        copy.execute('PRAGMA foreign_keys=ON')
        copy.execute('BEGIN IMMEDIATE')
        sanitize_provider_backup(copy, live_database_path=database.path)
        copy.commit()
        config = ProviderRepository(copy, identity.workspace_id).config('provider_test')
        assert config == original_config and config.secret_present
        repo = ConsentRepository(copy, identity.workspace_id)
        summary, material, body = repo.dispatch_material(ack.id)
        assert summary == proposal.summary and material == original_material and body == original_body
        assert copy.execute('SELECT count(*) FROM provider_private_commands').fetchone()[0] == 0
        assert copy.execute('SELECT count(*) FROM provider_private_references').fetchone()[0] == 0
        copy.execute('BEGIN IMMEDIATE')
        with pytest.raises(ApiError) as blocked:
            repo.begin_dispatch(ack.id, request.job_id, proposal.summary.input_token_assurance.request_body_sha256,
                proposal.summary.created_at)
        assert blocked.value.code == 'CONSENT_REVOKED'
        copy.rollback()
    backup_bytes = Path(backup_path).read_bytes()
    assert b'synthetic-controlled-provider-key' not in backup_bytes
    assert not any(value in backup_bytes for value in authentication_bytes), 'Export file retains excluded authentication material'
    assert service.page(identity, consent_id=ack.id).items[0].status == 'active'


def test_forward_migration_preserves_legacy_rows_without_promoting_them_to_native_grants(tmp_path):
    from services.api.app.infrastructure.config import Settings
    from services.api.app.infrastructure.database import Database, utc_now

    class PreviousSchema(Database):
        def migration_files(self):
            return [path for path in super().migration_files() if path.name < '0010_']

    old = PreviousSchema(Settings(data_dir=tmp_path / 'legacy-data'))
    workspace = old.initialize()
    with old.transaction() as conn:
        conn.execute('INSERT INTO provider_configs VALUES(?,?,1,?,?,?)',
            ('legacy_provider', workspace, '{"legacy":true}', 'synthetic_legacy_locator', utc_now()))
        conn.execute('INSERT INTO consents VALUES(?,?,?,1,?,?,?,?)',
            ('legacy_consent', workspace, 'legacy_provider', '{"legacy":true}', 'active', '2099-01-01T00:00:00Z', utc_now()))
        original_provider = tuple(conn.execute('SELECT * FROM provider_configs').fetchone())
        original_consent = tuple(conn.execute('SELECT * FROM consents').fetchone())
        old_migrations = list(conn.execute('SELECT version,checksum FROM schema_migrations ORDER BY version'))
    current = Database(old.settings)
    assert current.initialize() == workspace
    with current.transaction() as conn:
        assert tuple(conn.execute('SELECT * FROM provider_configs').fetchone()) == original_provider
        assert tuple(conn.execute('SELECT * FROM consents').fetchone()) == original_consent
        assert ProviderRepository(conn, workspace).configs() == []
        with pytest.raises(ApiError) as missing:
            ConsentRepository(conn, workspace).dispatch_material('legacy_consent')
        assert missing.value.status == 404
        assert conn.execute('SELECT COUNT(*) FROM provider_dispatches').fetchone()[0] == 0
        assert list(conn.execute("SELECT version,checksum FROM schema_migrations WHERE version<'0010_' ORDER BY version")) == old_migrations
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    backups = list((old.settings.data_dir / 'backups').glob('*.sqlite3'))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as raw:
        assert raw.execute("SELECT count(*) FROM sqlite_master WHERE name='provider_dispatches'").fetchone()[0] == 0
        assert tuple(raw.execute('SELECT * FROM consents').fetchone()) == original_consent
    assert current.initialize() == workspace
    assert len(list((old.settings.data_dir / 'backups').glob('*.sqlite3'))) == 1
