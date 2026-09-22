"""Real SQLite/consent/loopback protocol; synthetic model, never vendor proof."""
import asyncio
from dataclasses import replace

import pytest
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.authoring_group import AuthoringGroupService
from services.api.app.application.authoring_group_source import AuthoringGroupOutboundSource
from services.api.app.application.authoring_group_worker import AuthoringGroupWorker
from services.api.app.application.content import ContentService
from services.api.app.application.consents import ConsentsService
from services.api.app.application.jobs import JobService
from services.api.app.application.provider_budget import ProofRegistry, RequestPreparer
from services.api.app.application.provider_dispatch import CheckedDispatch
from services.api.app.application.provider_ports import OutboundSourceRegistry
from services.api.app.application.providers import ProviderService
from services.api.app.application.sessions import SessionService
from services.api.app.authoring_group_dto import AuthoringGroupPrepareWrite
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code, expires_after
from services.api.app.infrastructure.provider_secret_store import FileSecretStore
from services.api.app.provider_dto import ProviderConfigWrite, ProviderSecretWrite, ConsentCreate, ConsentPreviewWrite, OutboundBudget
from services.api.app.retrieval_dto import RetrievalQueryWrite
from tests.integration.test_authoring_group_context import request
from tests.integration.test_retrieval import all_rows, request_for
from tests.provider_protocol_fixture import MODEL, test_preparer, local_provider, chat_stream


def payload():
    from tests.integration.test_authoring_provider import payload as worked_payload
    body = request()
    plan = {'version': 'authoring-content-plan-v1', 'output_kind': 'lesson',
        'topic': body.topic, 'prerequisites': body.prerequisites, 'objectives': body.objectives,
        'proof_policy': body.proof_policy, 'entries': [
            {'member_key': 'lesson_text', 'entity': 'block', 'kind': 'text', 'title': '合成正文',
                'objective_indexes': [0], 'prerequisite_indexes': [], 'depends_on_keys': []},
            {'member_key': 'lesson_example', 'entity': 'block', 'kind': 'worked_example', 'title': '合成加法',
                'objective_indexes': [0], 'prerequisite_indexes': [], 'depends_on_keys': ['lesson_text']},
        ]}
    return {'version': 'authoring-group-generated-v1', 'content_plan': plan,
        'draft': {'output_kind': 'lesson', 'title': '合成教学小节', 'blocks': [
            {'member_key': 'lesson_text', 'depends_on_keys': [], 'payload': {
                'version': 'content-block-candidate-v1', 'kind': 'text', 'title': '合成正文',
                'body_markdown': '这是原创合成教学片段，未经过审校。', 'symbols': [], 'declared_source_refs': []}},
            {'member_key': 'lesson_example', 'depends_on_keys': ['lesson_text'], 'payload': worked_payload()},
        ]}}


def configured(tmp_path, url, *, proof=True):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    database.initialize()
    _, learner = consume_bootstrap(database, issue_bootstrap_code(database))
    SessionService(database).switch_role(learner, RoleRequest(role='author'), 'be-author')
    identity = replace(learner, role='author')
    service = AuthoringGroupService(database)
    secret_store = FileSecretStore(tmp_path / 'synthetic-authoring-secrets')
    secret_store.initialize()
    preparer = test_preparer(url) if proof else RequestPreparer(ProofRegistry())
    providers = ProviderService(database, secret_store, preparer)
    providers.save_config(identity, 'test_provider', ProviderConfigWrite(expected_revision=0,
        adapter='compatible_chat', base_url=url, model=MODEL, embedding_model=None,
        endpoint_policy='explicit_loopback', pricing=None), 'config')
    providers.save_secret(identity, 'test_provider', ProviderSecretWrite(expected_revision=1,
        secret='synthetic-authoring-test-key'), 'secret')
    registry = OutboundSourceRegistry({'authoring': AuthoringGroupOutboundSource(service.context)})
    dispatch = CheckedDispatch(database, secret_store, registry, preparer)
    service.provider = dispatch
    return database, identity, service, AuthoringGroupWorker(database, service.context, dispatch), ConsentsService(database, secret_store, registry, preparer), dispatch


