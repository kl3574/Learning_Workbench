"""Forward upgrade preserves real prior publication bytes and rollback under enabled FKs."""

from dataclasses import replace
import shutil
import sqlite3

import pytest

from services.api.app.infrastructure.database import Database
from tests.integration.test_draft_edit_migration import previous as previous, owners
from tests.integration.test_authoring_numeric_provider_history import table_hashes

TABLES = ["draft_publications", "draft_publication_events", "draft_publication_results", "draft_publication_commands"]


def prior_schema(previous, tmp_path):
    _, settings, identity, candidate, receipt, body, ref = previous
    folder = tmp_path / "through-edit-owner"
    folder.mkdir()
    for path in settings.migrations_dir.glob("*.sql"):
        if path.name < "0020":
            shutil.copyfile(path, folder / path.name)
    database = Database(replace(settings, migrations_dir=folder))
    database.initialize()
    return database, settings, identity, candidate, receipt, body, ref


def test_nonempty_publication_rows_rowids_triggers_and_old_ack_survive_forward_upgrade(previous, tmp_path):
    old, settings, identity, candidate, receipt, body, ref = prior_schema(previous, tmp_path)
    with old.connect() as conn:
        rows = {t: [tuple(x) for x in conn.execute(f"SELECT rowid,* FROM {t} ORDER BY rowid")] for t in TABLES}
        triggers = {
            r["name"]: r["sql"]
            for r in conn.execute(
                "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name IN (?,?,?,?)", TABLES
            )
        }
    before = table_hashes(old)
    upgraded = Database(settings)
    upgraded.initialize()
    with upgraded.connect() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert rows == {t: [tuple(x) for x in conn.execute(f"SELECT rowid,* FROM {t} ORDER BY rowid")] for t in TABLES}
        current_triggers = {
            r["name"]: r["sql"]
            for r in conn.execute(
                "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name IN (?,?,?,?)", TABLES
            )
        }
        assert triggers == {name: current_triggers[name] for name in triggers}
        assert set(current_triggers) - set(triggers) == {f'{table}_no_replace' for table in TABLES}
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE draft_publication_results SET record_json='{}'")
    after = table_hashes(upgraded)
    assert {'content_impact_legacy_events', 'content_impact_snapshots',
            'content_impact_decisions', 'content_impact_decision_heads'} <= set(after) - set(before)
    # Restore copies only existing provenance identities into an independent
    # witness. All other added ledgers are empty; every prior row stays exact.
    with upgraded.connect() as conn:
        columns = 'workspace_id,block_id,block_revision,block_sha256,source_id,import_id,snapshot_sha256'
        provenance = [tuple(row) for row in conn.execute(f'SELECT {columns} FROM block_provenance ORDER BY 1,2,3,4')]
        witnesses = [tuple(row) for row in conn.execute(f'SELECT {columns} FROM block_provenance_witnesses ORDER BY 1,2,3,4')]
        assert provenance and witnesses == provenance
        assert all(conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
                   for table in set(after) - set(before) - {'block_provenance_witnesses'})
    assert {k: v for k, v in before.items() if k != "schema_migrations"} == {
        k: after[k] for k in before if k != "schema_migrations"
    }
    _, reviews, publication = owners(upgraded)
    assert reviews.read(identity, receipt.id) == receipt
    assert publication.publish(identity, candidate.draft_id, body, "publication") == ref


@pytest.mark.parametrize("location", ["after_drop", "after_copy"])
def test_migration_failure_keeps_exact_prior_rows_and_schema(previous, tmp_path, location):
    old, settings, *_ = prior_schema(previous, tmp_path)
    before = table_hashes(old)
    with old.connect() as conn:
        schema = [tuple(r) for r in conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]
    path = settings.migrations_dir / "0020_edit_publications.sql"
    text = path.read_text()
    marker = "DROP TABLE draft_publications;" if location == "after_drop" else "DROP TABLE edit_publication_copy_check;"
    text = text.replace(marker, marker + "\nSELECT synthetic_unavailable_function();", 1)
    target = old.settings.migrations_dir / path.name
    target.write_text(text)
    with pytest.raises(sqlite3.OperationalError):
        old.initialize()
    assert table_hashes(old) == before
    with old.connect() as conn:
        assert schema == [
            tuple(r) for r in conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")
        ]
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
