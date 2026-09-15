"""SQLite connections, verified forward migrations and consistent online snapshots."""

import hashlib
import os
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from packages.contracts.domain_models import WorkbenchSession

from .config import Settings
from ..serialization import canonical_json

SCHEMA_VERSION = "3.0.0"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class MigrationError(RuntimeError):
    """A safe fixed diagnostic; database paths and SQL are not public errors."""


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.data_dir / "workspace.sqlite3"

    @contextmanager
    def connect(self, *, busy_timeout_ms: int = 10_000) -> Iterator[sqlite3.Connection]:
        if type(busy_timeout_ms) is not int or not 0 <= busy_timeout_ms <= 10_000:
            raise ValueError("SQLite busy timeout must be an integer between 0 and 10000 milliseconds.")
        connection = sqlite3.connect(self.path, timeout=busy_timeout_ms / 1000, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise MigrationError("SQLite foreign keys could not be enabled.")
            if connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
                raise MigrationError("SQLite WAL could not be enabled.")
            connection.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self, *, busy_timeout_ms: int = 10_000, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        with self.connect(busy_timeout_ms=busy_timeout_ms) as connection:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def migration_files(self) -> list[Path]:
        files = sorted(self.settings.migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql"))
        if not files or files[0].name != "0001_baseline.sql":
            raise MigrationError("Baseline migration is unavailable.")
        versions = [path.name.split("_", 1)[0] for path in files]
        if len(versions) != len(set(versions)):
            raise MigrationError("Migration versions are ambiguous.")
        return files

    def pending_migrations(self, connection: sqlite3.Connection) -> list[Path]:
        files = self.migration_files()
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        rows = connection.execute("SELECT version, checksum FROM schema_migrations").fetchall() if table_exists else []
        applied = {row["version"]: row["checksum"] for row in rows}
        known = {path.stem: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
        if any(version not in known for version in applied):
            raise MigrationError("Database schema is newer or incompatible; automatic downgrade is disabled.")
        if any(checksum != known[version] for version, checksum in applied.items()):
            raise MigrationError("Applied migration checksum does not match the installed migration.")
        pending = [path for path in files if path.stem not in applied]
        if pending and any(path.stem > pending[0].stem for path in files if path.stem in applied):
            raise MigrationError("Migration history contains a gap.")
        return pending

    def online_backup(self, destination: Path | None = None) -> Path:
        directory = self.settings.data_dir / "backups"
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
        destination = destination or directory / f"database-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid4().hex}.sqlite3"
        if destination.resolve() == self.path.resolve() or destination.exists():
            raise MigrationError("Backup destination must be a new file.")
        descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            with self.connect() as source, closing(sqlite3.connect(destination)) as target:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise MigrationError("Backup integrity check failed.")
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        return destination

    def initialize(self) -> str:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.settings.data_dir, 0o700)
        if not self.path.exists():
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        os.chmod(self.path, 0o600)
        with self.transaction() as connection:
            pending = self.pending_migrations(connection)
            has_tables = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
            if pending and has_tables:
                # A separate reader snapshots committed WAL while this writer lock excludes mutation.
                self.online_backup()
            for path in pending:
                statement = ""
                for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
                    statement += line
                    if sqlite3.complete_statement(statement):
                        connection.execute(statement)
                        statement = ""
                if statement.strip() and any(not line.lstrip().startswith("--") for line in statement.splitlines() if line.strip()):
                    raise MigrationError("Incomplete migration statement.")
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at, checksum) VALUES (?, ?, ?)",
                    (path.stem, utc_now(), hashlib.sha256(path.read_bytes()).hexdigest()),
                )
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise MigrationError("Database foreign key integrity failed.")
            workspace = connection.execute("SELECT id FROM workspace ORDER BY created_at LIMIT 1").fetchone()
            if workspace:
                return str(workspace["id"])
            workspace_id = f"workspace_{uuid4().hex}"
            connection.execute(
                "INSERT INTO workspace(id,title,preferences_json,created_at) VALUES(?,?,?,?)",
                (workspace_id, "我的学习工作区", canonical_json({"language": "zh-CN", "reader_font_size": 18, "default_learning_minutes": 30, "auto_attach_current_lesson": True}), utc_now()),
            )
            connection.execute(
                "INSERT INTO workbench_sessions(workspace_id,revision,session_json,updated_at) VALUES(?,1,?,?)",
                (workspace_id, canonical_json(WorkbenchSession(revision=1).model_dump()), utc_now()),
            )
            return workspace_id

    def workspace_id(self) -> str:
        with self.connect() as connection:
            row = connection.execute("SELECT id FROM workspace ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                raise MigrationError("Workspace is not initialized.")
            return str(row["id"])
