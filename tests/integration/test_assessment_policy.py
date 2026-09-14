"""Independent real-SQLite policy checks around existing disclosure entry points."""

from dataclasses import replace

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.application.assessment_content import AssessmentContent
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.application.policy import Policy, guard_attempt_access
from services.api.app.application.practice import PracticeService
from services.api.app.application.practice_history import PracticeHistory
from services.api.app.application.reader import ReaderService
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import utc_now
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.import_dto import JobCancelRequest
from services.api.app.practice_dto import PracticeHintRequest, PracticeSessionCreate, PracticeSolutionRequest
from tests.integration.test_assessment_learning_port import assessment_learning_state

state = assessment_learning_state


def start(state, mode='independent', key='assessment-start'):
    _, identity, fixture, service = state
    return service.create_attempt(identity, fixture.assessment.id,
        dm.AttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), key)


def blocked(code, callback):
    with pytest.raises(ApiError) as error:
        callback()
    assert error.value.code == code


def practice(state):
    database, identity, fixture, _ = state
    service = PracticeService(database)
    session = service.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), 'practice-start')
    return service, session


def test_calculation_numeric_answer_and_review_fallback_both_freeze_without_declaring_grades(state):
    database, identity, fixture, _ = state
    with database.transaction() as connection:
        content = AssessmentContent(connection, identity.workspace_id)
        bundle = content.question_bundle(fixture.assessment)
        original = next(pin for pin in bundle.private_pins if pin.question_ref.id == fixture.questions[3].id)
        assert content.solution(original).grading_kind == 'numeric_tolerance'
        assert content.preflight(fixture.assessment).review_statuses == ('needs_review',) * 5
        changed = content.solution(original).model_copy(update={'revision': 2, 'grading_kind': 'rubric_review', 'review_status': 'draft'})
        connection.execute('INSERT INTO solutions VALUES(?,?,?,?,?,?)', (changed.question_ref.id, changed.question_ref.revision,
            changed.revision, canonical_bytes(changed).decode(), metadata_sha256(changed), changed.review_status))
        refreshed = content.question_bundle(fixture.assessment)
        assert refreshed.private_pins[3].solution_revision == 2
        assert content.solution(original).grading_kind == 'numeric_tolerance'
        assert content.preflight(fixture.assessment).startable
    attempt = start(state)
    assert attempt.preflight.grading.status == 'unreviewed' and attempt.grading_status == 'not_graded'


def test_one_historical_course_is_required_to_witness_the_entire_exact_concept_set(state):
    database, identity, fixture, _ = state
    content_service = ContentService(database)
    second = fixture.concept.model_copy(update={'id': 'concept_second'})
    second_course = fixture.course.model_copy(update={'id': 'course_second', 'concept_refs': [reference(second)]})
    newer = fixture.concept.model_copy(update={'revision': 2, 'title': '概念第二修订'})
    newer_course = fixture.course.model_copy(update={'revision': 2, 'concept_refs': [reference(newer)]})
    content_service.publish(identity.workspace_id, [second, second_course, newer, newer_course], {})
    with database.transaction() as connection:
        content = AssessmentContent(connection, identity.workspace_id)
        frozen_dependencies = content.concepts(content.questions(fixture.assessment))
        assert frozen_dependencies == (reference(fixture.concept),)
        assert content.course_witnesses(frozen_dependencies, fixture.course.id) == (reference(fixture.course),)
        assert content.course_witnesses([reference(fixture.concept), reference(second)]) == ()
        assert content.course_witnesses([reference(fixture.concept)], second_course.id) == ()
        assert content.catalog() == (fixture.assessment,)


