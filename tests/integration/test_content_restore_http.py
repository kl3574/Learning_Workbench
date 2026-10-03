"""Actual Restore/Review/Content transactions. All human judgments here are synthetic."""
import sqlite3
import pytest
from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from tests.integration.test_review_http import prepared_review_http as prepared_review_http
from tests.integration.test_draft_edit_http import published_base
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes


def source(case, kind='text'):
    content = ContentService(case.database)
    if kind == 'text':
        old = published_base(case)
        block = content.read(case.identity.workspace_id, 'block', old.id, 1)
        raw = content.body(case.identity.workspace_id, old.id, 1)[0]
    else:
        raw = b'Synthetic mathematical statement; no actual academic approval.\n'
        block = dm.ContentBlock(id='restore_block', revision=1, kind=kind, title='Synthetic old kind',
            body_path='content/restore.md', body_sha256=sha256_bytes(raw), concepts=[], citations=[], depends_on=[])
        old = content.publish(case.identity.workspace_id, [block], {block.body_path: raw})[0]
    current_body = b'Synthetic current revision differs from original bytes.\n'
    current = content.publish(case.identity.workspace_id,
        [block.model_copy(update={'revision': 2, 'kind': 'summary', 'title': 'Current distinct title', 'body_sha256': sha256_bytes(current_body)})], {block.body_path: current_body})[0]
    return old, current, block, raw


def create(case, old, current, key='restore'):
    body = {'source_ref': old.model_dump(mode='json'), 'expected_current_ref': current.model_dump(mode='json'), 'reason': 'Synthetic explicit historical restoration.'}
    result = case.client.post('/api/v1/content/restore-drafts', json=body, headers=command(case.headers, key))
    assert result.status_code == 201, result.text
    identifier = result.json()['candidate']['draft_id']
    read = case.client.get('/api/v1/content/restore-drafts/' + identifier)
    assert read.status_code == 200, read.text
    return identifier, body, read.json()


def approve(case, identifier, snapshot, *, math='APPROVED', sources='APPROVED'):
    response = case.client.post(f'/api/v1/drafts/{identifier}/review', json={
        'expected_revision': 1, 'checks': ['structure', 'mathematics', 'sources'], 'reviewer_note': 'Synthetic protocol only.'},
        headers=command(case.headers, 'restore-review'))
    assert response.status_code == 202, response.text
    assert case.app.state.review_worker.run_once()
    path = '/api/v1/reviews/' + response.json()['id']
    machine = case.client.get(path)
    assert machine.status_code == 200, machine.text
    assert machine.json()['structural'] == 'PASS'
    assert machine.json()['mathematical'] == machine.json()['sources'] == 'NOT_RUN'
    human = case.client.post(path + '/decision', json={
        'expected_revision': machine.json()['revision'], 'candidate_sha256': snapshot['candidate']['candidate_sha256'],
        'mathematical': math, 'sources': sources, 'reason': 'Synthetic human intent, not mathematical validation.', 'evidence_artifact_ids': []},
        headers=command(case.headers, 'restore-human'))
    assert human.status_code == 200, human.text
    return {'expected_revision': 1, 'expected_content_sha256': snapshot['candidate']['candidate_sha256'],
        'review_receipt_id': response.json()['id'], 'acknowledged_warning_codes': sorted({w['code'] for w in snapshot['warnings'] if w['severity'] == 'warning'})}


