"""Complete owner materials from actual producers; no review decision or vendor call."""

from dataclasses import dataclass, replace
import asyncio
import json

import pytest

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from packages.contracts import domain_models as dm
from services.api.app.application.draft_candidates import DraftCandidates
from services.api.app.application.errors import ApiError
from tests.integration.test_authoring_numeric_provider_history import ProviderHistoryCase, table_hashes
from tests.integration.test_draft_candidate_owners import imported_candidate as import_fixture, remove_catalog_fixture
from tests.integration.test_authoring_numeric_service import generated as single_fixture
from tests.integration.test_authoring_group_numeric_service import generated_group


class Imported(tuple):
    def __repr__(self):
        return '<synthetic Import material fixture; session values omitted>'


@pytest.fixture
def imported_candidate(tmp_path):
    for value in import_fixture.__wrapped__(tmp_path):
        yield Imported(value)


def checked_read(database, identity, owner, source_kind, candidate, monkeypatch):
    before = table_hashes(database)
    with database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        changes = conn.total_changes
        with monkeypatch.context() as patch:
            def unexpected_connection():
                pytest.fail('Review material must use the caller transaction')
            patch.setattr(database, 'connect', unexpected_connection)
            candidates = DraftCandidates({source_kind: owner})
            resolved = candidates.lookup(conn, identity, candidate.draft_id, candidate.draft_revision)
            material = candidates.read_review_material(conn, identity, candidate.draft_id, candidate.draft_revision)
            assert material.candidate == resolved.candidate
            assert conn.in_transaction and conn.total_changes == changes
    assert table_hashes(database) == before
    raw = material.model_dump(mode='json')
    digest = raw.pop('descriptor_sha256')
    assert sha256_bytes(canonical_bytes(raw)) == digest
    return material


def test_real_import_material_preserves_body_and_excludes_private_solutions(imported_candidate, monkeypatch):
    database, identity, owner, staged, draft, candidate = imported_candidate
    value = checked_read(database, identity, owner, 'import', candidate, monkeypatch)
    assert value.payload.payload == draft.payload
    assert value.payload.import_id == staged.import_id
    assert value.payload.original_input_sha256 == staged.input_sha256
    assert value.payload.private_solution_coverage == 'excluded'
    # The selected candidate is the heading block, not the separate paragraph.
    assert value.payload.payload.body_markdown == '# Synthetic source\n'
    assert 'state' not in value.payload.model_dump()


@pytest.mark.parametrize('kind', ['single', 'lesson', 'practice_set', 'assessment'])
def test_real_generated_material_keeps_complete_plan_members_private_and_history(tmp_path, monkeypatch, kind):
    state = single_fixture.__wrapped__(tmp_path) if kind == 'single' else generated_group(tmp_path, kind)
    database, identity, owner, _, candidate, *_ = state
    original = owner.draft(identity, candidate.draft_id)
    source_kind = 'authoring_single' if kind == 'single' else 'authoring_group'
    value = checked_read(database, identity, owner, source_kind, candidate, monkeypatch)
    assert value.payload.record.source_job_id == original.source_job_id
    assert value.payload.input.job_id == original.source_job_id
    assert value.payload.context.job_id == original.source_job_id
    table = 'authoring_candidates' if kind == 'single' else 'authoring_group_candidates'
    with database.connect() as conn:
        stored = conn.execute(f'SELECT record_sha256 FROM {table} WHERE draft_id=?', (candidate.draft_id,)).fetchone()
    assert value.owner_record_sha256 == stored['record_sha256']
    assert 'numeric_check_ids' not in value.payload.record.model_dump()
    assert 'state' not in value.payload.record.model_dump()
    if kind == 'single':
        assert value.payload.record.payload == original.payload
    else:
        payload = value.payload.record.payload
        assert payload.root == original.root
        assert payload.blocks == original.blocks and payload.questions == original.questions
        assert value.payload.plan.plan == payload.content_plan
        assert value.payload.plan.plan_ref == value.payload.record.plan_ref
        assert value.payload.private_solution_coverage == 'included_in_complete_root_sha'
        for private, ref in zip(payload.private_solutions, original.private_solution_refs, strict=True):
            assert private.question == ref.question
            assert sha256_bytes(canonical_bytes(private)) == ref.solution_sha256
            actual = owner.solution(identity, candidate.draft_id, ref.question.member_key)
            assert actual.payload == private
    # Existing numeric preview is independent; even this mutable ledger cannot
    # change the frozen review material, and no numeric executor is invoked.
    case = ProviderHistoryCase('single' if kind == 'single' else 'group', state)
    case.preview()
    after = checked_read(database, identity, owner, source_kind, candidate, monkeypatch)
    assert after == value