def test_missing_or_damaged_private_binding_never_becomes_a_partial_allocation(state):
    database, identity, fixture, _ = state
    with database.transaction() as connection:
        connection.execute('DELETE FROM solutions WHERE question_id=?', (fixture.questions[0].id,))
        connection.execute('DROP TRIGGER solution_no_update')
        connection.execute('UPDATE solutions SET sha256=? WHERE question_id=?', ('0' * 64, fixture.questions[1].id))
        content = AssessmentContent(connection, identity.workspace_id)
        preflight = content.preflight(fixture.assessment)
        assert not preflight.startable and preflight.review_statuses[:2] == ('missing', 'damaged')
        assert preflight.reason_codes == ('answer_missing', 'answer_damaged')
    blocked('ASSESSMENT_ANSWER_UNAVAILABLE', lambda: start(state))
    with database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM attempts').fetchone()[0] == 0


@pytest.mark.parametrize('kind,status', [('tutor', 'queued'), ('authoring', 'running'), ('codex', 'awaiting_approval'), ('future_unknown', 'queued')])
def test_atomic_start_excludes_actual_subject_or_unknown_jobs_without_new_attempt(state, kind, status):
    database, identity, _, _ = state
    with database.transaction() as connection:
        now = utc_now()
        connection.execute('INSERT INTO jobs(id,workspace_id,kind,status,revision,input_sha256,input_json,created_at,updated_at) VALUES(?,?,?,?,1,?,?,?,?)',
            ('job_subject_probe', identity.workspace_id, kind, status, '1' * 64, '{}', now, now))
    blocked('SUBJECT_WORK_ACTIVE', lambda: start(state))
    with database.transaction() as connection:
        assert connection.execute('SELECT COUNT(*) FROM attempts').fetchone()[0] == 0
        connection.execute("UPDATE jobs SET status='cancelled' WHERE id='job_subject_probe'")
    assert start(state).status == 'active'


def test_start_exclusion_requires_a_transaction_and_ignores_terminal_jobs(state):
    database, identity, _, _ = state
    with database.connect() as connection:
        blocked('TRANSACTION_REQUIRED', lambda: Policy(connection, identity.workspace_id).start_exclusion('independent'))
    assert start(state).status == 'active'  # completed original-import job is not a blocker


def test_cached_practice_solution_rechecks_active_and_pending_independent_policy(state):
    database, identity, fixture, assessment = state
    practice_service, session = practice(state)
    request = PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=session.revision)
    released = practice_service.solution(identity, session.id, request, 'cached-solution')
    attempt = start(state)
    blocked('ASSESSMENT_ACTIVE', lambda: practice_service.solution(identity, session.id, request, 'cached-solution'))
    with database.transaction() as connection:
        access = guard_attempt_access(connection, identity.workspace_id, attempt.id, assessment_ref=reference(fixture.assessment))
        assert access.status == 'active'
        assert not hasattr(access, 'private_pins')
    submitted = assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=attempt.revision), 'submit')
    assert submitted.status == 'submitted'
    blocked('ASSESSMENT_ANSWER_PROTECTED', lambda: practice_service.solution(identity, session.id, request, 'cached-solution'))
    with database.transaction() as connection:
        Policy(connection, identity.workspace_id).check('subject_read')
        with pytest.raises(ApiError):
            guard_attempt_access(connection, 'workspace_other', attempt.id)
        assert connection.execute('SELECT COUNT(*) FROM practice_exposures').fetchone()[0] == 1
    assert released.review_status == 'needs_review'


@pytest.mark.parametrize('mode,hint_allowed', [('open_book', False), ('assisted', True)])
def test_open_book_and_assisted_materials_and_matching_help_follow_their_frozen_policy(state, mode, hint_allowed):
    database, identity, fixture, assessment = state
    practice_service, session = practice(state)
    hint_request = PracticeHintRequest(question_id=fixture.questions[0].id, expected_revision=1, level=1)
    hint = practice_service.hint(identity, session.id, hint_request, 'cached-hint')
    attempt = start(state, mode)
    with database.transaction() as connection:
        Policy(connection, identity.workspace_id).check('subject_read')
    def callback():
        return practice_service.hint(identity, session.id, hint_request, 'cached-hint')
    if hint_allowed:
        assert callback() == hint
    else:
        blocked('ASSESSMENT_ANSWER_PROTECTED', callback)
    answer = PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=hint.revision)
    blocked('ASSESSMENT_ANSWER_PROTECTED', lambda: practice_service.solution(identity, session.id, answer, 'answer-active'))
    assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'submit')
    assert practice_service.solution(identity, session.id, answer, 'answer-after-submit').solution_markdown