def approved(state):
    database, identity, service, _, consents, _ = state
    original = service.prepare(identity, request(), 'prepare')
    proposal = consents.preview(identity, ConsentPreviewWrite(job_id=original.id, expected_job_revision=1,
        provider_id='test_provider', expected_provider_revision=2, expires_at=expires_after(300),
        budget=OutboundBudget(max_input_tokens=20000, max_output_tokens=5000, max_provider_calls=1,
            max_search_calls=0, max_tool_calls=0, timeout_seconds=10, max_cost_usd=None)), 'preview')
    command = ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256)
    grant = consents.grant(identity, command, 'grant')
    assert service.read(identity, original.id).summary.status == 'queued'
    return original, command, grant


PRIVATE_SENTINEL = 'zzgroupprivateanswercanary'
PUBLIC_SENTINEL = 'zzgrouppublicmaterialcanary'
QUESTION_GRADERS = (
    ('single_choice', 'choice_exact', ['option_a']),
    ('text_blank', 'text_normalized', ['forty two', 'forty-two']),
    ('numeric', 'numeric_tolerance', ['42', '42.0']),
    ('expression', 'symbolic_review', ['2*x', 'x+x']),
    ('calculation', 'rubric_review', ['42', '17+25=42']),
)


def mixed_question_material(kind='practice_set'):
    """Original five-kind draft; only existing public targets are published."""
    from tests.integration.test_authoring_provider import payload as worked_payload

    concept = dm.Concept(id='mixed_group_concept', revision=1, title='合成数量关系概念')
    raw = (PUBLIC_SENTINEL + '\nOriginal synthetic public target material.\n').encode()
    block = dm.ContentBlock(id='mixed_group_target', revision=1, kind='text', title='合成公开目标',
        body_path='content/mixed_group_target.md', body_sha256=sha256_bytes(raw))
    lesson = dm.Lesson(id='mixed_group_lesson', revision=1, title='已有合成目标小节',
        objectives=['区分未审题面与私解'], block_refs=[reference(block)])
    body = {'topic': '原创合成五题型草稿', 'prerequisites': [], 'objectives': ['保留五题型评分结构'],
        'proof_policy': 'full', 'output_kind': kind, 'source_refs': [], 'provider_id': 'test_provider',
        'target_concept_refs': [reference(concept).model_dump()]}
    if kind == 'practice_set':
        body['lesson_ref'] = reference(lesson).model_dump()
    elif kind == 'assessment':
        body.update(allowed_modes=['independent', 'open_book'], time_limit_seconds=600)
    else:
        raise ValueError('Only explicit question roots belong to this fixture')
    entries, questions, solutions = [], [], []
    for number, (question_kind, grader, answers) in enumerate(QUESTION_GRADERS):
        key = 'question_' + question_kind
        entries.append({'member_key': key, 'entity': 'question', 'kind': question_kind,
            'objective_indexes': [0], 'prerequisite_indexes': [], 'depends_on_keys': []})
        questions.append({'member_key': key, 'kind': question_kind,
            'stem_markdown': f'原创合成第 {number + 1} 题：说明或计算给定数量关系。',
            'choices': [{'id': 'option_a', 'text_markdown': '四十二'},
                        {'id': 'option_b', 'text_markdown': '四十一'}] if question_kind == 'single_choice' else [],
            'concept_refs': [reference(concept).model_dump()], 'skill': 'compute',
            'exposure_family_key': 'mixed_family_' + question_kind, 'max_score': 1.0,
            'input_instructions': '合成软件验收；未经教学或数学审核。',
            'declared_source_refs': [], 'depends_on_keys': []})
        example = worked_payload()
        solutions.append({'question_key': key, 'grading_kind': grader, 'accepted_answers': list(answers),
            'absolute_tolerance': 0.0, 'relative_tolerance': 0.0, 'unit': None,
            'domain_assumptions': [], 'solution_markdown': PRIVATE_SENTINEL + ' ' + question_kind,
            'rubric_markdown': '未审合成评分建议', 'symbols': example['symbols'],
            'numeric_plan': example['numeric_plan'] if question_kind == 'numeric' else None})
    output = {'version': 'authoring-group-generated-v1',
        'content_plan': {'version': 'authoring-content-plan-v1', 'output_kind': kind,
            'topic': body['topic'], 'prerequisites': [], 'objectives': body['objectives'],
            'proof_policy': 'full', 'entries': entries},
        'draft': {'output_kind': kind, 'title': '原创合成五题型候选', 'questions': questions, 'solutions': solutions}}
    return AuthoringGroupPrepareWrite.model_validate(body), output, [concept, block, lesson], {block.body_path: raw}


