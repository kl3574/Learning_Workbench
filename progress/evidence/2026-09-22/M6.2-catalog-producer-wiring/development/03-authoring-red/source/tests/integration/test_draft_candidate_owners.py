"""Real owner admission; catalog/FK success never means human approval or publication."""

from dataclasses import replace
import json
import shutil

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.application.authoring import AuthoringService
from services.api.app.application.authoring_group import AuthoringGroupService
from services.api.app.application.draft_candidates import DraftCandidates
from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
from tests.integration.test_authoring_numeric_provider_history import (
    ProviderHistoryCase, generated_history as history_fixture, table_hashes,
)


@pytest.fixture(params=['single', 'group'])
def generated_history(request, tmp_path):
    return history_fixture.__wrapped__(request, tmp_path)


def owner_kind(case):
    return 'authoring_group' if case.variant == 'group' else 'authoring_single'


def admit(case, candidate=None, service=None):
    candidate = dm.DraftCandidate.model_validate((candidate or case.candidate).model_dump())
    owners = DraftCandidates({owner_kind(case): service or case.authoring})
    with case.database.transaction() as conn:
        return owners.admit(conn, case.identity, owner_kind(case), candidate)


def test_admission_and_fresh_retry_preserve_original_payloads_and_do_not_create_approval(generated_history):
    case = generated_history
    before = table_hashes(case.database)
    result = admit(case)
    after = table_hashes(case.database)
    assert {name for name in before if before[name] != after[name]} == {
        'draft_candidate_identities', 'draft_candidate_revisions'}
    assert result.candidate.model_dump() == case.candidate.model_dump()
    assert result.workspace_id == case.identity.workspace_id and result.owner == 'authoring'
    assert result.source_kind == owner_kind(case)
    service_class = AuthoringGroupService if case.variant == 'group' else AuthoringService
    fresh = service_class(case.database, provider=case.authoring.provider)
    assert admit(case, service=fresh) == result
    assert table_hashes(case.database) == after
    draft = fresh.draft(case.identity, result.candidate.draft_id)
    assert draft.state == 'draft'
    assert draft.validation.mathematical == draft.validation.sources == 'NOT_RUN'
    with case.database.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM reviews').fetchone()[0] == 0


@pytest.mark.parametrize('registered', [False, True])
def test_existing_catalog_never_masks_damaged_original_provider_history(generated_history, registered):
    case = generated_history
    if registered:
        admit(case)
    before = case.damage_original_artifact()
    with pytest.raises(ApiError) as caught:
        admit(case)
    assert (caught.value.status, caught.value.code) == (503, 'PROVIDER_INTEGRITY_INVALID')
    assert table_hashes(case.database) == before


def test_missing_provider_owner_cannot_reuse_registered_candidate(generated_history):
    case = generated_history
    admit(case)
    before = table_hashes(case.database)
    service_class = AuthoringGroupService if case.variant == 'group' else AuthoringService
    with pytest.raises(ApiError) as caught:
        admit(case, service=service_class(case.database))
    assert caught.value.code == 'AUTHORING_OUTPUT_UNAVAILABLE'
    assert table_hashes(case.database) == before


@pytest.mark.parametrize(('field', 'value', 'status'), [
    ('draft_revision', 2, 412), ('candidate_sha256', '0' * 64, 409),
    ('entity', 'course', 409), ('draft_id', 'missing_candidate', 404),
])
def test_exact_identity_rejected_without_catalog_or_other_writes(generated_history, field, value, status):
    case = generated_history
    candidate = dm.DraftCandidate.model_validate({**case.candidate.model_dump(), field: value})
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught:
        admit(case, candidate)
    assert caught.value.status == status
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('change', ['role', 'revoke', 'workspace'])
def test_current_session_is_rechecked_before_exact_catalog_retry(generated_history, change):
    case = generated_history
    admit(case)
    if change == 'role':
        SessionService(case.database).switch_role(case.identity, RoleRequest(role='learner'), 'leave-author')
    else:
        with case.database.transaction() as conn:
            if change == 'revoke':
                conn.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?",
                             (case.identity.id,))
            else:
                case.state = (case.database, replace(case.identity, workspace_id='workspace_missing'), *case.state[2:])
    before = table_hashes(case.database)
    with pytest.raises(ApiError):
        admit(case)
    assert table_hashes(case.database) == before


