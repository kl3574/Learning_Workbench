"""Real SQLite/consent/loopback protocol; synthetic model, never vendor proof."""
import asyncio
from dataclasses import replace

import pytest
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.authoring_group import AuthoringGroupService
from services.api.app.application.authoring_group_source import AuthoringGroupOutboundSource
from services.api.app.application.authoring_group_worker import AuthoringGroupWorker
from services.api.app.application.consents import ConsentsService
from services.api.app.application.provider_budget import ProofRegistry, RequestPreparer
from services.api.app.application.provider_dispatch import CheckedDispatch
from services.api.app.application.provider_ports import OutboundSourceRegistry
from services.api.app.application.providers import ProviderService
from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code, expires_after
from services.api.app.infrastructure.provider_secret_store import FileSecretStore
from services.api.app.provider_dto import ProviderConfigWrite, ProviderSecretWrite, ConsentCreate, ConsentPreviewWrite, OutboundBudget
from tests.integration.test_authoring_group_context import request
from tests.integration.test_retrieval import all_rows
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

