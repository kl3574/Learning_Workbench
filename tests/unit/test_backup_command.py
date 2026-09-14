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