def test_explicit_wrong_owner_does_not_fall_back_to_other_owner_table(generated_history):
    case = generated_history
    wrong = AuthoringService(case.database, provider=case.authoring.provider) if case.variant == 'group' else (
        AuthoringGroupService(case.database, provider=case.authoring.provider))
    kind = 'authoring_single' if case.variant == 'group' else 'authoring_group'
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught, case.database.transaction() as conn:
        DraftCandidates({kind: wrong}).admit(conn, case.identity, kind,
            dm.DraftCandidate.model_validate(case.candidate.model_dump()))
    assert caught.value.status == 404
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('kind', ['practice_set', 'assessment'])
def test_question_group_admits_complete_original_group_without_approving_private_answers(tmp_path, kind):
    from tests.integration.test_authoring_group_numeric_service import generated_group

    case = ProviderHistoryCase('group', generated_group(tmp_path, kind))
    original = case.authoring.draft(case.identity, case.candidate.draft_id)
    private = [case.authoring.solution(case.identity, case.candidate.draft_id, item.question.member_key)
               for item in original.private_solution_refs]
    assert len(private) == 2
    before = table_hashes(case.database)
    result = admit(case)
    after = table_hashes(case.database)
    assert result.candidate.entity == kind and result.candidate.model_dump() == case.candidate.model_dump()
    assert {name for name in before if before[name] != after[name]} == {
        'draft_candidate_identities', 'draft_candidate_revisions'}
    assert [case.authoring.solution(case.identity, case.candidate.draft_id, item.question.member_key)
            for item in original.private_solution_refs] == private
    assert table_hashes(case.database) == after


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_actual_assessment_policy_precedes_existing_identity_retry(generated_history, mode):
    from services.api.app.application.assessment import AssessmentService
    from services.api.app.assessment_dto import AssessmentAttemptCreate
    from services.api.app.infrastructure.content_repository import reference
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture

    case = generated_history
    admit(case)
    fixture = assessment_fixture('candidateguard')
    import_fixture(case.database, case.identity, fixture, 'guard-material')
    assessment = AssessmentService(case.database)
    attempt = assessment.create_attempt(case.identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'guard-attempt')
    assert attempt.status == 'active'
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught:
        admit(case)
    assert caught.value.code in {'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED', 'POLICY_DENIED'}
    assert table_hashes(case.database) == before


