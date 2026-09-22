"""Real original-content submissions, grading transactions and immutable evidence.

The one approved-answer fixture is a controlled rule precondition, never a claim
that an imported reference has actually received expert approval.
"""

from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.assessment import AssessmentService
from services.api.app.application.evidence import EvidenceRecovery, EvidenceService, checked_submission_basis, history, record_grade_finalized
from services.api.app.application.errors import ApiError
from services.api.app.application.grading import GradingService, GradingWorker
from services.api.app.application.imports import ImportService
from services.api.app.application.practice import PracticeService
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.draft_candidate_repository import DraftCandidateRepository
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.infrastructure.security import SessionIdentity, consume_bootstrap, issue_bootstrap_code
from services.api.app.main import create_app
from services.api.app.practice_dto import PracticeSessionCreate, PracticeSolutionRequest
from tests.assessment_fixtures import assessment_fixture
from tests.integration.test_assessment_attempts import import_fixture, insert_answer, start, storage as assessment_storage
from tests.integration.test_assessment_grading import real_author, review_request


@pytest.fixture
def storage(tmp_path):
    return assessment_storage.__wrapped__(tmp_path)


def submit(storage, key='first', mode='independent'):
    _, identity, _, assessment = storage
    attempt = start(storage, key=key, mode=mode)
    return assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=attempt.revision), key + '-submit')


def counts(database):
    tables = ('attempts', 'grades', 'assessment_grade_audits', 'learning_events', 'outbox', 'jobs', 'job_events',
              'learning_submission_bases', 'learning_grade_bindings', 'learning_evidence_refs', 'evidence', 'idempotency')
    with database.connect() as connection:
        return {table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in tables}


def raw_history(database):
    with database.connect() as connection:
        return {table: [tuple(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY rowid')]
                for table in ('grades', 'assessment_grade_audits', 'assessment_manual_reviews', 'learning_submission_bases',
                              'learning_grade_bindings', 'evidence', 'learning_evidence_refs')}


def manual(storage, attempt_id, revision=1, key='manual'):
    database, _, fixture, _ = storage
    service = GradingService(database)
    service.regrade(real_author(database), attempt_id, review_request(fixture, revision=revision), key)
    assert GradingWorker(database).run_once()


def test_freeze_insert_failure_rolls_back_submit_event_queue_and_replay_receipt(storage):
    database, identity, _, assessment = storage
    attempt = start(storage)
    before = counts(database)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER injected_basis_failure BEFORE INSERT ON learning_submission_bases BEGIN SELECT RAISE(ABORT,'synthetic basis failure'); END")
    with pytest.raises(ApiError) as rejected:
        assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'retry-submit')
    assert rejected.value.code == 'ASSESSMENT_STORAGE_UNAVAILABLE'
    assert counts(database) == before
    assert assessment.get_attempt(identity, attempt.id).status == 'active'
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER injected_basis_failure')
    first = assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'retry-submit')
    after = counts(database)
    assert assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'retry-submit') == first
    assert counts(database) == after
    assert after['learning_submission_bases'] == 1


def test_worker_reads_frozen_non_score_prerequisites_before_first_rule_and_never_counts_itself_seen(storage, monkeypatch):
    import services.api.app.application.grading as grading
    database, identity, fixture, _ = storage
    attempt = submit(storage)
    original = grading.grade_item
    observed = []
    def check_before_score(**kwargs):
        with database.connect() as connection:
            basis = checked_submission_basis(connection, identity.workspace_id, attempt.id)
            assert basis.prerequisites is not None
            observed.append(basis.prerequisites_sha256)
            assert {item.prerequisites.prior_seen for item in basis.prerequisites.items} == {'unseen'}
            assert all(item.prerequisites.pre_submission_help_state == 'none' for item in basis.prerequisites.items)
            assert 'score' not in basis.prerequisites.model_dump_json().replace('max_score', '')
        return original(**kwargs)
    monkeypatch.setattr(grading, 'grade_item', check_before_score)
    assert GradingWorker(database).run_once()
    assert len(observed) == len(fixture.questions) and len(set(observed)) == 1
    with database.connect() as connection:
        entries = history(connection, identity.workspace_id, attempt.id)
        assert len(entries) == 1
        assert all(item.freshness == 'novel' and item.independence == 'independent' for item in entries[0].items)
        assert all(not item.eligible and item.score is None and 'ANSWER_UNREVIEWED' in item.reason_codes for item in entries[0].items)


