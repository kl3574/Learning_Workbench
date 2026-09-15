"""Real forward migration and consumer ownership; no legacy history replacement."""

import sqlite3

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.retrieval import RetrievalService
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.retrieval_repository import RetrievalInvalidation
from services.api.app.infrastructure.security import SessionIdentity


def material(identifier='retrieval_migration_block'):
    body = '迁移保留的公开正文。'.encode()
    return dm.ContentBlock(id=identifier, revision=1, kind='text', title='未审迁移材料',
        body_path=f'content/{identifier}.md', body_sha256=sha256_bytes(body)), body


def test_forward_migration_preserves_content_outbox_and_exact_backup(tmp_path):
    class Previous(Database):
        def migration_files(self):
            return [path for path in super().migration_files() if path.name < '0011_']

    old = Previous(Settings(data_dir=tmp_path / 'data'))
    workspace = old.initialize()
    block, body = material()
    ContentService(old).publish(workspace, [block], {block.body_path: body})
    with old.connect() as conn:
        tables = ('objects', 'revisions', 'block_bodies', 'content_blobs', 'outbox', 'jobs', 'job_events')
        before = {name: [tuple(row) for row in conn.execute(f'SELECT * FROM {name}')] for name in tables}
        migrations = [tuple(row) for row in conn.execute('SELECT * FROM schema_migrations ORDER BY version')]
    current = Database(old.settings)
    assert current.initialize() == workspace
    with current.connect() as conn:
        for name in tables:
            assert [tuple(row) for row in conn.execute(f'SELECT * FROM {name}')] == before[name]
        assert [tuple(row) for row in conn.execute("SELECT * FROM schema_migrations WHERE version<'0011_' ORDER BY version")] == migrations
        assert conn.execute('SELECT count(*) FROM retrieval_scopes').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM retrieval_generations').fetchone()[0] == 0
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    backups = list((old.settings.data_dir / 'backups').glob('*.sqlite3'))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("SELECT count(*) FROM sqlite_master WHERE name='retrieval_scopes'").fetchone()[0] == 0
        for name in tables:
            assert backup.execute(f'SELECT * FROM {name}').fetchall() == before[name]
    identity = SessionIdentity('session_synthetic_migration', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    status = RetrievalService(current).scope_status(identity, [reference(block)])
    assert status.state == 'missing' and status.index_version is None
    assert current.initialize() == workspace
    assert list((old.settings.data_dir / 'backups').glob('*.sqlite3')) == backups


def test_invalidation_rollback_and_own_consumer_leave_shared_outbox_pending(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    block, body = material()
    service = ContentService(database)
    with pytest.raises(RuntimeError, match='synthetic rollback'):
        with database.transaction() as conn:
            service.publish_in_transaction(conn, workspace, [block], {block.body_path: body})
            assert conn.execute('SELECT count(*) FROM retrieval_input_events').fetchone()[0] == 1
            raise RuntimeError('synthetic rollback')
    with database.connect() as conn:
        assert conn.execute('SELECT count(*) FROM objects').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM retrieval_input_events').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM outbox').fetchone()[0] == 0
    service.publish(workspace, [block], {block.body_path: body})
    with database.transaction() as conn:
        before = [tuple(row) for row in conn.execute('SELECT * FROM outbox')]
        assert before and all(row[3] is None for row in before)
        consumer = RetrievalInvalidation(conn, workspace)
        assert consumer.consume_one()
        assert not consumer.consume_one()
        assert [tuple(row) for row in conn.execute('SELECT * FROM outbox')] == before
        assert conn.execute('SELECT count(*) FROM retrieval_scopes').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM jobs').fetchone()[0] == 0
