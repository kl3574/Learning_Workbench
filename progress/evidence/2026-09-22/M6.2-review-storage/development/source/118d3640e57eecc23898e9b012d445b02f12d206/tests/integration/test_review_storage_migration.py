"""SQLite schema boundaries only; SQL fixtures do not authenticate a review."""
from contextlib import closing
import shutil
import sqlite3

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