def test_final_evidence_insert_failure_rolls_back_real_completed_grade_event_and_job(storage):
    database, identity, _, _ = storage
    attempt = submit(storage)
    worker = GradingWorker(database)
    lease = worker.claim()
    assert lease is not None
    result, audit = worker.compute(lease)
    before = counts(database)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER injected_evidence_failure BEFORE INSERT ON learning_evidence_refs BEGIN SELECT RAISE(ABORT,'synthetic final evidence failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        worker.finish(lease, result, audit)
    assert counts(database) == before
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER injected_evidence_failure')
    assert worker.finish(lease, result, audit)
    after = counts(database)
    assert after['grades'] == after['learning_grade_bindings'] == 1
    with database.transaction() as connection:
        again = record_grade_finalized(connection, identity.workspace_id, attempt.id, 1)
        assert again.grading_revision == 1
    assert counts(database) == after


def test_regrade_keeps_old_bytes_and_current_projection_uses_only_latest_successful_version(storage):
    database, identity, fixture, _ = storage
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    original = raw_history(database)
    manual(storage, attempt.id)
    current = EvidenceService(database).page(identity.workspace_id)
    assert len(current.items) == len(fixture.questions)
    assert all(item.score == .5 and not item.eligible and 'ANSWER_UNREVIEWED' in item.reason for item in current.items)
    with database.connect() as connection:
        versions = history(connection, identity.workspace_id, attempt.id)
        assert [item.grading_revision for item in versions] == [1, 2]
        assert all(item.score is None for item in versions[0].items)
        assert {item.id for item in current.items} == {identifier for item in versions[1].items for identifier in item.evidence_ids}
    after = raw_history(database)
    for table, rows in original.items():
        assert after[table][:len(rows)] == rows
    assert len(after['learning_submission_bases']) == 1


def test_original_approved_rule_fixture_can_contribute_zero_without_claiming_expert_approval(storage):
    database, identity, fixture, _ = storage
    for answer in fixture.solutions:
        insert_answer(database, answer.model_copy(update={'revision': 2, 'review_status': 'approved'}))
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    current = EvidenceService(database).page(identity.workspace_id)
    admitted = [item for item in current.items if item.eligible]
    assert admitted and all(item.score == 0 and item.reason == 'ELIGIBLE_INDEPENDENT_NOVEL' for item in admitted)
    assert all(item.score is None for item in current.items if 'GRADE_UNRESOLVED' in item.reason)
    assert len(current.items) == len(fixture.questions)
    with database.connect() as connection:
        frozen = checked_submission_basis(connection, identity.workspace_id, attempt.id)
        assert frozen.prerequisites and all(item.prerequisites.answer_review_status == 'approved' for item in frozen.prerequisites.items)


def test_post_submission_real_help_does_not_rewrite_original_qualification_or_signed_history(storage):
    database, identity, fixture, _ = storage
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    manual(storage, attempt.id)
    original = raw_history(database)
    before = EvidenceService(database).page(identity.workspace_id)
    practice = PracticeService(database)
    session = practice.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), 'after-test-practice')
    practice.solution(identity, session.id, PracticeSolutionRequest(expected_revision=session.revision,
        question_id=fixture.questions[0].id), 'after-test-solution')
    assert EvidenceService(database).page(identity.workspace_id) == before
    assert raw_history(database) == original
    with database.connect() as connection:
        assert len(history(connection, identity.workspace_id, attempt.id)) == 2


