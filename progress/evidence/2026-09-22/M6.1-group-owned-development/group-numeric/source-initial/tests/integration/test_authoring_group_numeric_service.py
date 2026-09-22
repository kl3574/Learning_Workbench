"""Real generated groups and SQLite approval history; ledger cases do not execute.

The explicit LedgerRuntime fixture never starts processes. Separate worker tests
exercise the actual sealed runtime and preserve its real environment verdict.
"""

import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import subprocess

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.authoring_group_numeric_service import GroupNumericService
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.authoring_group_dto import AuthoringGroupNumericPreviewWrite, AuthoringGroupPrepareWrite
from services.api.app.import_dto import JobCancelRequest
from services.api.app.infrastructure.authoring_group_numeric_repository import GroupNumericRepository
from services.api.app.infrastructure.authoring_numeric_runtime import NumericRuntime
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.security import expires_after
from services.api.app.provider_dto import ConsentCreate, ConsentPreviewWrite, OutboundBudget
from tests.integration import test_authoring_group_provider as generation
from tests.integration.test_authoring_numeric_service import Generated, LedgerRuntime, blocked_result, decision
from tests.integration.test_authoring_provider import payload as worked_payload
from tests.integration.test_retrieval import all_rows
from tests.provider_protocol_fixture import local_provider


def lesson_payload():
    value = deepcopy(generation.payload())
    second = deepcopy(worked_payload())
    second.update(title='第二个合成算式', body_markdown='合成算式：5+25=30，未经审校。')
    second['numeric_plan']['variables'][0]['value'] = 5.0
    second['numeric_plan']['assertions'][0]['expected'] = 30.0
    value['content_plan']['entries'].append({'member_key': 'second_example', 'entity': 'block',
        'kind': 'worked_example', 'title': second['title'], 'objective_indexes': [0],
        'prerequisite_indexes': [], 'depends_on_keys': ['lesson_example']})
    value['draft']['blocks'].append({'member_key': 'second_example',
        'depends_on_keys': ['lesson_example'], 'payload': second})
    return value


def question_material(kind):
    concept = dm.Concept(id='numeric_group_concept', revision=1, title='合成数量关系')
    raw_body = b'Synthetic question target lesson.\n'
    block = dm.ContentBlock(id='numeric_group_target_block', revision=1, kind='text', title='合成目标正文',
        body_path='content/numeric_group_target.md', body_sha256=sha256_bytes(raw_body))
    lesson = dm.Lesson(id='numeric_group_target_lesson', revision=1, title='合成目标小节',
        objectives=[], block_refs=[reference(block)])
    request = {'topic': '合成数量关系题组', 'prerequisites': [], 'objectives': ['复算指定算术实例'],
        'proof_policy': 'full', 'output_kind': kind, 'source_refs': [], 'provider_id': 'test_provider',
        'target_concept_refs': [reference(concept).model_dump()]}
    if kind == 'practice_set':
        request['lesson_ref'] = reference(lesson).model_dump()
    else:
        request.update(allowed_modes=['independent', 'open_book'], time_limit_seconds=None)
    keys = ['numeric_question', 'no_plan_question']
    plan = {'version': 'authoring-content-plan-v1', 'output_kind': kind, 'topic': request['topic'],
        'prerequisites': [], 'objectives': request['objectives'], 'proof_policy': 'full',
        'entries': [{'member_key': key, 'entity': 'question', 'kind': 'numeric', 'objective_indexes': [0],
            'prerequisite_indexes': [], 'depends_on_keys': []} for key in keys]}
    example = worked_payload()
    questions = [{'member_key': key, 'kind': 'numeric', 'stem_markdown': '合成题：17+25是多少？', 'choices': [],
        'concept_refs': [reference(concept).model_dump()], 'skill': 'compute', 'exposure_family_key': key,
        'max_score': 1.0, 'input_instructions': '输入数值', 'declared_source_refs': [], 'depends_on_keys': []} for key in keys]
    solutions = [{'question_key': key, 'grading_kind': 'numeric_tolerance', 'accepted_answers': ['42', '42.0'],
        'absolute_tolerance': 0.0, 'relative_tolerance': 0.0, 'unit': None, 'domain_assumptions': [],
        'solution_markdown': '仅私解：17+25=42，未经审核。', 'rubric_markdown': '',
        'symbols': example['symbols'], 'numeric_plan': example['numeric_plan'] if index == 0 else None}
        for index, key in enumerate(keys)]
    output = {'version': 'authoring-group-generated-v1', 'content_plan': plan,
        'draft': {'output_kind': kind, 'title': '未审合成题组', 'questions': questions, 'solutions': solutions}}
    return AuthoringGroupPrepareWrite.model_validate(request), output, [concept, block, lesson], {block.body_path: raw_body}