def test_pending_independent_blocks_opaque_private_original_and_preserves_safe_public_body(state):
    database, identity, fixture, assessment = state
    importer = ImportService(database)
    author = replace(identity, role='author')
    with database.connect() as connection:
        row = connection.execute('SELECT i.source_id,s.metadata_json,i.id FROM ingestion_imports i JOIN sources s ON i.source_id=s.id').fetchone()
        source_id, import_id = row['source_id'], row['id']
    original = importer.source(author, source_id)
    assert importer.download(author, original.artifact.artifact_id)[0] == fixture.archive
    assert ReaderService(database).block(author, fixture.block.id, 1).original_source.original_access == 'allowed'
    attempt = start(state)
    assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'submit')
    blocked('ASSESSMENT_ANSWER_PROTECTED', lambda: importer.source(author, source_id))
    blocked('ASSESSMENT_ANSWER_PROTECTED', lambda: importer.download(author, original.artifact.artifact_id))
    blocked('ASSESSMENT_ANSWER_PROTECTED', lambda: importer.preview(author, import_id))
    source = ReaderService(database).block(author, fixture.block.id, 1).original_source
    assert source.original_access == 'unavailable' and source.source.id == source_id
    with database.transaction() as connection:
        Policy(connection, identity.workspace_id).check('subject_read')
        assert AssessmentContent(connection, identity.workspace_id).exact(reference(fixture.block)) == fixture.block


def test_prior_seen_uses_persisted_assignments_and_preserves_unknown_import_claims(state):
    database, identity, fixture, _ = state
    with database.transaction() as connection:
        assert {item.state for item in PracticeHistory(connection, identity.workspace_id).seen(fixture.questions)} == {'unseen'}
        assert connection.execute('SELECT COUNT(*) FROM learning_events').fetchone()[0] == 0
        question = fixture.questions[0]
        event = dm.LearningEvent(event_id='event_claim', workspace_id=identity.workspace_id, actor='import',
            origin='user_supplied_import', kind='solution_revealed', ref=reference(question), occurred_at=utc_now())
        connection.execute('INSERT INTO learning_events VALUES(?,?,?,?,?,?)', (event.event_id, event.workspace_id, event.kind,
            event.origin, canonical_bytes(event).decode(), event.occurred_at))
        connection.execute('INSERT INTO exposures VALUES(?,?,?,?,?,?,?)', ('exposure_claim', identity.workspace_id,
            event.event_id, question.exposure_group, canonical_bytes(reference(question)).decode(), 'imported_claim', event.occurred_at))
        facts = PracticeHistory(connection, identity.workspace_id).seen(fixture.questions)
        assert facts[0].state == 'unknown' and facts[1].state == 'unseen'
    practice(state)
    with database.transaction() as connection:
        facts = PracticeHistory(connection, identity.workspace_id).seen(fixture.questions)
        assert {item.state for item in facts} == {'seen'}
        assert connection.execute('SELECT COUNT(*) FROM learning_events').fetchone()[0] == 1


