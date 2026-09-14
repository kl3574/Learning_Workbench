"""Actual import persistence, exact provenance, guards and role-dependent source access."""

from dataclasses import replace

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.application.errors import ApiError
from services.api.app.application.reader import ReaderService
from tests.integration import test_import_repository as importing

imports = importing.imports
staged_ready = importing.staged_ready
decision = importing.decision


def committed(imports, **options):
    database, service, _, identity = imports
    staged, preview = staged_ready(imports, **options)
    result = service.commit(replace(identity, role='author'), staged.import_id, decision(staged, preview), 'commit_' + staged.import_id)
    course = service.content.read(identity.workspace_id, 'course', result.course_refs[0].id, result.course_refs[0].revision)
    lesson = service.content.read(identity.workspace_id, 'lesson', course.lesson_refs[0].id, course.lesson_refs[0].revision)
    block = service.content.read(identity.workspace_id, 'block', lesson.block_refs[0].id, lesson.block_refs[0].revision)
    return staged, block


def test_reader_guard_blocks_provenance_and_directory_before_storage_projection(imports):
    database, service, _, identity = imports
    _, block = committed(imports)
    blueprint = dm.AssessmentBlueprint(id='reader_guard', revision=1, title='合成', question_refs=[dm.ContentRef(entity='question', id='synthetic_q', revision=1, sha256='0' * 64)],
        allowed_modes=['independent'])
    # Existing guard rows need a real immutable assessment revision, but no active assessment API.
    with database.transaction() as connection:
        connection.execute("INSERT INTO objects(id,workspace_id,kind) VALUES(?,?,'assessment')", (blueprint.id,identity.workspace_id))
        connection.execute('INSERT INTO revisions(object_id,revision,sha256,metadata_json,created_at) VALUES(?,?,?,?,?)',
            (blueprint.id,1,metadata_sha256(blueprint),canonical_bytes(blueprint).decode(),'2026-09-14T00:00:00Z'))
        connection.execute("INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) VALUES('reader_attempt',?,?,1,'independent','{}','[]','[]','active',1,'2026-09-14T00:00:00Z')", (identity.workspace_id,blueprint.id))
    reader = ReaderService(database)
    for actor in (identity,replace(identity,role='author')):
        with pytest.raises(ApiError) as error:
            reader.block(actor,block.id,block.revision)
        assert error.value.code == 'ASSESSMENT_ACTIVE'
        with pytest.raises(ApiError) as error:
            reader.outline(actor,'missing_course',1)
        assert error.value.code == 'ASSESSMENT_ACTIVE'


def test_committed_provenance_survives_draft_removal_restart_and_source_metadata_change(imports):
    from services.api.app.database import Database
    database, _, _, identity = imports
    staged, block = committed(imports)
    first = ReaderService(database).block(identity, block.id, block.revision)
    assert first.block_ref.sha256 == metadata_sha256(block)
    assert first.citations and not first.unresolved_citation_ids
    assert first.citations[0].source.sha256 == staged.input_sha256
    assert first.citations[0].citation.verification == 'user_supplied'
    with database.transaction() as connection:
        connection.execute('DELETE FROM drafts WHERE workspace_id=?', (identity.workspace_id,))
        connection.execute("UPDATE sources SET metadata_json=json_set(metadata_json,'$.citations',json('[]'),'$.warnings',json('[]')) WHERE workspace_id=?", (identity.workspace_id,))
    reopened = ReaderService(Database(database.settings)).block(identity, block.id, block.revision)
    assert reopened == first
    assert all(item.original_access == 'allowed' for item in reopened.citations)


