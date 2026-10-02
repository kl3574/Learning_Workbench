"""Independent fixed-SHA probes; synthetic local data only."""
import pytest
from packages.contracts.canonical import canonical_bytes
from tests.integration.test_content_impact_decisions_http import case as case
from tests.integration.test_content_impact_discovery_http import PATH, get, publish
from tests.integration.test_content_repository import tree, second_workspace
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes


def fault(case, sql, args=()):
    with case.database.connect() as conn:
        conn.execute('PRAGMA foreign_keys=OFF')
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('DROP TRIGGER valid_current_revision')
        conn.execute(sql, args)
        conn.commit()


def unchanged(case, expected, **params):
    before = table_hashes(case.database)
    response = case.client.get(PATH, params=params)
    assert table_hashes(case.database) == before
    assert response.headers['cache-control'] == 'no-store'
    assert response.status_code == expected, response.text
    return response


@pytest.mark.parametrize('filtered', [False, True])
def test_missing_current_target_revision_is_integrity_error(case, filtered):
    # A retained exact target and its historical ref remain intact; its current
    # pointer now names absent storage. This is not a caller-supplied missing ID.
    fault(case, "UPDATE objects SET current_revision=999 WHERE id='lesson'")
    unchanged(case, 409, **({'changed_object_id': 'unknown'} if filtered else {}))


@pytest.mark.parametrize('filtered', [False, True])
def test_authorized_artifact_corruption_blocks_discovery_even_nonmatch(case, filtered):
    upload = case.client.post('/api/v1/imports', files={'file': ('evidence.md', b'# Synthetic decision evidence\n', 'text/markdown')}, data={'kind':'markdown'}, headers=command(case.headers,'probe-upload'))
    assert upload.status_code == 202 and case.app.state.import_worker.run_once()
    with case.database.connect() as conn:
        row = conn.execute('SELECT id,blob_sha256 FROM artifacts ORDER BY rowid LIMIT 1').fetchone()
    body = case.write(); body['evidence_artifact_ids'] = [row['id']]
    assert case.decide(body).status_code == 200
    get(case)
    digest = row['blob_sha256']
    (case.database.settings.data_dir/'blobs'/digest[:2]/digest).write_bytes(b'bad independent bytes')
    unchanged(case, 409, **({'changed_object_id':'unknown'} if filtered else {}))


def test_valid_foreign_event_excluded_but_forged_foreign_snapshot_rejected(case):
    workspace = second_workspace(case.database)
    values, bodies = tree(suffix='_foreign')
    case.service.publish(workspace, values, bodies)
    case.service.publish(workspace, [values[1].model_copy(update={'revision':2,'title':'Foreign synthetic change'})], {})
    assert len(get(case)['items']) == 1
    assert get(case, changed_object_id='block_foreign')['items'] == []
    with case.database.transaction() as conn:
        foreign = conn.execute("SELECT event_id FROM content_impact_snapshots WHERE workspace_id=?",(workspace,)).fetchone()[0]
        conn.execute('DROP TRIGGER content_impact_snapshot_no_update')
        conn.execute('UPDATE content_impact_snapshots SET workspace_id=? WHERE event_id=?',(case.identity.workspace_id,foreign))
    unchanged(case,409,changed_object_id='unknown')


def test_signed_membership_detects_prefix_event_and_witness_all_removed(case):
    publish(case,1,3)
    page = get(case,limit=1)
    with case.database.connect() as conn:
        conn.execute('PRAGMA foreign_keys=OFF'); conn.execute('BEGIN IMMEDIATE')
        conn.execute('DROP TRIGGER content_impact_snapshot_no_delete')
        conn.execute('DELETE FROM content_impact_snapshots WHERE event_id=?',(case.event_id,))
        conn.execute('DELETE FROM outbox WHERE id=?',(case.event_id,)); conn.commit()
    unchanged(case,409,limit=1,cursor=page['next_cursor'])


@pytest.mark.parametrize('filter_id', [None, 'block'])
def test_membership_three_filtered_pages_delivery_and_new_events(case, filter_id):
    publish(case,0,2); publish(case,1,3); publish(case,0,3); publish(case,1,4)
    params = {'limit':1}
    if filter_id: params['changed_object_id']=filter_id
    expected = [x['event_id'] for x in get(case, **({'changed_object_id':filter_id} if filter_id else {}))['items']]
    first=get(case,**params); seen=[first['items'][0]['event_id']]
    cursor=first['next_cursor']; assert cursor
    with case.database.transaction() as conn:
        conn.execute("UPDATE outbox SET delivered_at='2026-10-02T00:00:00Z',attempts=attempts+1")
    publish(case,1,5)
    while cursor:
        page=get(case,**params,cursor=cursor)
        seen += [x['event_id'] for x in page['items']]; cursor=page['next_cursor']
    assert seen == expected and len(seen)==len(set(seen))
    fresh=get(case,**({'changed_object_id':filter_id} if filter_id else {}))
    assert len(fresh['items']) == len(expected)+1


