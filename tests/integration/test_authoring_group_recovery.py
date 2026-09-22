"""Three roots recover one real checked result using fresh SQLite owner instances.

The expired lease is explicit crash fault injection, not an observed OS crash.
The loopback Provider stays running so a second request would remain observable.
No unreviewed group is published and no numeric evaluator is invoked.
"""

import asyncio
from contextlib import aclosing

import pytest

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.authoring_group import AuthoringGroupService
from services.api.app.application.authoring_group_context import AuthoringGroupContext
from services.api.app.application.authoring_group_source import AuthoringGroupOutboundSource
from services.api.app.application.authoring_group_worker import AuthoringGroupWorker
from services.api.app.application.consents import ConsentsService
from services.api.app.application.content import ContentService
from services.api.app.application.provider_dispatch import CheckedDispatch
from services.api.app.application.provider_ports import OutboundSourceRegistry
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.provider_secret_store import FileSecretStore
from tests.integration.test_authoring_group_provider import (
    approve_request,
    configured,
    mixed_question_material,
    payload,
    request,
)
from tests.integration.test_retrieval import all_rows
from tests.provider_protocol_fixture import local_provider, test_preparer


def reopen(settings, secret_directory, provider_url):
    """Read persisted owners through entirely new application/Provider objects."""
    database = Database(settings)
    context = AuthoringGroupContext(database)
    secrets = FileSecretStore(secret_directory)
    preparer = test_preparer(provider_url)
    registry = OutboundSourceRegistry({'authoring': AuthoringGroupOutboundSource(context)})
    dispatch = CheckedDispatch(database, secrets, registry, preparer)
    authoring = AuthoringGroupService(database, context, dispatch)
    worker = AuthoringGroupWorker(database, context, dispatch)
    consents = ConsentsService(database, secrets, registry, preparer)
    return database, authoring, worker, consents, dispatch


@pytest.mark.parametrize('kind', ['lesson', 'practice_set', 'assessment'])
def test_completed_provider_result_recovers_one_group_and_survives_fresh_owner_readback(tmp_path, kind):
    async def run():
        if kind == 'lesson':
            body, generated, objects, bodies = request(), payload(), [], {}
        else:
            body, generated, objects, bodies = mixed_question_material(kind)
        answer = canonical_bytes(generated).decode()
        async with local_provider(text=answer) as server:
            state = configured(tmp_path, server.base_url)
            database, identity, original_service, original_worker, _, dispatch = state
            if objects:
                ContentService(database).publish(identity.workspace_id, objects, bodies)
            original, grant_command, grant = approve_request(state, body)
            assert server.requests == []
            lease = original_worker.claim()
            assert lease is not None and lease.job_id == original.id
            # Consume the real Provider terminal without calling owner finish.
            # This is the exact durable seam between dispatch and group adoption.
            async with aclosing(dispatch.dispatch(identity, original.id, grant.id,
                                                  lease.dispatch(), asyncio.Event())) as stream:
                async for _ in stream:
                    pass
            assert len(server.requests) == 1
            with database.transaction(immediate=False) as conn:
                checked = dispatch.read_result(conn, identity, original.id, grant.id)
                assert checked is not None and checked.answer is not None
                assert checked.answer.text == answer
                provider_receipt_id = checked.receipt.id
                assert conn.execute('SELECT COUNT(*) FROM authoring_group_candidates').fetchone()[0] == 0
                assert conn.execute('SELECT COUNT(*) FROM authoring_content_plans').fetchone()[0] == 0
            pending = original_service.read(identity, original.id)
            assert pending.summary.status == 'running' and pending.summary.candidate is None
            assert pending.raw_answer is pending.content_plan is pending.plan_ref is None
            assert pending.provider_receipt_id is None

            # Simulate the crashed owner's expired lease, preserving all checked
            # Provider artifacts, original authorization and immutable job input.
            with database.transaction() as conn:
                conn.execute('UPDATE jobs SET lease_until=? WHERE id=?', ('2000-01-01T00:00:00Z', original.id))
            fresh, authoring, recovered_worker, consents, recovered_dispatch = reopen(
                database.settings, tmp_path / 'synthetic-authoring-secrets', server.base_url
            )
            assert await asyncio.to_thread(recovered_worker.run_once)
            completed = authoring.read(identity, original.id)
            assert completed.summary.status == 'completed' and completed.summary.candidate is not None
            assert completed.preparation == pending.preparation and completed.request == body
            assert completed.provider_receipt_id == provider_receipt_id and completed.consent_id == grant.id
            assert completed.raw_answer == answer and completed.raw_refusal is None
            candidate = completed.summary.candidate
            draft = authoring.draft(identity, candidate.draft_id)
            assert draft.candidate == candidate and draft.root.entity == kind
            assert draft.content_plan.model_dump(mode='json') == generated['content_plan']
            assert draft.plan_ref == completed.plan_ref and draft.source_job_id == original.id
            assert draft.state == 'draft' and draft.base_ref is None and draft.numeric_check_ids == []
            assert draft.validation.mathematical == draft.validation.sources == draft.validation.independent_pedagogy == 'NOT_RUN'
            if kind == 'lesson':
                assert [item.model_dump(mode='json') for item in draft.blocks] == generated['draft']['blocks']
            else:
                assert [item.model_dump(mode='json') for item in draft.questions] == generated['draft']['questions']
                if kind == 'practice_set':
                    assert draft.root.lesson_ref == body.root.lesson_ref
                else:
                    assert draft.root.allowed_modes == ['independent', 'open_book']
                    assert draft.root.time_limit_seconds == 600
            private = [authoring.solution(identity, candidate.draft_id, ref.question.member_key)
                       for ref in draft.private_solution_refs]
            assert len(private) == (0 if kind == 'lesson' else 5)
            with fresh.transaction(immediate=False) as conn:
                assert recovered_dispatch.read_result(conn, identity, original.id, grant.id) == checked
                assert conn.execute('SELECT COUNT(*) FROM authoring_group_candidates WHERE source_job_id=?',
                                    (original.id,)).fetchone()[0] == 1
                assert conn.execute('SELECT COUNT(*) FROM authoring_content_plans WHERE source_job_id=?',
                                    (original.id,)).fetchone()[0] == 1
                assert conn.execute('SELECT COUNT(*) FROM provider_dispatches WHERE job_id=?',
                                    (original.id,)).fetchone()[0] == 1
            assert len(server.requests) == 1

            # A second reopen uses no initialize, seed, configuration update,
            # authorization or finish call. All protected reads are read-only.
            before = all_rows(fresh)
            reopened, reread, idle_worker, replay_consents, reread_dispatch = reopen(
                database.settings, tmp_path / 'synthetic-authoring-secrets', server.base_url
            )
            assert reread.read(identity, original.id) == completed
            assert reread.draft(identity, candidate.draft_id) == draft
            assert [reread.solution(identity, candidate.draft_id, ref.question.member_key)
                    for ref in draft.private_solution_refs] == private
            assert reread.prepare(identity, body, 'prepare-explicit-group') == original
            assert replay_consents.grant(identity, grant_command, 'grant-explicit-group') == grant
            assert consents.grant(identity, grant_command, 'grant-explicit-group') == grant
            with reopened.transaction(immediate=False) as conn:
                assert reread_dispatch.read_result(conn, identity, original.id, grant.id) == checked
            assert not await asyncio.to_thread(idle_worker.run_once)
            assert all_rows(reopened) == before and len(server.requests) == 1
    asyncio.run(run())
