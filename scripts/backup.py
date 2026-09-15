"""Create an online database/blob backup locally; restore workflows belong to M7.

Never copies arbitrary data-directory files, provider keys, or live sessions.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def create_backup(settings) -> Path:
    from services.api.app.application.provider_backup import sanitize_provider_backup
    from services.api.app.database import Database

    database = Database(settings)
    if not database.path.is_file():
        raise ValueError("Workspace has not been initialized. Start the local application first.")
    destination = settings.data_dir / "backups"
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(destination, 0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = destination / f"workspace-{stamp}-{uuid4().hex[:12]}.zip"
    with tempfile.TemporaryDirectory(prefix="backup-staging-", dir=destination) as temporary:
        staging = Path(temporary)
        snapshot = database.online_backup(staging / "workspace.sqlite3")
        with closing(sqlite3.connect(snapshot)) as connection:
            # The copied database can retain WAL mode. Scrub this isolated copy
            # with a rollback journal so the archived .db contains the scrub.
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.row_factory = sqlite3.Row
            blobs = connection.execute("SELECT sha256,relative_path,size FROM content_blobs").fetchall()
            migrations = [dict(row) for row in connection.execute("SELECT * FROM schema_migrations ORDER BY version")]
            for row in connection.execute("SELECT config_json FROM provider_configs"):
                config = json.loads(row[0])
                if {"secret", "api_key", "token", "authorization"} & set(config):
                    raise ValueError("Provider metadata contains a secret-like field; backup stopped.")
            connection.execute("BEGIN IMMEDIATE")
            provider_backup = sanitize_provider_backup(connection, live_database_path=database.path)
            connection.execute("UPDATE reviews SET reviewer_session_id=NULL")
            connection.execute("UPDATE approvals SET actor_session_id=NULL")
            connection.execute("DELETE FROM local_sessions")
            connection.execute("DELETE FROM bootstrap_codes")
            connection.execute("DELETE FROM idempotency")
            connection.commit()
            # VACUUM removes authentication material from SQLite free pages.
            connection.execute("VACUUM")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or connection.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Sanitized backup database failed integrity verification")
            counts = {row[0]: connection.execute('SELECT count(*) FROM "' + row[0].replace('"', '""') + '"').fetchone()[0]
                      for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'fts_%'")}
        payloads = {"workspace.sqlite3": snapshot.read_bytes()}
        for blob in blobs:
            relative = PurePosixPath(blob["relative_path"])
            target = settings.data_dir / str(relative)
            expected_parts = ("blobs", blob["sha256"][:2], blob["sha256"])
            if relative.parts != expected_parts or not target.resolve().is_relative_to(settings.data_dir.resolve()):
                raise ValueError("Blob manifest contains an unsafe path")
            walk = settings.data_dir
            for part in relative.parts:
                walk = walk / part
                if walk.is_symlink():
                    raise ValueError("Blob manifest cannot follow symbolic links")
            data = target.read_bytes()
            if len(data) != blob["size"] or hashlib.sha256(data).hexdigest() != blob["sha256"]:
                raise ValueError("Blob integrity mismatch; backup stopped")
            payloads["blobs/" + blob["sha256"]] = data
        manifest = {"format": "learning-workbench-backup", "schema_version": "3.0.0", "profile": "full_backup",
                    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "sensitive_personal_data": True, "migrations": migrations, "object_counts": counts,
                    "excluded": ["provider_secrets", "provider_secret_locators", "provider_hmac_material",
                                 "bootstrap_codes", "local_sessions", "idempotency_replays"],
                    "consent_dispatch_disabled": True, "provider_backup": provider_backup,
                    "restore_acceptance": "NOT_RUN",
                    "files": [{"path": path, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                              for path, data in sorted(payloads.items())]}
        partial = staging / "archive.zip"
        with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for path, data in payloads.items():
                output.writestr(path, data)
            output.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode())
        with zipfile.ZipFile(partial) as readback:
            for entry in manifest["files"]:
                if hashlib.sha256(readback.read(entry["path"])).hexdigest() != entry["sha256"]:
                    raise ValueError("Backup archive readback failed")
        os.chmod(partial, 0o600)
        with partial.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(partial, archive)
        descriptor = os.open(destination, os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return archive


if __name__ == "__main__":
    from services.api.app.config import Settings

    result = create_backup(Settings.from_env())
    print("Sensitive local backup created; do not publish: " + str(result))
    print("Database/blob hashes verified. M7 restore preview and recovery acceptance have not been completed.")