@pytest.fixture
def imported_candidate(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    database.initialize()
    _, learner = consume_bootstrap(database, issue_bootstrap_code(database))
    SessionService(database).switch_role(learner, RoleRequest(role='author'), 'author-role')
    identity = replace(learner, role='author')
    service = ImportService(database)
    worker = ImportWorker(database)
    try:
        staged = service.stage(identity, data=b'# Synthetic source\n\nOriginal public body.\n',
                               filename='source.md', kind='markdown', key='original-import')
        assert worker.run_once()
        preview = service.preview(identity, staged.import_id)
        draft = next(value for value in (service.draft(identity, item) for item in preview.preview_refs)
                     if value.kind == 'block')
        candidate = dm.DraftCandidate(draft_id=draft.id, draft_revision=draft.revision,
                                     entity=draft.kind, candidate_sha256=draft.candidate_sha256)
        yield database, identity, service, staged, draft, candidate
    finally:
        worker.stop()


def test_import_identity_uses_real_import_preview_and_keeps_existing_read_contract(imported_candidate):
    database, identity, service, _, original, candidate = imported_candidate
    before = table_hashes(database)
    with database.transaction() as conn:
        result = DraftCandidates({'import': service}).admit(conn, identity, 'import', candidate)
    after = table_hashes(database)
    assert result.owner == result.source_kind == 'import' and result.candidate == candidate
    assert {name for name in before if before[name] != after[name]} == {
        'draft_candidate_identities', 'draft_candidate_revisions'}
    assert service.draft(identity, candidate.draft_id) == original
    with database.transaction() as conn:
        assert DraftCandidates({'import': ImportService(database)}).admit(conn, identity, 'import', candidate) == result
    assert table_hashes(database) == after


def test_imported_question_identity_does_not_approve_or_publish_its_private_solution(imported_candidate):
    from tests.assessment_fixtures import assessment_fixture

    database, identity, service, _, _, _ = imported_candidate
    fixture = assessment_fixture('unreviewed')
    staged = service.stage(identity, data=fixture.archive, filename='author.learnpack.zip',
                           kind='learnpack', key='private-package')
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
        preview = service.preview(identity, staged.import_id)
        question = next(item for item in (service.draft(identity, draft_id) for draft_id in preview.preview_refs)
                        if item.kind == 'question')
        candidate = dm.DraftCandidate(draft_id=question.id, draft_revision=question.revision,
                                     entity='question', candidate_sha256=question.candidate_sha256)
        assert metadata_sha256(question.payload) == candidate.candidate_sha256
        with database.connect() as conn:
            raw_preview = conn.execute('SELECT preview_json FROM ingestion_imports WHERE id=?',
                                       (staged.import_id,)).fetchone()[0]
            private = [item for item in json.loads(raw_preview)['solutions']
                       if item['question_ref']['id'] == question.payload.id]
            assert private and private[0]['solution_markdown']
            assert 'solution_markdown' not in question.payload.model_dump()
        before = table_hashes(database)
        with database.transaction() as conn:
            result = DraftCandidates({'import': service}).admit(conn, identity, 'import', candidate)
        after = table_hashes(database)
        assert result.candidate == candidate
        assert {name for name in before if before[name] != after[name]} == {
            'draft_candidate_identities', 'draft_candidate_revisions'}
        with database.connect() as conn:
            for table in ['objects', 'revisions', 'solutions', 'reviews']:
                assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
            assert conn.execute('SELECT preview_json FROM ingestion_imports WHERE id=?',
                                (staged.import_id,)).fetchone()[0] == raw_preview
    finally:
        worker.stop()


@pytest.mark.parametrize('damage', ['membership', 'preview_metadata', 'body_binding', 'source_bytes'])
def test_import_registration_rechecks_original_preview_and_actual_bytes(imported_candidate, damage):
    database, identity, service, staged, draft, candidate = imported_candidate
    with database.transaction() as conn:
        DraftCandidates({'import': service}).admit(conn, identity, 'import', candidate)
        row = conn.execute('SELECT * FROM ingestion_imports WHERE id=?', (staged.import_id,)).fetchone()
        preview = json.loads(row['preview_json'])
        if damage == 'membership':
            preview['draft_ids'].remove(candidate.draft_id)
        elif damage == 'preview_metadata':
            next(item for item in preview['objects'] if item['id'] == draft.payload.metadata.id)['title'] = 'Changed'
        elif damage == 'body_binding':
            preview['bodies'][draft.payload.metadata.body_path] = '0' * 64
        else:
            blob = conn.execute('SELECT relative_path FROM content_blobs WHERE sha256=?',
                                (staged.input_sha256,)).fetchone()
            (database.settings.data_dir / blob['relative_path']).write_bytes(b'Changed source')
        conn.execute('UPDATE ingestion_imports SET preview_json=? WHERE id=?',
                     (canonical_bytes(preview).decode(), staged.import_id))
    before = table_hashes(database)
    with pytest.raises(ApiError), database.transaction() as conn:
        DraftCandidates({'import': service}).admit(conn, identity, 'import', candidate)
    assert table_hashes(database) == before


def test_caller_rollback_includes_both_identity_tables(imported_candidate):
    database, identity, service, _, _, candidate = imported_candidate
    before = table_hashes(database)
    with pytest.raises(RuntimeError, match='caller rollback'), database.transaction() as conn:
        DraftCandidates({'import': service}).admit(conn, identity, 'import', candidate)
        raise RuntimeError('caller rollback')
    assert table_hashes(database) == before


@pytest.mark.parametrize('kind', ['single', 'practice_set', 'assessment'])
def test_upgrade_of_real_original_owner_records_backfills_without_rewriting_payloads(tmp_path, monkeypatch, kind):
    from services.api.app.infrastructure.config import REPOSITORY_ROOT
    from tests.integration import test_authoring_provider as single_generation
    from tests.integration import test_authoring_group_provider as group_generation
    from tests.integration.test_authoring_group_numeric_service import generated_group
    from tests.integration.test_authoring_numeric_service import generated as single_fixture

    migrations = tmp_path / 'old_migrations'
    migrations.mkdir()
    for path in (REPOSITORY_ROOT / 'migrations').glob('*.sql'):
        if path.name < '0016_draft_candidate_identities.sql':
            shutil.copyfile(path, migrations / path.name)
    generation = single_generation if kind == 'single' else group_generation
    with monkeypatch.context() as patch:
        patch.setattr(generation, 'Settings', lambda **kwargs: Settings(migrations_dir=migrations, **kwargs))
        state = single_fixture.__wrapped__(tmp_path) if kind == 'single' else generated_group(tmp_path, kind)
    case = ProviderHistoryCase('single' if kind == 'single' else 'group', state)
    before = table_hashes(case.database)
    assert 'draft_candidate_identities' not in before
    original = case.authoring.draft(case.identity, case.candidate.draft_id)
    shutil.copyfile(REPOSITORY_ROOT / 'migrations/0016_draft_candidate_identities.sql',
                    migrations / '0016_draft_candidate_identities.sql')
    assert case.database.initialize() == case.identity.workspace_id
    after = table_hashes(case.database)
    assert {name for name in before if before[name] != after[name]} == {'schema_migrations'}
    assert case.authoring.draft(case.identity, case.candidate.draft_id) == original
    assert admit(case).candidate.model_dump() == case.candidate.model_dump()
    assert table_hashes(case.database) == after
    assert len(list((case.database.settings.data_dir / 'backups').glob('*.sqlite3'))) == 1