@pytest.mark.parametrize('kind', ['text', 'theorem', 'proof'])
def test_restore_full_review_publication_restart_and_parent_pins(prepared_review_http, kind):
    case = prepared_review_http
    old, current, block, raw = source(case, kind)
    content = ContentService(case.database)
    lesson = dm.Lesson(id='restore_parent', revision=1, title='Pinned parent', objectives=[], block_refs=[old])
    parent = content.publish(case.identity.workspace_id, [lesson], {})[0]
    identifier, request, snapshot = create(case, old, current)
    assert snapshot['owner'] == 'authoring_restore' and snapshot['state'] == 'draft' and snapshot['published_ref'] is None
    assert snapshot['proposed_block'] == block.model_copy(update={'revision': 3}).model_dump(mode='json')
    before = table_hashes(case.database)
    read = case.client.get('/api/v1/content/restore-drafts/' + identifier)
    assert read.headers['cache-control'] == 'no-store' and read.json() == snapshot
    assert table_hashes(case.database) == before
    publish = approve(case, identifier, snapshot)
    result = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publish, headers=command(case.headers, 'restore-publish'))
    assert result.status_code == 201, result.text
    ref = dm.ContentRef.model_validate_json(result.content)
    assert ref.revision == 3 and ref.id == old.id and ref.sha256 != snapshot['candidate']['candidate_sha256']
    assert content.body(case.identity.workspace_id, ref.id, ref.revision)[0] == raw
    assert content.read(case.identity.workspace_id, 'block', ref.id, 3) == block.model_copy(update={'revision': 3})
    assert content.current(case.identity.workspace_id, parent.id) == parent
    assert content.read(case.identity.workspace_id, 'lesson', parent.id, 1).block_refs == [old]
    assert content.body(case.identity.workspace_id, old.id, 1)[0] == raw
    from services.api.app.main import create_app
    restarted = create_app(case.database.settings)
    restored = restarted.state.content_restore_service.read(case.identity, identifier)
    assert restored.state == 'published' and restored.published_ref == ref
    before = table_hashes(case.database)
    assert case.client.post('/api/v1/content/restore-drafts', json=request, headers=command(case.headers, 'restore')).json()['state'] == 'draft'
    assert case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publish, headers=command(case.headers, 'restore-publish')).json() == ref.model_dump(mode='json')
    assert table_hashes(case.database) == before
    provenance = case.client.get(f'/api/v1/blocks/{ref.id}?revision=3&include_provenance=true').json()
    if kind == 'text':
        assert provenance['original_source'] is not None
    else:
        assert provenance['original_source'] is None and 'PROVENANCE_UNRESOLVED' in {w['code'] for w in provenance['warnings']}
    with case.database.connect() as conn:
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        assert conn.execute("SELECT source_kind FROM draft_candidate_identities WHERE draft_id=?", (identifier,)).fetchone()[0] == 'authoring_restore'
        assert conn.execute('SELECT count(*) FROM content_impact_snapshots').fetchone()[0] >= 2
    before = table_hashes(case.database)
    with case.database.transaction() as conn:
        publication = conn.execute('SELECT id FROM draft_publications WHERE draft_id=?', (identifier,)).fetchone()[0]
        for table in ('draft_publication_events', 'draft_publication_results', 'draft_publication_commands'):
            row = tuple(conn.execute(f'SELECT * FROM {table} WHERE publication_id=? LIMIT 1', (publication,)).fetchone())
            with pytest.raises(sqlite3.IntegrityError, match='immutable'):
                conn.execute(f'INSERT OR REPLACE INTO {table} VALUES({",".join("?" for _ in row)})', row)
        row = tuple(conn.execute('SELECT * FROM draft_publication_commands WHERE publication_id=?', (publication,)).fetchone())
        with pytest.raises(sqlite3.IntegrityError, match='immutable'):
            conn.execute('INSERT OR REPLACE INTO draft_publication_commands VALUES(?,?,?,?,?)', (*row[:3], 'replacement_key', row[4]))
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('fault', ['current_race', 'denied_review', 'worked_example', 'rollback'])
def test_restore_publish_refuses_unadmitted_or_stale_and_rolls_back(prepared_review_http, monkeypatch, fault):
    case = prepared_review_http
    old, current, block, raw = source(case, 'worked_example' if fault == 'worked_example' else 'theorem')
    identifier, _, snapshot = create(case, old, current)
    publish = approve(case, identifier, snapshot, math='REJECTED' if fault == 'denied_review' else 'APPROVED')
    if fault == 'current_race':
        ContentService(case.database).publish(case.identity.workspace_id, [block.model_copy(update={'revision': 3, 'title': 'Concurrent head'})], {block.body_path: raw})
    if fault == 'rollback':
        from services.api.app.application.errors import ApiError
        from services.api.app.application.restore_publication import RestoreBlockPublication
        monkeypatch.setattr(RestoreBlockPublication, 'freeze', lambda *a: (_ for _ in ()).throw(ApiError(409, 'SYNTHETIC_FAILURE', 'Injected after Content write')))
    before = table_hashes(case.database)
    response = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publish, headers=command(case.headers, 'restore-failed'))
    assert response.status_code == (412 if fault == 'current_race' else 409), response.text
    assert table_hashes(case.database) == before
    assert case.client.get('/api/v1/content/restore-drafts/' + identifier).json()['state'] == 'draft'


