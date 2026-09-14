"""Actual graded source observations, never imported declarations or answer data."""

import pytest

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.errors import ApiError
from services.api.app.application.evidence import EvidenceService, latest_checked_observations
from services.api.app.application.grading import GradingWorker
from tests.integration.test_learning_evidence import counts, manual, raw_history, storage, submit

__all__ = ['storage']


def test_regrade_observations_keep_original_time_exact_sources_and_only_latest_success(storage):
    database, identity, fixture, _ = storage
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    with database.transaction() as connection:
        initial = latest_checked_observations(connection, identity.workspace_id)
    assert len(initial) == len(fixture.questions)
    assert all(item.evidence.score is None and not item.evidence.eligible for item in initial)
    first_time = {item.submitted_at for item in initial}
    manual(storage, attempt.id)
    before, rows = counts(database), raw_history(database)
    with database.transaction() as connection:
        current = latest_checked_observations(connection, identity.workspace_id)
    assert counts(database) == before and raw_history(database) == rows
    assert {item.submitted_at for item in current} == first_time
    assert {item.grading_revision for item in current} == {2}
    assert {item.attempt_id for item in current} == {attempt.id}
    assert {item.question_ref.id for item in current} == {item.id for item in fixture.questions}
    assert all(item.concept_ref.id == item.evidence.concept_id for item in current)
    assert all(item.assessment_ref == initial[0].assessment_ref for item in current)
    assert all(item.qualification_basis == 'submission_frozen' and 'ANSWER_UNREVIEWED' in item.reason_codes for item in current)
    assert {item.evidence.id for item in initial}.isdisjoint(item.evidence.id for item in current)
    assert [item.evidence for item in current] == EvidenceService(database).page(identity.workspace_id).items
    serialized = canonical_bytes([item.model_dump(mode='json') for item in current])
    assert not any(name in serialized for name in [b'private_pins', b'solution_markdown', b'accepted_answers', b'feedback_markdown', b'responses'])


def test_corrupt_older_grade_binding_is_not_hidden_by_newer_observations(storage):
    database, identity, _, _ = storage
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    manual(storage, attempt.id)
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER evidence_binding_no_update')
        connection.execute("UPDATE learning_grade_bindings SET binding_sha256=? WHERE attempt_id=? AND grading_revision=1", ('0' * 64, attempt.id))
    before = counts(database)
    with database.transaction() as connection, pytest.raises(ApiError) as rejected:
        latest_checked_observations(connection, identity.workspace_id)
    assert rejected.value.code == 'EVIDENCE_HISTORY_INVALID'
    assert counts(database) == before


def test_observations_require_one_transaction_and_current_subject_policy(storage):
    database, identity, _, _ = storage
    with database.connect() as connection, pytest.raises(ApiError) as rejected:
        latest_checked_observations(connection, identity.workspace_id)
    assert rejected.value.code == 'TRANSACTION_REQUIRED'
    from tests.integration.test_assessment_attempts import start
    start(storage)
    before = counts(database)
    with database.transaction() as connection, pytest.raises(ApiError) as denied:
        latest_checked_observations(connection, identity.workspace_id)
    assert denied.value.status == 409
    assert counts(database) == before
