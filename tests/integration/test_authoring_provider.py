"""Real SQLite/consent/loopback protocol; synthetic model, never vendor proof."""
import asyncio
from dataclasses import replace

import pytest
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.authoring import AuthoringService
from services.api.app.application.authoring_source import AuthoringOutboundSource
from services.api.app.application.authoring_worker import AuthoringWorker
from services.api.app.application.errors import ApiError
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
from tests.integration.test_authoring_context import request
from tests.integration.test_retrieval import all_rows
from tests.provider_protocol_fixture import MODEL, test_preparer, local_provider, chat_stream


def payload():
    return {'version':'worked-example-candidate-v1','kind':'worked_example','title':'合成加法',
        'body_markdown':'测试声明：17+25=42。未经数学或教学审核。\n',
        'symbols':[{'name':'x','tex':'x','domain':'real','dimension':'number'}],
        'declared_source_refs':[], 'numeric_plan':{'version':'finite-arithmetic-v1',
            'variables':[{'name':'x','value':17.0,'unit':'number'}],
            'assertions':[{'id':'sum_check','expression':'x+25','expected':42.0,'atol':0.0,'rtol':0.0,'unit':'number'}],
            'seed':None}}


def configured(tmp_path, url, *, proof=True):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    database.initialize()
    _, learner = consume_bootstrap(database, issue_bootstrap_code(database))
    SessionService(database).switch_role(learner, RoleRequest(role='author'), 'be-author')
    identity = replace(learner, role='author')
    service = AuthoringService(database)
    secret_store = FileSecretStore(tmp_path / 'synthetic-authoring-secrets')
    secret_store.initialize()
    preparer = test_preparer(url) if proof else RequestPreparer(ProofRegistry())
    providers = ProviderService(database, secret_store, preparer)
    providers.save_config(identity, 'test_provider', ProviderConfigWrite(expected_revision=0,
        adapter='compatible_chat', base_url=url, model=MODEL, embedding_model=None,
        endpoint_policy='explicit_loopback', pricing=None), 'config')
    providers.save_secret(identity, 'test_provider', ProviderSecretWrite(expected_revision=1,
        secret='synthetic-authoring-test-key'), 'secret')
    registry = OutboundSourceRegistry({'authoring': AuthoringOutboundSource(service.context)})
    dispatch = CheckedDispatch(database, secret_store, registry, preparer)
    service.provider = dispatch
    return database, identity, service, AuthoringWorker(database, service.context, dispatch), ConsentsService(database, secret_store, registry, preparer), dispatch


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


@pytest.mark.parametrize('mode', ['valid', 'invalid_json', 'refusal', 'incomplete'])
def test_real_authoring_approval_result_draft_and_original_ack(tmp_path, mode):
    async def run():
        text = canonical_bytes(payload()).decode() if mode != 'invalid_json' else '```json\n{}\n```'
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
                draft = service.draft(identity, current.summary.candidate.draft_id)
                assert draft.state == 'draft' and draft.base_ref is None and draft.numeric_check_ids == []
                assert draft.payload.model_dump(mode='json') == payload()
                assert draft.validation.mathematical == draft.validation.independent_pedagogy == 'NOT_RUN'
            else:
                assert current.summary.candidate is None
                with database.connect() as conn:
                    assert conn.execute('SELECT COUNT(*) FROM authoring_candidates').fetchone()[0] == 0
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


def test_current_author_role_checked_before_original_provider_grant_ack(tmp_path):
    async def run():
        async with local_provider() as server:
            state = configured(tmp_path, server.base_url)
            database, identity, _, _, consents, _ = state
            _, command, _ = approved(state)
            SessionService(database).switch_role(identity, RoleRequest(role='learner'), 'be-learner')
            before = all_rows(database)
            with pytest.raises(ApiError) as caught:
                consents.grant(replace(identity, role='learner'), command, 'grant')
            assert caught.value.status == 403 and server.requests == []
            assert all_rows(database) == before
    asyncio.run(run())


def test_original_checked_provider_artifact_required_even_after_self_consistent_owner_edit(tmp_path):
    async def run():
        async with local_provider(text=canonical_bytes(payload()).decode()) as server:
            state = configured(tmp_path, server.base_url)
            database, identity, service, worker, _, _ = state
            original, _, _ = approved(state)
            assert await asyncio.to_thread(worker.run_once)
            from services.api.app.infrastructure.authoring_repository import AuthoringRepository
            with database.transaction() as conn:
                repo = AuthoringRepository(conn, identity.workspace_id)
                record = repo.load(original.id)
                record.view.raw_answer = 'self-consistent owner edit cannot replace the original provider artifact'
                repo.save(record)
            before = all_rows(database)
            with pytest.raises(ApiError) as caught:
                service.read(identity, original.id)
            assert caught.value.code == 'AUTHORING_INTEGRITY_ERROR'
            assert all_rows(database) == before
    asyncio.run(run())