def generated_group(tmp_path, kind='lesson'):
    async def build():
        if kind == 'lesson':
            request, output, objects, bodies = generation.request(), lesson_payload(), [], {}
        else:
            request, output, objects, bodies = question_material(kind)
        async with local_provider(text=canonical_bytes(output).decode()) as server:
            state = generation.configured(tmp_path, server.base_url)
            database, identity, authoring, worker, consents, _ = state
            if objects:
                ContentService(database).publish(identity.workspace_id, objects, bodies)
            original = authoring.prepare(identity, request, 'prepare-numeric-group')
            preview = consents.preview(identity, ConsentPreviewWrite(job_id=original.id, expected_job_revision=1,
                provider_id='test_provider', expected_provider_revision=2, expires_at=expires_after(300),
                budget=OutboundBudget(max_input_tokens=20000, max_output_tokens=10000, max_provider_calls=1,
                    max_search_calls=0, max_tool_calls=0, timeout_seconds=10, max_cost_usd=None)), 'preview-numeric-group')
            consents.grant(identity, ConsentCreate(proposal_id=preview.id,
                proposal_sha256=preview.proposal_sha256), 'grant-numeric-group')
            assert await asyncio.to_thread(worker.run_once)
            completed = authoring.read(identity, original.id)
            assert completed.summary.status == 'completed', completed.error_code
            assert completed.summary.candidate is not None and len(server.requests) == 1
            draft = authoring.draft(identity, completed.summary.candidate.draft_id)
            target = draft.root.blocks[1] if kind == 'lesson' else draft.root.questions[0]
            runtime = LedgerRuntime()
            numeric = GroupNumericService(database, authoring.context, runtime)
            return Generated((database, identity, authoring, numeric, completed.summary.candidate, target, runtime))
    return asyncio.run(build())


@pytest.fixture
def generated(tmp_path):
    return generated_group(tmp_path)


def preview(generated, key='numeric-preview', target=None):
    _, identity, _, service, candidate, selected, _ = generated
    target = target or selected
    return service.preview(identity, candidate.draft_id, target.member_key,
        AuthoringGroupNumericPreviewWrite(candidate=candidate, target=target), key)


def failure(code, call):
    with pytest.raises(ApiError) as caught:
        call()
    assert caught.value.code == code
    return caught.value


