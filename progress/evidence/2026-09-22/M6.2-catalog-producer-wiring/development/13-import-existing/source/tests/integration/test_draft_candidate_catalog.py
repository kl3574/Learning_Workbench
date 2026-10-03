"""Actual producers register immutable identities; lookup never repairs or approves."""

import asyncio
from contextlib import aclosing
from dataclasses import replace
from uuid import UUID

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.draft_candidate_models import ResolvedDraftCandidate
from services.api.app.application.draft_candidates import DraftCandidates
from services.api.app.application.errors import ApiError
from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.draft_candidate_repository import DraftCandidateRepository
from services.api.app.infrastructure.security import expires_after
from tests.integration.test_authoring_numeric_provider_history import ProviderHistoryCase, table_hashes

from tests.integration.test_draft_candidate_owners import imported_candidate as original_import_fixture


@pytest.fixture
def imported_candidate(tmp_path):
    yield from original_import_fixture.__wrapped__(tmp_path)


def test_real_import_preview_already_has_exact_catalog_identity(imported_candidate):
    database, identity, _, _, _, candidate = imported_candidate
    with database.transaction(immediate=False) as connection:
        row = connection.execute(
            'SELECT i.workspace_id,i.owner,i.source_kind,i.entity,r.draft_revision,r.candidate_sha256 '
            'FROM draft_candidate_identities i JOIN draft_candidate_revisions r USING(draft_id) '
            'WHERE i.draft_id=?', (candidate.draft_id,),
        ).fetchone()
        assert row is not None
        assert tuple(row) == (identity.workspace_id, 'import', 'import', 'block', 1, candidate.candidate_sha256)


@pytest.fixture(params=['single', 'lesson', 'practice_set', 'assessment'])
def generated_candidate(request, tmp_path):
    from tests.integration.test_authoring_numeric_service import generated
    from tests.integration.test_authoring_group_numeric_service import generated_group
    state = generated.__wrapped__(tmp_path) if request.param == 'single' else generated_group(tmp_path, request.param)
    return request.param, state


def test_real_checked_generation_already_has_exact_catalog_identity(generated_candidate):
    kind, state = generated_candidate
    database, identity, _, _, candidate, *_ = state
    with database.transaction(immediate=False) as connection:
        row = connection.execute(
            'SELECT i.workspace_id,i.owner,i.source_kind,i.entity,r.draft_revision,r.candidate_sha256 '
            'FROM draft_candidate_identities i JOIN draft_candidate_revisions r USING(draft_id) '
            'WHERE i.draft_id=?', (candidate.draft_id,),
        ).fetchone()
        assert row is not None
        assert tuple(row) == (identity.workspace_id, 'authoring',
            'authoring_single' if kind == 'single' else 'authoring_group',
            'block' if kind == 'single' else kind, 1, candidate.candidate_sha256)


def test_lookup_revalidates_real_import_without_writes(imported_candidate):
    database, identity, service, _, original, candidate = imported_candidate
    before = table_hashes(database)
    with database.transaction(immediate=False) as connection:
        connection.execute('PRAGMA query_only=ON')
        result = DraftCandidates({'import': service}).lookup(
            connection, identity, candidate.draft_id, candidate.draft_revision)
    assert result.candidate == candidate and result.source_kind == 'import'
    assert service.draft(identity, candidate.draft_id) == original
    assert table_hashes(database) == before


def test_lookup_revalidates_each_real_authoring_root_without_writes(generated_candidate):
    from services.api.app.application.authoring import AuthoringService
    from services.api.app.application.authoring_group import AuthoringGroupService

    kind, state = generated_candidate
    database, identity, original, _, candidate, *_ = state
    source = 'authoring_single' if kind == 'single' else 'authoring_group'
    fresh_class = AuthoringService if kind == 'single' else AuthoringGroupService
    fresh = fresh_class(database, provider=original.provider)
    before = table_hashes(database)
    with database.transaction(immediate=False) as connection:
        connection.execute('PRAGMA query_only=ON')
        result = DraftCandidates({source: fresh}).lookup(connection, identity, candidate.draft_id, 1)
    assert result.candidate.model_dump() == candidate.model_dump()
    assert result.source_kind == source
    assert table_hashes(database) == before


