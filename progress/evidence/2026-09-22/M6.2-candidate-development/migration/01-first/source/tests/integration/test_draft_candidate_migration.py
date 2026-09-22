"""Real SQLite migration tests; catalog fixtures do not authenticate owner history."""
from contextlib import closing
import json
import shutil
import sqlite3

import pytest

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.infrastructure.config import REPOSITORY_ROOT, Settings
from services.api.app.infrastructure.database import Database


MIGRATION = '0016_draft_candidate_identities.sql'
STAMP = '2026-09-22T00:00:00Z'
LEGACY_TABLES = ('drafts', 'reviews', 'authoring_candidates', 'authoring_group_candidates',
                 'authoring_content_plans', 'authoring_records', 'jobs', 'ingestion_imports', 'sources')


def encoded(value):
    return canonical_bytes(value).decode()


def database_before_migration(tmp_path):
    migrations = tmp_path / 'migrations'
    migrations.mkdir()
    for path in (REPOSITORY_ROOT / 'migrations').glob('*.sql'):
        if path.name < MIGRATION:
            shutil.copyfile(path, migrations / path.name)
    database = Database(Settings(data_dir=tmp_path / 'data', migrations_dir=migrations))
    workspace = database.initialize()
    return database, workspace


def enable_migration(database):
    target = database.settings.migrations_dir / MIGRATION
    shutil.copyfile(REPOSITORY_ROOT / 'migrations' / MIGRATION, target)
    return target


def other_workspace(connection):
    connection.execute("INSERT OR IGNORE INTO workspace(id,title,created_at) VALUES('workspace_other','other',?)", (STAMP,))
    return 'workspace_other'


def job(connection, identifier, workspace, kind):
    connection.execute(
        'INSERT INTO jobs(id,workspace_id,kind,status,revision,input_sha256,input_json,created_at,updated_at) '
        "VALUES(?,?,?,'completed',1,?,'{}',?,?)", (identifier, workspace, kind, 'a' * 64, STAMP, STAMP),
    )


def source_candidate(connection, workspace, draft_id, source_kind, *, entity=None):
    """Structural owner-table fixture only: these are not callable owner proofs."""
    entity = entity or ('concept' if source_kind == 'import' else 'block' if source_kind == 'authoring_single' else 'lesson')
    candidate = {'draft_id': draft_id, 'draft_revision': 1, 'entity': entity,
                 'candidate_sha256': sha256_bytes(draft_id.encode())}
    suffix = f'{source_kind}_{draft_id}'
    job_id = 'job_' + suffix
    job(connection, job_id, workspace, 'import' if source_kind == 'import' else 'authoring')
    if source_kind == 'import':
        source_id, import_id = 'source_' + suffix, 'import_' + suffix
        connection.execute(
            'INSERT INTO sources(id,workspace_id,media_type,title,rights,metadata_json,created_at) '
            "VALUES(?,?,'text/plain','synthetic','unknown','{}',?)", (source_id, workspace, STAMP),
        )
        connection.execute(
            'INSERT INTO ingestion_imports(id,workspace_id,source_id,job_id,input_sha256,status,preview_json,created_at) '
            "VALUES(?,?,?,?,?,'preview_ready',?,?)",
            (import_id, workspace, source_id, job_id, 'b' * 64, encoded({'draft_ids': [draft_id]}), STAMP),
        )
        payload = {'import_id': import_id, 'metadata': {'entity': entity, 'id': 'content_' + draft_id, 'revision': 1}}
        connection.execute(
            'INSERT INTO drafts(id,workspace_id,kind,revision,candidate_json,candidate_sha256,status,updated_at) '
            "VALUES(?,?,?,1,?,?,'draft',?)",
            (draft_id, workspace, entity, json.dumps(payload, indent=2), candidate['candidate_sha256'], STAMP),
        )
        return candidate
    version = 'authoring-job-v1' if source_kind == 'authoring_single' else 'authoring-group-job-v1'
    envelope = {'input': {'version': version, 'workspace_id': workspace, 'job_id': job_id},
                'view': {'summary': {'candidate': candidate}}}
    raw = encoded(envelope)
    connection.execute(
        'INSERT INTO authoring_records(job_id,workspace_id,actor_id,record_json,record_sha256) VALUES(?,?,?,?,?)',
        (job_id, workspace, 'synthetic_actor', raw, sha256_bytes(raw.encode())),
    )
    record = {'version': 'authoring-candidate-v1' if source_kind == 'authoring_single' else 'authoring-group-record-v1',
              'workspace_id': workspace, 'source_job_id': job_id, 'candidate': candidate,
              'provider_receipt_id': 'receipt_' + suffix}
    table = 'authoring_candidates'
    if source_kind == 'authoring_group':
        plan = {'workspace_id': workspace, 'source_job_id': job_id, 'provider_receipt_id': record['provider_receipt_id'],
                'plan_ref': {'source_job_id': job_id, 'plan_sha256': 'c' * 64}}
        record['plan_ref'] = plan['plan_ref']
        raw_plan = encoded(plan)
        connection.execute('INSERT INTO authoring_content_plans VALUES(?,?,?,?)',
                           (job_id, workspace, raw_plan, sha256_bytes(raw_plan.encode())))
        table = 'authoring_group_candidates'
    raw = encoded(record)
    connection.execute(f'INSERT INTO {table} VALUES(?,?,?,?,?)',
                       (draft_id, workspace, job_id, raw, sha256_bytes(raw.encode())))
    return candidate


