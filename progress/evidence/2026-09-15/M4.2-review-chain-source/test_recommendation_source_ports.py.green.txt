"""Native grading provenance and source reads; approvals below are test preconditions."""

import json
import sqlite3

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.assessment_recommendation_access import (
    assessment_recommendation_readiness, checked_recommendation_observations,
)
from services.api.app.application.concept_states import read_concept_states
from services.api.app.application.errors import ApiError
from services.api.app.application.grading import GradingService, GradingWorker
from services.api.app.application.learning import LearningService
from services.api.app.application.profile import ProfileService
from services.api.app.application.profile import read_profile
from services.api.app.assessment_dto import RegradeItemReview, RegradeRequest
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.grading_repository import GradingRepository
from services.api.app.learning_dto import LearningActionRequest
from tests.integration.test_assessment_attempts import insert_answer, start
from tests.integration.test_assessment_grading import real_author, review_request
from tests.integration.test_learning_evidence import counts, raw_history, storage as evidence_storage, submit
from tests.integration.test_learner_profile import request as profile_request


@pytest.fixture
def storage(tmp_path):
    return evidence_storage.__wrapped__(tmp_path)


def approve_fixture_answers(database, fixture):
    for answer in fixture.solutions:
        insert_answer(database, answer.model_copy(update={'revision': 2, 'review_status': 'approved'}))


def observations(database, identity):
    with database.transaction() as connection:
        return checked_recommendation_observations(connection, identity.workspace_id)


def test_safe_sources_are_same_transaction_read_only_and_enforce_current_policy(storage):
    database, identity, fixture, _ = storage
    before = counts(database)
    with database.transaction() as connection:
        read_profile(connection, identity.workspace_id)
        read_concept_states(connection, identity.workspace_id)
        assert checked_recommendation_observations(connection, identity.workspace_id) == []
        ready = assessment_recommendation_readiness(connection, identity.workspace_id, reference(fixture.assessment))
        assert ready.preflight.startable and not ready.independent_ready
        assert 'ANSWER_UNREVIEWED' in ready.reason_codes
    assert counts(database) == before
    with database.connect() as connection:
        for port in (read_profile, read_concept_states, checked_recommendation_observations):
            with pytest.raises(ApiError) as error:
                port(connection, identity.workspace_id)
            assert error.value.code == 'TRANSACTION_REQUIRED'
    start(storage)
    with database.transaction() as connection:
        for port in (read_profile, read_concept_states, checked_recommendation_observations):
            with pytest.raises(ApiError) as error:
                port(connection, identity.workspace_id)
            assert error.value.code == 'ASSESSMENT_ACTIVE'


def test_blank_zero_is_unanswered_not_deterministic_error(storage):
    database, identity, fixture, _ = storage
    approve_fixture_answers(database, fixture)
    submit(storage)
    assert GradingWorker(database).run_once()
    before = counts(database), raw_history(database)
    rows = observations(database, identity)
    resolved = [row for row in rows if row.grading_origin == 'deterministic']
    assert len(resolved) == 4
    assert all(row.outcome == 'unanswered' and row.source.evidence.score == 0 for row in resolved)
    assert not any(row.outcome == 'incorrect' for row in rows)
    assert (counts(database), raw_history(database)) == before
    assert all(term not in rows[0].model_dump_json() for term in ('private_pin', 'accepted_answers', 'response', 'numeric'))


def test_partial_signed_review_overrides_only_covered_old_incorrect_trace(storage):
    database, identity, fixture, assessment = storage
    approve_fixture_answers(database, fixture)
    attempt = start(storage)
    saved = assessment.save_responses(identity, attempt.id, dm.ResponsesWrite(expected_revision=1,
        responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer='choice_four'),
                   dm.ResponseDraft(question_id=fixture.questions[1].id, answer='wrong')]), 'wrong-answers')
    assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=saved.revision), 'wrong-submit')
    assert GradingWorker(database).run_once()
    prior = observations(database, identity)
    assert sum(row.outcome == 'incorrect' for row in prior) == 2
    GradingService(database).regrade(real_author(database), attempt.id, review_request(fixture, count=1), 'partial-review')
    assert GradingWorker(database).run_once()
    current = {row.source.question_ref.id: row for row in observations(database, identity)}
    human = current[fixture.questions[0].id]
    assert human.grading_origin == 'human_review' and human.outcome is None
    assert human.source.evidence.score == .5 and human.source.grading_revision == 2
    untouched = current[fixture.questions[1].id]
    assert untouched.grading_origin == 'deterministic' and untouched.outcome == 'incorrect'
    assert all(row.source.submitted_at == prior[0].source.submitted_at for row in current.values())