@pytest.mark.parametrize(('draft_id', 'revision', 'status', 'code'), [
    (None, True, 422, 'SCHEMA_INVALID'), (None, 1.0, 422, 'SCHEMA_INVALID'),
    (None, '1', 422, 'SCHEMA_INVALID'), (None, 0, 422, 'SCHEMA_INVALID'),
    (None, 2, 412, 'DRAFT_REVISION_MISMATCH'), ('missing', 1, 404, 'DRAFT_CANDIDATE_UNREGISTERED'),
    ('', 1, 422, 'SCHEMA_INVALID'),
])
def test_lookup_requires_exact_typed_identity(imported_candidate, draft_id, revision, status, code):
    database, identity, service, _, _, candidate = imported_candidate
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught, database.transaction(immediate=False) as connection:
        connection.execute('PRAGMA query_only=ON')
        DraftCandidates({'import': service}).lookup(connection, identity,
            candidate.draft_id if draft_id is None else draft_id, revision)
    assert (caught.value.status, caught.value.code) == (status, code)
    assert table_hashes(database) == before


@pytest.mark.parametrize('change', ['role', 'revoke', 'expire'])
def test_lookup_rechecks_current_session_not_captured_author(imported_candidate, change):
    database, identity, service, _, _, candidate = imported_candidate
    if change == 'role':
        SessionService(database).switch_role(identity, RoleRequest(role='learner'), 'leave-author')
    else:
        with database.transaction() as connection:
            column = 'revoked_at' if change == 'revoke' else 'expires_at'
            connection.execute(f'UPDATE local_sessions SET {column}=? WHERE id=?',
                               ('2000-01-01T00:00:00Z', identity.id))
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught, database.transaction(immediate=False) as connection:
        DraftCandidates({'import': service}).lookup(connection, identity, candidate.draft_id, 1)
    assert (caught.value.status, caught.value.code) == (403, 'POLICY_DENIED')
    assert table_hashes(database) == before


def test_lookup_cannot_locate_another_workspace_candidate(imported_candidate):
    database, identity, service, _, _, candidate = imported_candidate
    other = replace(identity, id='other_author', workspace_id='workspace_other', csrf_token='')
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES(?, 'other', '2026-01-01T00:00:00Z')",
                           (other.workspace_id,))
        connection.execute('INSERT INTO local_sessions(id,workspace_id,token_hash,csrf_hash,role,expires_at) '
                           "VALUES(?,?,'controlled-other-token','controlled-other-csrf','author',?)",
                           (other.id, other.workspace_id, expires_after(300)))
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught, database.transaction(immediate=False) as connection:
        DraftCandidates({'import': service}).lookup(connection, other, candidate.draft_id, 1)
    assert (caught.value.status, caught.value.code) == (404, 'DRAFT_CANDIDATE_UNREGISTERED')
    assert table_hashes(database) == before


def test_valid_legacy_candidate_without_catalog_stays_unregistered_on_lookup(imported_candidate):
    database, identity, service, _, original, candidate = imported_candidate
    # Controlled historical fixture: remove only the two catalog facts, retaining
    # the complete authenticated Import history. Production lookup cannot repair it.
    with database.transaction() as connection:
        for table in ('draft_candidate_revisions', 'draft_candidate_identities'):
            connection.execute(f'DROP TRIGGER {table}_no_delete')
            connection.execute(f'DELETE FROM {table} WHERE draft_id=?', (candidate.draft_id,))
    assert service.draft(identity, candidate.draft_id) == original
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught, database.transaction(immediate=False) as connection:
        connection.execute('PRAGMA query_only=ON')
        DraftCandidates({'import': service}).lookup(connection, identity, candidate.draft_id, 1)
    assert caught.value.code == 'DRAFT_CANDIDATE_UNREGISTERED'
    assert table_hashes(database) == before


def test_catalog_hash_cannot_substitute_for_real_import_history(imported_candidate):
    database, identity, service, _, _, candidate = imported_candidate
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER draft_candidate_revisions_no_update')
        connection.execute('UPDATE draft_candidate_revisions SET candidate_sha256=? WHERE draft_id=?',
                           ('0' * 64, candidate.draft_id))
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught, database.transaction(immediate=False) as connection:
        DraftCandidates({'import': service}).lookup(connection, identity, candidate.draft_id, 1)
    assert caught.value.status == 409
    assert table_hashes(database) == before