@pytest.mark.parametrize('same_group', [True, False])
def test_pending_answer_protection_matches_exact_template_group_but_allows_unrelated_practice(state, same_group):
    database, identity, fixture, assessment = state
    other_question = fixture.questions[0].model_copy(update={'id': 'question_related_probe',
        'exposure_group': fixture.questions[0].exposure_group if same_group else 'exposure_unrelated'})
    other_practice = fixture.practice.model_copy(update={'id': 'practice_related_probe', 'question_refs': [reference(other_question)]})
    ContentService(database).publish(identity.workspace_id, [other_question, other_practice], {})
    answer = fixture.solutions[0].model_copy(update={'id': 'solution_related_probe', 'question_ref': reference(other_question)})
    with database.transaction() as connection:
        connection.execute('INSERT INTO solutions VALUES(?,?,?,?,?,?)', (answer.question_ref.id, 1, 1,
            canonical_bytes(answer).decode(), metadata_sha256(answer), answer.review_status))
    practices = PracticeService(database)
    session = practices.create_session(identity, PracticeSessionCreate(practice_ref=reference(other_practice)), 'related-practice')
    attempt = start(state)
    assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'submit')
    request = PracticeSolutionRequest(question_id=other_question.id, expected_revision=1)
    def reveal():
        return practices.solution(identity, session.id, request, 'related-answer')
    if same_group:
        blocked('ASSESSMENT_ANSWER_PROTECTED', reveal)
    else:
        assert reveal().solution_markdown == answer.solution_markdown


def test_invalid_legacy_practice_history_is_unknown_and_cannot_manufacture_freshness(state):
    database, identity, fixture, _ = state
    _, session = practice(state)
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER immutable_practice_assignment')
        connection.execute('UPDATE practice_sessions SET snapshot_sha256=? WHERE id=?', ('0' * 64, session.id))
        facts = PracticeHistory(connection, identity.workspace_id).seen(fixture.questions)
        assert {item.state for item in facts} == {'unknown'}
        assert {item.reason_codes for item in facts} == {('practice_history_incomplete',)}


def test_valid_native_hint_does_not_mark_unrelated_question_history_unknown(state):
    database, identity, fixture, _ = state
    service, session = practice(state)
    service.hint(identity, session.id, PracticeHintRequest(question_id=fixture.questions[0].id, expected_revision=1, level=1), 'actual-hint')
    other = fixture.questions[0].model_copy(update={'id': 'question_never_seen', 'exposure_group': 'exposure_never_seen'})
    ContentService(database).publish(identity.workspace_id, [other], {})
    with database.transaction() as connection:
        facts = PracticeHistory(connection, identity.workspace_id).seen([fixture.questions[0], other])
        assert [fact.state for fact in facts] == ['seen', 'unseen']



def test_private_job_cancellation_acknowledges_without_returning_blocked_cached_preview(state):
    database, identity, fixture, assessment = state
    importer = ImportService(database)
    author = replace(identity, role='author')
    staged = importer.stage(author, data=fixture.archive, filename='pending-private.learnpack.zip', kind='learnpack', key='pending-source')
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
        before = importer.job(author, staged.job.id)
        assert before.status == 'awaiting_approval' and before.warnings
        attempt = start(state)
        assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'submit')
        blocked('ASSESSMENT_ANSWER_PROTECTED', lambda: importer.job(author, staged.job.id))
        cancelled = importer.cancel_job(author, staged.job.id, JobCancelRequest(expected_revision=before.revision), 'cancel-private')
        assert cancelled.status == 'cancelled' and cancelled.warnings == [] and cancelled.result_refs == []
        assert importer.cancel_job(author, staged.job.id, JobCancelRequest(expected_revision=before.revision), 'cancel-private') == cancelled
    finally:
        worker.stop()


def test_cached_private_cancel_receipt_rechecks_later_answer_protection(state):
    database, identity, fixture, assessment = state
    importer = ImportService(database)
    author = replace(identity, role='author')
    staged = importer.stage(author, data=fixture.archive, filename='cached-private.learnpack.zip', kind='learnpack', key='cached-source')
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
        before = importer.job(author, staged.job.id)
        request = JobCancelRequest(expected_revision=before.revision)
        cancelled = importer.cancel_job(author, staged.job.id, request, 'cached-cancel')
        assert cancelled.warnings
        attempt = start(state)
        assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'submit')
        replay = importer.cancel_job(author, staged.job.id, request, 'cached-cancel')
        assert replay.status == 'cancelled' and replay.warnings == [] and replay.result_refs == []
    finally:
        worker.stop()
