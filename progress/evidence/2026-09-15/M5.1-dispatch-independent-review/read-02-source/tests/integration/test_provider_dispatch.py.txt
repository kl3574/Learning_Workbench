import asyncio
from pathlib import Path
from services.api.app.application.provider_dispatch import CheckedDispatch
from services.api.app.infrastructure.consent_repository import ConsentRepository
from services.api.app.infrastructure.provider_transport import ProviderTransport
from tests.provider_protocol_fixture import authorized_source, local_provider
import pytest
from services.api.app.application.errors import ApiError
from services.api.app.provider_dto import ConsentRevoke
from tests.provider_protocol_fixture import chat_stream, responses_stream

def test_real_http_dispatch_persists_single_terminal_and_never_replays_network(tmp_path: Path) -> None:
    async def run():
        async with local_provider() as server:
            db, identity, source, registry, job, secrets, preparer, consents, grant, lease = authorized_source(tmp_path, server.base_url)
            service = CheckedDispatch(db, secrets, registry, preparer, ProviderTransport())
            events = [event async for event in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            assert ''.join(event.text for event in events if event.type == 'delta') == 'ok'
            assert events[-1].type == 'finished' and events[-1].outcome == 'complete'
            with db.transaction() as conn:
                record = ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(grant.id)
                assert record is not None and record.terminal is not None
                assert record.terminal.terminal == events[-1]
            replay = [event async for event in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            assert replay == [events[-1]]
            assert len(server.requests) == server.connections == 1
            assert service.terminal(identity, record.id) == record.terminal
    asyncio.run(run())


def test_cancellation_of_real_waiting_http_retains_consumed_call_and_closes_stream(tmp_path: Path) -> None:
    async def run():
        async with local_provider(hold=True) as server:
            db, identity, _, registry, job, secrets, preparer, _, grant, lease = authorized_source(tmp_path, server.base_url)
            service = CheckedDispatch(db, secrets, registry, preparer)
            abort = asyncio.Event()
            async def consume():
                return [event async for event in service.dispatch(identity, job, grant.id, lease, abort)]
            task = asyncio.create_task(consume())
            await asyncio.wait_for(server.request_seen.wait(), 2)
            abort.set()
            events = await asyncio.wait_for(task, 2)
            assert events[-1].type == 'error' and events[-1].error_code == 'PROVIDER_CANCELLED'
            assert events[-1].provider_outcome == 'unknown'
            with db.transaction() as conn:
                record = ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(grant.id)
                assert record.terminal.terminal == events[-1]
            assert len(server.requests) == 1
    asyncio.run(run())


def test_real_sqlite_writer_lock_does_not_block_event_loop_or_cancel_preflight(tmp_path: Path) -> None:
    import threading
    import time
    from services.api.app.application.errors import ApiError
    async def run():
        async with local_provider() as server:
            db, identity, _, registry, job, secrets, preparer, _, grant, lease = authorized_source(tmp_path, server.base_url)
            locked = threading.Event()
            def hold_writer():
                with db.transaction():
                    locked.set()
                    time.sleep(0.6)
            thread = threading.Thread(target=hold_writer)
            thread.start()
            await asyncio.to_thread(locked.wait)
            service = CheckedDispatch(db, secrets, registry, preparer)
            abort = asyncio.Event()
            async def consume():
                try:
                    return [event async for event in service.dispatch(identity, job, grant.id, lease, abort)]
                except ApiError as error:
                    return error.code
            task = asyncio.create_task(consume())
            start = time.monotonic()
            await asyncio.sleep(0.03)
            heartbeat_elapsed = time.monotonic() - start
            abort.set()
            result = await asyncio.wait_for(task, 3)
            await asyncio.to_thread(thread.join)
            print(f'provider_sqlite_heartbeat_seconds={heartbeat_elapsed:.6f}; writer_hold_seconds=0.6')
            assert heartbeat_elapsed < 0.2
            assert result == 'PROVIDER_CANCELLED'
            assert server.requests == []
            with db.transaction() as conn:
                assert ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(grant.id) is None
    asyncio.run(run())


def test_recovery_skips_real_active_lease_then_records_unknown_after_expiry_without_http(tmp_path):
    from services.api.app.infrastructure.database import utc_now
    from packages.contracts.canonical import sha256_bytes
    db, identity, _, registry, job, secrets, preparer, _, grant, _ = authorized_source(tmp_path, 'http://127.0.0.1:1/v1')
    service = CheckedDispatch(db, secrets, registry, preparer)
    with db.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        _, _, body = repo.dispatch_material(grant.id)
        record, created = repo.begin_dispatch(grant.id, job, sha256_bytes(body), utc_now())
        assert created
    assert service.recover_unfinished(identity.workspace_id) == []
    with db.transaction() as conn:
        # Test-owned source explicitly advances the real Jobs lease into the past.
        conn.execute("UPDATE jobs SET lease_until='2020-01-01T00:00:00Z' WHERE id=?", (job,))
    recovered = service.recover_unfinished(identity.workspace_id)
    assert len(recovered) == 1 and recovered[0].dispatch_id == record.id
    assert recovered[0].terminal.error_code == 'PROVIDER_OUTCOME_UNKNOWN'
    assert recovered[0].terminal.usage.input_tokens is None
    assert service.recover_unfinished(identity.workspace_id) == []




@pytest.mark.parametrize('adapter', ['compatible_chat', 'official_responses'])
def test_both_real_adapters_send_exact_frozen_body_and_preserve_refusal(tmp_path, adapter):
    async def run():
        payload = (chat_stream if adapter == 'compatible_chat' else responses_stream)('拒绝 \n', refusal=True)
        async with local_provider(adapter=adapter, payload=payload) as server:
            db, identity, _, registry, job, secrets, preparer, _, grant, lease = authorized_source(tmp_path, server.base_url, adapter=adapter)
            service = CheckedDispatch(db, secrets, registry, preparer)
            events = [event async for event in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            assert events[-1].outcome == 'refused' and events[-1].output_state == 'complete'
            assert ''.join(event.text for event in events if event.type == 'delta') == '拒绝 \n'
            with db.transaction() as conn:
                repo = ConsentRepository(conn, identity.workspace_id)
                _, _, body = repo.dispatch_material(grant.id)
                receipt = repo.dispatch_for_consent(grant.id).terminal
                assert receipt.answer_artifact_id is None and receipt.refusal_artifact_id is not None
            assert server.requests == [body]
    asyncio.run(run())


def test_live_revoke_closes_real_waiting_request_with_unknown_remote_outcome(tmp_path):
    async def run():
        async with local_provider(hold=True) as server:
            db, identity, _, registry, job, secrets, preparer, consents, grant, lease = authorized_source(tmp_path, server.base_url)
            service = CheckedDispatch(db, secrets, registry, preparer)
            async def consume():
                return [event async for event in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            task = asyncio.create_task(consume())
            await asyncio.wait_for(server.request_seen.wait(), 2)
            await asyncio.to_thread(consents.revoke, identity, grant.id, ConsentRevoke(expected_revision=1), 'live-revoke')
            events = await asyncio.wait_for(task, 2)
            assert events[-1].error_code == 'CONSENT_REVOKED' and events[-1].provider_outcome == 'unknown'
            assert len(server.requests) == 1
    asyncio.run(run())


def test_total_deadline_runs_while_consumer_is_paused_and_keeps_partial_private_output(tmp_path):
    import time
    async def run():
        payload = chat_stream('partial')
        first_two = payload.find(b'\n\n', payload.find(b'\n\n') + 2) + 2
        async with local_provider(payload=payload, stall_after=first_two) as server:
            db, identity, _, registry, job, secrets, preparer, _, grant, lease = authorized_source(tmp_path, server.base_url, timeout=1)
            service = CheckedDispatch(db, secrets, registry, preparer)
            started = time.monotonic()
            stream = service.dispatch(identity, job, grant.id, lease, asyncio.Event())
            first = await anext(stream)
            assert first.type == 'delta' and first.text == 'partial'
            await asyncio.sleep(1.2)  # Deliberately do not consume the generator.
            with db.transaction() as conn:
                receipt = ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(grant.id).terminal
            assert receipt is not None and receipt.terminal.error_code == 'PROVIDER_TIMEOUT'
            assert receipt.terminal.output_state == 'partial' and receipt.answer_artifact_id is not None
            rest = [event async for event in stream]
            assert rest[-1] == receipt.terminal
            assert time.monotonic() - started < 1.8
            assert len(server.requests) == 1
    asyncio.run(run())


def test_abort_after_real_dns_resolution_prevents_tcp_and_keeps_one_consumed_reservation(tmp_path):
    async def run():
        async with local_provider() as server:
            db, identity, _, registry, job, secrets, preparer, _, grant, lease = authorized_source(tmp_path, server.base_url)
            abort = asyncio.Event()
            async def resolver(host, port):
                # The actual resolver result is released only after cancellation.
                result = await asyncio.get_running_loop().getaddrinfo(host, port, type=__import__('socket').SOCK_STREAM)
                abort.set()
                return tuple(dict.fromkeys(str(item[4][0]) for item in result))
            service = CheckedDispatch(db, secrets, registry, preparer, ProviderTransport(resolver=resolver))
            events = [event async for event in service.dispatch(identity, job, grant.id, lease, abort)]
            assert events[-1].error_code == 'PROVIDER_CANCELLED'
            assert server.connections == 0 and server.requests == []
            with db.transaction() as conn:
                assert ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(grant.id).terminal is not None
    asyncio.run(run())


def test_actual_usage_over_frozen_bound_preserves_completed_fact_and_observed_counts(tmp_path):
    async def run():
        async with local_provider(payload=chat_stream('ok', input_tokens=99999)) as server:
            db, identity, _, registry, job, secrets, preparer, _, grant, lease = authorized_source(tmp_path, server.base_url)
            service = CheckedDispatch(db, secrets, registry, preparer)
            events = [event async for event in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            terminal = events[-1]
            assert terminal.type == 'error' and terminal.error_code == 'OUTBOUND_BUDGET_EXCEEDED'
            assert terminal.provider_outcome == 'completed' and terminal.usage.input_tokens == 99999
            assert terminal.output_state == 'partial'
            with db.transaction() as conn:
                receipt = ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(grant.id).terminal
                assert receipt.terminal == terminal and receipt.answer_artifact_id is not None
    asyncio.run(run())


def test_current_independent_policy_blocks_queued_terminal_after_real_completion(tmp_path):
    from services.api.app.application.assessment import AssessmentService
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture, start
    async def run():
        async with local_provider() as server:
            db, identity, source, registry, job, secrets, preparer, _, grant, lease = authorized_source(tmp_path, server.base_url)
            fixture = assessment_fixture('providerdeliverypolicy')
            import_fixture(db, identity, fixture, 'policy-material')
            service = CheckedDispatch(db, secrets, registry, preparer)
            stream = service.dispatch(identity, job, grant.id, lease, asyncio.Event())
            assert (await anext(stream)).type == 'delta'
            for _ in range(100):
                with db.transaction() as conn:
                    record = ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(grant.id)
                if record.terminal:
                    break
                await asyncio.sleep(0.01)
            assert record.terminal is not None
            source.cancel(identity, job)
            assert start((db, identity, fixture, AssessmentService(db)), key='actual-policy-start').status == 'active'
            with pytest.raises(ApiError) as error:
                await anext(stream)
            assert error.value.code == 'ASSESSMENT_ACTIVE'
            with pytest.raises(ApiError) as error:
                service.terminal(identity, record.id)
            assert error.value.code == 'ASSESSMENT_ACTIVE'
            assert len(server.requests) == 1
    asyncio.run(run())


@pytest.mark.parametrize('change', ['revoke', 'secret_missing', 'source_preparation', 'new_consent_binding',
                                   'proof_missing', 'wrong_lease', 'wrong_job', 'source_cancel'])
def test_changed_authorization_or_source_has_zero_connections_and_zero_dispatch(tmp_path, change):
    from services.api.app.application.provider_budget import RequestPreparer
    from services.api.app.infrastructure.provider_repository import ProviderRepository
    from services.api.app.provider_dto import ConsentCreate, ConsentPreviewWrite, OutboundBudget
    async def run():
        async with local_provider() as server:
            db, identity, source, registry, job, secrets, preparer, consents, grant, lease = authorized_source(tmp_path, server.base_url)
            if change == 'revoke':
                consents.revoke(identity, grant.id, ConsentRevoke(expected_revision=1), 'revoke-before')
            elif change == 'secret_missing':
                with db.transaction() as conn:
                    locator = ProviderRepository(conn, identity.workspace_id).secret_locator('provider_test', 2)
                secrets.delete(locator)
            elif change == 'source_preparation':
                source.advance_preparation(identity, job)
            elif change == 'new_consent_binding':
                proposal = consents.preview(identity, ConsentPreviewWrite(job_id=job, expected_job_revision=2,
                    provider_id='provider_test', expected_provider_revision=2, expires_at=grant.summary.expires_at,
                    budget=OutboundBudget.model_validate(grant.summary.budget.model_dump())), 'preview-second')
                consents.grant(identity, ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256), 'grant-second')
            elif change == 'proof_missing':
                preparer = RequestPreparer()
            elif change == 'wrong_lease':
                lease = lease.model_copy(update={'owner_id': 'different_worker'})
            elif change == 'source_cancel':
                source.cancel(identity, job)
            service = CheckedDispatch(db, secrets, registry, preparer)
            with pytest.raises(ApiError):
                async for _ in service.dispatch(identity, 'job_other' if change == 'wrong_job' else job,
                                                grant.id, lease, asyncio.Event()):
                    pass
            assert server.connections == 0 and server.requests == []
            with db.transaction() as conn:
                assert ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(grant.id) is None
    asyncio.run(run())


def test_terminal_replay_after_revoke_uses_original_history_without_new_network(tmp_path):
    async def run():
        async with local_provider() as server:
            db, identity, source, registry, job, secrets, preparer, consents, grant, lease = authorized_source(tmp_path, server.base_url)
            service = CheckedDispatch(db, secrets, registry, preparer)
            original = [e async for e in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            consents.revoke(identity, grant.id, ConsentRevoke(expected_revision=1), 'after-completion-revoke')
            source.cancel(identity, job)
            replay = [e async for e in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            assert replay == [original[-1]] and len(server.requests) == 1
    asyncio.run(run())


@pytest.mark.parametrize('case,expected', [('complete', 'finished'), ('refused', 'PROVIDER_REFUSAL'),
                                         ('incomplete', 'PROVIDER_INCOMPLETE')])
def test_core_projection_requires_saved_receipt_and_never_leaks_refusal_as_answer(tmp_path, case, expected):
    async def run():
        async with local_provider(payload=chat_stream('text', refusal=case == 'refused',
                finish='length' if case == 'incomplete' else 'stop')) as server:
            db, identity, _, registry, job, secrets, preparer, _, grant, lease = authorized_source(tmp_path, server.base_url)
            service = CheckedDispatch(db, secrets, registry, preparer)
            events = [e async for e in service.core_events(identity, job, grant.id, lease, asyncio.Event())]
            if case == 'complete':
                assert events[-1].type == expected
            else:
                assert events[-1].type == 'error' and events[-1].error_code == expected
            if case == 'refused':
                assert all(e.type != 'delta' for e in events)
            with db.transaction() as conn:
                assert ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(grant.id).terminal is not None
    asyncio.run(run())


@pytest.mark.parametrize('watched', ['delta', 'usage'])
def test_received_checked_fact_survives_real_revoke_before_public_delivery(tmp_path, monkeypatch, watched):
    from services.api.app.infrastructure.provider_sse import ProtocolDecoder
    async def run():
        async with local_provider() as server:
            db, identity, _, registry, job, secrets, preparer, consents, grant, lease = authorized_source(tmp_path, server.base_url)
            original = ProtocolDecoder.stream
            revoked = False
            received = None
            async def release_after_revoke(decoder, chunks):
                nonlocal revoked, received
                async for event in original(decoder, chunks):
                    if event.type == watched and not revoked:
                        received = event
                        await asyncio.to_thread(consents.revoke, identity, grant.id,
                                                ConsentRevoke(expected_revision=1), 'receive-boundary-revoke')
                        revoked = True
                    yield event
            monkeypatch.setattr(ProtocolDecoder, 'stream', release_after_revoke)
            service = CheckedDispatch(db, secrets, registry, preparer)
            events = [e async for e in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            assert revoked and received is not None
            assert events[-1].error_code == 'CONSENT_REVOKED'
            with db.transaction() as conn:
                repo = ConsentRepository(conn, identity.workspace_id)
                receipt = repo.dispatch_for_consent(grant.id).terminal
                assert receipt.terminal.output_state == 'partial' and receipt.answer_artifact_id is not None
                if watched == 'usage':
                    assert receipt.terminal.usage.input_tokens == received.input_tokens
                    assert receipt.terminal.usage.output_tokens == received.output_tokens
                else:
                    assert all(event.type != 'delta' for event in events)
                artifact = conn.execute('SELECT bytes FROM provider_artifacts WHERE id=?', (receipt.answer_artifact_id,)).fetchone()
                assert bytes(artifact[0]) == b'ok'
            assert len(server.requests) == 1
    asyncio.run(run())


def test_guard_which_finishes_after_deadline_cannot_release_request_bytes(tmp_path, monkeypatch):
    import threading
    import time
    async def run():
        async with local_provider() as server:
            db, identity, source, registry, job, secrets, preparer, _, grant, lease = authorized_source(tmp_path, server.base_url, timeout=1)
            trigger = threading.Event()
            counter_lock = threading.Lock()
            slow_count = 0
            original_verify = source.verify_dispatch
            def slow_actual_verification(*args, **kwargs):
                nonlocal slow_count
                result = original_verify(*args, **kwargs)
                if trigger.is_set():
                    with counter_lock:
                        slow_count += 1
                        number = slow_count
                    # Both real owner checks start within the deadline. Release
                    # the network-bound check first, while the monitoring check
                    # is still performing its actual transaction's verification.
                    time.sleep(1.1 if number == 1 else 1.3)
                return result
            monkeypatch.setattr(source, 'verify_dispatch', slow_actual_verification)
            class ReleaseBoundaryTransport(ProviderTransport):
                async def stream(self, config, body, secret, *, guard=None):
                    calls = 0
                    async def network_guard():
                        nonlocal calls
                        calls += 1
                        if calls == 3:  # resolve, connect, then first HTTP write
                            trigger.set()
                        await guard()
                    async for chunk in super().stream(config, body, secret, guard=network_guard):
                        yield chunk
            service = CheckedDispatch(db, secrets, registry, preparer, ReleaseBoundaryTransport())
            events = [e async for e in service.dispatch(identity, job, grant.id, lease, asyncio.Event())]
            assert trigger.is_set() and slow_count >= 2
            assert events[-1].error_code == 'PROVIDER_TIMEOUT'
            assert server.requests == []
            assert server.headers_received == 0
    asyncio.run(run())