def approve_request(state, body):
    """Prepare and explicitly approve the original request on one real Job."""
    _, identity, service, _, consents, _ = state
    original = service.prepare(identity, body, 'prepare-explicit-group')
    assert original.status == 'awaiting_approval'
    proposal = consents.preview(identity, ConsentPreviewWrite(job_id=original.id, expected_job_revision=1,
        provider_id='test_provider', expected_provider_revision=2, expires_at=expires_after(300),
        budget=OutboundBudget(max_input_tokens=20000, max_output_tokens=10000, max_provider_calls=1,
            max_search_calls=0, max_tool_calls=0, timeout_seconds=10, max_cost_usd=None)), 'preview-explicit-group')
    command = ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256)
    grant = consents.grant(identity, command, 'grant-explicit-group')
    return original, command, grant


def test_checked_five_question_kinds_keep_private_answers_out_of_public_control_and_real_index(tmp_path):
    from services.api.app.application.retrieval import RetrievalService, RetrievalWorker
    from services.api.app.infrastructure.retrieval_repository import RetrievalRepository

    async def run():
        body, generated, objects, bodies = mixed_question_material()
        answer = canonical_bytes(generated).decode()
        async with local_provider(text=answer) as server:
            state = configured(tmp_path, server.base_url)
            database, identity, service, worker, _, _ = state
            empty = all_rows(database)
            assert empty['objects'] == empty['solutions'] == []
            ContentService(database).publish(identity.workspace_id, objects, bodies)
            published = all_rows(database)
            assert len(published['objects']) == 3 and published['solutions'] == []
            content_tables = ('objects', 'revisions', 'block_bodies', 'solutions', 'drafts', 'reviews')
            original, _, grant = approve_request(state, body)
            assert server.requests == []
            assert await asyncio.to_thread(worker.run_once)
            current = service.read(identity, original.id)
            assert current.summary.status == 'completed' and current.raw_answer == answer
            assert current.consent_id == grant.id and len(server.requests) == 1
            draft = service.draft(identity, current.summary.candidate.draft_id)
            assert draft.root.entity == 'practice_set' and draft.root.lesson_ref == body.root.lesson_ref
            assert [question.kind for question in draft.questions] == [item[0] for item in QUESTION_GRADERS]
            assert len(draft.root.questions) == len(draft.private_solution_refs) == len(draft.validation.question_checks) == 5
            assert draft.state == 'draft' and draft.base_ref is None
            for member, quality, (_, grader, answers) in zip(
                draft.root.questions, draft.validation.question_checks, QUESTION_GRADERS, strict=True
            ):
                private = service.solution(identity, draft.candidate.draft_id, member.member_key)
                assert private.payload.question == member and quality.question == member
                assert private.payload.answer.grading_kind == grader
                assert private.payload.answer.accepted_answers == answers
                assert PRIVATE_SENTINEL in private.payload.answer.solution_markdown
                assert private.payload.review_status == 'needs_review'
                assert quality.grading_compatibility == quality.accepted_answer_membership == 'PASS'
                assert quality.answer_uniqueness == quality.solution_grading_semantics == 'NOT_RUN'
            assert draft.validation.mathematical == draft.validation.sources == draft.validation.independent_pedagogy == 'NOT_RUN'
            learner = replace(identity, role='learner')
            safe = JobService(database).job(learner, original.id)
            for public in (draft, safe):
                raw = canonical_bytes(public)
                assert PRIVATE_SENTINEL.encode() not in raw and b'accepted_answers' not in raw
                assert b'solution_markdown' not in raw and b'numeric_plan' not in raw
            assert safe.status == 'completed' and safe.result_refs == []
            after_generation = all_rows(database)
            assert all(after_generation[table] == published[table] for table in content_tables)

            # A ready index and positive hit prevent an empty/cold index from
            # vacuously passing the private-sentinel query. No draft is published.
            retrieval, indexing = RetrievalService(database), RetrievalWorker(database)
            refs = [body.root.lesson_ref]
            rebuild = retrieval.rebuild(identity, request_for(retrieval, identity, refs), 'index-public-target')
            assert indexing.run_once()
            assert retrieval.job(identity, rebuild.id).status == 'completed'
            assert retrieval.scope_status(identity, refs).state == 'ready'
            before = all_rows(database)
            positive = retrieval.query(identity, RetrievalQueryWrite(query=PUBLIC_SENTINEL, scope_refs=refs, limit=5))
            absent = retrieval.query(identity, RetrievalQueryWrite(query=PRIVATE_SENTINEL, scope_refs=refs, limit=5))
            assert positive.result_state == 'matched' and positive.matched_count == 1
            assert positive.hits[0].ref == reference(objects[1])
            assert PUBLIC_SENTINEL in positive.hits[0].text
            assert absent.index_state == 'ready' and absent.result_state == 'no_match'
            assert absent.hits == [] and absent.matched_count == 0
            assert PRIVATE_SENTINEL not in canonical_bytes(positive).decode()
            with database.transaction(immediate=False) as conn:
                repo = RetrievalRepository(conn, identity.workspace_id)
                scopes = repo.scopes('', 20)
                assert len(scopes) == 1 and repo.roots(scopes[0]) == refs
                indexed = repo.generation(scopes[0])
                assert indexed is not None
                manifest, terms = indexed
                assert [entry.ref for entry in manifest.blocks] == [reference(objects[1])]
                assert [entry.ref for entry in manifest.descriptor.blocks] == [reference(objects[1])]
                assert set(terms) == {manifest.blocks[0].chunk_id}
                # Global physical rows, with no query-scope filter, prove no
                # extra group document/chunk was silently added elsewhere.
                assert conn.execute('SELECT COUNT(*) FROM retrieval_scopes').fetchone()[0] == 1
                assert conn.execute('SELECT COUNT(*) FROM retrieval_generations').fetchone()[0] == 1
                chunks = conn.execute('SELECT ref_json,tokens FROM retrieval_chunks').fetchall()
                fts = conn.execute('SELECT tokens FROM retrieval_fts').fetchall()
                assert len(chunks) == len(fts) == 1
                assert chunks[0]['ref_json'] == canonical_bytes(reference(objects[1])).decode()
                assert chunks[0]['tokens'] == fts[0]['tokens'] == ' '.join(terms[manifest.blocks[0].chunk_id])
                decoded_terms = [bytes.fromhex(token[1:]).decode() for token in chunks[0]['tokens'].split()]
                assert PUBLIC_SENTINEL in decoded_terms and PRIVATE_SENTINEL not in decoded_terms
                for raw in (canonical_bytes(manifest).decode(), chunks[0]['ref_json']):
                    assert PRIVATE_SENTINEL not in raw and draft.candidate.draft_id not in raw
                    assert all(member.member_key not in raw for member in draft.root.questions)
            assert all_rows(database) == before and len(server.requests) == 1
            assert all(before[table] == published[table] for table in content_tables)
    asyncio.run(run())


