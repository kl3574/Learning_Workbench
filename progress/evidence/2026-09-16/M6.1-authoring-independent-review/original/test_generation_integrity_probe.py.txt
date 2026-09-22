"""Private independent counterexamples; real SQLite and real loopback fixture."""
import asyncio
import pytest
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.errors import ApiError
from services.api.app.authoring_dto import candidate_sha256
from services.api.app.infrastructure.authoring_repository import AuthoringRepository
from services.api.app.provider_dto import ConsentRevoke, ConsentPreviewWrite, OutboundBudget
from services.api.app.infrastructure.security import expires_after
from tests.integration.test_authoring_provider import configured, approved, payload
from tests.provider_protocol_fixture import local_provider


def test_self_consistent_candidate_cannot_replace_actual_completed_provider_output(tmp_path):
    async def run():
        async with local_provider(text=canonical_bytes(payload()).decode()) as server:
            state = configured(tmp_path, server.base_url)
            database, identity, service, worker, _, _ = state
            original, _, _ = approved(state)
            assert await asyncio.to_thread(worker.run_once)
            real = service.read(identity, original.id)
            draft_id = real.summary.candidate.draft_id
            assert len(server.requests) == 1
            with database.transaction() as conn:
                repo = AuthoringRepository(conn, identity.workspace_id)
                candidate = repo.candidate(draft_id)
                record = repo.load(original.id)
                candidate.payload.body_markdown = '合成损坏反例：这个候选不是供应商实际原输出。'
                candidate.body_sha256 = sha256_bytes(candidate.payload.body_markdown.encode())
                candidate.candidate.candidate_sha256 = candidate_sha256(candidate.payload)
                raw = canonical_bytes(candidate).decode()
                conn.execute('UPDATE authoring_candidates SET record_json=?,record_sha256=? WHERE draft_id=?',
                    (raw, sha256_bytes(raw.encode()), draft_id))
                record.view.summary.candidate = candidate.candidate
                repo.save(record)
                # Do not modify the Provider receipt/artifact, Jobs result or its terminal event.
            with pytest.raises(ApiError) as caught:
                service.draft(identity, draft_id)
            assert caught.value.code == 'AUTHORING_INTEGRITY_ERROR'
            assert len(server.requests) == 1
    asyncio.run(run())


def test_revoked_before_dispatch_can_prepare_new_explicit_consent_for_same_job(tmp_path):
    async def run():
        async with local_provider(text=canonical_bytes(payload()).decode()) as server:
            state = configured(tmp_path, server.base_url)
            _, identity, service, worker, consents, _ = state
            original, _, grant = approved(state)
            consents.revoke(identity, grant.id, ConsentRevoke(expected_revision=1), 'revoke-before-dispatch')
            assert server.requests == []
            # Existing work is processed by the owner; GET itself must not repair state.
            assert await asyncio.to_thread(worker.run_once)
            current = service.read(identity, original.id)
            assert current.summary.id == original.id
            assert current.summary.status == 'awaiting_approval'
            proposal = consents.preview(identity, ConsentPreviewWrite(job_id=original.id,
                expected_job_revision=current.summary.job_revision, provider_id='test_provider',
                expected_provider_revision=2, expires_at=expires_after(300), budget=OutboundBudget(
                max_input_tokens=20000,max_output_tokens=5000,max_provider_calls=1,max_search_calls=0,
                max_tool_calls=0,timeout_seconds=10,max_cost_usd=None)), 'explicit-preview-again')
            assert proposal.summary.job_id == original.id
            assert server.requests == []
    asyncio.run(run())