@dataclass(repr=False)
class MaterialCase:
    database: object
    identity: object
    owner: object
    candidate: object
    kind: str
    state: object = None

    def __repr__(self):
        return f'<synthetic {self.kind} review fixture; session values omitted>'


@pytest.fixture(params=['import', 'single', 'group'])
def material_case(request, tmp_path):
    if request.param == 'import':
        for database, identity, owner, _, _, candidate in import_fixture.__wrapped__(tmp_path):
            yield MaterialCase(database, identity, owner, candidate, 'import')
    else:
        state = single_fixture.__wrapped__(tmp_path) if request.param == 'single' else generated_group(tmp_path, 'assessment')
        database, identity, owner, _, candidate, *_ = state
        yield MaterialCase(database, identity, owner, candidate, 'authoring_' + request.param, state)


def read_case(case, identity=None, *, direct=False):
    identity = identity or case.identity
    with case.database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        if direct:
            return case.owner.read_review_material(conn, identity, case.candidate)
        return DraftCandidates({case.kind: case.owner}).read_review_material(
            conn, identity, case.candidate.draft_id, case.candidate.draft_revision)


@pytest.mark.parametrize('damage', ['revoked', 'role', 'workspace'])
def test_material_checks_actual_current_author_and_workspace_without_writes(material_case, damage):
    case = material_case
    assert read_case(case).candidate.model_dump() == case.candidate.model_dump()
    identity = case.identity
    if damage == 'workspace':
        identity = replace(identity, workspace_id='workspace_missing')
    else:
        with case.database.transaction() as conn:
            if damage == 'revoked':
                conn.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?", (identity.id,))
            else:
                conn.execute("UPDATE local_sessions SET role='learner' WHERE id=?", (identity.id,))
    before = table_hashes(case.database)
    for direct in [False, True]:
        with pytest.raises(ApiError) as caught:
            read_case(case, identity, direct=direct)
        assert caught.value.status == 403
    assert table_hashes(case.database) == before


def test_missing_catalog_never_reconstructs_or_guesses_owner(material_case):
    case = material_case
    remove_catalog_fixture(case.database, case.candidate.draft_id)
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught:
        read_case(case)
    assert (caught.value.status, caught.value.code) == (404, 'DRAFT_CANDIDATE_UNREGISTERED')
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_material_rechecks_real_active_assessment_policy(material_case, mode):
    from services.api.app.application.assessment import AssessmentService
    from services.api.app.assessment_dto import AssessmentAttemptCreate
    from services.api.app.infrastructure.content_repository import reference
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture as import_assessment

    case = material_case
    fixture = assessment_fixture('reviewpolicy')
    import_assessment(case.database, case.identity, fixture, 'review-policy-material')
    attempt = AssessmentService(case.database).create_attempt(case.identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'review-policy-attempt')
    assert attempt.status == 'active'
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught:
        read_case(case)
    assert caught.value.code in {'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED', 'POLICY_DENIED'}
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('kind', ['single', 'assessment'])
def test_material_rejects_corrupt_complete_provider_history(tmp_path, kind):
    state = single_fixture.__wrapped__(tmp_path) if kind == 'single' else generated_group(tmp_path, kind)
    original = ProviderHistoryCase('single' if kind == 'single' else 'group', state)
    before = original.damage_original_artifact()
    case = MaterialCase(original.database, original.identity, original.authoring, original.candidate,
        'authoring_single' if kind == 'single' else 'authoring_group')
    with pytest.raises(ApiError) as caught:
        read_case(case)
    assert (caught.value.status, caught.value.code) == (503, 'PROVIDER_INTEGRITY_INVALID')
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('damage', ['source_missing', 'body_missing', 'membership', 'metadata'])
def test_import_review_rejects_missing_original_bytes_or_changed_history(imported_candidate, damage):
    database, identity, owner, staged, draft, candidate = imported_candidate
    with database.transaction() as conn:
        if damage.endswith('missing'):
            digest = staged.input_sha256 if damage == 'source_missing' else draft.payload.metadata.body_sha256
            row = conn.execute('SELECT relative_path FROM content_blobs WHERE sha256=?', (digest,)).fetchone()
            (database.settings.data_dir / row['relative_path']).unlink()
        else:
            row = conn.execute('SELECT preview_json FROM ingestion_imports WHERE id=?', (staged.import_id,)).fetchone()
            preview = json.loads(row['preview_json'])
            if damage == 'membership':
                preview['draft_ids'].remove(candidate.draft_id)
            else:
                next(item for item in preview['objects'] if item['id'] == draft.payload.metadata.id)['title'] = 'Tampered'
            conn.execute('UPDATE ingestion_imports SET preview_json=? WHERE id=?', (canonical_bytes(preview).decode(), staged.import_id))
    before = table_hashes(database)
    with pytest.raises(ApiError):
        read_case(MaterialCase(database, identity, owner, candidate, 'import'))
    assert table_hashes(database) == before


