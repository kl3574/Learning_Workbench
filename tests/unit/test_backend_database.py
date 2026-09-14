import shutil
import sqlite3

import pytest

from services.api.app.config import REPOSITORY_ROOT, Settings
from services.api.app.database import Database, MigrationError
from services.api.app.idempotency import execute_idempotent


def make_database(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    shutil.copyfile(REPOSITORY_ROOT / "migrations/0001_baseline.sql", migrations / "0001_baseline.sql")
    settings = Settings(data_dir=tmp_path / "data", migrations_dir=migrations)
    database = Database(settings)
    database.initialize()
    return database, migrations


def test_each_connection_enforces_wal_foreign_keys_and_ten_second_budget(tmp_path):
    database, _ = make_database(tmp_path)
    for _ in range(2):
        with database.connect() as connection:
            assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 10000
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO bootstrap_codes VALUES('hash','missing_workspace','2099-01-01T00:00:00Z',NULL)")


def test_repeat_startup_preserves_workspace_and_migration_receipt(tmp_path):
    database, _ = make_database(tmp_path)
    before = database.workspace_id()
    assert database.initialize() == before
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM workspace").fetchone()[0] == 1
        row = connection.execute("SELECT * FROM schema_migrations").fetchone()
        assert row["version"] == "0001_baseline" and len(row["checksum"]) == 64


def test_checksum_drift_refuses_start_without_mutation(tmp_path):
    database, migrations = make_database(tmp_path)
    old_id = database.workspace_id()
    with (migrations / "0001_baseline.sql").open("a") as stream:
        stream.write("\n-- changed after apply\n")
    with pytest.raises(MigrationError, match="checksum"):
        database.initialize()
    assert database.workspace_id() == old_id


def test_unknown_newer_schema_never_downgrades(tmp_path):
    database, _ = make_database(tmp_path)
    with database.transaction() as connection:
        connection.execute("INSERT INTO schema_migrations VALUES('0099_future','2026-09-14T00:00:00Z',?)", ("a" * 64,))
    with pytest.raises(MigrationError, match="downgrade"):
        database.initialize()
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 2


def test_forward_migration_takes_pre_migration_online_backup(tmp_path):
    database, migrations = make_database(tmp_path)
    workspace_id = database.workspace_id()
    (migrations / "0002_test.sql").write_text("CREATE TABLE migration_test(id INTEGER PRIMARY KEY);\n", encoding="utf-8")
    database.initialize()
    backups = list((database.settings.data_dir / "backups").glob("*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("SELECT id FROM workspace").fetchone()[0] == workspace_id
        assert backup.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 1
        assert backup.execute("SELECT name FROM sqlite_master WHERE name='migration_test'").fetchone() is None
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # online_backup closes its target; downstream sanitizers can switch journal mode immediately.
        assert backup.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 2


def test_failed_migration_rolls_back_ddl_and_keeps_backup(tmp_path):
    database, migrations = make_database(tmp_path)
    (migrations / "0002_failure.sql").write_text("CREATE TABLE must_rollback(id INTEGER);\nINVALID SQL;\n", encoding="utf-8")
    with pytest.raises(sqlite3.OperationalError):
        database.initialize()
    with database.connect() as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='must_rollback'").fetchone() is None
        assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 1
    assert len(list((database.settings.data_dir / "backups").glob("*.sqlite3"))) == 1


def test_online_backup_contains_committed_wal_and_rejects_overwrite(tmp_path):
    database, _ = make_database(tmp_path)
    with database.connect() as reader:
        reader.execute("BEGIN")
        reader.execute("SELECT * FROM workspace").fetchall()
        with database.transaction() as writer:
            writer.execute("UPDATE workspace SET title='已提交的 WAL 内容'")
        assert database.path.with_name(database.path.name + "-wal").exists()
        path = database.online_backup()
        with sqlite3.connect(path) as backup:
            assert backup.execute("SELECT title FROM workspace").fetchone()[0] == "已提交的 WAL 内容"
        assert path.stat().st_mode & 0o777 == 0o600
        with pytest.raises(MigrationError, match="new file"):
            database.online_backup(path)


def test_idempotent_side_effect_and_receipt_share_rollback(tmp_path):
    database, _ = make_database(tmp_path)
    with pytest.raises(RuntimeError, match="intentional"):
        with database.transaction() as connection:
            def operation():
                connection.execute("UPDATE workspace SET title='must roll back'")
                raise RuntimeError("intentional")
            execute_idempotent(connection, actor="session_test", route="test", key="key1", payload={"x": 1}, operation=operation)
    with database.connect() as connection:
        assert connection.execute("SELECT title FROM workspace").fetchone()[0] == "我的学习工作区"
        assert connection.execute("SELECT count(*) FROM idempotency").fetchone()[0] == 0