def test_missing_new_basis_fails_before_grading_and_cannot_be_reclassified_as_legacy(storage):
    database, identity, _, _ = storage
    attempt = submit(storage)
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER evidence_basis_no_delete')
        connection.execute('DELETE FROM learning_submission_bases WHERE attempt_id=?', (attempt.id,))
    before = counts(database)
    with database.connect() as connection, pytest.raises(ApiError) as rejected:
        checked_submission_basis(connection, identity.workspace_id, attempt.id)
    assert rejected.value.code == 'EVIDENCE_PREREQUISITES_INVALID'
    assert GradingWorker(database).run_once()
    assert counts(database)['grades'] == before['grades'] == 0
    assert counts(database)['learning_submission_bases'] == 0
    assert GradingService(database).job(identity, _grading_job(database, attempt.id)).status == 'failed'


def _grading_job(database, attempt_id):
    with database.connect() as connection:
        return connection.execute('SELECT job_id FROM assessment_grade_jobs WHERE attempt_id=? ORDER BY sequence DESC', (attempt_id,)).fetchone()[0]


def test_evidence_paging_binds_filters_workspace_limit_watermark_and_reads_never_write(storage):
    database, identity, _, _ = storage
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    service = EvidenceService(database)
    before = raw_history(database)
    first = service.page(identity.workspace_id, limit=2)
    assert len(first.items) == 2 and first.next_cursor
    second = service.page(identity.workspace_id, limit=2, cursor=first.next_cursor)
    assert {item.id for item in first.items}.isdisjoint({item.id for item in second.items})
    for arguments in ({'limit': 3}, {'limit': 2, 'concept_id': 'concept_other'}, {'limit': 2, 'skill': 'derive'}):
        with pytest.raises(ApiError) as invalid:
            service.page(identity.workspace_id, cursor=first.next_cursor, **arguments)
        assert invalid.value.code == 'CURSOR_INVALID'
    assert raw_history(database) == before
    manual(storage, attempt.id)
    with pytest.raises(ApiError) as expired:
        service.page(identity.workspace_id, limit=2, cursor=first.next_cursor)
    assert expired.value.code == 'CURSOR_EXPIRED'
    all_current = service.page(identity.workspace_id)
    assert len(all_current.items) == 5
    assert all(item.score == .5 for item in all_current.items)


def test_http_evidence_queries_are_strict_read_only_and_other_active_attempt_blocks_old_results(storage):
    database, identity, _, assessment = storage
    token, _ = consume_bootstrap(database, issue_bootstrap_code(database))
    client = TestClient(create_app(database.settings), base_url='http://127.0.0.1:8765')
    client.cookies.set('learning_session', token)
    assert client.get('/api/v1/learning/evidence').json() == {'items': [], 'next_cursor': None}
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    before = counts(database)
    for query in ('?unknown=1', '?limit=1&limit=2', '?limit=101', '?skill=guess', '?revision=1'):
        assert client.get('/api/v1/learning/evidence' + query).status_code == 422
    assert client.get('/api/v1/learning/evidence').status_code == 200
    assert counts(database) == before
    active = start(storage, key='other')
    assert client.get('/api/v1/learning/evidence').status_code == 409
    assert client.get(f'/api/v1/attempts/{attempt.id}/result').status_code == 409
    assessment.abandon(identity, active.id, dm.AttemptSubmit(expected_revision=1), 'end-other')