def test_import_question_material_explicitly_excludes_actual_unapproved_private_answer(imported_candidate, monkeypatch):
    from services.api.app.infrastructure.import_worker import ImportWorker
    from tests.assessment_fixtures import assessment_fixture

    database, identity, owner, *_ = imported_candidate
    fixture = assessment_fixture('reviewprivate')
    staged = owner.stage(identity, data=fixture.archive, filename='synthetic.learnpack.zip',
                         kind='learnpack', key='private-material')
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
        preview = owner.preview(identity, staged.import_id)
        draft = next(item for item in (owner.draft(identity, identifier) for identifier in preview.preview_refs)
                     if item.kind == 'question')
        candidate = dm.DraftCandidate(draft_id=draft.id, draft_revision=draft.revision,
                                     entity='question', candidate_sha256=draft.candidate_sha256)
        with database.connect() as conn:
            raw = conn.execute('SELECT preview_json FROM ingestion_imports WHERE id=?', (staged.import_id,)).fetchone()[0]
        solutions = [item for item in json.loads(raw)['solutions'] if item['question_ref']['id'] == draft.payload.id]
        assert solutions and solutions[0]['solution_markdown']
        material = checked_read(database, identity, owner, 'import', candidate, monkeypatch)
        assert material.payload.payload == draft.payload
        assert material.payload.private_solution_coverage == 'excluded'
        assert 'solution_markdown' not in canonical_bytes(material).decode()
        with database.connect() as conn:
            assert conn.execute('SELECT preview_json FROM ingestion_imports WHERE id=?', (staged.import_id,)).fetchone()[0] == raw
            for table in ['objects', 'revisions', 'solutions', 'reviews']:
                assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
    finally:
        worker.stop()


def generated_with_sources(tmp_path, kind):
    """Real producer and CheckedDispatch, selecting two complete public blocks."""
    from services.api.app.infrastructure.content_repository import reference
    from services.api.app.infrastructure.security import expires_after
    from services.api.app.provider_dto import ConsentCreate, ConsentPreviewWrite, OutboundBudget
    from tests.integration import test_authoring_provider as single
    from tests.integration import test_authoring_group_provider as group
    from tests.integration.test_retrieval import publish_small
    from tests.provider_protocol_fixture import local_provider

    generation = single if kind == 'single' else group

    async def build():
        async with local_provider(text=canonical_bytes(generation.payload()).decode()) as server:
            state = generation.configured(tmp_path, server.base_url)
            database, identity, owner, worker, consents, _ = state
            blocks, _, _ = publish_small(database, identity, 'reviewsource', ['Complete source one.\n', 'Complete source two.\n'])
            refs = [reference(blocks[1]), reference(blocks[0])]
            original_body = generation.request()
            raw_body = original_body.model_dump(mode='json')
            raw_body['source_refs'] = [ref.model_dump(mode='json') for ref in refs]
            body = type(original_body).model_validate(raw_body)
            original = owner.prepare(identity, body, 'prepare-sources')
            proposal = consents.preview(identity, ConsentPreviewWrite(job_id=original.id, expected_job_revision=1,
                provider_id='test_provider', expected_provider_revision=2, expires_at=expires_after(300),
                budget=OutboundBudget(max_input_tokens=20000, max_output_tokens=5000, max_provider_calls=1,
                    max_search_calls=0, max_tool_calls=0, timeout_seconds=10, max_cost_usd=None)), 'preview-sources')
            consents.grant(identity, ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256), 'grant-sources')
            assert await asyncio.to_thread(worker.run_once)
            result = owner.read(identity, original.id)
            assert result.summary.status == 'completed' and len(server.requests) == 1
            return MaterialCase(database, identity, owner, result.summary.candidate, 'authoring_' + kind), blocks, refs
    return asyncio.run(build())


