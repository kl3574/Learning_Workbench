"""Real frozen course trees, title-only queries and learning projection integration."""

from dataclasses import replace

import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.errors import ApiError
from services.api.app.application.learning import LearningService
from services.api.app.application.reader import ReaderService
from services.api.app.infrastructure.security import SessionIdentity
from services.api.app.learning_dto import LearningActionRequest
from tests.integration import test_content_repository as content_tests

store=content_tests.store


def identity(workspace):
    return SessionIdentity('session_reader',workspace,'learner','synthetic_csrf','2099-01-01T00:00:00Z')


def test_outline_exact_history_fallback_and_no_body_access(store,monkeypatch):
    from services.api.app.infrastructure.blobs import BlobStore
    database,content,workspace=store
    old,bodies=content_tests.tree(concept=False)
    content.publish(workspace,old,bodies)
    newer,new_bodies=content_tests.tree(2,concept=False)
    content.publish(workspace,newer,new_bodies)
    monkeypatch.setattr(BlobStore,'read',lambda *_args,**_kwargs:pytest.fail('directory must not read bodies'))
    result=ReaderService(database).outline(identity(workspace),'course',1)
    assert result.course_ref == content_tests.ref(old[-1])
    assert result.sections[0].id == old[-1].id and result.sections[0].title == old[-1].title
    assert result.sections[0].lessons[0].ref == content_tests.ref(old[1])
    assert result.sections[0].lessons[0].blocks[0].ref == content_tests.ref(old[0])
    assert result.sections[0].lessons[0].reading_state == 'unread'


def test_title_and_ancestor_search_scoped_bounded_literal_and_body_free(store):
    database,content,workspace=store
    values,bodies=content_tests.tree(concept=False)
    course=values[-1].model_copy(update={'sections':[dm.CourseSection(id='section',title='长章名 %_',lesson_ids=[values[1].id])]})
    values[-1]=course
    content.publish(workspace,values,bodies)
    other,other_bodies=content_tests.tree(suffix='_other',concept=False)
    content.publish(workspace,other,other_bodies)
    reader=ReaderService(database)
    hits=reader.directory_search(identity(workspace),'course',1,q='%_',limit=50).hits
    assert [hit.ref.entity for hit in hits] == ['lesson','block']
    assert any(ancestor.id == 'section' for ancestor in hits[-1].ancestors)
    assert all('_other' not in hit.ref.id for hit in hits)
    assert reader.directory_search(identity(workspace),'course',1,q='x^2').hits == []
    assert len(reader.directory_search(identity(workspace),'course',1,q='测试',limit=1).hits) == 1
    for kwargs in [{'q':' '},{'q':'test','limit':51},{'q':'test','limit':True}]:
        with pytest.raises(ApiError):
            reader.directory_search(identity(workspace),'course',1,**kwargs)
    foreign=replace(identity(workspace),workspace_id=content_tests.second_workspace(database))
    with pytest.raises(ApiError) as error:
        reader.directory_search(foreign,'course',1,q='测试')
    assert error.value.status == 404


def test_outline_consumes_actual_learning_actions_and_marks_new_revision_stale(store):
    database,content,workspace=store
    values,bodies=content_tests.tree(concept=False)
    content.publish(workspace,values,bodies)
    actor=identity(workspace)
    learning=LearningService(database)
    learning.action(actor,LearningActionRequest(kind='read_marked',ref=content_tests.ref(values[0]),expected_revision=1,value=True),'mark')
    reader=ReaderService(database)
    assert reader.outline(actor,'course',1).sections[0].lessons[0].reading_state == 'read'
    new,new_bodies=content_tests.tree(2,concept=False)
    content.publish(workspace,new,new_bodies)
    assert reader.outline(actor,'course',2).sections[0].lessons[0].reading_state == 'stale'
    assert reader.outline(actor,'course',1).sections[0].lessons[0].reading_state == 'read'


def test_directory_rejects_stored_course_reference_with_wrong_hash(store):
    from packages.contracts.canonical import canonical_bytes, metadata_sha256
    database,content,workspace=store
    values,bodies=content_tests.tree(concept=False)
    content.publish(workspace,values,bodies)
    course=values[-1].model_copy(update={'revision':2,'lesson_refs':[content_tests.ref(values[1]).model_copy(update={'sha256':'0'*64})]})
    # Simulate a corrupted legacy metadata relationship, with a valid owning row hash.
    with database.transaction() as connection:
        connection.execute('INSERT INTO revisions(object_id,revision,sha256,metadata_json,created_at) VALUES(?,?,?,?,?)',
            (course.id,2,metadata_sha256(course),canonical_bytes(course).decode(),'2026-09-14T00:00:00Z'))
    reader=ReaderService(database)
    for operation in [lambda:reader.outline(identity(workspace),'course',2),
                      lambda:reader.directory_search(identity(workspace),'course',2,q='测试')]:
        with pytest.raises(ApiError) as error:
            operation()
        assert error.value.code == 'CONTENT_HASH_MISMATCH'