@pytest.mark.parametrize('fault', ['source_body', 'source_metadata', 'source_descriptor', 'source_original', 'source_record', 'source_import'])
def test_restore_rechecks_source_corruption_on_read_and_publish(prepared_review_http, fault):
    case = prepared_review_http
    old, current, block, raw = source(case)
    identifier, _, snapshot = create(case, old, current)
    publish = approve(case, identifier, snapshot)
    with case.database.transaction() as conn:
        if fault in {'source_metadata', 'source_descriptor'}:
            table = 'revisions' if fault == 'source_metadata' else 'block_provenance'
            for trigger in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)).fetchall():
                conn.execute('DROP TRIGGER ' + trigger[0])
        if fault == 'source_metadata':
            conn.execute("UPDATE revisions SET metadata_json=json_set(metadata_json,'$.title','Corrupted') WHERE object_id=? AND revision=1", (old.id,))
        elif fault == 'source_descriptor':
            conn.execute("UPDATE block_provenance SET snapshot_sha256=? WHERE block_id=? AND block_revision=1", ('0'*64, old.id))
        elif fault == 'source_record':
            conn.execute("UPDATE sources SET metadata_json=json_set(metadata_json,'$.warnings',json('[{}]'))")
        elif fault == 'source_import':
            conn.execute("UPDATE ingestion_imports SET input_sha256=?", ('0'*64,))
        else:
            digest = block.body_sha256 if fault == 'source_body' else conn.execute('SELECT blob_sha256 FROM sources LIMIT 1').fetchone()[0]
            path = case.database.settings.data_dir / 'blobs' / digest[:2] / digest
            path.write_bytes(b'corrupted bytes')
    before = table_hashes(case.database)
    assert case.client.get('/api/v1/content/restore-drafts/' + identifier).status_code == 409
    assert case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publish, headers=command(case.headers, 'corrupt')).status_code == 409
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('fault', ['query', 'duplicate_query', 'extra', 'reason', 'bool_revision', 'same_revision', 'wrong_owner', 'get_body', 'role', 'huge_revision', 'current_hash'])
def test_restore_transport_permissions_and_identity_are_closed(prepared_review_http, fault):
    case = prepared_review_http
    old, current, _, _ = source(case, 'definition')
    identifier, body, _ = create(case, old, current)
    before = table_hashes(case.database)
    path = '/api/v1/content/restore-drafts'
    if fault in {'query', 'duplicate_query'}:
        response = case.client.post(path + ('?x=1' if fault == 'query' else '?revision=1&revision=1'), json=body, headers=command(case.headers, 'bad'))
    elif fault == 'wrong_owner':
        response = case.client.get(path + '/' + case.candidate['draft_id'])
    elif fault == 'get_body':
        response = case.client.request('GET', path + '/' + identifier, content='{}')
    elif fault == 'role':
        case.client.post('/api/v1/session/role', json={'role': 'learner'}, headers=command(case.headers, 'deny'))
        before = table_hashes(case.database)
        response = case.client.get(path + '/' + identifier)
    else:
        if fault == 'extra':
            body['claimed_approval'] = True
        if fault == 'reason':
            body['reason'] = '  '
        if fault == 'bool_revision':
            body['source_ref']['revision'] = True
        if fault == 'same_revision':
            body['source_ref'] = body['expected_current_ref']
        if fault == 'huge_revision':
            body['expected_current_ref']['revision'] = 2**100
        if fault == 'current_hash':
            body['expected_current_ref']['sha256'] = '0'*64
        response = case.client.post(path, json=body, headers=command(case.headers, 'bad'))
    assert response.status_code == {'wrong_owner':404, 'role':403, 'huge_revision':412, 'current_hash':412}.get(fault, 422), response.text
    assert table_hashes(case.database) == before


def test_restore_uses_original_concept_revision_and_explicit_dependency(prepared_review_http):
    case = prepared_review_http
    content = ContentService(case.database)
    concept = dm.Concept(id='restore_concept', revision=1, title='Original concept')
    dependency = dm.ContentBlock(id='restore_dependency', revision=1, kind='definition', title='Original dependency',
        body_path='content/dependency.md', body_sha256=sha256_bytes(b'Dependency.'))
    refs = content.publish(case.identity.workspace_id, [concept, dependency], {dependency.body_path: b'Dependency.'})
    old_block = dm.ContentBlock(id='restore_semantics', revision=1, kind='definition', title='Historical semantics',
        body_path='content/semantics.md', body_sha256=sha256_bytes(b'Original.'), concepts=[concept.id], depends_on=[refs[1]])
    old = content.publish(case.identity.workspace_id, [old_block], {old_block.body_path: b'Original.'})[0]
    current = content.publish(case.identity.workspace_id, [old_block.model_copy(update={'revision':2, 'concepts':[], 'depends_on':[]})], {old_block.body_path:b'Original.'})[0]
    content.publish(case.identity.workspace_id, [concept.model_copy(update={'revision':2, 'title':'Later different concept'})], {})
    identifier, _, snapshot = create(case, old, current)
    body = approve(case, identifier, snapshot)
    response = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=body, headers=command(case.headers, 'restore-semantic-publish'))
    assert response.status_code == 201, response.text
    with case.database.connect() as conn:
        edges = {tuple(r) for r in conn.execute('SELECT target_id,target_revision,relation FROM object_dependencies WHERE owner_id=? AND owner_revision=3', (old.id,))}
    assert edges == {(concept.id,1,'concept'), (dependency.id,1,'reference')}