def test_approved_does_not_claim_unsupported_grader_is_independent_ready(storage):
    database, identity, fixture, assessment = storage
    approve_fixture_answers(database, fixture)
    with database.transaction() as connection:
        initial = assessment_recommendation_readiness(connection, identity.workspace_id, reference(fixture.assessment))
    assert initial.preflight.startable and initial.preflight.grading.status == 'reviewed'
    assert not initial.independent_ready and initial.reason_codes == ['DETERMINISTIC_GRADING_UNAVAILABLE']
    attempt = start(storage, mode='open_book')
    assessment.abandon(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'abandon-seen')
    with database.transaction() as connection:
        later = assessment_recommendation_readiness(connection, identity.workspace_id, reference(fixture.assessment))
    assert 'INDEPENDENT_NOVELTY_UNAVAILABLE' in later.reason_codes
    assert {item.state for item in later.preflight.prior_seen.questions} == {'seen'}


def source_events(database):
    with database.connect() as connection:
        return [tuple(row) for row in connection.execute('SELECT * FROM recommendation_input_events ORDER BY generation')]


def all_table_rows(database):
    with database.connect() as connection:
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {table: sorted((tuple(row) for row in connection.execute(f'SELECT * FROM "{table}"')), key=repr)
                for table in tables}


@pytest.mark.parametrize('owner', ['profile', 'reading', 'allocation'])
def test_source_invalidation_failure_rolls_back_real_mutation_and_receipt_then_replay_is_once(storage, owner):
    database, identity, fixture, _ = storage
    learning = LearningService(database)
    revision = learning.progress(identity.workspace_id).revision
    code = {'profile': 'PROFILE_STORAGE_UNAVAILABLE', 'reading': 'LEARNING_STORAGE_UNAVAILABLE',
            'allocation': 'ASSESSMENT_STORAGE_UNAVAILABLE'}[owner]

    def invoke():
        if owner == 'profile':
            return ProfileService(database).save(identity, profile_request(), 'source-retry')
        if owner == 'reading':
            return learning.action(identity, LearningActionRequest(kind='read_marked', ref=reference(fixture.block),
                expected_revision=revision, value=True), 'source-retry')
        return start(storage, key='source-retry')
    before = all_table_rows(database)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER injected_recommendation_failure BEFORE INSERT ON recommendation_input_events BEGIN SELECT RAISE(ABORT,'synthetic recommendation write failure'); END")
    with pytest.raises(ApiError) as error:
        invoke()
    assert error.value.code == code and all_table_rows(database) == before
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER injected_recommendation_failure')
    old_events = source_events(database)
    saved = invoke()
    assert len(source_events(database)) == len(old_events) + 1
    after = all_table_rows(database)
    assert invoke() == saved
    assert all_table_rows(database) == after