def test_lookup_rechecks_original_checked_provider_artifact(generated_candidate):
    kind, state = generated_candidate
    case = ProviderHistoryCase('single' if kind == 'single' else 'group', state)
    before = case.damage_original_artifact()
    source = 'authoring_single' if kind == 'single' else 'authoring_group'
    with pytest.raises(ApiError) as caught, case.database.transaction(immediate=False) as connection:
        DraftCandidates({source: case.authoring}).lookup(connection, case.identity, case.candidate.draft_id, 1)
    assert (caught.value.status, caught.value.code) == (503, 'PROVIDER_INTEGRITY_INVALID')
    assert table_hashes(case.database) == before


def test_lookup_does_not_guess_an_available_wrong_owner(imported_candidate):
    database, identity, service, _, _, candidate = imported_candidate
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught, database.transaction(immediate=False) as connection:
        DraftCandidates({'authoring_single': service}).lookup(connection, identity, candidate.draft_id, 1)
    assert caught.value.code == 'DRAFT_OWNER_UNAVAILABLE'
    assert table_hashes(database) == before


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_lookup_checks_live_assessment_policy_before_returning_candidate(imported_candidate, mode):
    from services.api.app.application.assessment import AssessmentService
    from services.api.app.assessment_dto import AssessmentAttemptCreate
    from services.api.app.infrastructure.content_repository import reference
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture

    database, identity, service, _, _, candidate = imported_candidate
    fixture = assessment_fixture('lookupguard')
    import_fixture(database, identity, fixture, 'guard-material')
    attempt = AssessmentService(database).create_attempt(identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'guard-attempt')
    assert attempt.status == 'active'
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught, database.transaction(immediate=False) as connection:
        DraftCandidates({'import': service}).lookup(connection, identity, candidate.draft_id, 1)
    assert caught.value.code in {'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED', 'POLICY_DENIED'}
    assert table_hashes(database) == before


def test_learner_import_still_registers_without_granting_author_lookup(imported_candidate):
    from services.api.app.infrastructure.import_worker import ImportWorker

    database, identity, service, _, _, _ = imported_candidate
    SessionService(database).switch_role(identity, RoleRequest(role='learner'), 'leave-author')
    learner = replace(identity, role='learner')
    staged = service.stage(learner, data=b'# Learner source\n\nLearner allowed import.\n',
                           filename='learner.md', kind='markdown', key='learner-import')
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
        preview = service.preview(learner, staged.import_id)
        assert preview.preview_refs
        with database.transaction(immediate=False) as connection:
            for draft_id in preview.preview_refs:
                assert DraftCandidateRepository(connection).lookup(learner.workspace_id, draft_id, 1).owner == 'import'
        before = table_hashes(database)
        with pytest.raises(ApiError) as caught, database.transaction(immediate=False) as connection:
            DraftCandidates({'import': service}).lookup(connection, learner, preview.preview_refs[0], 1)
        assert caught.value.code == 'POLICY_DENIED'
        assert table_hashes(database) == before
    finally:
        worker.stop()


