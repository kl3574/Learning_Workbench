"""Actual SQLite source/consent/dispatch with only a synthetic loopback model."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from services.api.app.application.consents import ConsentsService
from services.api.app.application.errors import ApiError
from services.api.app.application.provider_budget import ProofRegistry
from services.api.app.application.provider_dispatch import CheckedDispatch
from services.api.app.application.providers import ProviderService
from services.api.app.infrastructure.consent_repository import ConsentRepository
from services.api.app.infrastructure.provider_secret_store import FileSecretStore
from services.api.app.provider_dto import ConsentCreate, ConsentPreviewWrite, OutboundBudget, ProviderConfigWrite, ProviderSecretWrite
from tests.provider_fixture import provider_source
from tests.provider_protocol_fixture import MODEL, local_provider, test_preparer


def prepared_source(tmp_path, url):
    db, identity, source, registry, job = provider_source(tmp_path)
    store = FileSecretStore(tmp_path / 'synthetic-secrets')
    store.initialize()
    preparer = test_preparer(url)
    providers = ProviderService(db, store, preparer)
    providers.save_config(identity, 'provider_proof', ProviderConfigWrite(expected_revision=0,
        adapter='official_responses', base_url=url, model=MODEL, embedding_model=None,
        endpoint_policy='explicit_loopback', pricing=None), 'config')
    providers.save_secret(identity, 'provider_proof', ProviderSecretWrite(expected_revision=1,
        secret='synthetic-proof-fixture-secret'), 'secret')
    config = providers.read_config(identity, 'provider_proof')
    original = preparer.registry.resolve(config)
    deadline = (datetime.now(UTC) + timedelta(minutes=2)).isoformat().replace('+00:00', 'Z')
    proof = replace(original, valid_until=deadline,
        validity_evidence=b'Explicit synthetic review deadline; not evidence for a vendor alias.')
    preparer.registry = ProofRegistry([proof])
    service = ConsentsService(db, store, registry, preparer)
    request = ConsentPreviewWrite(job_id=job, expected_job_revision=1, provider_id=config.id,
        expected_provider_revision=config.revision,
        expires_at=(datetime.now(UTC) + timedelta(minutes=5)).isoformat().replace('+00:00', 'Z'),
        budget=OutboundBudget(max_input_tokens=20000, max_output_tokens=100, max_provider_calls=1,
            max_search_calls=0, max_tool_calls=0, timeout_seconds=10, max_cost_usd=None))
    return db, identity, source, registry, job, store, preparer, service, request, proof


def test_changed_model_binding_makes_old_proposal_unavailable_without_rewriting_it(tmp_path):
    from tests.integration.test_retrieval import all_rows

    async def run():
        async with local_provider(adapter='official_responses') as server:
            db, identity, _, _, _, _, preparer, consents, request, proof = prepared_source(tmp_path, server.base_url)
            original = consents.preview(identity, request, 'preview')
            # A trusted composition update records a different reviewed model
            # version for the same request alias; the old proof is not reused.
            preparer.registry = ProofRegistry([replace(proof, model_versions=('synthetic-byte-model-revision-2',))])
            before = all_rows(db)
            current = consents.proposal(identity, original.id)
            assert current.validity == 'unavailable'
            assert current.summary == original.summary and current.proposal_sha256 == original.proposal_sha256
            assert consents.preview(identity, request, 'preview') == original
            assert all_rows(db) == before
            assert server.connections == server.headers_received == 0 and not server.requests
    asyncio.run(run())


def invalidate(preparer, proof, cause, monkeypatch):
    if cause == 'deadline':
        # Change only the current clock at the recorded proof boundary, not its
        # evidence/bytes or the still-future consent expiry.
        monkeypatch.setattr('services.api.app.application.provider_budget.utc_now', lambda: proof.valid_until)
    else:
        preparer.registry = ProofRegistry([proof], withdrawn_proofs=[proof.sha256])


@pytest.mark.parametrize('cause', ['deadline', 'withdrawal'])
def test_invalid_proof_blocks_new_preview_and_grant_but_preserves_original_preview(tmp_path, monkeypatch, cause):
    from tests.integration.test_retrieval import all_rows

    async def run():
        async with local_provider(adapter='official_responses') as server:
            db, identity, _, _, _, _, preparer, consents, request, proof = prepared_source(tmp_path, server.base_url)
            original = consents.preview(identity, request, 'preview')
            invalidate(preparer, proof, cause, monkeypatch)
            before = all_rows(db)
            for operation in (lambda: consents.preview(identity, request, 'new-preview'),
                              lambda: consents.grant(identity, ConsentCreate(proposal_id=original.id,
                                  proposal_sha256=original.proposal_sha256), 'new-grant')):
                with pytest.raises(ApiError) as refused:
                    operation()
                assert refused.value.code == 'CAPABILITY_UNSUPPORTED'
            assert consents.proposal(identity, original.id).validity == 'unavailable'
            assert consents.preview(identity, request, 'preview') == original
            assert all_rows(db) == before
            assert server.connections == server.headers_received == 0 and not server.requests
    asyncio.run(run())


@pytest.mark.parametrize('cause', ['deadline', 'withdrawal'])
def test_invalid_proof_blocks_granted_dispatch_and_keeps_original_grant_ack(tmp_path, monkeypatch, cause):
    from tests.integration.test_retrieval import all_rows

    async def run():
        async with local_provider(adapter='official_responses') as server:
            db, identity, source, registry, job, store, preparer, consents, request, proof = prepared_source(tmp_path, server.base_url)
            proposal = consents.preview(identity, request, 'preview')
            approval = ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256)
            grant = consents.grant(identity, approval, 'grant')
            lease = source.claim(identity, job)
            invalidate(preparer, proof, cause, monkeypatch)
            before = all_rows(db)
            service = CheckedDispatch(db, store, registry, preparer)
            with pytest.raises(ApiError) as refused:
                _ = [event async for event in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            assert refused.value.code == 'CAPABILITY_UNSUPPORTED'
            assert consents.grant(identity, approval, 'grant') == grant
            with db.transaction() as conn:
                assert ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(grant.id) is None
            assert all_rows(db) == before
            assert server.connections == server.headers_received == 0 and not server.requests
    asyncio.run(run())


@pytest.mark.parametrize('cause', ['deadline', 'withdrawal'])
def test_completed_result_and_ack_remain_readable_after_proof_invalidation_without_resending(tmp_path, monkeypatch, cause):
    from tests.integration.test_retrieval import all_rows

    async def run():
        async with local_provider(adapter='official_responses') as server:
            db, identity, source, registry, job, store, preparer, consents, request, proof = prepared_source(tmp_path, server.base_url)
            proposal = consents.preview(identity, request, 'preview')
            approval = ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256)
            grant = consents.grant(identity, approval, 'grant')
            lease = source.claim(identity, job)
            service = CheckedDispatch(db, store, registry, preparer)
            events = [event async for event in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            assert events[-1].type == 'finished' and events[-1].outcome == 'complete'
            assert ''.join(event.text for event in events if event.type == 'delta') == 'ok'
            with db.transaction() as conn:
                result = service.read_result(conn, identity, job, grant.id)
            assert result is not None and result.answer is not None and result.answer.text == 'ok'
            invalidate(preparer, proof, cause, monkeypatch)
            before = all_rows(db)
            assert consents.grant(identity, approval, 'grant') == grant
            assert service.terminal(identity, result.receipt.dispatch_id) == result.receipt
            with db.transaction() as conn:
                assert service.read_result(conn, identity, job, grant.id) == result
            replay = [event async for event in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            assert replay == [events[-1]]
            assert all_rows(db) == before
            assert server.connections == server.headers_received == len(server.requests) == 1
    asyncio.run(run())