def test_exact_old_revision_keeps_provenance_and_new_unbound_revision_stays_unresolved(imports):
    database, service, _, identity = imports
    _, block = committed(imports)
    reader = ReaderService(database)
    original = reader.block(identity, block.id, block.revision)
    newer = block.model_copy(update={'revision': block.revision + 1, 'title': '新修订未提供新来源'})
    service.content.publish(identity.workspace_id, [newer], {})
    assert reader.block(identity, block.id, block.revision) == original
    unresolved = reader.block(identity, block.id, newer.revision)
    assert unresolved.block_ref.sha256 == metadata_sha256(newer)
    assert unresolved.citations == [] and unresolved.unresolved_citation_ids == newer.citations
    assert any(item.code == 'PROVENANCE_UNRESOLVED' for item in unresolved.warnings)
    foreign = replace(identity, workspace_id='workspace_other')
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_other','合成','2026-09-14T00:00:00Z')")
    with pytest.raises(ApiError) as error:
        reader.block(foreign, block.id, block.revision)
    assert error.value.status == 404


def citation_package(title):
    from io import BytesIO
    from zipfile import ZipFile, ZIP_STORED
    from packages.contracts.canonical import sha256_bytes
    from services.api.app.infrastructure.content_repository import reference
    text = b'Synthetic cited content.\n'
    block = dm.ContentBlock(id='cited_block', revision=1, kind='text', title='引用正文',
        body_path='body.md', body_sha256=sha256_bytes(text), citations=['shared_citation'])
    lesson = dm.Lesson(id='cited_lesson', revision=1, title='引用小节', objectives=[], block_refs=[reference(block)])
    course = dm.Course(id='cited_course', revision=1, title='引用课程', audience='合成', lesson_refs=[reference(lesson)])
    citation = dm.Citation(id='shared_citation', title=title, locator='p. 1', verification='unverified', source_sha256='a'*64)
    payloads = {'course.json':canonical_bytes(course),'lessons/one.json':canonical_bytes(lesson),
        'blocks/one.json':canonical_bytes(block), 'body.md':text,
        'sources/citations.json':canonical_bytes([citation.model_dump(mode="json")])}
    manifest = dm.Manifest(package_id='synthetic_package',profile='learner',created_at='2026-09-14T00:00:00Z',
        files=[dm.FileEntry(path=path,size=len(data),sha256=sha256_bytes(data),media_type='text/markdown' if path.endswith('.md') else 'application/json',visibility='learner') for path,data in payloads.items()])
    output=BytesIO()
    with ZipFile(output,'w',compression=ZIP_STORED) as archive:
        for path,data in {**payloads,'manifest.json':canonical_bytes(manifest)}.items():
            archive.writestr(path,data)
    return output.getvalue()


def test_two_legal_packages_reusing_citation_id_never_cross_bind_sources(imports):
    from services.api.app.import_dto import ImportIdMapping
    database, service, _, identity = imports
    source_ids=[]
    for number, title in enumerate(['第一份来源声明','第二份来源声明']):
        staged, preview=staged_ready(imports,data=citation_package(title),filename='synthetic.learnpack',kind='learnpack',key=f'stage_{number}')
        mappings=[]
        if number:
            mappings=[ImportIdMapping(old_id=id,new_id='second_'+id) for id in ['cited_course','cited_lesson','cited_block']]
        service.commit(identity,staged.import_id,decision(staged,preview,mappings),f'commit_{number}')
        block_id='second_cited_block' if number else 'cited_block'
        result=ReaderService(database).block(identity,block_id,1)
        assert result.citations[0].citation.id == 'shared_citation'
        assert result.citations[0].citation.title == title
        assert result.citations[0].source.sha256 == staged.input_sha256
        # The imported container and the cited external source retain different hashes.
        assert result.citations[0].citation.source_sha256 == 'a'*64
        source_ids.append(result.citations[0].source.id)
    assert len(set(source_ids)) == 2