@pytest.mark.parametrize('kind', ['single', 'group'])
def test_catalog_conflict_rolls_back_original_authoring_finish_without_new_id(tmp_path, monkeypatch, kind):
    from services.api.app.application import authoring_worker, authoring_group_worker
    from tests.integration import test_authoring_provider as single
    from tests.integration import test_authoring_group_provider as group
    from tests.provider_protocol_fixture import local_provider

    async def run():
        fixture = single if kind == 'single' else group
        module = authoring_worker if kind == 'single' else authoring_group_worker
        async with local_provider(text=canonical_bytes(fixture.payload()).decode()) as server:
            state = fixture.configured(tmp_path, server.base_url)
            database, identity, service, worker, _, dispatch = state
            original, _, grant = fixture.approved(state)
            lease = worker.claim()
            assert lease is not None
            async with aclosing(dispatch.dispatch(identity, original.id, grant.id,
                                                  lease.dispatch(), asyncio.Event())) as stream:
                async for _ in stream:
                    pass
            assert len(server.requests) == 1
            prefix = 'authoring_draft_' if kind == 'single' else 'authoring_group_'
            collision_id = prefix + UUID(int=1).hex
            # Adversarial catalog claim from another owner; catalog is not itself
            # authentication. The actual producer must not overwrite or evade it.
            with database.transaction() as connection:
                DraftCandidateRepository(connection).register(ResolvedDraftCandidate(
                    identity.workspace_id, 'import', 'import', dm.DraftCandidate(
                        draft_id=collision_id, draft_revision=1, entity='block', candidate_sha256='0' * 64)))
            ids = []

            def next_identifier():
                value = UUID(int=len(ids) + 1)
                ids.append(value)
                return value

            monkeypatch.setattr(module, 'uuid4', next_identifier)
            before = table_hashes(database)
            with pytest.raises(ApiError) as caught:
                await worker.process(lease)
            assert caught.value.code == 'DRAFT_IDENTITY_CONFLICT'
            assert ids == [UUID(int=1)]
            assert table_hashes(database) == before
            current = service.read(identity, original.id)
            assert current.summary.status == 'running' and current.summary.candidate is None
            assert len(server.requests) == 1
            # This rollback is not a new permanent terminal state. Existing lease
            # recovery may consume the already checked result, never pay again.
            with database.transaction() as connection:
                connection.execute('UPDATE jobs SET lease_until=? WHERE id=?',
                                   ('2000-01-01T00:00:00Z', original.id))
            assert await asyncio.to_thread(worker.run_once)
            recovered = service.read(identity, original.id)
            assert recovered.summary.status == 'completed'
            assert recovered.summary.candidate.draft_id != collision_id
            assert len(server.requests) == 1
            with database.transaction(immediate=False) as connection:
                existing = DraftCandidateRepository(connection).lookup(identity.workspace_id, collision_id, 1)
                actual = DraftCandidates({
                    'authoring_single' if kind == 'single' else 'authoring_group': service,
                }).lookup(connection, identity, recovered.summary.candidate.draft_id, 1)
            assert existing.owner == 'import' and existing.candidate.candidate_sha256 == '0' * 64
            assert actual.candidate.model_dump() == recovered.summary.candidate.model_dump()

    asyncio.run(run())


@pytest.mark.parametrize('cross_workspace', [False, True])
def test_import_catalog_conflict_rolls_back_entire_preview_batch(imported_candidate, monkeypatch, cross_workspace):
    from services.api.app.application.import_parsing import parse_import
    from services.api.app.infrastructure import import_worker as module

    database, identity, service, _, _, _ = imported_candidate
    staged = service.stage(identity, data=b'# Second source\n\nChanged candidate body.\n',
                           filename='second.md', kind='markdown', key='collision-import')
    worker = module.ImportWorker(database)
    try:
        lease = worker.claim()
        assert lease is not None and lease.import_id == staged.import_id
        data, options = worker._input(lease)
        parsed = parse_import(data, **options)
        assert len(parsed.objects) >= 2
        conflict_id = 'draft_conflicting_second_member'
        workspace = 'workspace_other' if cross_workspace else identity.workspace_id
        with database.transaction() as connection:
            if cross_workspace:
                connection.execute("INSERT INTO workspace(id,title,created_at) VALUES(?, 'other', '2026-01-01T00:00:00Z')",
                                   (workspace,))
            DraftCandidateRepository(connection).register(ResolvedDraftCandidate(
                workspace, 'authoring', 'authoring_single', dm.DraftCandidate(
                    draft_id=conflict_id, draft_revision=1, entity='block', candidate_sha256='0' * 64)))
        allocated = []
        original_identifier = module.identifier

        def identifier(prefix):
            if prefix != 'draft':
                return original_identifier(prefix)
            value = 'draft_inserted_before_conflict' if not allocated else conflict_id
            allocated.append(value)
            return value

        monkeypatch.setattr(module, 'identifier', identifier)
        before = table_hashes(database)
        with pytest.raises(ApiError) as caught:
            worker.complete_preview(lease, parsed)
        assert caught.value.code == 'DRAFT_IDENTITY_CONFLICT'
        assert allocated == ['draft_inserted_before_conflict', conflict_id]
        assert table_hashes(database) == before
        # Existing run_once records a separate failure transaction after this
        # rolled-back preview transaction. Preserve that honest failure behavior.
        worker.fail(lease, caught.value)
        with database.connect() as connection:
            assert connection.execute('SELECT status FROM jobs WHERE id=?', (staged.job.id,)).fetchone()[0] == 'failed'
            assert connection.execute('SELECT COUNT(*) FROM drafts WHERE id IN (?,?)', tuple(allocated)).fetchone()[0] == 0
            assert connection.execute('SELECT COUNT(*) FROM draft_candidate_identities WHERE draft_id=?',
                                      (allocated[0],)).fetchone()[0] == 0
    finally:
        worker.stop()
