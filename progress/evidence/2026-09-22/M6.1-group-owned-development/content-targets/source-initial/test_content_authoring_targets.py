"""Exact Content metadata ports over real SQLite and synthetic publications.

Storage faults below are isolated test fixtures, never a product editing or
approval path. These tests do not exercise generation, HTTP or publication of
Authoring drafts.
"""

from dataclasses import replace
import sqlite3

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from services.api.app.application.assessment import AssessmentService
from services.api.app.application.content import ContentService
from services.api.app.application.content_authoring_targets import ContentAuthoringTargetSource
from services.api.app.application.errors import ApiError
from services.api.app.assessment_dto import AssessmentAttemptCreate
from services.api.app.infrastructure.blobs import BlobStore
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import ContentRepository, reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import SessionIdentity
from tests.assessment_fixtures import assessment_fixture


@pytest.fixture
def targets(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    identity = SessionIdentity('session_targets_synthetic', workspace, 'author', 'unused', '2099-01-01T00:00:00Z')
    dependency = dm.Concept(id='target_dependency', revision=1, title='未选择的先修概念')
    first = dm.Concept(id='target_first', revision=1, title='合成目标甲', prerequisite_ids=[dependency.id])
    second = dm.Concept(id='target_second', revision=1, title='合成目标乙')
    body = b'Synthetic material, not reviewed.\n'
    block = dm.ContentBlock(id='target_block', revision=1, kind='text', title='合成正文',
        body_path='content/target_block.md', body_sha256=sha256_bytes(body), concepts=[first.id])
    lesson = dm.Lesson(id='target_lesson', revision=1, title='合成小节', objectives=['识别所选概念'],
        prerequisite_ids=[dependency.id], block_refs=[reference(block)])
    publisher = ContentService(database)
    publisher.publish(workspace, [dependency, first, second, block, lesson], {block.body_path: body})
    return database, identity, publisher, ContentAuthoringTargetSource(database), lesson, first, second


def error(code, operation):
    with pytest.raises(ApiError) as caught:
        operation()
    assert caught.value.code == code
    return caught.value


def selected(lesson, first, second):
    return [reference(lesson), reference(second), reference(first)]


def resolve(targets, refs):
    database, identity, _, source, *_ = targets
    with database.transaction() as conn:
        return source.resolve_targets(conn, identity, refs)


def test_exact_order_metadata_and_no_implicit_children_dependencies_or_writes(targets, monkeypatch):
    database, identity, _, source, lesson, first, second = targets
    refs = selected(lesson, first, second)
    loaded = []
    load = ContentRepository.load

    def observe(repository, entity, identifier, revision):
        loaded.append((entity, identifier, revision))
        return load(repository, entity, identifier, revision)

    monkeypatch.setattr(ContentRepository, 'load', observe)
    monkeypatch.setattr(ContentRepository, 'current', lambda *args: pytest.fail('read current pointer'))
    monkeypatch.setattr(BlobStore, 'read', lambda *args, **kwargs: pytest.fail('opened child body'))
    with database.transaction() as conn:
        conn.execute('PRAGMA query_only=ON')
        before = conn.total_changes
        with monkeypatch.context() as same_transaction:
            same_transaction.setattr(database, 'connect', lambda **kwargs: pytest.fail('opened another connection'))
            result = source.resolve_targets(conn, identity, refs)
            frozen = canonical_bytes(result)
            assert source.revalidate_targets(conn, identity, result) is None
            assert conn.total_changes == before and conn.in_transaction
        assert canonical_bytes(result) == frozen
    assert [item.ref.model_dump() for item in result] == [ref.model_dump() for ref in refs]
    assert [item.metadata for item in result] == [lesson, second, first]
    assert loaded == [(ref.entity, ref.id, ref.revision) for ref in refs] * 2
    # Concept prerequisites and Lesson block refs remain metadata, not sources.
    assert result[2].metadata.prerequisite_ids == ['target_dependency']
    assert b'Synthetic material' not in frozen


def test_same_transaction_reads_uncommitted_revision_and_leaves_rollback_to_caller(targets):
    database, identity, publisher, source, _, first, _ = targets
    updated = first.model_copy(update={'revision': 2, 'title': '尚未提交的真实修订'})
    with database.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        publisher.publish_in_transaction(conn, identity.workspace_id, [updated], {})
        before = conn.total_changes
        result = source.resolve_targets(conn, identity, [reference(updated)])
        source.revalidate_targets(conn, identity, result)
        assert result[0].metadata == updated and conn.total_changes == before and conn.in_transaction
        conn.rollback()
    with database.transaction() as conn:
        error('REFERENCE_MISSING', lambda: source.resolve_targets(conn, identity, [reference(updated)]))


def test_frozen_old_revisions_survive_new_current_and_archive_without_substitution(targets):
    database, identity, publisher, source, lesson, first, second = targets
    original = resolve(targets, selected(lesson, first, second))
    new_lesson = lesson.model_copy(update={'revision': 2, 'title': '新修订小节'})
    new_first = first.model_copy(update={'revision': 2, 'title': '新修订概念'})
    publisher.publish(identity.workspace_id, [new_lesson, new_first], {})
    with database.transaction() as conn:
        # Explicit archive fixture; this port does not implement archive writes.
        conn.execute("UPDATE objects SET lifecycle='archived' WHERE id IN (?,?)", (lesson.id, first.id))
        source.revalidate_targets(conn, identity, original)
        assert source.resolve_targets(conn, identity, selected(lesson, first, second)) == original
        both = source.resolve_targets(conn, identity, [reference(new_first), reference(first)])
        assert [item.metadata.revision for item in both] == [2, 1]


def test_empty_and_maximum_inputs_are_ordered_zero_write_reads(targets):
    database, identity, publisher, source, *_ = targets
    values = [dm.Concept(id=f'target_limit_{index}', revision=1, title=f'合成概念 {index}') for index in range(33)]
    publisher.publish(identity.workspace_id, values, {})
    with database.transaction() as conn:
        before = conn.total_changes
        assert source.resolve_targets(conn, identity, []) == []
        assert source.revalidate_targets(conn, identity, []) is None
        result = source.resolve_targets(conn, identity, [reference(value) for value in reversed(values)])
        assert [item.metadata for item in result] == list(reversed(values))
        source.revalidate_targets(conn, identity, result)
        assert conn.total_changes == before


@pytest.mark.parametrize('operation', ['resolve', 'revalidate'])
@pytest.mark.parametrize('transaction', ['not_started', 'committed', 'fake'])
def test_requires_real_still_open_transaction_even_for_empty_input(targets, operation, transaction):
    database, identity, _, source, *_ = targets
    method = source.resolve_targets if operation == 'resolve' else source.revalidate_targets
    with database.connect() as conn:
        if transaction == 'committed':
            conn.execute('BEGIN')
            conn.commit()
        supplied = type('FakeTransaction', (), {'in_transaction': True})() if transaction == 'fake' else conn
        error('TRANSACTION_REQUIRED', lambda: method(supplied, identity, []))


@pytest.mark.parametrize('fault', ['duplicate', 'conflicting_sha', 'bool_revision', 'missing_sha',
    'invalid_sha', 'unsupported_entity', 'over_limit', 'not_a_ref', 'not_a_list'])
def test_invalid_selections_fail_before_loading_or_writing(targets, monkeypatch, fault):
    database, identity, _, source, _, first, _ = targets
    ref = reference(first)
    refs = [ref]
    if fault == 'duplicate':
        refs += [ref]
    elif fault == 'conflicting_sha':
        refs += [ref.model_copy(update={'sha256': '0' * 64})]
    elif fault in {'bool_revision', 'missing_sha', 'invalid_sha', 'unsupported_entity'}:
        update = {'bool_revision': {'revision': True}, 'missing_sha': {'sha256': None},
            'invalid_sha': {'sha256': 'G' * 64}, 'unsupported_entity': {'entity': 'question'}}[fault]
        refs = [ref.model_copy(update=update)]
    elif fault == 'over_limit':
        refs *= 34
    elif fault == 'not_a_ref':
        refs = [ref.model_dump()]
    else:
        refs = (ref,)
    monkeypatch.setattr(ContentRepository, 'load', lambda *args: pytest.fail('invalid list partially resolved'))
    with database.transaction() as conn:
        before = conn.total_changes
        error('AUTHORING_TARGET_INVALID', lambda: source.resolve_targets(conn, identity, refs))
        assert conn.total_changes == before


@pytest.mark.parametrize('fault', ['absent_id', 'absent_revision', 'wrong_entity', 'wrong_sha', 'other_workspace'])
def test_missing_mismatched_and_cross_workspace_refs_reject_without_fallback(targets, fault):
    database, identity, _, source, _, first, _ = targets
    ref = reference(first)
    expected = 'REFERENCE_MISSING'
    if fault == 'other_workspace':
        with database.transaction() as conn:
            conn.execute("INSERT INTO workspace(id,title,created_at) VALUES('other_targets','合成','2026-09-22T00:00:00Z')")
        identity = replace(identity, workspace_id='other_targets')
    else:
        updates = {'absent_id': {'id': 'absent_target'}, 'absent_revision': {'revision': 99},
            'wrong_entity': {'entity': 'lesson'}, 'wrong_sha': {'sha256': '0' * 64}}
        ref = ref.model_copy(update=updates[fault])
        if fault == 'wrong_sha':
            expected = 'CONTENT_HASH_MISMATCH'
    with database.transaction() as conn:
        before = conn.total_changes
        error(expected, lambda: source.resolve_targets(conn, identity, [ref]))
        assert conn.total_changes == before


@pytest.mark.parametrize('operation', ['resolve', 'revalidate'])
def test_nonexistent_workspace_is_not_vacuously_valid_for_empty_input(targets, operation):
    database, identity, _, source, *_ = targets
    missing = replace(identity, workspace_id='missing_workspace')
    method = source.resolve_targets if operation == 'resolve' else source.revalidate_targets
    with database.transaction() as conn:
        error('REFERENCE_MISSING', lambda: method(conn, missing, []))


@pytest.mark.parametrize('fault', ['sha', 'malformed_json', 'actual_type', 'actual_id', 'actual_revision',
    'consistent_changed_metadata', 'missing'])
def test_revalidate_reloads_exact_real_storage_and_rejects_corruption(targets, fault):
    database, identity, _, source, _, first, _ = targets
    original = resolve(targets, [reference(first)])
    frozen = canonical_bytes(original)
    with database.transaction() as conn:
        conn.execute('DROP TRIGGER revisions_no_update')
        if fault == 'missing':
            conn.execute('DROP TRIGGER revisions_no_delete')
            conn.execute('DELETE FROM revisions WHERE object_id=? AND revision=1', (first.id,))
        elif fault == 'sha':
            conn.execute('UPDATE revisions SET sha256=? WHERE object_id=?', ('0' * 64, first.id))
        else:
            altered = first.model_dump()
            if fault == 'actual_type':
                altered = dm.Lesson(id=first.id, revision=1, title='伪造类型', objectives=[],
                    block_refs=[reference(first)]).model_dump()
            elif fault == 'actual_id':
                altered['id'] = 'changed_identity'
            elif fault == 'actual_revision':
                altered['revision'] = 2
            else:
                altered['title'] = '存储故障：历史元数据改变'
            raw = b'{' if fault == 'malformed_json' else canonical_bytes(altered)
            conn.execute('UPDATE revisions SET metadata_json=?,sha256=? WHERE object_id=?',
                (raw.decode(), sha256_bytes(raw), first.id))
        before = conn.total_changes
        code = 'REFERENCE_MISSING' if fault == 'missing' else 'CONTENT_HASH_MISMATCH'
        error(code, lambda: source.revalidate_targets(conn, identity, original))
        error(code, lambda: source.resolve_targets(conn, identity, [reference(first)]))
        assert conn.total_changes == before and canonical_bytes(original) == frozen


@pytest.mark.parametrize('fault', ['metadata', 'ref', 'metadata_type', 'nested_construct', 'duplicate', 'over_limit'])
def test_forged_frozen_material_does_not_replace_original_snapshot(targets, fault):
    database, identity, _, source, lesson, first, _ = targets
    original = resolve(targets, [reference(first)])
    frozen = canonical_bytes(original)
    item = original[0]
    if fault == 'metadata':
        item = item.model_copy(update={'metadata': first.model_copy(update={'title': '伪造内容'})})
    elif fault == 'ref':
        item = item.model_copy(update={'ref': reference(first).model_copy(update={'revision': 2})})
    elif fault == 'metadata_type':
        item = item.model_copy(update={'metadata': lesson})
    elif fault == 'nested_construct':
        item = item.model_copy(update={'metadata': first.model_copy(update={'revision': True})})
    expected = [item] * (2 if fault == 'duplicate' else 34 if fault == 'over_limit' else 1)
    with database.transaction() as conn:
        before = conn.total_changes
        code = 'AUTHORING_TARGET_INVALID' if fault in {'duplicate', 'over_limit'} else 'CONTENT_HASH_MISMATCH'
        error(code, lambda: source.revalidate_targets(conn, identity, expected))
        assert canonical_bytes(original) == frozen and conn.total_changes == before


def test_current_policy_is_rechecked_for_learner_author_and_empty_inputs(targets):
    database, identity, publisher, source, _, first, _ = targets
    original = resolve(targets, [reference(first)])
    fixture = assessment_fixture('targets_policy')
    publisher.publish(identity.workspace_id, fixture.public_objects, fixture.bodies)
    with database.transaction() as conn:
        # Actual unreviewed synthetic answers are needed for real attempt preflight.
        for answer in fixture.solutions:
            conn.execute('INSERT INTO solutions(question_id,question_revision,solution_revision,private_json,sha256,review_status) '
                'VALUES(?,?,?,?,?,?)', (answer.question_ref.id, answer.question_ref.revision, answer.revision,
                    canonical_bytes(answer).decode(), metadata_sha256(answer), answer.review_status))
    learner = replace(identity, role='learner')
    with database.transaction() as conn:
        assert source.resolve_targets(conn, learner, [reference(first)]) == original
    AssessmentService(database).create_attempt(learner, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode='independent'), 'targets-start')
    with database.transaction() as conn:
        before = conn.total_changes
        for actor in (identity, learner):
            error('ASSESSMENT_ACTIVE', lambda: source.resolve_targets(conn, actor, [reference(first)]))
            error('ASSESSMENT_ACTIVE', lambda: source.revalidate_targets(conn, actor, original))
            error('ASSESSMENT_ACTIVE', lambda: source.resolve_targets(conn, actor, []))
            error('ASSESSMENT_ACTIVE', lambda: source.revalidate_targets(conn, actor, []))
        assert conn.total_changes == before


def test_storage_failure_is_safe_and_has_no_repair_write(targets):
    database, identity, _, source, _, first, _ = targets
    with database.transaction() as conn:
        conn.execute('ALTER TABLE revisions RENAME TO unavailable_synthetic_revisions')
        before = conn.total_changes
        result = error('CONTENT_STORAGE_UNAVAILABLE', lambda: source.resolve_targets(conn, identity, [reference(first)]))
        assert result.status == 503 and result.retryable and conn.total_changes == before
        assert 'unavailable_synthetic' not in result.message and 'sqlite' not in result.message.lower()


def test_connection_from_other_database_cannot_be_substituted_by_constructor_database(targets, tmp_path):
    _, identity, _, source, _, first, _ = targets
    with sqlite3.connect(tmp_path / 'unrelated.sqlite3') as conn:
        conn.execute('BEGIN')
        error('CONTENT_STORAGE_UNAVAILABLE', lambda: source.resolve_targets(conn, identity, [reference(first)]))