@pytest.mark.parametrize('damage', ['incompatible_grader', 'absent_choice', 'nonfinite_numeric_answer'])
def test_checked_question_grading_mismatch_retains_plan_and_original_output_without_any_candidate(tmp_path, damage):
    async def run():
        body, generated, objects, bodies = mixed_question_material()
        solutions = generated['draft']['solutions']
        if damage == 'incompatible_grader':
            solutions[3]['grading_kind'] = 'rubric_review'  # expression requires symbolic_review
        elif damage == 'absent_choice':
            solutions[0]['accepted_answers'] = ['absent_option']
        else:
            solutions[2]['accepted_answers'] = ['Infinity']
        answer = canonical_bytes(generated).decode()
        async with local_provider(text=answer) as server:
            state = configured(tmp_path, server.base_url)
            database, identity, service, worker, _, _ = state
            ContentService(database).publish(identity.workspace_id, objects, bodies)
            original, _, grant = approve_request(state, body)
            assert server.requests == []
            assert await asyncio.to_thread(worker.run_once)
            current = service.read(identity, original.id)
            assert current.summary.status == 'failed' and current.summary.candidate is None
            assert current.consent_id == grant.id and current.raw_answer == answer
            assert current.provider_outcome == 'completed' and current.provider_receipt_id is not None
            # The complete generated DTO applies the shared answer precheck in
            # its after-validator; these valid JSON fields fail that schema gate.
            assert current.error_code == 'AUTHORING_OUTPUT_INVALID'
            assert current.content_plan is not None and current.plan_ref is not None
            assert current.content_plan.model_dump(mode='json') == generated['content_plan']
            assert current.validation.schema_check == 'FAIL' and current.validation.plan_membership == 'PASS'
            with database.connect() as conn:
                assert conn.execute('SELECT COUNT(*) FROM authoring_group_candidates').fetchone()[0] == 0
            before = all_rows(database)
            assert service.read(identity, original.id) == current
            assert not await asyncio.to_thread(worker.run_once)
            assert all_rows(database) == before and len(server.requests) == 1
    asyncio.run(run())