def test_provenance_failure_rolls_back_publication_and_retry_freezes_once(imports):
    database,service,_,identity=imports
    staged,preview=staged_ready(imports)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER fail_provenance BEFORE INSERT ON block_provenance BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    with pytest.raises(ApiError) as error:
        service.commit(identity,staged.import_id,decision(staged,preview),'commit')
    assert error.value.status == 503
    with database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM revisions').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM block_provenance').fetchone()[0] == 0
    assert service.preview(identity,staged.import_id).status == 'preview_ready'
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER fail_provenance')
    service.commit(identity,staged.import_id,decision(staged,preview),'commit')
    service.commit(identity,staged.import_id,decision(staged,preview),'commit')
    with database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM block_provenance').fetchone()[0] == preview.candidate_summary.block_count


def test_docx_safe_provenance_role_switch_rechecks_original_access_and_never_304(tmp_path):
    from tests.document_fixtures import docx_fixture
    from tests.integration.test_document_http import application_client, change_role, staged_document, confirm
    from services.api.app.config import Settings
    settings=Settings(data_dir=tmp_path/'data')
    with application_client(settings) as (app,client):
        _,preview=staged_document(client,settings,docx_fixture(),'docx')
        assert preview['status'] == 'preview_ready'
        result=confirm(client,settings,preview,acknowledge=True)
        assert result.status_code == 200
        course=result.json()['course_refs'][0]
        outline=client.get(f"/api/v1/courses/{course['id']}/outline",params={'revision':course['revision']})
        assert outline.status_code == 200,outline.text
        block=outline.json()['sections'][0]['lessons'][0]['blocks'][0]['ref']
        path=f"/api/v1/blocks/{block['id']}"
        params={'revision':block['revision'],'include_provenance':'true'}
        learner=client.get(path,params=params)
        assert learner.status_code == 200,learner.text
        body=learner.json()
        assert body['citations'][0]['original_access'] == 'author_required'
        assert all(key not in learner.text for key in ['artifact_id','download_path','filename','metadata_json','assets'])
        source_id=body['citations'][0]['source']['id']
        assert client.get('/api/v1/sources/'+source_id).status_code == 403
        change_role(client,settings,'author')
        author=client.get(path,params=params,headers={'If-None-Match':learner.headers['etag']})
        assert author.status_code == 200
        assert author.json()['citations'][0]['original_access'] == 'allowed'
        assert author.headers['etag'] == learner.headers['etag'] == '"'+block['sha256']+'"'
        assert author.headers['cache-control'] == 'no-store' and author.headers['vary'] == 'Cookie'
        change_role(client,settings,'learner')
        again=client.get(path,params=params,headers={'If-None-Match':author.headers['etag']})
        assert again.status_code == 200 and again.json()['citations'][0]['original_access'] == 'author_required'
        default=client.get(path,params={'revision':block['revision']})
        assert default.status_code == 200 and dm.ContentBlock.model_validate(default.json()).id == block['id']
        assert client.get(path,params=[('revision',1),('include_provenance','true'),('include_provenance','false')]).status_code == 422


def test_startup_backfill_reparses_original_not_mutable_metadata_and_is_idempotent(imports,monkeypatch):
    from services.api.app.application.reader import backfill_provenance
    from services.api.app.application import import_parsing
    database,_,_,identity=imports
    _,block=committed(imports)
    reader=ReaderService(database)
    expected=reader.block(identity,block.id,block.revision)
    with database.transaction() as connection:
        connection.execute('DELETE FROM block_provenance')
        connection.execute('DELETE FROM drafts')
        connection.execute("UPDATE sources SET metadata_json=json_set(metadata_json,'$.citations[0].title','FORGED_MUTABLE_TITLE')")
    original_parser=import_parsing.parse_import
    calls=[]
    def observed(*args,**kwargs):
        calls.append(kwargs['source_id'])
        return original_parser(*args,**kwargs)
    monkeypatch.setattr(import_parsing,'parse_import',observed)
    assert reader.block(identity,block.id,block.revision).citations == []
    assert not calls
    outcome=backfill_provenance(database)
    assert outcome.scanned_imports == 1 and outcome.frozen_blocks >= 1 and outcome.unresolved_blocks == 0
    assert len(calls) == 1
    result=reader.block(identity,block.id,block.revision)
    assert result == expected
    assert 'FORGED_MUTABLE_TITLE' not in result.model_dump_json()
    assert backfill_provenance(database).scanned_imports == 0
    assert len(calls) == 1


