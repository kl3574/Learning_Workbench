"""Independent temporary SQLite schema probes; no authenticated owner claim."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

source = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(source))
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from tests.integration.test_review_storage_constraints import catalog, job, insert, command, receipt, binding, artifact
from tests.integration.test_draft_candidate_migration import STAMP

out = []

def prepared(root):
    database = Database(Settings(data_dir=root / 'data', migrations_dir=source / 'migrations'))
    workspace = database.initialize()
    with database.transaction() as connection:
        candidate = catalog(connection, workspace, 'probe_draft')
        registered = job(connection, candidate, 'probe_review')
        insert(connection, 'review_jobs', registered)
        insert(connection, 'job_events', {'job_id': registered['review_id'], 'seq': 2,
            'type': 'cancelled', 'payload_json': '{}', 'occurred_at': STAMP})
    return database, registered

for event_seq in [1, 2]:
    for operation in ['DELETE', 'UPDATE']:
        with tempfile.TemporaryDirectory(prefix='review-independent-') as temporary:
            database, registered = prepared(Path(temporary))
            with database.transaction() as connection:
                insert(connection, 'review_commands', {**command(registered, 'cancel'), 'resulting_revision': 2})
            sql = ('DELETE FROM job_events WHERE seq=?' if operation == 'DELETE'
                   else 'UPDATE job_events SET seq=20 WHERE seq=?')
            try:
                with database.transaction() as connection:
                    connection.execute(sql, (event_seq,))
                result = 'ACCEPTED_ORPHAN'
            except sqlite3.IntegrityError as exc:
                result = 'REJECTED'
            with database.connect() as connection:
                out.append({'case': f'cancel-{operation.lower()}-endpoint-{event_seq}', 'result': result,
                    'retained_events': [r['seq'] for r in connection.execute('SELECT seq FROM job_events ORDER BY seq')],
                    'foreign_key_check': [tuple(r) for r in connection.execute('PRAGMA foreign_key_check')]})

with tempfile.TemporaryDirectory(prefix='review-independent-') as temporary:
    database, registered = prepared(Path(temporary))
    with database.transaction() as connection:
        connection.execute('DELETE FROM job_events WHERE seq=1')
    try:
        with database.transaction() as connection:
            insert(connection, 'review_commands', command(registered))
        result = 'ACCEPTED_ORPHAN'
    except sqlite3.IntegrityError:
        result = 'REJECTED'
    out.append({'case': 'create-missing-initial-event', 'result': result})

# Real snapshot sanitation with nonempty review history AND nonempty create/cancel commands.
with tempfile.TemporaryDirectory(prefix='review-independent-') as temporary:
    root = Path(temporary)
    database, registered = prepared(root)
    with database.transaction() as connection:
        first = receipt(connection, registered)
        insert(connection, 'review_revisions', first)
        insert(connection, 'review_commands', command(registered))
        insert(connection, 'review_commands', {**command(registered, 'cancel'), 'resulting_revision': 2})
        connection.execute('INSERT INTO local_sessions(id,workspace_id,token_hash,csrf_hash,role,expires_at) '
            "VALUES('synthetic_actor',?,?,?,'author','2099-01-01T00:00:00Z')", (registered['workspace_id'], 'c'*64, 'd'*64))
        connection.execute("UPDATE reviews SET reviewer_session_id='synthetic_actor'")
        before = [tuple(r) for r in connection.execute('SELECT * FROM review_commands')]
    snapshot = database.online_backup(root / 'copy.sqlite3')
    with closing(sqlite3.connect(snapshot)) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('UPDATE reviews SET reviewer_session_id=NULL')
        connection.execute('DELETE FROM local_sessions')
        connection.commit()
        assert connection.execute('SELECT * FROM review_commands').fetchall() == before
        assert connection.execute('SELECT receipt_json FROM reviews').fetchone()[0] == first['receipt_json']
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
    with database.connect() as connection:
        assert connection.execute('SELECT reviewer_session_id FROM reviews').fetchone()[0] == 'synthetic_actor'
    out.append({'case': 'nonempty-command-copy-sanitization', 'result': 'PASS'})
print(json.dumps({'source': str(source), 'sqlite_version': sqlite3.sqlite_version,
    'scope': 'synthetic temporary SQLite relations only, not authenticated review functionality', 'cases': out}, indent=2))