def test_restore_keeps_real_grade_private_answer_note_and_index_history(prepared_review_http, monkeypatch):
    # Exercise the established full grading / note / retrieval scenario using a
    # real restore candidate and its new Review, not the ordinary Edit owner.
    from tests.integration import test_edit_publication_learning_http as flow
    case = prepared_review_http
    old, current, _, raw = source(case)
    identifier, _, snapshot = create(case, old, current)
    body = approve(case, identifier, snapshot)
    monkeypatch.setattr(flow, 'ready', lambda _: (current, identifier, raw.decode(), body))
    monkeypatch.setattr(flow, '_GRADE_HISTORY_TABLES', (*flow._GRADE_HISTORY_TABLES, 'solutions', 'responses', 'learning_events'))
    flow.test_edit_publish_keeps_old_grade_marks_note_stale_and_invalidates_index(case)


def test_restore_sql_rejects_replace_update_and_delete(prepared_review_http):
    case = prepared_review_http
    old, current, _, _ = source(case, 'theorem')
    identifier, _, _ = create(case, old, current)
    before = table_hashes(case.database)
    with case.database.transaction() as conn:
        original = tuple(conn.execute('SELECT * FROM content_restore_drafts WHERE id=?', (identifier,)).fetchone())
        for replacement in (original, ('replacement_id', *original[1:])):
            with pytest.raises(sqlite3.IntegrityError, match='restore history immutable'):
                conn.execute('INSERT OR REPLACE INTO content_restore_drafts VALUES(?,?,?,?,?,?)', replacement)
        for statement in ('UPDATE content_restore_drafts SET command_key=command_key', 'DELETE FROM content_restore_drafts'):
            with pytest.raises(sqlite3.IntegrityError, match='restore history immutable'):
                conn.execute(statement)
        original_command = tuple(conn.execute('SELECT * FROM content_restore_commands WHERE draft_id=?', (identifier,)).fetchone())
        for replacement in (original_command, (*original_command[:3], 'replacement_id', original_command[4])):
            with pytest.raises(sqlite3.IntegrityError, match='restore command immutable'):
                conn.execute('INSERT OR REPLACE INTO content_restore_commands VALUES(?,?,?,?,?)', replacement)
        for statement in ('UPDATE content_restore_commands SET command_key=command_key', 'DELETE FROM content_restore_commands'):
            with pytest.raises(sqlite3.IntegrityError, match='restore command immutable'):
                conn.execute(statement)
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('remove_all', [False, True])
def test_restore_catalog_detects_truncated_owner_history(prepared_review_http, remove_all):
    case = prepared_review_http
    old, current, _, _ = source(case, 'theorem')
    earlier, _, _ = create(case, old, current, 'earlier')
    identifier, request, snapshot = create(case, old, current)
    publish = approve(case, identifier, snapshot)
    with case.database.transaction() as conn:
        # Simulate storage damage beyond normal SQL immutability enforcement.
        conn.execute('DROP TRIGGER content_restore_no_delete')
        conn.execute('DELETE FROM content_restore_drafts' if remove_all else 'DELETE FROM content_restore_drafts WHERE id=?',
            () if remove_all else (identifier,))
    before = table_hashes(case.database)
    read = case.client.get('/api/v1/content/restore-drafts/' + identifier)
    assert read.status_code == 409 and read.json()['error']['code'] == 'RESTORE_INTEGRITY_ERROR'
    assert case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publish, headers=command(case.headers, 'truncated')).status_code == 409
    assert case.client.post('/api/v1/content/restore-drafts', json=request, headers=command(case.headers, 'restore')).status_code == 409
    assert case.client.get('/api/v1/content/restore-drafts/' + earlier).status_code == (409 if remove_all else 200)
    assert table_hashes(case.database) == before