def test_grade_refresh_failure_rolls_back_grade_evidence_job_and_keeps_lease_retryable(storage):
    database, _, _, _ = storage
    submit(storage)
    worker = GradingWorker(database)
    lease = worker.claim()
    assert lease is not None
    result, audit = worker.compute(lease)
    before = all_table_rows(database)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER injected_recommendation_failure BEFORE INSERT ON recommendation_input_events BEGIN SELECT RAISE(ABORT,'synthetic recommendation write failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        worker.finish(lease, result, audit)
    assert all_table_rows(database) == before
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER injected_recommendation_failure')
    old_events = source_events(database)
    assert worker.finish(lease, result, audit)
    assert len(source_events(database)) == len(old_events) + 1


def test_rehashed_private_blank_trace_cannot_become_a_false_error(storage):
    database, identity, fixture, _ = storage
    approve_fixture_answers(database, fixture)
    submit(storage)
    assert GradingWorker(database).run_once()
    assert not any(row.outcome == 'incorrect' for row in observations(database, identity))
    with database.transaction() as connection:
        row = connection.execute('SELECT private_json FROM assessment_grade_audits').fetchone()
        changed = json.loads(row[0])
        changed['traces'][0]['outcome'] = 'incorrect'
        changed['traces'][0]['reason_codes'] = ['choice_mismatch']
        payload = canonical_bytes(changed)
        connection.execute('DROP TRIGGER assessment_grade_audit_no_update')
        connection.execute('UPDATE assessment_grade_audits SET private_json=?,private_sha256=?',
                           (payload.decode(), sha256_bytes(payload)))
    before = all_table_rows(database)
    with pytest.raises(ApiError) as error:
        observations(database, identity)
    assert error.value.code == 'ASSESSMENT_SNAPSHOT_INVALID'
    assert all_table_rows(database) == before


def test_same_score_and_feedback_human_review_cannot_be_removed_from_origin_chain(storage):
    database, identity, fixture, assessment = storage
    approve_fixture_answers(database, fixture)
    attempt = start(storage)
    saved = assessment.save_responses(identity, attempt.id, dm.ResponsesWrite(expected_revision=1,
        responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer='choice_four')]), 'actual-wrong')
    assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=saved.revision), 'wrong-for-human')
    assert GradingWorker(database).run_once()
    with database.transaction() as connection:
        repository = GradingRepository(connection, identity.workspace_id)
        loaded = repository.load_grade(repository.attempts.load(attempt.id))
        assert loaded is not None
        original = loaded[0].items[0]
    assert original.score == 0 and original.status == 'graded'
    GradingService(database).regrade(real_author(database), attempt.id,
        RegradeRequest(expected_grading_revision=1, reason='Human explicitly keeps the same original result.',
            item_reviews=[RegradeItemReview(question_id=original.question_ref.id, score=original.score,
                feedback_markdown=original.feedback_markdown)]), 'same-score-review')
    assert GradingWorker(database).run_once()
    before_tamper = observations(database, identity)
    assert next(row for row in before_tamper if row.source.question_ref == original.question_ref).grading_origin == 'human_review'
    with database.transaction() as connection:
        row = connection.execute('SELECT private_json FROM assessment_grade_audits WHERE grading_revision=2').fetchone()
        changed = json.loads(row[0])
        assert len(changed['review_ids']) == 1
        changed['review_ids'] = []
        payload = canonical_bytes(changed)
        connection.execute('DROP TRIGGER assessment_grade_audit_no_update')
        connection.execute('UPDATE assessment_grade_audits SET private_json=?,private_sha256=? WHERE grading_revision=2',
                           (payload.decode(), sha256_bytes(payload)))
    with pytest.raises(ApiError) as error:
        observations(database, identity)
    assert error.value.code == 'ASSESSMENT_SNAPSHOT_INVALID'


@pytest.mark.parametrize('change', ['drop_first', 'drop_last', 'reverse', 'duplicate'])
def test_each_review_chain_preserves_exact_signed_job_order(storage, change):
    database, identity, fixture, _ = storage
    approve_fixture_answers(database, fixture)
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    for revision in (1, 2):
        GradingService(database).regrade(real_author(database), attempt.id,
            review_request(fixture, revision=revision, count=1), f'chain-review-{revision}')
        assert GradingWorker(database).run_once()
    assert next(row for row in observations(database, identity)
                if row.source.question_ref == fixture.assessment.question_refs[0]).grading_origin == 'human_review'
    with database.transaction() as connection:
        row = connection.execute('SELECT private_json FROM assessment_grade_audits WHERE grading_revision=3').fetchone()
        changed = json.loads(row[0])
        chain = changed['review_ids']
        assert len(chain) == 2
        changed['review_ids'] = {'drop_first': chain[1:], 'drop_last': chain[:-1],
                                 'reverse': chain[::-1], 'duplicate': [chain[0], chain[0], chain[1]]}[change]
        payload = canonical_bytes(changed)
        connection.execute('DROP TRIGGER assessment_grade_audit_no_update')
        connection.execute('UPDATE assessment_grade_audits SET private_json=?,private_sha256=? WHERE grading_revision=3',
                           (payload.decode(), sha256_bytes(payload)))
    before = all_table_rows(database)
    with pytest.raises(ApiError) as error:
        observations(database, identity)
    assert error.value.code == 'ASSESSMENT_SNAPSHOT_INVALID'
    assert all_table_rows(database) == before