def legacy_review(connection, workspace, candidate, *, identifier='review_original', session=True):
    session_id = 'session_' + identifier if session else None
    if session_id:
        connection.execute(
            'INSERT INTO local_sessions(id,workspace_id,token_hash,csrf_hash,role,expires_at) '
            "VALUES(?,?,?,?,'author','2099-01-01T00:00:00Z')",
            (session_id, workspace, sha256_bytes(session_id.encode()), 'd' * 64),
        )
    receipt = {'id': identifier, 'revision': 1, 'candidate': candidate, 'structural': 'NOT_RUN',
               'mathematical': 'NOT_RUN', 'sources': 'NOT_RUN', 'independent_pedagogy': 'NOT_RUN',
               'reviewer': 'synthetic historical fixture', 'created_at': STAMP, 'evidence_paths': [],
               'decision_reason': 'Preserve this historical receipt, never approve it.'}
    raw = json.dumps(receipt, indent=3, ensure_ascii=False) + '\n'
    connection.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?)',
                       (identifier, candidate['draft_id'], candidate['draft_revision'], candidate['candidate_sha256'],
                        1, raw, session_id, STAMP))
    return raw


def snapshot(connection):
    return {table: [tuple(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in LEGACY_TABLES}


def assert_rollback(database, before):
    with database.connect() as connection:
        assert snapshot(connection) == before
        assert connection.execute("SELECT count(*) FROM schema_migrations WHERE version LIKE '0016_%'").fetchone()[0] == 0
        assert connection.execute("SELECT name FROM sqlite_master WHERE name IN ('draft_candidate_identities','draft_candidate_revisions','reviews_m62')").fetchall() == []
        assert [row['table'] for row in connection.execute('PRAGMA foreign_key_list(reviews)')] == ['local_sessions', 'drafts']
    backups = sorted((database.settings.data_dir / 'backups').glob('*.sqlite3'))
    assert len(backups) == 1
    with closing(sqlite3.connect(backups[0])) as backup:
        assert snapshot(backup) == before
        assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert backup.execute('PRAGMA foreign_key_check').fetchall() == []


def test_empty_install_and_repeated_initialization(tmp_path):
    database, workspace = database_before_migration(tmp_path)
    enable_migration(database)
    assert database.initialize() == database.initialize() == workspace
    with database.connect() as connection:
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
        assert connection.execute('SELECT count(*) FROM draft_candidate_identities').fetchone()[0] == 0
        assert connection.execute('SELECT count(*) FROM schema_migrations').fetchone()[0] == 16


def test_all_owner_shapes_and_old_receipts_preserve_exact_bytes(tmp_path):
    database, workspace = database_before_migration(tmp_path)
    with database.transaction() as connection:
        candidate = source_candidate(connection, workspace, 'draft_import', 'import')
        legacy_review(connection, workspace, candidate)
        legacy_review(connection, workspace, candidate, identifier='review_second', session=False)
        source_candidate(connection, workspace, 'draft_single', 'authoring_single')
        for entity in ('lesson', 'practice_set', 'assessment'):
            source_candidate(connection, workspace, 'draft_' + entity, 'authoring_group', entity=entity)
        before = snapshot(connection)
    enable_migration(database)
    database.initialize()
    with database.connect() as connection:
        after = snapshot(connection)
        assert {k: v for k, v in after.items() if k != 'reviews'} == {k: v for k, v in before.items() if k != 'reviews'}
        assert [row[:8] for row in after['reviews']] == before['reviews']
        assert all(row[8:] == (workspace, 'import', 'concept') for row in after['reviews'])
        assert connection.execute('SELECT count(*) FROM draft_candidate_identities').fetchone()[0] == 5
        assert connection.execute('SELECT count(*) FROM draft_candidate_revisions').fetchone()[0] == 5
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
        assert {row['table'] for row in connection.execute('PRAGMA foreign_key_list(reviews)')} == {'local_sessions', 'draft_candidate_revisions'}
        assert connection.execute("SELECT count(*) FROM drafts WHERE status<>'draft'").fetchone()[0] == 0


@pytest.mark.parametrize(('left', 'right'), [('import', 'authoring_single'), ('import', 'authoring_group'),
                                           ('authoring_single', 'authoring_group')])
@pytest.mark.parametrize('cross_workspace', [False, True])
def test_global_owner_collision_rolls_back_without_selecting_a_winner(tmp_path, left, right, cross_workspace):
    database, workspace = database_before_migration(tmp_path)
    with database.transaction() as connection:
        source_candidate(connection, workspace, 'same_draft_id', left)
        source_candidate(connection, other_workspace(connection) if cross_workspace else workspace, 'same_draft_id', right)
        before = snapshot(connection)
    enable_migration(database)
    with pytest.raises(sqlite3.IntegrityError):
        database.initialize()
    assert_rollback(database, before)


@pytest.mark.parametrize('damage', ['revision', 'hash', 'receipt_id', 'receipt_entity', 'receipt_hash', 'session_workspace'])
def test_unverifiable_legacy_review_aborts_instead_of_inventing_a_revision(tmp_path, damage):
    database, workspace = database_before_migration(tmp_path)
    with database.transaction() as connection:
        candidate = source_candidate(connection, workspace, 'draft_import', 'import')
        raw = legacy_review(connection, workspace, candidate)
        if damage == 'revision':
            connection.execute('UPDATE reviews SET draft_revision=2')
        elif damage == 'hash':
            connection.execute('UPDATE reviews SET candidate_sha256=?', ('f' * 64,))
        elif damage == 'session_workspace':
            connection.execute('UPDATE local_sessions SET workspace_id=?', (other_workspace(connection),))
        else:
            receipt = json.loads(raw)
            if damage == 'receipt_id':
                receipt['id'] = 'another_review'
            elif damage == 'receipt_entity':
                receipt['candidate']['entity'] = 'question'
            else:
                receipt['candidate']['candidate_sha256'] = 'f' * 64
            connection.execute('UPDATE reviews SET receipt_json=?', (encoded(receipt),))
        before = snapshot(connection)
    enable_migration(database)
    with pytest.raises(sqlite3.IntegrityError):
        database.initialize()
    assert_rollback(database, before)


@pytest.mark.parametrize('damage', ['import_id', 'preview_membership', 'job_workspace', 'record_workspace', 'plan_workspace'])
def test_invalid_real_source_association_aborts_catalog_migration(tmp_path, damage):
    database, workspace = database_before_migration(tmp_path)
    source_kind = 'import' if damage in {'import_id', 'preview_membership'} else 'authoring_group'
    with database.transaction() as connection:
        source_candidate(connection, workspace, 'draft_source', source_kind)
        if damage == 'import_id':
            connection.execute("UPDATE drafts SET candidate_json=json_set(candidate_json,'$.import_id','missing_import')")
        elif damage == 'preview_membership':
            connection.execute("UPDATE ingestion_imports SET preview_json='{}'")
        elif damage == 'job_workspace':
            connection.execute('UPDATE jobs SET workspace_id=?', (other_workspace(connection),))
        elif damage == 'record_workspace':
            connection.execute("UPDATE authoring_group_candidates SET record_json=json_set(record_json,'$.workspace_id',?)", (other_workspace(connection),))
        else:
            connection.execute('UPDATE authoring_content_plans SET workspace_id=?', (other_workspace(connection),))
        before = snapshot(connection)
    enable_migration(database)
    with pytest.raises(sqlite3.IntegrityError):
        database.initialize()
    assert_rollback(database, before)


def test_failure_after_review_rebuild_rolls_back_schema_data_and_receipt(tmp_path):
    database, workspace = database_before_migration(tmp_path)
    with database.transaction() as connection:
        legacy_review(connection, workspace, source_candidate(connection, workspace, 'draft_import', 'import'))
        before = snapshot(connection)
    target = enable_migration(database)
    with target.open('a') as stream:
        stream.write('\nINVALID SQL;\n')
    with pytest.raises(sqlite3.OperationalError):
        database.initialize()
    assert_rollback(database, before)


@pytest.mark.parametrize(('field', 'value'), [('workspace_id', 'workspace_other'), ('owner', 'import'),
    ('entity', 'question'), ('draft_revision', 2), ('candidate_sha256', 'f' * 64), ('draft_id', 'another_draft')])
def test_review_composite_fk_rejects_each_foreign_candidate_field(tmp_path, field, value):
    database, workspace = database_before_migration(tmp_path)
    with database.transaction() as connection:
        candidate = source_candidate(connection, workspace, 'draft_single', 'authoring_single')
        other_workspace(connection)
    enable_migration(database)
    database.initialize()
    row = {'id': 'review_new', 'draft_id': candidate['draft_id'], 'draft_revision': 1,
           'candidate_sha256': candidate['candidate_sha256'], 'revision': 1, 'receipt_json': '{}',
           'reviewer_session_id': None, 'created_at': STAMP, 'workspace_id': workspace, 'owner': 'authoring', 'entity': 'block'}
    with database.transaction() as connection:
        connection.execute('INSERT INTO reviews VALUES(:id,:draft_id,:draft_revision,:candidate_sha256,:revision,:receipt_json,:reviewer_session_id,:created_at,:workspace_id,:owner,:entity)', row)
        assert connection.execute('SELECT count(*) FROM drafts').fetchone()[0] == 0
    row.update(id='review_wrong', **{field: value})
    with pytest.raises(sqlite3.IntegrityError), database.transaction() as connection:
        connection.execute('INSERT INTO reviews VALUES(:id,:draft_id,:draft_revision,:candidate_sha256,:revision,:receipt_json,:reviewer_session_id,:created_at,:workspace_id,:owner,:entity)', row)
    with database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM reviews').fetchone()[0] == 1


@pytest.mark.parametrize('table', ['draft_candidate_identities', 'draft_candidate_revisions'])
@pytest.mark.parametrize('operation', ['UPDATE', 'DELETE', 'REPLACE'])
def test_identity_rows_cannot_be_changed_or_replaced(tmp_path, table, operation):
    database, workspace = database_before_migration(tmp_path)
    with database.transaction() as connection:
        source_candidate(connection, workspace, 'draft_single', 'authoring_single')
    enable_migration(database)
    database.initialize()
    with database.connect() as connection:
        before = [tuple(row) for row in connection.execute(f'SELECT * FROM {table}')]
    statement = {'UPDATE': f'UPDATE {table} SET entity=entity', 'DELETE': f'DELETE FROM {table}',
                 'REPLACE': f'INSERT OR REPLACE INTO {table} SELECT * FROM {table}'}[operation]
    with pytest.raises(sqlite3.IntegrityError), database.transaction() as connection:
        connection.execute(statement)
    with database.connect() as connection:
        assert [tuple(row) for row in connection.execute(f'SELECT * FROM {table}')] == before


def test_sanitized_backup_can_remove_session_without_rewriting_review_receipt(tmp_path):
    database, workspace = database_before_migration(tmp_path)
    with database.transaction() as connection:
        original = legacy_review(connection, workspace, source_candidate(connection, workspace, 'draft_import', 'import'))
    enable_migration(database)
    database.initialize()
    backup_path = database.online_backup(tmp_path / 'sanitized-copy.sqlite3')
    with closing(sqlite3.connect(backup_path)) as backup:
        backup.execute('PRAGMA foreign_keys=ON')
        backup.execute('UPDATE reviews SET reviewer_session_id=NULL')
        backup.execute('DELETE FROM local_sessions')
        backup.commit()
        assert backup.execute('SELECT receipt_json,reviewer_session_id FROM reviews').fetchone() == (original, None)
        assert backup.execute('PRAGMA foreign_key_check').fetchall() == []
    with database.connect() as connection:
        assert connection.execute('SELECT receipt_json,reviewer_session_id FROM reviews').fetchone()['reviewer_session_id'] is not None


def test_revision_catalog_retains_earlier_identity_without_requiring_consecutive_numbers(tmp_path):
    database, workspace = database_before_migration(tmp_path)
    with database.transaction() as connection:
        source_candidate(connection, workspace, 'draft_import', 'import')
    enable_migration(database)
    database.initialize()
    with database.transaction() as connection:
        connection.execute('INSERT INTO draft_candidate_revisions VALUES(?,?,?,?,?,?)',
                           ('draft_import', workspace, 'import', 'concept', 3, 'e' * 64))
    with database.connect() as connection:
        assert [row[0] for row in connection.execute('SELECT draft_revision FROM draft_candidate_revisions ORDER BY draft_revision')] == [1, 3]


def test_pure_sql_catalog_does_not_claim_to_authenticate_canonical_payload_hash(tmp_path):
    database, workspace = database_before_migration(tmp_path)
    with database.transaction() as connection:
        source_candidate(connection, workspace, 'draft_import', 'import')
        connection.execute('UPDATE drafts SET candidate_sha256=?', ('0' * 64,))
    enable_migration(database)
    database.initialize()
    with database.connect() as connection:
        assert connection.execute('SELECT candidate_sha256 FROM draft_candidate_revisions').fetchone()[0] == '0' * 64
        assert connection.execute('SELECT count(*) FROM reviews').fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM drafts WHERE status='draft'").fetchone()[0] == 1
