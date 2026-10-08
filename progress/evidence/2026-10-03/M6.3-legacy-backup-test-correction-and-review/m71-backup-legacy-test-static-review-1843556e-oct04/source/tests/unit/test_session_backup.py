"""Session-owned independent-copy port, transaction and non-authenticating history."""

from contextlib import closing
import os
import sqlite3

import pytest
from starlette.requests import Request

from services.api.app.application.errors import ApiError
from services.api.app.application.session_backup import sanitize_session_backup
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import (
    authenticate, consume_bootstrap, historical_session_belongs_to, issue_bootstrap_code,
)


def initialized(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'source'))
    database.initialize()
    token, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    return database, token, identity


@pytest.mark.parametrize('target', ['live', 'symlink', 'hardlink', 'memory'])
def test_session_backup_rejects_nonindependent_targets_before_any_write(tmp_path, target):
    database, _, _ = initialized(tmp_path)
    path = database.path
    if target in {'symlink', 'hardlink'}:
        path = tmp_path / 'alias.sqlite3'
        if target == 'symlink':
            path.symlink_to(database.path)
        else:
            os.link(database.path, path)
    with closing(sqlite3.connect(':memory:' if target == 'memory' else path)) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        before = '\n'.join(conn.iterdump())
        conn.execute('BEGIN IMMEDIATE')
        with pytest.raises(ApiError) as error:
            sanitize_session_backup(conn, live_database_path=database.path)
        assert (error.value.status, error.value.code) == (409, 'SESSION_BACKUP_TARGET_INVALID')
        conn.rollback()
        assert '\n'.join(conn.iterdump()) == before


def test_session_backup_requires_transaction_and_rollback_keeps_authentication(tmp_path):
    database, _, _ = initialized(tmp_path)
    snapshot = database.online_backup(tmp_path / 'copy.sqlite3')
    with closing(sqlite3.connect(snapshot)) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        before = '\n'.join(conn.iterdump())
        with pytest.raises(ApiError) as error:
            sanitize_session_backup(conn, live_database_path=database.path)
        assert error.value.code == 'TRANSACTION_REQUIRED'
        conn.execute('BEGIN IMMEDIATE')
        sanitize_session_backup(conn, live_database_path=database.path)
        conn.rollback()
        assert '\n'.join(conn.iterdump()) == before


def test_session_backup_rejects_disabled_foreign_keys_before_mutating_copy(tmp_path):
    database, _, _ = initialized(tmp_path)
    snapshot = database.online_backup(tmp_path / 'copy.sqlite3')
    with closing(sqlite3.connect(snapshot)) as conn:
        before = '\n'.join(conn.iterdump())
        conn.execute('BEGIN IMMEDIATE')
        with pytest.raises(ApiError) as error:
            sanitize_session_backup(conn, live_database_path=database.path)
        assert error.value.code == 'SESSION_BACKUP_TARGET_INVALID'
        conn.rollback()
        assert '\n'.join(conn.iterdump()) == before


def test_revoked_historical_actor_survives_but_original_cookie_never_authenticates(tmp_path):
    database, token, identity = initialized(tmp_path)
    revoked = '2020-01-01T00:00:00Z'
    with database.transaction() as conn:
        conn.execute('UPDATE local_sessions SET revoked_at=? WHERE id=?', (revoked, identity.id))
    target = tmp_path / 'readback'
    target.mkdir()
    database.online_backup(target / 'workspace.sqlite3')
    copy = Database(Settings(data_dir=target))
    with copy.transaction() as conn:
        report = sanitize_session_backup(conn, live_database_path=database.path)
        assert report['historical_actors_retained'] == 1 and report['authentication_disabled'] is True
        assert historical_session_belongs_to(conn, identity.workspace_id, identity.id)
        assert conn.execute('SELECT revoked_at FROM local_sessions').fetchone()[0] == revoked
        before = '\n'.join(conn.iterdump())
        assert sanitize_session_backup(conn, live_database_path=database.path) == report
        assert '\n'.join(conn.iterdump()) == before
        # Clearing only revocation cannot turn the exported sentinel back into a credential.
        conn.execute('UPDATE local_sessions SET revoked_at=NULL')
    request = Request({'type': 'http', 'headers': [(b'cookie', ('learning_session=' + token).encode())]})
    with pytest.raises(ApiError) as error:
        authenticate(copy, request)
    assert error.value.code == 'SESSION_REQUIRED'