@pytest.mark.parametrize('mode', ['valid', 'invalid_json', 'refusal', 'incomplete', 'missing_member'])
def test_real_authoring_approval_result_draft_and_original_ack(tmp_path, mode):
    async def run():
        generated = payload()
        if mode == 'missing_member':
            generated['draft']['blocks'].pop()
        text = canonical_bytes(generated).decode() if mode != 'invalid_json' else '```json\n{}\n```'
        stream = chat_stream(text, refusal=mode == 'refusal', finish='length' if mode == 'incomplete' else 'stop')
        async with local_provider(payload=stream) as server:
            state = configured(tmp_path, server.base_url)
            database, identity, service, worker, consents, dispatch = state
            original, command, grant = await asyncio.to_thread(approved, state)
            assert server.requests == []
            assert await asyncio.to_thread(worker.run_once)
            current = service.read(identity, original.id)
            assert current.summary.status == ('completed' if mode == 'valid' else 'failed')
            assert current.provider_outcome == ('incomplete' if mode == 'incomplete' else 'completed')
            assert current.raw_answer == (None if mode == 'refusal' else text)
            assert current.raw_refusal == (text if mode == 'refusal' else None)
            if mode == 'valid':
                from services.api.app.infrastructure.authoring_group_repository import AuthoringGroupRepository
                with database.transaction(immediate=False) as conn:
                    draft = AuthoringGroupRepository(conn, identity.workspace_id).draft(current.summary.candidate.draft_id)
                assert draft.state == 'draft' and draft.base_ref is None and draft.numeric_check_ids == []
                assert draft.content_plan.model_dump(mode='json') == payload()['content_plan']
                assert [item.model_dump(mode='json') for item in draft.blocks] == payload()['draft']['blocks']
                assert draft.validation.mathematical == draft.validation.independent_pedagogy == 'NOT_RUN'
            else:
                assert current.summary.candidate is None
                assert (current.plan_ref is not None) == (mode == 'missing_member')
                with database.connect() as conn:
                    assert conn.execute('SELECT COUNT(*) FROM authoring_group_candidates').fetchone()[0] == 0
            before = all_rows(database)
            assert service.prepare(identity, request(), 'prepare') == original
            assert consents.grant(identity, command, 'grant') == grant
            assert all_rows(database) == before
            assert not await asyncio.to_thread(worker.run_once)
            assert len(server.requests) == 1
            with database.transaction(immediate=False) as conn:
                checked = dispatch.read_result(conn, identity, original.id, grant.id)
                assert checked.receipt.id == current.provider_receipt_id
    asyncio.run(run())