def test_empty_current_targets_do_not_claim_other_owners_done(case):
    for target in ['course','lesson','lesson_candidate']:
        assert case.decide(case.write(target),target).status_code == 200
    listed=get(case)['items'][0]
    assert listed['pending_target_ids'] == listed['action_required_target_ids'] == []
    detail=case.client.get(PATH+'/'+listed['event_id']).json()
    assert 'note_impact' in detail['affected_ids'] and 'route_impact' in detail['affected_ids']
    assert listed == {key:detail[key] for key in listed}


def test_current_target_body_revalidated_without_any_decisions(case):
    publish(case,0,2)
    get(case)
    digest=case.original[1].body_sha256
    (case.database.settings.data_dir/'blobs'/digest[:2]/digest).write_bytes(b'bad current bytes')
    unchanged(case,409,changed_object_id='unknown')


def test_nonmatching_event_payload_is_closed_not_filterable(case):
    with case.database.transaction() as conn:
        row=conn.execute('SELECT payload_json FROM outbox WHERE id=?',(case.event_id,)).fetchone()
        import json
        value=json.loads(row[0]);value['unexpected']='unsafe'
        conn.execute('UPDATE outbox SET payload_json=? WHERE id=?',(canonical_bytes(value).decode(),case.event_id))
    unchanged(case,409,changed_object_id='unknown')


def test_genuine_pre0021_migration_list_detail_readonly(tmp_path, monkeypatch):
    from dataclasses import replace
    from types import SimpleNamespace
    import shutil
    from fastapi.testclient import TestClient
    from services.api.app.application import content_impact as module
    from services.api.app.application.content import ContentService
    from services.api.app.application.sessions import SessionService
    from services.api.app.dto import RoleRequest
    from services.api.app.infrastructure.config import Settings
    from services.api.app.infrastructure.database import Database
    from services.api.app.infrastructure.security import COOKIE_NAME, consume_bootstrap, issue_bootstrap_code
    from services.api.app.main import create_app
    settings=Settings(data_dir=tmp_path/'legacy')
    migrations=tmp_path/'migrations';migrations.mkdir()
    for path in settings.migrations_dir.glob('*.sql'):
        if path.name<'0021': shutil.copyfile(path,migrations/path.name)
    old=Database(replace(settings,migrations_dir=migrations));workspace=old.initialize()
    service=ContentService(old);values,bodies=tree();service.publish(workspace,values,bodies)
    with monkeypatch.context() as patch:
        patch.setattr(module,'freeze_impact_event',lambda *args:None)
        service.publish(workspace,[values[1].model_copy(update={'revision':2,'title':'Genuine pre-migration synthetic'})],{})
    database=Database(settings);assert database.initialize()==workspace
    token,learner=consume_bootstrap(database,issue_bootstrap_code(database))
    SessionService(database).switch_role(learner,RoleRequest(role='author'),'author')
    client=TestClient(create_app(settings),base_url=settings.origin)
    try:
        client.cookies.set(COOKIE_NAME,token)
        proxy=SimpleNamespace(client=client,database=database)
        summary=get(proxy)['items'][0]
        assert summary['evidence_version']=='legacy_unverified' and summary['event_snapshot_sha256'] is None
        before=table_hashes(database)
        detail=client.get(PATH+'/'+summary['event_id'])
        assert detail.status_code==200 and summary=={key:detail.json()[key] for key in summary}
        assert detail.json()['exact_dependency_refs']==[] and detail.json()['decisions']==[]
        assert table_hashes(database)==before
    finally:
        client.close()


@pytest.mark.parametrize('cursor_invalid', [False, True])
def test_role_recheck_precedes_even_signed_or_malformed_cursor(case,cursor_invalid):
    publish(case,1,3);cursor=get(case,limit=1)['next_cursor']
    if cursor_invalid: cursor+='invalid'
    response=case.client.post('/api/v1/session/role',json={'role':'learner'},headers=command(case.headers,'downgrade'))
    assert response.status_code==200
    unchanged(case,403,limit=1,cursor=cursor)


def test_orphaned_known_pure_id_candidate_not_silently_dropped(case):
    # Candidate's only relation to this event is ID-only. Its surviving published
    # Content revision proves a deleted objects row is broken storage, not a new
    # unknown owner identity. Normal foreign keys prevent this deletion.
    import sqlite3
    with case.database.transaction() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM objects WHERE id='lesson_candidate'")
    with case.database.connect() as conn:
        conn.execute('PRAGMA foreign_keys=OFF');conn.execute('BEGIN IMMEDIATE')
        conn.execute("DELETE FROM objects WHERE id='lesson_candidate'");conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM revisions WHERE object_id='lesson_candidate'").fetchone()[0]==1
    unchanged(case,409,changed_object_id='unknown')