def legacy_storage(tmp_path, monkeypatch, *, two=False):
    """Compatibility fixture: real six-migration storage and original grading.

    Only later evidence hooks and candidate registration are disabled while
    constructing old-style rows; no grades, signatures or submission JSON are
    manufactured by this fixture. All hooks return before the real upgrade.
    """
    import services.api.app.application.evidence as evidence
    migrations = tmp_path / 'six-migrations'
    migrations.mkdir()
    for path in Path('migrations').glob('000[1-6]_*.sql'):
        shutil.copyfile(path, migrations / path.name)
    settings = Settings(data_dir=tmp_path / 'legacy-data', migrations_dir=migrations)
    database = Database(settings)
    workspace = database.initialize()
    identity = SessionIdentity('session_legacy_fixture', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    fixture = assessment_fixture('legacyevidence')
    storage = database, identity, fixture, AssessmentService(database)

    def legacy_producer_registration(repository, value):
        # Model the six-migration producer, which predates the M6.2 catalog.
        # Never allow this fixture override to mask a failure on current storage.
        assert repository.connection.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0] == 6
        assert repository.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name='draft_candidate_identities'").fetchone() is None
        assert value.owner == value.source_kind == 'import'

    with monkeypatch.context() as patch:
        patch.setattr(DraftCandidateRepository, 'register', legacy_producer_registration)
        patch.setattr(EvidenceRecovery, 'run_once', lambda self: False)
        patch.setattr(evidence, 'freeze_submission_prerequisites', lambda *args: None)
        patch.setattr(evidence, 'checked_submission_basis', lambda *args: None)
        patch.setattr(evidence, 'record_grade_finalized', lambda *args: None)
        import_fixture(database, identity, fixture, 'legacy-import')
        old = submit(storage, key='legacy', mode='open_book')
        assert GradingWorker(database).run_once()
        # Actual signed human review is retained byte for byte across migration.
        manual(storage, old.id)
        second = submit(storage, key='second-legacy', mode='open_book') if two else None
        if second:
            assert GradingWorker(database).run_once()
        active = start(storage, key='legacy-active', mode='open_book')
    with database.connect() as connection:
        immutable = {table: [tuple(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in ('grades', 'assessment_grade_audits', 'assessment_manual_reviews')}
        submissions = [tuple(row) for row in connection.execute('SELECT id,submission_json,submission_sha256,submitted_responses_json FROM attempts ORDER BY id')]
    new_database = Database(replace(settings, migrations_dir=Settings().migrations_dir))
    new_database.initialize()
    return (new_database, identity, fixture, AssessmentService(new_database)), old, second, active, immutable, submissions


def test_migration_marks_only_old_submissions_legacy_and_recovery_never_rewrites_grades(tmp_path, monkeypatch):
    storage, old, _, active, immutable, submissions = legacy_storage(tmp_path, monkeypatch)
    database, identity, _, assessment = storage
    with database.connect() as connection:
        rows = connection.execute('SELECT attempt_id,basis,prerequisites_json FROM learning_submission_bases').fetchall()
        assert [tuple(row) for row in rows] == [(old.id, 'history_not_frozen', None)]
    before = counts(database)
    with pytest.raises(ApiError) as pending:
        GradingService(database).result(identity, old.id)
    assert pending.value.code == 'EVIDENCE_RECOVERY_PENDING'
    assert counts(database) == before
    recovery = EvidenceRecovery(database)
    assert recovery.run_once() and recovery.run_once() and not recovery.run_once()
    with database.connect() as connection:
        entries = history(connection, identity.workspace_id, old.id)
        assert [item.grading_revision for item in entries] == [1, 2]
        assert all(entry.qualification_basis == 'history_not_frozen' for entry in entries)
        assert all('HISTORY_PREREQUISITES_NOT_FROZEN' in item.reason_codes and not item.eligible for entry in entries for item in entry.items)
        assert all(entry.qualification_recorded_at > entry.finalized_at for entry in entries)
        for table, original in immutable.items():
            assert [tuple(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY rowid')] == original
        assert [tuple(row) for row in connection.execute('SELECT id,submission_json,submission_sha256,submitted_responses_json FROM attempts ORDER BY id')] == submissions
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
    restarted = Database(database.settings)
    restarted.initialize()
    assert not EvidenceRecovery(restarted).run_once()
    manual(storage, old.id, revision=2, key='new-legacy-review')
    with database.connect() as connection:
        entries = history(connection, identity.workspace_id, old.id)
        assert all('HISTORY_PREREQUISITES_NOT_FROZEN' in item.reason_codes for item in entries[-1].items)
    assessment.submit(identity, active.id, dm.AttemptSubmit(expected_revision=1), 'actual-new-submit')
    with database.connect() as connection:
        assert checked_submission_basis(connection, identity.workspace_id, active.id).basis == 'submission_frozen'


def test_corrupt_legacy_grade_is_quarantined_without_starving_valid_grade_or_safe_import(tmp_path, monkeypatch):
    storage, old, _, active, _, _ = legacy_storage(tmp_path, monkeypatch)
    database, identity, _, assessment = storage
    with database.transaction() as connection:
        connection.execute("UPDATE outbox SET payload_json='{}' WHERE event_type='assessment.grading.requested' AND json_extract(payload_json,'$.attempt_id')=?", (old.id,))
    valid = assessment.submit(identity, active.id, dm.AttemptSubmit(expected_revision=1), 'new-valid')
    ingestion = ImportService(database)
    staged = ingestion.stage(identity, data=b'# Safe original text\n\nRetained.', filename='valid.txt', kind='text', key='safe-import')
    worker = ImportWorker(database)
    assert worker.run_once()
    assert worker.run_once()
    assert GradingService(database).result(identity, valid.id).grading_revision == 1
    preview = ingestion.preview(identity, staged.import_id)
    assert preview.status == 'preview_ready'
    # The legacy-only override ended before migration. The real post-upgrade
    # producer must already have registered every safe-import candidate.
    assert preview.preview_refs
    with database.transaction(immediate=False) as connection:
        catalog = DraftCandidateRepository(connection)
        for draft_id in preview.preview_refs:
            registered = catalog.lookup(identity.workspace_id, draft_id, 1)
            assert registered.owner == registered.source_kind == 'import'
    with database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM learning_evidence_recovery_failures WHERE attempt_id=?', (old.id,)).fetchone()[0] == 2
        assert connection.execute('SELECT COUNT(*) FROM learning_grade_bindings WHERE attempt_id=?', (old.id,)).fetchone()[0] == 0
    assert not worker.run_once()


@pytest.mark.parametrize('table,statement', [
    ('learning_submission_bases', "UPDATE learning_submission_bases SET rule_version='forged'"),
    ('learning_grade_bindings', "DELETE FROM learning_grade_bindings"),
    ('learning_evidence_refs', "UPDATE learning_evidence_refs SET skill='derive'"),
    ('evidence', "DELETE FROM evidence"),
])
def test_published_evidence_tables_refuse_mutation(storage, table, statement):
    database, _, _, _ = storage
    submit(storage)
    assert GradingWorker(database).run_once()
    before = raw_history(database)
    with pytest.raises(sqlite3.IntegrityError), database.transaction() as connection:
        connection.execute(statement)
    assert raw_history(database) == before


def test_stored_qualification_tamper_is_rejected_even_with_recomputed_json_hash(storage):
    from packages.contracts.canonical import canonical_bytes, sha256_bytes
    database, identity, _, _ = storage
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    with database.transaction() as connection:
        row = connection.execute('SELECT binding_json FROM learning_grade_bindings').fetchone()
        value = json.loads(row[0])
        value['items'][0]['prerequisites']['answer_review_status'] = 'approved'
        data = canonical_bytes(value)
        connection.execute('DROP TRIGGER evidence_binding_no_update')
        connection.execute('UPDATE learning_grade_bindings SET binding_json=?,binding_sha256=?', (data.decode(), sha256_bytes(data)))
    with pytest.raises(ApiError) as invalid:
        GradingService(database).result(identity, attempt.id)
    assert invalid.value.code == 'EVIDENCE_HISTORY_INVALID'