def test_preview_decline_and_expired_replay_do_not_create_job_or_execution(generated, monkeypatch):
    database, identity, authoring, numeric, candidate, target, runtime = generated
    source_before = authoring.read(identity, authoring.draft(identity, candidate.draft_id).source_job_id)
    view = preview(generated)
    assert view.target.model_dump() == target.model_dump() and view.candidate == candidate and view.job is view.result is None
    assert view.plan == authoring.draft(identity, candidate.draft_id).blocks[1].payload.numeric_plan
    with database.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM jobs WHERE kind='authoring_numeric_check'").fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM authoring_numeric_executions').fetchone()[0] == 0
    from services.api.app.application import authoring_group_numeric_service as service_module
    from services.api.app.infrastructure import authoring_group_numeric_repository as repository_module
    monkeypatch.setattr(service_module, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    monkeypatch.setattr(repository_module, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    before = all_rows(database)
    assert numeric.read(identity, view.id).expired and all_rows(database) == before
    failure('NUMERIC_APPROVAL_EXPIRED', lambda: numeric.decide(identity, view.id, decision(view), 'late-approve'))
    declined = numeric.decide(identity, view.id, decision(view, 'decline'), 'decline')
    assert declined.job is None and declined.revision == 2
    runtime.changed = True
    before = all_rows(database)
    assert numeric.decide(identity, view.id, decision(view, 'decline'), 'decline') == declined
    assert preview(generated) == view and all_rows(database) == before
    assert runtime.prepares == 1 and runtime.checks == 0
    assert authoring.read(identity, source_before.summary.id) == source_before


@pytest.mark.parametrize('damage', ['root_hash', 'root_revision', 'root_url', 'member_hash', 'member_url', 'missing_member'])
def test_exact_root_and_member_binding_rejects_without_side_effects(generated, damage):
    database, identity, _, numeric, candidate, target, runtime = generated
    root_id, member_key = candidate.draft_id, target.member_key
    if damage == 'root_hash':
        candidate = candidate.model_copy(update={'candidate_sha256': '0' * 64})
    elif damage == 'root_revision':
        candidate = candidate.model_copy(update={'draft_revision': 2})
    elif damage == 'root_url':
        root_id = 'absent_group_draft'
    elif damage == 'member_hash':
        target = target.model_copy(update={'member_sha256': '0' * 64})
    elif damage == 'member_url':
        member_key = 'second_example'
    else:
        target = target.model_copy(update={'member_key': 'missing_member'})
        member_key = target.member_key
    before = all_rows(database)
    with pytest.raises(ApiError) as caught:
        numeric.preview(identity, root_id, member_key, AuthoringGroupNumericPreviewWrite(candidate=candidate, target=target), 'bad-binding')
    assert caught.value.status == (412 if damage == 'root_revision' else 404 if damage == 'root_url' else 409)
    assert all_rows(database) == before and runtime.prepares == 0


def test_approval_is_separate_job_with_original_ack_idempotency_cas_and_safe_cancel(generated):
    database, identity, authoring, numeric, candidate, target, runtime = generated
    draft = authoring.draft(identity, candidate.draft_id)
    original = authoring.read(identity, draft.source_job_id)
    view = preview(generated)
    other = AuthoringGroupNumericPreviewWrite(candidate=candidate, target=draft.root.blocks[2])
    failure('IDEMPOTENCY_CONFLICT', lambda: numeric.preview(identity, candidate.draft_id, target.member_key, other, 'numeric-preview'))
    failure('REVISION_MISMATCH', lambda: numeric.decide(identity, view.id, decision(view, revision=2), 'bad-cas'))
    wrong = decision(view).model_copy(update={'operation_sha256': '0' * 64})
    failure('NUMERIC_OPERATION_MISMATCH', lambda: numeric.decide(identity, view.id, wrong, 'bad-operation'))
    runtime.changed = True
    failure('NUMERIC_RUNTIME_CHANGED', lambda: numeric.decide(identity, view.id, decision(view), 'changed-runtime'))
    runtime.changed = False
    ack = numeric.decide(identity, view.id, decision(view), 'approve')
    assert ack.job.status == 'queued' and ack.job.id != original.summary.id
    failure('IDEMPOTENCY_CONFLICT', lambda: numeric.decide(identity, view.id, decision(view, 'decline'), 'approve'))
    with database.transaction(immediate=False) as conn:
        repo = GroupNumericRepository(conn, identity.workspace_id)
        job = repo.job_input(ack.job.id)
        assert job.version == 'authoring-group-numeric-job-v1' and job.candidate == candidate
        assert job.target.model_dump() == target.model_dump()
        assert job.plan == view.plan and job.operation_sha256 == view.operation_sha256
        assert repo.execution_state(job.job_id) == (None, None)
    learner = replace(identity, role='learner')
    failure('POLICY_DENIED', lambda: numeric.read(learner, view.id))
    control = numeric.job(learner, ack.job.id)
    assert control.result_refs == control.warnings == [] and control.error is None
    command = JobCancelRequest(expected_revision=1)
    cancelled = numeric.cancel_job(learner, ack.job.id, command, 'cancel')
    assert cancelled.status == 'cancelled'
    runtime.changed = True
    before = all_rows(database)
    assert numeric.decide(identity, view.id, decision(view), 'approve') == ack
    assert numeric.cancel_job(learner, ack.job.id, command, 'cancel') == cancelled
    current = numeric.read(identity, view.id)
    assert current.result.outcome == 'cancelled' and current.result.verdict == 'BLOCKED'
    assert current.result.started_at is current.result.exit_code is None and current.result.assertions == []
    assert authoring.read(identity, original.summary.id) == original
    assert authoring.draft(identity, candidate.draft_id).candidate == candidate and all_rows(database) == before


@pytest.mark.parametrize('kind', ['practice_set', 'assessment'])
def test_question_numeric_plan_is_read_from_exact_private_solution_only(tmp_path, kind):
    generated = generated_group(tmp_path, kind)
    database, identity, authoring, numeric, candidate, target, _ = generated
    draft = authoring.draft(identity, candidate.draft_id)
    public = canonical_bytes([question.model_dump(mode='json') for question in draft.questions])
    assert b'numeric_plan' not in public and b'accepted_answers' not in public and '仅私解'.encode() not in public
    private = authoring.solution(identity, candidate.draft_id, target.member_key)
    view = preview(generated)
    assert view.plan == private.payload.answer.numeric_plan
    other = draft.root.questions[1]
    before = all_rows(database)
    with pytest.raises(ApiError):
        numeric.preview(identity, candidate.draft_id, other.member_key,
            AuthoringGroupNumericPreviewWrite(candidate=candidate, target=other), 'no-private-plan')
    assert all_rows(database) == before


def test_foreign_member_result_hash_cannot_leave_terminal_rows_when_caller_catches_rejection(generated):
    from services.api.app.authoring_dto import NumericCheckResult, numeric_result_sha256
    from services.api.app.infrastructure.database import utc_now
    database, identity, authoring, numeric, candidate, _, _ = generated
    view = preview(generated)
    ack = numeric.decide(identity, view.id, decision(view), 'approve')
    with database.transaction() as conn:
        repo = GroupNumericRepository(conn, identity.workspace_id)
        lease, job, _ = repo.claim(ack.job.id)
        assert repo.begin(lease, utc_now())
    other = authoring.draft(identity, candidate.draft_id).root.blocks[2]
    forged_input = job.model_copy(update={'target': other})
    value = blocked_result(job, 'environment_unavailable').model_dump(mode='json')
    value['input_sha256'] = sha256_bytes(canonical_bytes(forged_input))
    value['result_sha256'] = numeric_result_sha256(value)
    wrong = NumericCheckResult.model_validate(value)
    before = all_rows(database)
    with database.transaction() as conn:
        repo = GroupNumericRepository(conn, identity.workspace_id)
        with pytest.raises((ApiError, ValueError)):
            repo.finish(lease, wrong)
    assert all_rows(database) == before
    with database.transaction() as conn:
        repo = GroupNumericRepository(conn, identity.workspace_id)
        start, end = repo.execution_state(job.job_id)
        assert start.admitted_at is not None and start.actual_started_at is None and end is None
        terminal = repo.finish(lease, blocked_result(job, 'environment_unavailable'))
        assert terminal.job.status == 'failed' and terminal.result.verdict == 'BLOCKED'


def test_preview_and_approval_freeze_actual_runtime_without_process_launch(generated, monkeypatch):
    database, identity, authoring, _, candidate, target, _ = generated
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('preview/approval started process'))
    runtime = NumericRuntime()
    service = GroupNumericService(database, authoring.context, runtime)
    view = service.preview(identity, candidate.draft_id, target.member_key,
        AuthoringGroupNumericPreviewWrite(candidate=candidate, target=target), 'actual-runtime')
    assert sha256_bytes(runtime.manifest_document()) == view.runtime.runtime_manifest_sha256
    ack = service.decide(identity, view.id, decision(view), 'actual-approve')
    with database.transaction(immediate=False) as conn:
        assert GroupNumericRepository(conn, identity.workspace_id).execution_state(ack.job.id) == (None, None)


def test_group_quota_counts_both_members_expired_declined_and_original_preview_acks(generated, monkeypatch):
    database, identity, authoring, numeric, candidate, target, _ = generated
    other = authoring.draft(identity, candidate.draft_id).root.blocks[2]
    previews = [preview(generated, f'quota-{index}', target if index % 2 == 0 else other) for index in range(100)]
    from services.api.app.application import authoring_group_numeric_service as service_module
    from services.api.app.infrastructure import authoring_group_numeric_repository as repository_module
    monkeypatch.setattr(service_module, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    monkeypatch.setattr(repository_module, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    declined = numeric.decide(identity, previews[0].id, decision(previews[0], 'decline'), 'decline-at-quota')
    before = all_rows(database)
    failure('NUMERIC_PREVIEW_LIMIT', lambda: preview(generated, 'quota-101', other))
    assert preview(generated, 'quota-0') == previews[0]
    assert numeric.decide(identity, previews[0].id, decision(previews[0], 'decline'), 'decline-at-quota') == declined
    assert numeric.read(identity, previews[-1].id).expired and all_rows(database) == before
    assert authoring.draft(identity, candidate.draft_id).numeric_check_ids == [item.id for item in previews]


def test_deleted_preview_membership_does_not_replenish_quota(generated):
    database, _, _, _, _, _, _ = generated
    view = preview(generated)
    with database.transaction() as conn:
        conn.execute('DELETE FROM authoring_group_numeric_checks WHERE check_id=?', (view.id,))
    before = all_rows(database)
    failure('AUTHORING_INTEGRITY_ERROR', lambda: preview(generated, 'after-deletion'))
    assert all_rows(database) == before


@pytest.mark.parametrize('damage', ['cancel_ack', 'context', 'member_plan', 'manifest'])
def test_corrupt_history_rejects_safe_controls_and_original_ack_without_repair(generated, damage):
    database, identity, _, numeric, _, _, _ = generated
    view = preview(generated)
    ack = numeric.decide(identity, view.id, decision(view), 'approve')
    command = JobCancelRequest(expected_revision=1)
    numeric.cancel_job(identity, ack.job.id, command, 'cancel')
    with database.transaction() as conn:
        if damage == 'context':
            conn.execute('UPDATE context_snapshots SET snapshot_sha256=?', ('0' * 64,))
        elif damage == 'cancel_ack':
            row = conn.execute("SELECT request_json FROM authoring_commands WHERE owner_id=? AND key='cancel'", (view.id,)).fetchone()
            body = json.loads(row[0]); body['expected_revision'] = 99
            raw = canonical_bytes(body).decode()
            conn.execute("UPDATE authoring_commands SET request_json=?,request_sha256=? WHERE owner_id=? AND key='cancel'",
                (raw, sha256_bytes(raw.encode()), view.id))
        else:
            row = conn.execute('SELECT record_json FROM authoring_group_numeric_checks WHERE check_id=?', (view.id,)).fetchone()
            body = json.loads(row[0])
            if damage == 'manifest':
                body['runtime_manifest_json'] = canonical_bytes({'format': 'self-consistent-fake-manifest'}).decode()
            else:
                body['view']['plan']['assertions'][0]['expected'] = 99.0
            raw = canonical_bytes(body).decode()
            conn.execute('UPDATE authoring_group_numeric_checks SET record_json=?,record_sha256=? WHERE check_id=?',
                (raw, sha256_bytes(raw.encode()), view.id))
    before = all_rows(database)
    learner = replace(identity, role='learner')
    failure('AUTHORING_INTEGRITY_ERROR', lambda: numeric.job(learner, ack.job.id))
    failure('AUTHORING_INTEGRITY_ERROR', lambda: numeric.cancel_job(learner, ack.job.id, command, 'cancel'))
    assert all_rows(database) == before
