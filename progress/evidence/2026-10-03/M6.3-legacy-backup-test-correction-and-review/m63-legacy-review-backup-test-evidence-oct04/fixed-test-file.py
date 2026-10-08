"""SQLite schema boundaries only; SQL fixtures do not authenticate a review."""
from contextlib import closing
import json
import shutil
import sqlite3
import zipfile

import pytest

from services.api.app.infrastructure.config import REPOSITORY_ROOT, Settings
from services.api.app.infrastructure.database import Database
from tests.integration.test_draft_candidate_migration import (
    database_before_migration as before_catalog, enable_migration as enable_catalog,
    legacy_review, source_candidate,
)


MIGRATION = '0017_review_history.sql'
TABLES = ('review_jobs', 'review_revisions', 'review_artifact_bindings', 'review_commands')


def enable_migration(database):
    target = database.settings.migrations_dir / MIGRATION
    shutil.copyfile(REPOSITORY_ROOT / 'migrations' / MIGRATION, target)
    return target


def rows(connection, table):
    return [tuple(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY rowid')]


def test_upgrade_preserves_legacy_receipt_and_jobs_without_backfilling_approval(tmp_path):
    database, workspace = before_catalog(tmp_path)
    with database.transaction() as connection:
        candidate = source_candidate(connection, workspace, 'draft_legacy', 'import')
        original = legacy_review(connection, workspace, candidate)
    enable_catalog(database)
    database.initialize()
    with database.connect() as connection:
        before = {table: rows(connection, table) for table in ('reviews', 'jobs', 'job_events',
                  'draft_candidate_identities', 'draft_candidate_revisions')}
    backups_before = set((database.settings.data_dir / 'backups').glob('*.sqlite3'))
    enable_migration(database)
    assert database.initialize() == database.initialize() == workspace
    with database.connect() as connection:
        assert {table: rows(connection, table) for table in before} == before
        assert all(rows(connection, table) == [] for table in TABLES)
        assert connection.execute('SELECT receipt_json FROM reviews').fetchone()[0] == original
        assert connection.execute('SELECT count(*) FROM schema_migrations').fetchone()[0] == 17
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
    backups = set((database.settings.data_dir / 'backups').glob('*.sqlite3')) - backups_before
    assert len(backups) == 1
    with closing(sqlite3.connect(backups.pop())) as backup:
        assert {table: rows(backup, table) for table in before} == before
        assert backup.execute('SELECT count(*) FROM schema_migrations').fetchone()[0] == 16
        assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert backup.execute('PRAGMA foreign_key_check').fetchall() == []


def test_empty_install_has_no_machine_or_human_review(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    database.initialize()
    with database.connect() as connection:
        assert all(rows(connection, table) == [] for table in (*TABLES, 'reviews', 'jobs'))
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []


def test_failure_after_new_schema_rolls_back_tables_indexes_and_migration_record(tmp_path):
    database, workspace = before_catalog(tmp_path)
    with database.transaction() as connection:
        legacy_review(connection, workspace, source_candidate(connection, workspace, 'draft_legacy', 'import'))
    enable_catalog(database)
    database.initialize()
    with database.connect() as connection:
        before = {table: rows(connection, table) for table in ('reviews', 'jobs', 'schema_migrations')}
        schema = rows(connection, 'sqlite_master')
    backups_before = set((database.settings.data_dir / 'backups').glob('*.sqlite3'))
    target = enable_migration(database)
    with target.open('a') as stream:
        stream.write('\nINVALID SQL;\n')
    with pytest.raises(sqlite3.OperationalError):
        database.initialize()
    with database.connect() as connection:
        assert {table: rows(connection, table) for table in before} == before
        assert rows(connection, 'sqlite_master') == schema
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
    backups = set((database.settings.data_dir / 'backups').glob('*.sqlite3')) - backups_before
    assert len(backups) == 1
    with closing(sqlite3.connect(backups.pop())) as backup:
        assert {table: rows(backup, table) for table in before} == before
        assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_actual_backup_script_revokes_legacy_authentication_without_changing_history(tmp_path):
    from scripts.backup import create_backup

    database, workspace = before_catalog(tmp_path)
    with database.transaction() as connection:
        original = legacy_review(connection, workspace, source_candidate(connection, workspace, 'draft_legacy', 'import'))
    enable_catalog(database)
    database.initialize()
    enable_migration(database)
    database.initialize()
    # These SQL-only legacy rows exercise backup structure, not authentication
    # or a real human approval. Historical actor references must survive export.
    with database.transaction() as connection:
        actor = dict(connection.execute('SELECT * FROM local_sessions').fetchone())
        connection.execute(
            'INSERT INTO bootstrap_codes(code_hash,workspace_id,expires_at) VALUES(?,?,?)',
            ('e' * 64, workspace, actor['expires_at']),
        )
        connection.execute(
            'INSERT INTO idempotency(actor,route,key,request_sha256,result_json,created_at,expires_at) '
            'VALUES(?,?,?,?,?,?,?)',
            (actor['id'], '/synthetic-legacy-backup', 'synthetic-history-only', 'f' * 64,
             '{}', '2026-09-22T00:00:00Z', actor['expires_at']),
        )
        original_reviews = rows(connection, 'reviews')
    with database.connect() as connection:
        source_before = '\n'.join(connection.iterdump())
        assert actor['revoked_at'] is None
        assert connection.execute('SELECT count(*) FROM bootstrap_codes').fetchone()[0] == 1
        assert connection.execute('SELECT count(*) FROM idempotency').fetchone()[0] == 1
    archive = create_backup(database.settings)
    snapshot = tmp_path / 'readback.sqlite3'
    with zipfile.ZipFile(archive) as backup:
        snapshot.write_bytes(backup.read('workspace.sqlite3'))
        manifest = json.loads(backup.read('manifest.json'))
        assert manifest['restore_acceptance'] == 'NOT_RUN'
        assert manifest['session_backup']['historical_actors_retained'] == 1
        assert manifest['session_backup']['authentication_disabled'] is True
    with closing(sqlite3.connect(snapshot)) as connection:
        connection.row_factory = sqlite3.Row
        assert rows(connection, 'reviews') == original_reviews
        receipt = connection.execute('SELECT CAST(receipt_json AS BLOB),reviewer_session_id FROM reviews').fetchone()
        assert tuple(receipt) == (original.encode('utf-8'), actor['id'])
        assert connection.execute('SELECT count(*) FROM local_sessions').fetchone()[0] == 1
        copied_actor = dict(connection.execute('SELECT * FROM local_sessions').fetchone())
        assert {field: copied_actor[field] for field in ('id', 'workspace_id', 'role', 'expires_at')} == {
            field: actor[field] for field in ('id', 'workspace_id', 'role', 'expires_at')}
        assert copied_actor['token_hash'] == 'backup-disabled:' + actor['id'] != actor['token_hash']
        assert copied_actor['csrf_hash'] == 'backup-disabled' != actor['csrf_hash']
        assert copied_actor['revoked_at'] is not None
        assert connection.execute('SELECT count(*) FROM bootstrap_codes').fetchone()[0] == 0
        assert connection.execute('SELECT count(*) FROM idempotency').fetchone()[0] == 0
        assert all(rows(connection, table) == [] for table in TABLES)
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
    with database.connect() as connection:
        assert '\n'.join(connection.iterdump()) == source_before
        assert dict(connection.execute('SELECT * FROM local_sessions').fetchone()) == actor
        assert rows(connection, 'reviews') == original_reviews