def test_restore_missing_command_witness_cannot_recreate_original_ack(prepared_review_http):
    case = prepared_review_http
    old, current, _, _ = source(case, 'theorem')
    identifier, request, _ = create(case, old, current)
    with case.database.transaction() as conn:
        conn.execute('DROP TRIGGER content_restore_commands_no_delete')
        conn.execute('DELETE FROM content_restore_commands')
    before = table_hashes(case.database)
    assert case.client.get('/api/v1/content/restore-drafts/' + identifier).status_code == 409
    assert case.client.post('/api/v1/content/restore-drafts', json=request, headers=command(case.headers, 'restore')).status_code == 409
    assert table_hashes(case.database) == before


def test_restore_rejects_deleted_known_provenance_before_first_create(prepared_review_http):
    case = prepared_review_http
    old, current, _, _ = source(case)
    with case.database.transaction() as conn:
        conn.execute('DELETE FROM block_provenance WHERE block_id=? AND block_revision=1', (old.id,))
    before = table_hashes(case.database)
    response = case.client.post('/api/v1/content/restore-drafts', json={
        'source_ref':old.model_dump(mode='json'), 'expected_current_ref':current.model_dump(mode='json'), 'reason':'Synthetic loss detection.'},
        headers=command(case.headers, 'missing-provenance'))
    assert response.status_code == 409, response.text
    assert table_hashes(case.database) == before


def test_restore_published_get_rechecks_human_decision(prepared_review_http):
    case = prepared_review_http
    old, current, _, _ = source(case, 'theorem')
    identifier, _, snapshot = create(case, old, current)
    publish = approve(case, identifier, snapshot)
    result = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publish, headers=command(case.headers, 'restore-publish'))
    assert result.status_code == 201, result.text
    with case.database.transaction() as conn:
        conn.execute('DROP TRIGGER review_revisions_no_update')
        conn.execute("UPDATE review_revisions SET record_sha256=? WHERE review_id=? AND revision=2", ('0'*64, publish['review_receipt_id']))
    before = table_hashes(case.database)
    assert case.client.get('/api/v1/content/restore-drafts/' + identifier).status_code == 409
    assert case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publish, headers=command(case.headers, 'restore-publish')).status_code == 409
    assert table_hashes(case.database) == before


def test_restore_historical_actor_belongs_to_workspace_but_need_not_remain_active_author(prepared_review_http):
    from dataclasses import replace
    from services.api.app.application.sessions import SessionService
    from services.api.app.application.errors import ApiError
    from services.api.app.dto import RoleRequest
    from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
    case = prepared_review_http
    old, current, _, _ = source(case, 'theorem')
    identifier, _, _ = create(case, old, current)
    _, later = consume_bootstrap(case.database, issue_bootstrap_code(case.database))
    SessionService(case.database).switch_role(later, RoleRequest(role='author'), 'later-author')
    later = replace(later, role='author')
    with case.database.transaction() as conn:
        conn.execute("UPDATE local_sessions SET role='learner',revoked_at='2020-01-01T00:00:00Z' WHERE id=?", (case.identity.id,))
    assert case.app.state.content_restore_service.read(later, identifier).state == 'draft'
    with case.database.transaction() as conn:
        conn.execute("INSERT INTO workspace(id,title,created_at) VALUES('other_workspace','Synthetic other workspace','2020-01-01T00:00:00Z')")
        conn.execute("UPDATE local_sessions SET workspace_id='other_workspace' WHERE id=?", (case.identity.id,))
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as failure:
        case.app.state.content_restore_service.read(later, identifier)
    assert failure.value.status == 409
    assert table_hashes(case.database) == before


def test_restore_known_source_revision_loss_is_integrity_error(prepared_review_http):
    case = prepared_review_http
    old, current, _, _ = source(case, 'theorem')
    identifier, _, _ = create(case, old, current)
    with case.database.connect() as conn:
        # Storage damage injection; normal FK/immutable guards prevent this.
        conn.execute('PRAGMA foreign_keys=OFF')
        for trigger in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='revisions'").fetchall():
            conn.execute('DROP TRIGGER ' + trigger[0])
        conn.execute('DELETE FROM revisions WHERE object_id=? AND revision=1', (old.id,))
    before = table_hashes(case.database)
    read = case.client.get('/api/v1/content/restore-drafts/' + identifier)
    assert read.status_code == 409 and read.json()['error']['code'] == 'RESTORE_INTEGRITY_ERROR'
    assert table_hashes(case.database) == before
