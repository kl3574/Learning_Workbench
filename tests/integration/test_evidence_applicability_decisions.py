"""Real imported questions, submitted attempts and graded evidence; no evidence seeding."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import sqlite3

import pytest

from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from services.api.app.application.artifacts import ArtifactsService
from services.api.app.application.concept_states import ConceptStateService
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.evidence import EvidenceService
from services.api.app.application.evidence_applicability import EvidenceApplicabilityService, current_evidence_applicability
from services.api.app.application.grading import GradingWorker
from services.api.app.application.imports import ImportService, IMPORT_ARTIFACT_PROFILES
from services.api.app.application.assessment_recommendation_access import checked_recommendation_observations
from services.api.app.evidence_applicability_dto import EvidenceImpactDecisionWrite
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
from tests.integration.test_assessment_attempts import insert_answer, start
from tests.integration.test_assessment_grading import real_author
from tests.integration.test_content_impact_snapshot import invalidation_id
from tests.integration.test_learning_evidence import storage, submit, manual

__all__ = ['storage']


def tables(database):
    with database.connect() as conn:
        names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name: sha256_bytes(repr([tuple(row) for row in conn.execute(f'SELECT * FROM "{name}"')]).encode())
                for name in names}


def protected_history(database):
    names = ('attempts', 'responses', 'assessment_attempt_snapshots', 'solutions', 'revisions',
             'grades', 'assessment_grade_audits', 'learning_events', 'evidence', 'learning_evidence_refs',
             'learning_grade_bindings', 'learning_submission_bases')
    snapshot = tables(database)
    return {name: snapshot[name] for name in names if name in snapshot}


@pytest.fixture
def case(storage):
    database, _, fixture, _ = storage
    # Controlled approved answers exercise software eligibility; no expert approval claim.
    for answer in fixture.solutions:
        insert_answer(database, answer.model_copy(update={'revision': 2, 'review_status': 'approved'}))
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    # Resolve the synthetic rubric item through the actual human regrade path;
    # otherwise the workspace correctly keeps private review material protected.
    manual(storage, attempt.id)
    author = real_author(database)
    imports = ImportService(database)
    artifacts = ArtifactsService(database, {(profile, 'import'): imports for profile in IMPORT_ARTIFACT_PROFILES})
    service = EvidenceApplicabilityService(database, artifacts)
    values = EvidenceService(database).page(author.workspace_id).items
    evidence = next(value for value in values if value.eligible)
    return database, author, fixture, service, evidence, attempt


def change(case, revision=2):
    database, author, fixture, *_ = case
    ContentService(database).publish(author.workspace_id,
        [fixture.concept.model_copy(update={'revision': revision, 'title': f'Changed concept {revision}'})], {})
    return invalidation_id(database, fixture.concept.id)


def command(view, event, *, head=0, decision='usable', reason='Explicit applicability judgment', artifacts=None):
    return EvidenceImpactDecisionWrite(event_id=event, expected_decision_revision=head,
        expected_current_basis_sha256=view.current_basis_sha256, decision=decision,
        reason=reason, evidence_artifact_ids=artifacts or [])


def rejected(status, operation, code=None):
    with pytest.raises(ApiError) as error:
        operation()
    assert error.value.status == status
    if code:
        assert error.value.code == code
    return error.value


def test_real_origin_readonly_exact_decision_and_learning_consumers(case):
    database, author, fixture, service, evidence, _ = case
    before = tables(database)
    initial = service.read(author, evidence.id)
    assert initial.applicability == 'usable' and initial.original_evidence == evidence
    assert initial.original_evidence_sha256 == metadata_sha256(evidence)
    assert initial.relevant_event_ids == [] and initial.event_decision_head is None
    assert service.read(author, evidence.id) == initial
    assert tables(database) == before
    event = change(case)
    old = protected_history(database)
    pending = service.read(author, evidence.id, event)
    assert pending.applicability == 'pending_review' and pending.event_decision_head == 0
    assert pending.relevant_event_ids == [event]
    request = command(pending, event)
    accepted = service.decide(author, evidence.id, request, 'accept-one')
    assert accepted.relevance == 'exact_ref' and accepted.decision_revision == 1
    assert accepted.actor_session_id == author.id and accepted.grading_revision == 2
    current = service.read(author, evidence.id, event)
    assert current.applicability == 'usable' and current.original_evidence == evidence
    assert current.current_basis_sha256 == pending.current_basis_sha256
    assert current.event_decision_head == 1 and current.decisions == [accepted]
    assert protected_history(database) == old
    with database.transaction() as conn:
        assert current_evidence_applicability(conn, author.workspace_id, evidence.id).status == 'usable'
        observed = checked_recommendation_observations(conn, author.workspace_id)
        assert next(item for item in observed if item.source.evidence.id == evidence.id).applicability.status == 'usable'
        assert any(item.source.evidence.id != evidence.id and item.applicability.status == 'pending_review' for item in observed)
        assert conn.execute("SELECT COUNT(*) FROM recommendation_input_events WHERE source='learning.evidence_applicability_decided'").fetchone()[0] == 1
    states = ConceptStateService(database).read(author.workspace_id)
    source = next(source for row in states.items for source in row.sources if source.evidence.id == evidence.id)
    assert source.evidence == evidence and source.applicability.status == 'usable'
    raw = current.model_dump_json()
    for secret in ('private_pins', 'accepted_answers', 'solution_markdown', 'submission_sha256', 'assignment_sha256'):
        assert secret not in raw


def test_multiple_events_id_only_replay_correction_and_new_basis(case):
    database, author, _, service, evidence, _ = case
    first = change(case)
    initial = service.read(author, evidence.id, first)
    request = command(initial, first)
    original = service.decide(author, evidence.id, request, 'first')
    second = change(case, 3)
    with database.transaction() as conn:
        conn.execute("UPDATE outbox SET delivered_at='2026-10-02T00:00:00Z' WHERE id IN (?,?)", (first, second))
    current = service.read(author, evidence.id)
    assert current.applicability == 'pending_review'
    assert set(current.relevant_event_ids) == {first, second}
    assert current.current_basis_sha256 != initial.current_basis_sha256
    stable = tables(database)
    assert service.decide(author, evidence.id, request, 'first') == original
    assert tables(database) == stable
    rejected(412, lambda: service.decide(author, evidence.id, request, 'old-basis'))
    id_only = service.decide(author, evidence.id, command(current, second), 'second')
    assert id_only.relevance == 'id_only_candidate'
    assert service.read(author, evidence.id).applicability == 'pending_review'
    service.decide(author, evidence.id, command(current, first, head=1, decision='confirmed_stale'), 'stale')
    assert service.read(author, evidence.id).applicability == 'confirmed_stale'
    fixed = service.decide(author, evidence.id, command(current, first, head=2), 'correction')
    assert fixed.decision_revision == 3 and service.read(author, evidence.id).applicability == 'usable'
    reopened = EvidenceApplicabilityService(Database(database.settings), service.artifacts)
    assert reopened.read(author, evidence.id) == service.read(author, evidence.id)
    assert reopened.decide(author, evidence.id, request, 'first') == original
    assert len(reopened.read(author, evidence.id).decisions) == 4
    # An unrelated container publication does not change the semantic basis.
    fixture = case[2]
    ContentService(database).publish(author.workspace_id, [fixture.course.model_copy(update={'revision': 2, 'title': 'Container'})], {})
    assert reopened.read(author, evidence.id).current_basis_sha256 == current.current_basis_sha256


def test_usable_does_not_clear_archive_or_upgrade_original_qualification(case, storage):
    database, author, fixture, service, evidence, _ = case
    event = change(case)
    with database.transaction() as conn:
        conn.execute("UPDATE objects SET lifecycle='archived' WHERE id=?", (fixture.concept.id,))
    view = service.read(author, evidence.id)
    service.decide(author, evidence.id, command(view, event), 'archive')
    current = service.read(author, evidence.id)
    assert current.applicability == 'pending_review'
    assert current.reason_codes == ['SEMANTIC_DEPENDENCY_NOT_ACTIVE']
    assert current.original_evidence == evidence
    # A real assisted attempt remains ineligible after a human content decision.
    with database.transaction() as conn:
        conn.execute("UPDATE objects SET lifecycle='active' WHERE id=?", (fixture.concept.id,))
    assisted = submit(storage, key='assisted', mode='assisted')
    assert GradingWorker(database).run_once()
    manual(storage, assisted.id, key='assisted-review')
    other = next(item for item in EvidenceService(database).page(author.workspace_id).items if not item.eligible)
    other_view = service.read(author, other.id)
    service.decide(author, other.id, command(other_view, event), 'ineligible')
    assert service.read(author, other.id).original_evidence == other
    assert other.eligible is False


def test_two_author_race_one_cas_winner_and_per_actor_replay(case):
    database, author, _, service, evidence, _ = case
    event = change(case)
    other = real_author(database)
    view = service.read(author, evidence.id, event)
    request = command(view, event)
    def race(identity):
        try:
            return service.decide(identity, evidence.id, request, 'same-key')
        except ApiError as error:
            return error.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(race, [author, other]))
    assert sum(isinstance(item, int) and item == 412 for item in outcomes) == 1
    receipt = next(item for item in outcomes if not isinstance(item, int))
    winner = author if receipt.actor_session_id == author.id else other
    before = tables(database)
    assert service.decide(winner, evidence.id, request, 'same-key') == receipt
    rejected(409, lambda: service.decide(winner, evidence.id, request.model_copy(update={'reason': 'Different'}), 'same-key'), 'IDEMPOTENCY_CONFLICT')
    assert tables(database) == before


def test_keyset_history_pages_freeze_membership_and_reject_scope_changes(case):
    database, author, _, service, evidence, _ = case
    first, second = change(case), change(case, 3)
    view = service.read(author, evidence.id)
    for event in (first, second):
        for head in range(2):
            service.decide(author, evidence.id, command(view, event, head=head), f'{event}_{head}')
    page = service.read(author, evidence.id, limit=1)
    assert page.next_cursor is not None and len(page.decisions) == 1
    # A later correction must not get inserted into this frozen pagination stream.
    service.decide(author, evidence.id, command(view, first, head=2), 'late')
    output = list(page.decisions)
    cursor = page.next_cursor
    while cursor:
        page = service.read(author, evidence.id, cursor=cursor, limit=1)
        output.extend(page.decisions)
        cursor = page.next_cursor
    assert len(output) == 4
    assert [(item.event_id, item.decision_revision) for item in output] == sorted((event, head) for event in (first, second) for head in (1, 2))
    filtered = service.read(author, evidence.id, first, limit=1)
    assert filtered.event_decision_head == 3 and filtered.next_cursor
    before = tables(database)
    rejected(422, lambda: service.read(author, evidence.id, second, filtered.next_cursor, 1))
    rejected(422, lambda: service.read(author, evidence.id, first, filtered.next_cursor, 2))
    rejected(422, lambda: service.read(author, evidence.id, 'event_unrelated'))
    assert tables(database) == before


def test_decision_and_recommendation_dirty_are_one_atomic_transaction(case):
    database, author, _, service, evidence, _ = case
    event = change(case)
    view = service.read(author, evidence.id)
    with database.transaction() as conn:
        conn.execute("CREATE TRIGGER injected_applicability_failure BEFORE INSERT ON recommendation_input_events "
            "WHEN NEW.source='learning.evidence_applicability_decided' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    before = tables(database)
    rejected(503, lambda: service.decide(author, evidence.id, command(view, event), 'fail'))
    assert tables(database) == before
    with database.transaction() as conn:
        conn.execute('DROP TRIGGER injected_applicability_failure')
    assert service.decide(author, evidence.id, command(view, event), 'fail').decision_revision == 1
    with database.transaction() as conn:
        for sql in ("UPDATE learning_applicability_decisions SET command_key='other'",
                    'DELETE FROM learning_applicability_decisions',
                    'INSERT OR REPLACE INTO learning_applicability_decisions SELECT * FROM learning_applicability_decisions',
                    'INSERT OR REPLACE INTO learning_applicability_decisions SELECT sequence,workspace_id,evidence_id,'
                    "event_id,decision_revision+10,actor_session_id,route,command_key||'_different',request_sha256,"
                    'record_json,record_sha256,created_at FROM learning_applicability_decisions',
                    'DELETE FROM learning_applicability_heads',
                    'INSERT OR REPLACE INTO learning_applicability_heads SELECT * FROM learning_applicability_heads',
                    'UPDATE learning_applicability_heads SET decision_revision=decision_revision+2'):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)


@pytest.mark.parametrize('damage', ['private_pin', 'evidence', 'receipt', 'snapshot', 'missing_snapshot'])
def test_corrupt_sources_events_and_receipts_fail_closed_zero_write(case, damage):
    database, author, _, service, evidence, _ = case
    event = change(case)
    view = service.read(author, evidence.id)
    request = command(view, event)
    service.decide(author, evidence.id, request, 'accepted')
    with database.transaction() as conn:
        if damage == 'private_pin':
            conn.execute('DROP TRIGGER solution_no_update')
            conn.execute("UPDATE solutions SET sha256=? WHERE question_id=?", ('0' * 64, view.question_ref.id))
        elif damage == 'evidence':
            conn.execute('DROP TRIGGER evidence_no_update')
            conn.execute('UPDATE evidence SET evidence_json=? WHERE id=?', (canonical_bytes(evidence.model_copy(update={'reason': 'fabricated'})).decode(), evidence.id))
        elif damage == 'receipt':
            conn.execute('DROP TRIGGER learning_applicability_no_update')
            conn.execute("UPDATE learning_applicability_decisions SET request_sha256=?", ('0' * 64,))
        elif damage == 'snapshot':
            conn.execute('DROP TRIGGER content_impact_snapshot_no_update')
            conn.execute('UPDATE content_impact_snapshots SET snapshot_sha256=? WHERE event_id=?', ('0' * 64, event))
        else:
            conn.execute('DROP TRIGGER content_impact_snapshot_no_delete')
            # SQLite FK is a second protection; this controlled damage removes the child first.
            conn.execute('DROP TRIGGER learning_applicability_no_delete')
            conn.execute('DELETE FROM learning_applicability_decisions')
            conn.execute('DROP TRIGGER learning_applicability_head_no_delete')
            conn.execute('DELETE FROM learning_applicability_heads')
            conn.execute('DELETE FROM content_impact_snapshots WHERE event_id=?', (event,))
    before = tables(database)
    rejected(409, lambda: service.read(author, evidence.id))
    rejected(409, lambda: service.decide(author, evidence.id, request, 'accepted'))
    assert tables(database) == before


def test_historical_grade_evidence_is_addressable_but_never_replaces_current_grade(case, storage):
    database, author, _, service, evidence, attempt = case
    manual(storage, attempt.id, revision=2, key='later-review')
    assert evidence.id not in {item.id for item in EvidenceService(database).page(author.workspace_id).items}
    event = change(case)
    old = protected_history(database)
    view = service.read(author, evidence.id)
    assert view.grading_revision == 2
    service.decide(author, evidence.id, command(view, event), 'old-grade')
    assert service.read(author, evidence.id).original_evidence == evidence
    assert protected_history(database) == old


@pytest.mark.parametrize('mode', ['independent', 'assisted', 'open_book'])
def test_current_policy_precedes_get_and_old_key_replay(case, storage, mode):
    database, author, _, service, evidence, _ = case
    event = change(case)
    request = command(service.read(author, evidence.id), event)
    service.decide(author, evidence.id, request, 'accepted')
    start(storage, key='next-' + mode, mode=mode)
    before = tables(database)
    rejected(409, lambda: service.read(author, evidence.id))
    rejected(409, lambda: service.decide(author, evidence.id, request, 'accepted'))
    assert tables(database) == before


def test_current_role_revocation_unknown_and_foreign_workspace_zero_write(case):
    database, author, _, service, evidence, _ = case
    event = change(case)
    request = command(service.read(author, evidence.id), event)
    service.decide(author, evidence.id, request, 'accepted')
    before = tables(database)
    rejected(404, lambda: service.read(author, 'evidence_unknown'))
    rejected(404, lambda: service.decide(author, evidence.id, request.model_copy(update={'event_id': 'event_unknown'}), 'unknown'))
    assert tables(database) == before
    with database.transaction() as conn:
        conn.execute("UPDATE local_sessions SET role='learner' WHERE id=?", (author.id,))
    before = tables(database)
    rejected(403, lambda: service.read(author, evidence.id))
    rejected(403, lambda: service.decide(author, evidence.id, request, 'accepted'))
    assert tables(database) == before
    with database.transaction() as conn:
        conn.execute("UPDATE local_sessions SET revoked_at='2026-10-02T00:00:00Z' WHERE id=?", (author.id,))
    rejected(401, lambda: service.read(author, evidence.id))
    _, other = consume_bootstrap(database, issue_bootstrap_code(database))
    foreign = replace(other, workspace_id='workspace_foreign', role='author')
    with database.transaction() as conn:
        conn.execute("INSERT INTO workspace(id,title,created_at) VALUES(?,'Synthetic','2026-10-02T00:00:00Z')", (foreign.workspace_id,))
        conn.execute("UPDATE local_sessions SET workspace_id=?,role='author' WHERE id=?", (foreign.workspace_id, foreign.id))
    before = tables(database)
    rejected(404, lambda: service.read(foreign, evidence.id))
    assert tables(database) == before


@pytest.mark.parametrize('damage', ['tail', 'all', 'head_hash', 'actor_workspace'])
def test_independent_head_and_historical_actor_detect_ledger_damage(case, damage):
    database, author, _, service, evidence, _ = case
    event = change(case)
    request = command(service.read(author, evidence.id), event)
    first = service.decide(author, evidence.id, request, 'first')
    service.decide(author, evidence.id, request.model_copy(update={
        'expected_decision_revision': 1, 'decision': 'confirmed_stale'}), 'second')
    reader = real_author(database)
    with database.transaction() as conn:
        if damage in {'tail', 'all'}:
            conn.execute('DROP TRIGGER learning_applicability_no_delete')
            conn.execute('DELETE FROM learning_applicability_decisions' +
                         (' WHERE decision_revision=2' if damage == 'tail' else ''))
        elif damage == 'head_hash':
            conn.execute('DROP TRIGGER learning_applicability_head_cas')
            conn.execute('UPDATE learning_applicability_heads SET receipt_sha256=?', (first.receipt_sha256,))
        else:
            conn.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_corrupt','Synthetic','2026-10-02T00:00:00Z')")
            conn.execute("UPDATE local_sessions SET workspace_id='workspace_corrupt' WHERE id=?", (author.id,))
    before = tables(database)
    rejected(409, lambda: service.read(reader, evidence.id))
    rejected(409, lambda: service.decide(reader, evidence.id, request, 'new'))
    with database.transaction(immediate=False) as conn:
        rejected(409, lambda: current_evidence_applicability(conn, reader.workspace_id, evidence.id))
    assert tables(database) == before


def test_ended_historical_author_is_preserved_but_current_reader_is_authenticated(case):
    database, author, _, service, evidence, _ = case
    event = change(case)
    receipt = service.decide(author, evidence.id, command(service.read(author, evidence.id), event), 'accepted')
    reader = real_author(database)
    with database.transaction() as conn:
        conn.execute("UPDATE local_sessions SET role='learner',revoked_at='2026-10-02T00:00:00Z' WHERE id=?", (author.id,))
    assert service.read(reader, evidence.id).decisions == [receipt]


def test_registered_artifact_bytes_are_frozen_and_rechecked_on_read_and_replay(case):
    database, author, _, service, evidence, _ = case
    event = change(case)
    with database.connect() as conn:
        artifact = conn.execute("SELECT id,blob_sha256 FROM artifacts WHERE profile='import_original' LIMIT 1").fetchone()
    view = service.read(author, evidence.id)
    request = command(view, event, artifacts=[artifact['id']])
    before = tables(database)
    rejected(404, lambda: service.decide(author, evidence.id,
        request.model_copy(update={'evidence_artifact_ids': ['artifact_unknown']}), 'unknown'))
    assert tables(database) == before
    receipt = service.decide(author, evidence.id, request, 'artifact')
    assert [(item.id, item.sha256) for item in receipt.evidence_artifacts] == [(artifact['id'], artifact['blob_sha256'])]
    assert service.read(author, evidence.id).decisions == [receipt]
    digest = artifact['blob_sha256']
    blob = database.settings.data_dir / 'blobs' / digest[:2] / digest
    assert blob.is_file()
    blob.write_bytes(b'Controlled artifact corruption')
    before = tables(database)
    rejected(409, lambda: service.read(author, evidence.id))
    rejected(409, lambda: service.decide(author, evidence.id, request, 'artifact'))
    assert tables(database) == before


def test_id_only_candidates_use_original_evidence_question_and_concept_ids(case):
    from services.api.app.application.content_impact import impact_snapshot
    from services.api.app.application.evidence_applicability import _event
    database, author, _, service, evidence, _ = case
    event = change(case)
    view = service.read(author, evidence.id)
    direct = [view.question_ref, view.concept_ref]
    prerequisite = view.concept_ref.model_copy(update={'id': 'concept_prerequisite'})
    with database.transaction(immediate=False) as conn:
        snapshot = impact_snapshot(conn, author.workspace_id, event)
    # A broad frozen closure may contain a prerequisite, but an id-only
    # collision on that prerequisite cannot become a direct evidence decision.
    id_only = replace(snapshot, old_ref=prerequisite.model_copy(update={'revision': 2}),
                      affected_ids=(prerequisite.id,), exact_dependency_refs=(), conservative_only_ids=(prerequisite.id,))
    assert _event(id_only, [*direct, prerequisite], direct) is None
    exact = replace(id_only, old_ref=prerequisite)
    assert _event(exact, [*direct, prerequisite], direct).relevance == 'exact_ref'


@pytest.mark.parametrize('boundary', ['0021', '0023'])
def test_forward_upgrade_preserves_real_old_evidence_and_never_backfills_decisions(tmp_path, monkeypatch, boundary):
    import shutil
    from services.api.app.application import content_impact as impact_module
    from services.api.app.application.assessment import AssessmentService
    from services.api.app.infrastructure.config import Settings
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture

    settings = Settings(data_dir=tmp_path / 'old-data')
    migrations = tmp_path / 'prior-migrations'
    migrations.mkdir()
    for path in settings.migrations_dir.glob('*.sql'):
        if path.name < boundary:
            shutil.copyfile(path, migrations / path.name)
    prior = Database(replace(settings, migrations_dir=migrations))
    prior.initialize()
    author = real_author(prior)
    fixture = assessment_fixture('prior')
    import_fixture(prior, author, fixture, 'old-import')
    old_case = case.__wrapped__((prior, author, fixture, AssessmentService(prior)))
    with monkeypatch.context() as patch:
        if boundary == '0021':
            # Actual pre-snapshot install, with only its absent snapshot writer disabled.
            patch.setattr(impact_module, 'freeze_impact_event', lambda *args: None)
        event = change(old_case)
    original = protected_history(prior)
    upgraded = Database(settings)
    assert upgraded.initialize() == author.workspace_id
    assert protected_history(upgraded) == original
    imports = ImportService(upgraded)
    service = EvidenceApplicabilityService(upgraded,
        ArtifactsService(upgraded, {(profile, 'import'): imports for profile in IMPORT_ARTIFACT_PROFILES}))
    evidence = old_case[4]
    view = service.read(author, evidence.id, event)
    assert view.original_evidence == evidence and view.applicability == 'pending_review'
    assert view.decisions == [] and view.event_decision_head == 0
    with upgraded.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM learning_applicability_decisions').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM learning_applicability_heads').fetchone()[0] == 0
    if boundary == '0021':
        before = tables(upgraded)
        assert 'CONTENT_CHANGE_LEGACY_UNVERIFIED' in view.reason_codes
        rejected(409, lambda: service.decide(author, evidence.id, command(view, event), 'legacy'), 'IMPACT_LEGACY_UNVERIFIED')
        assert tables(upgraded) == before
    else:
        assert service.decide(author, evidence.id, command(view, event), 'new').decision_revision == 1
    assert protected_history(upgraded) == original