@pytest.mark.parametrize('kind', ['single', 'group'])
def test_material_preserves_ordered_complete_sources_and_rechecks_actual_missing_body(tmp_path, monkeypatch, kind):
    case, blocks, refs = generated_with_sources(tmp_path, kind)
    material = checked_read(case.database, case.identity, case.owner, case.kind, case.candidate, monkeypatch)
    assert material.source_refs == refs
    assert [item.text for item in material.payload.context.evidence] == ['Complete source two.\n', 'Complete source one.\n']
    assert [item.ref for item in material.payload.context.materials] == refs
    with case.database.connect() as conn:
        row = conn.execute('SELECT relative_path FROM content_blobs WHERE sha256=?', (blocks[0].body_sha256,)).fetchone()
    (case.database.settings.data_dir / row['relative_path']).unlink()
    before = table_hashes(case.database)
    with pytest.raises(ApiError):
        read_case(case)
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('damage', ['plan', 'root', 'question', 'private'])
def test_group_material_rejects_actual_persisted_plan_and_complete_member_corruption(tmp_path, damage):
    database, identity, owner, _, candidate, *_ = generated_group(tmp_path, 'assessment')
    case = MaterialCase(database, identity, owner, candidate, 'authoring_group')
    assert read_case(case).candidate.model_dump() == candidate.model_dump()
    table = 'authoring_content_plans' if damage == 'plan' else 'authoring_group_candidates'
    with database.transaction() as conn:
        row = conn.execute(f'SELECT rowid,record_json FROM {table}').fetchone()
        record = json.loads(row['record_json'])
        if damage == 'plan':
            record['plan']['topic'] += ' changed'
        elif damage == 'root':
            record['payload']['root']['title'] += ' changed'
        elif damage == 'question':
            record['payload']['questions'][0]['stem_markdown'] += ' changed'
        else:
            record['payload']['private_solutions'][0]['answer']['solution_markdown'] += ' changed'
        raw = canonical_bytes(record)
        # Recompute the storage envelope SHA: original owner/Provider bindings,
        # not a stale outer digest, must still reject this persisted alteration.
        conn.execute(f'UPDATE {table} SET record_json=?,record_sha256=? WHERE rowid=?',
                     (raw.decode(), sha256_bytes(raw), row['rowid']))
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught:
        read_case(case)
    assert (caught.value.status, caught.value.code) == (409, 'AUTHORING_INTEGRITY_ERROR')
    assert table_hashes(database) == before


@pytest.mark.parametrize('kind', ['single', 'assessment'])
def test_material_rejects_missing_original_provider_artifact(tmp_path, kind):
    state = single_fixture.__wrapped__(tmp_path) if kind == 'single' else generated_group(tmp_path, kind)
    database, identity, owner, _, candidate, *_ = state
    case = MaterialCase(database, identity, owner, candidate, 'authoring_single' if kind == 'single' else 'authoring_group')
    assert read_case(case).candidate.model_dump() == candidate.model_dump()
    with database.transaction() as conn:
        assert conn.execute('SELECT COUNT(*) FROM provider_artifacts').fetchone()[0] == 1
        conn.execute('DROP TRIGGER provider_artifacts_no_delete')
        conn.execute('DELETE FROM provider_artifacts')
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught:
        read_case(case)
    assert (caught.value.status, caught.value.code) == (503, 'PROVIDER_INTEGRITY_INVALID')
    assert table_hashes(database) == before


def test_review_port_requires_caller_transaction_and_exact_catalog_revision(imported_candidate):
    database, identity, owner, _, _, candidate = imported_candidate
    facade = DraftCandidates({'import': owner})
    before = table_hashes(database)
    with database.connect() as conn, pytest.raises(ApiError) as caught:
        facade.read_review_material(conn, identity, candidate.draft_id, candidate.draft_revision)
    assert caught.value.code == 'TRANSACTION_REQUIRED'
    with database.transaction(immediate=False) as conn, pytest.raises(ApiError) as caught:
        facade.read_review_material(conn, identity, candidate.draft_id, candidate.draft_revision + 1)
    assert caught.value.status == 412
    assert table_hashes(database) == before


@pytest.mark.parametrize('representation', ['repr', 'validation_error'])
def test_material_ordinary_representations_never_expand_academic_content(material_case, representation):
    from pydantic import ValidationError

    material = read_case(material_case)
    if material_case.kind == 'import':
        private_text = material.payload.payload.body_markdown
    elif material_case.kind == 'authoring_single':
        private_text = material.payload.record.payload.body_markdown
    else:
        private_text = material.payload.record.payload.private_solutions[0].answer.solution_markdown
    assert private_text
    for item in [material, material.payload]:
        if representation == 'repr':
            assert private_text not in repr(item)
            assert private_text not in str(item)
        else:
            raw = item.model_dump(mode='json')
            sentinel = 'zz_private_review_error_sentinel'
            raw['unexpected'] = sentinel
            with pytest.raises(ValidationError) as caught:
                type(item).model_validate(raw)
            assert sentinel not in str(caught.value)