def test_backfill_uses_real_commit_mapping_and_isolates_missing_original(imports):
    from services.api.app.application.reader import backfill_provenance
    from services.api.app.import_dto import ImportIdMapping
    database,service,_,identity=imports
    staged,_=committed(imports)
    original_digest=staged.input_sha256
    package,preview=staged_ready(imports,data=citation_package('可恢复的真实引用'),filename='synthetic.learnpack',kind='learnpack',key='package')
    mappings=[ImportIdMapping(old_id=id,new_id='mapped_'+id) for id in ['cited_course','cited_lesson','cited_block']]
    service.commit(identity,package.import_id,decision(package,preview,mappings),'commit_package')
    with database.transaction() as connection:
        connection.execute('DELETE FROM block_provenance')
        connection.execute('DELETE FROM drafts')
    (database.settings.data_dir/'blobs'/original_digest[:2]/original_digest).unlink()
    result=backfill_provenance(database)
    assert result.scanned_imports == 2 and result.frozen_blocks == 1 and result.unresolved_blocks >= 1
    restored=ReaderService(database).block(identity,'mapped_cited_block',1)
    assert restored.citations[0].citation.title == '可恢复的真实引用'
    assert restored.citations[0].source.sha256 == package.input_sha256
    assert result.warnings[0].code == 'PROVENANCE_BACKFILL_UNRESOLVED'
    assert original_digest not in result.warnings[0].message


def test_backfill_requires_exact_reparsed_candidate_hash_before_freezing(imports):
    from services.api.app.application.reader import backfill_provenance
    import json
    database,_,_,identity=imports
    staged,block=committed(imports)
    with database.transaction() as connection:
        connection.execute('DELETE FROM block_provenance')
        row=connection.execute('SELECT preview_json FROM ingestion_imports WHERE id=?',(staged.import_id,)).fetchone()
        preview=json.loads(row[0])
        next(item for item in preview['objects'] if item['entity']=='block')['title']='修改过的候选'
        connection.execute('UPDATE ingestion_imports SET preview_json=? WHERE id=?',(json.dumps(preview),staged.import_id))
    result=backfill_provenance(database)
    assert result.frozen_blocks == 0 and result.unresolved_blocks > 0
    assert ReaderService(database).block(identity,block.id,1).unresolved_citation_ids == block.citations


def test_missing_source_citation_blocks_confirmation_atomically(imports):
    database,service,_,identity=imports
    staged,preview=staged_ready(imports)
    with database.transaction() as connection:
        connection.execute("UPDATE sources SET metadata_json=json_set(metadata_json,'$.citations',json('[]'))")
    with pytest.raises(ApiError) as error:
        service.commit(identity,staged.import_id,decision(staged,preview),'broken_citation')
    assert error.value.code == 'CONTENT_HASH_MISMATCH'
    assert service.preview(identity,staged.import_id).status == 'preview_ready'
    with database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM revisions').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM block_provenance').fetchone()[0] == 0


def test_provenance_snapshot_is_immutable_and_tampering_fails_closed(imports):
    import sqlite3
    database,_,_,identity=imports
    _,block=committed(imports)
    with database.transaction() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE block_provenance SET snapshot_sha256=?",('0'*64,))
        # Deliberate offline corruption scenario, outside application permission paths.
        connection.execute('DROP TRIGGER block_provenance_no_update')
        connection.execute("UPDATE block_provenance SET snapshot_json=json_set(snapshot_json,'$.citations[0].title','tampered')")
    with pytest.raises(ApiError) as error:
        ReaderService(database).block(identity,block.id,block.revision)
    assert error.value.code == 'CONTENT_HASH_MISMATCH'
