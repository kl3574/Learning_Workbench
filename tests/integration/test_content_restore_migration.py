"""Nonempty original producer/review/publication rows survive restore migration or roll back."""
from dataclasses import replace
import shutil
import sqlite3
import pytest
from services.api.app.infrastructure.database import Database
from tests.integration.test_draft_edit_migration import previous as previous, owners
from tests.integration.test_authoring_numeric_provider_history import table_hashes


def prior(previous, tmp_path):
    _, settings, *rest = previous
    path = tmp_path / 'restore-prior'
    path.mkdir()
    for migration in settings.migrations_dir.glob('*.sql'):
        if migration.name < '0024':
            shutil.copyfile(migration, path / migration.name)
    old = Database(replace(settings, migrations_dir=path))
    old.initialize()
    return old, settings, rest


def test_nonempty_restore_migration_preserves_old_rows_rowids_and_acks(previous, tmp_path):
    old, settings, (identity, candidate, receipt, body, ref) = prior(previous, tmp_path)
    tables = ['draft_candidate_identities', 'draft_candidate_revisions', 'reviews', 'review_jobs', 'review_revisions',
        'review_artifact_bindings', 'review_commands', 'draft_publications', 'draft_publication_events', 'draft_publication_results', 'draft_publication_commands']
    with old.connect() as conn:
        original = {t:[tuple(r) for r in conn.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid')] for t in tables}
    before = table_hashes(old)
    upgraded = Database(settings)
    upgraded.initialize()
    with upgraded.connect() as conn:
        assert {t:[tuple(r) for r in conn.execute(f'SELECT rowid,* FROM {t} ORDER BY rowid')] for t in tables} == original
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    after = table_hashes(upgraded)
    assert {k:v for k,v in before.items() if k != 'schema_migrations'} == {k:after[k] for k in before if k != 'schema_migrations'}
    _, reviews, publication = owners(upgraded)
    assert reviews.read(identity, receipt.id) == receipt
    assert publication.publish(identity, candidate.draft_id, body, 'publication') == ref


@pytest.mark.parametrize('marker', ['-- RESTORE_SCHEMA_REBUILT', '-- RESTORE_HISTORY_RESTORED'])
def test_restore_migration_failure_preserves_previous_schema_and_data(previous, tmp_path, marker):
    old, settings, _ = prior(previous, tmp_path)
    migration = settings.migrations_dir / '0024_content_restore_drafts.sql'
    text = migration.read_text()
    assert marker in text
    (old.settings.migrations_dir / migration.name).write_text(text.replace(marker, marker + '\nSELECT restore_synthetic_failure();'))
    before = table_hashes(old)
    with old.connect() as conn:
        schema = [tuple(r) for r in conn.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name')]
    with pytest.raises(sqlite3.Error):
        old.initialize()
    assert table_hashes(old) == before
    with old.connect() as conn:
        assert [tuple(r) for r in conn.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name')] == schema
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
