"""Real SQLite Tutor/Jobs/Context and an explicitly artificial loopback protocol.

The complete-byte model is test-only: no production proof or paid endpoint.
"""

from dataclasses import replace

import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.errors import ApiError
from services.api.app.application.tutor import TutorService
from services.api.app.application.tutor_context import ContextService
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import SessionIdentity
from services.api.app.infrastructure.tutor_repository import TutorRepository
from services.api.app.tutor_dto import TutorContextBinding, TutorRunCancel, TutorRunCreate, TutorThreadCreate
from tests.integration.test_retrieval import all_rows, publish_small


@pytest.fixture
def tutor(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    identity = SessionIdentity('session_tutor_fixture', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    _, lesson, _ = publish_small(database, identity, 'tutorseam', ['原创合成完整上下文。\n'])
    scope = dm.ViewContext(view_kind='lesson', active_ref=reference(lesson))
    create = TutorThreadCreate(scope=scope, binding=TutorContextBinding(practice=None, assessment=None), title='原创测试对话')
    service = TutorService(database, ContextService(database))
    return database, identity, service, create


def started(tutor, key='start'):
    database, identity, service, create = tutor
    thread = service.create_thread(identity, create, 'thread')
    request = TutorRunCreate(request=dm.TutorRequest(thread_id=thread.id, workspace_id=identity.workspace_id,
        message='请解释当前完整材料。', intent='explain', context=create.scope, web_search=False, consent_id=None),
        expected_thread_revision=thread.revision, binding=create.binding)
    return thread, request, service.start(identity, request, key)


def test_created_run_is_real_same_id_job_and_original_ack_survives_cancel_restart(tutor):
    database, identity, service, create = tutor
    thread, request, ack = started(tutor)
    assert ack.run.id and ack.job_revision == 1 and ack.thread_revision == 2
    with database.connect() as connection:
        job = connection.execute('SELECT kind,status FROM jobs WHERE id=?', (ack.run.id,)).fetchone()
        assert tuple(job) == ('tutor', 'queued')
    cancelled = service.cancel(identity, ack.run.id, TutorRunCancel(expected_revision=1), 'cancel')
    assert cancelled.status == 'cancelled' and cancelled.cancel_requested
    reopened = TutorService(database, ContextService(database))
    before = all_rows(database)
    assert reopened.start(identity, request, 'start') == ack
    assert reopened.create_thread(identity, create, 'thread') == thread
    assert reopened.read(identity, ack.run.id).run.status == 'cancelled'
    assert [event.type for event in reopened.events(identity, ack.run.id, 0)] == ['queued', 'cancelled']
    assert all_rows(database) == before


def test_unknown_original_command_identity_and_thread_cas_are_not_replaced(tutor):
    database, identity, service, _ = tutor
    _, request, ack = started(tutor)
    before = all_rows(database)
    changed = request.model_copy(update={'request': request.request.model_copy(update={'message': '另一个问题。'})})
    with pytest.raises(ApiError) as conflict:
        service.start(identity, changed, 'start')
    assert conflict.value.code == 'IDEMPOTENCY_CONFLICT'
    with pytest.raises(ApiError) as active:
        service.start(identity, request, 'different')
    assert active.value.code == 'THREAD_RUN_ACTIVE'
    assert all_rows(database) == before
    service.cancel(identity, ack.run.id, TutorRunCancel(expected_revision=1), 'cancel')
    with pytest.raises(ApiError) as stale:
        service.start(identity, changed, 'new')
    assert stale.value.status == 412


def test_running_cancel_retains_lease_and_old_ack_without_second_terminal(tutor):
    database, identity, service, _ = tutor
    _, _, ack = started(tutor)
    with database.transaction() as connection:
        repo = TutorRepository(connection, identity.workspace_id)
        lease = repo.jobs.claim(repo.jobs.load(ack.run.id), 90)
        repo.sync_job(ack.run.id)
    control = service.cancel(identity, ack.run.id, TutorRunCancel(expected_revision=lease.revision), 'cancel')
    assert control.status == 'running' and control.cancel_requested and control.job_revision == lease.revision + 1
    with database.transaction() as connection:
        repo = TutorRepository(connection, identity.workspace_id)
        state = repo.source_state(ack.run.id)
        assert state.lease_owner == lease.owner and state.lease_until == lease.expires_at
        view = repo.view(ack.run.id)
        repo.finish(ack.run.id, 'cancelled', view.result, '', lease=lease)
    before = all_rows(database)
    assert service.cancel(identity, ack.run.id, TutorRunCancel(expected_revision=lease.revision), 'cancel') == control
    assert service.cancel(identity, ack.run.id, TutorRunCancel(expected_revision=1), 'terminal-noop').status == 'cancelled'
    assert len(service.events(identity, ack.run.id, 0)) == 2
    # Only the explicit no-op command receipt is new, not a second event/terminal.
    after = all_rows(database)
    assert len(after['tutor_commands']) == len(before['tutor_commands']) + 1
    after['tutor_commands'] = before['tutor_commands']
    assert after == before


def test_thread_pagination_freezes_high_water_and_binds_session(tutor):
    database, identity, service, create = tutor
    first = service.create_thread(identity, create, 'one')
    second = service.create_thread(identity, create, 'two')
    page = service.threads(identity, limit=1)
    assert [item.id for item in page.items] == [first.id] and page.next_cursor
    service.create_thread(identity, create, 'three')
    next_page = service.threads(identity, cursor=page.next_cursor, limit=1)
    assert [item.id for item in next_page.items] == [second.id] and next_page.next_cursor is None
    before = all_rows(database)
    with pytest.raises(ApiError):
        service.threads(replace(identity, id='session_other'), cursor=page.next_cursor, limit=1)
    assert all_rows(database) == before


@pytest.mark.parametrize('fault', ['missing_event', 'missing_original_command', 'forged_job_input'])
def test_owned_history_corruption_never_looks_like_an_empty_run(tutor, fault):
    database, identity, service, _ = tutor
    _, _, ack = started(tutor)
    with database.transaction() as connection:
        if fault == 'missing_event':
            connection.execute('DELETE FROM tutor_events WHERE run_id=?', (ack.run.id,))
        elif fault == 'missing_original_command':
            connection.execute("DELETE FROM tutor_commands WHERE run_id=? AND route='POST /tutor/runs'", (ack.run.id,))
        else:
            connection.execute("UPDATE jobs SET input_json='{}',input_sha256=? WHERE id=?", ('0' * 64, ack.run.id))
    before = all_rows(database)
    with pytest.raises(ApiError) as damaged:
        service.read(identity, ack.run.id)
    assert damaged.value.code == 'TUTOR_INTEGRITY_ERROR'
    assert all_rows(database) == before


class NoTransport:
    """An assertion-only absence of a Provider, never a synthetic success."""
    calls = 0

    def recover_unfinished(self, workspace_id):
        return []

    def read_result(self, connection, identity, job_id, consent_id):
        return None

    async def dispatch(self, *args):
        self.calls += 1
        raise AssertionError('No consent/proof authorizes a Provider call')
        yield  # pragma: no cover


def build_material(value, context, revision):
    from services.api.app.application.tutor_source import build_outbound
    return build_outbound(value, context, revision)


def test_real_context_freezes_without_model_and_waits_without_fake_approval(tutor):
    from services.api.app.application.tutor_worker import TutorWorker
    database, identity, service, _ = tutor
    _, _, ack = started(tutor)
    provider = NoTransport()
    worker = TutorWorker(database, service.context, provider, build_material)
    assert worker.run_once()
    current = service.read(identity, ack.run.id)
    assert current.run.status == 'awaiting_approval' and current.context is not None
    assert current.latest_proposal_id is current.consent_id is None
    assert current.context.included[0].material_review == 'unreviewed'
    assert current.context.included[0].body_sha256 is not None
    assert current.result.provider is None and current.result.usage.input_tokens is None
    assert [event.type for event in service.events(identity, ack.run.id, 0)] == ['queued', 'context_ready']
    before = all_rows(database)
    assert not worker.run_once() and provider.calls == 0
    assert all_rows(database) == before
    with database.transaction(immediate=False) as connection:
        state = TutorRepository(connection, identity.workspace_id).source_state(ack.run.id)
        prepared = service.context.read(connection, identity, state.context_id)
        assert build_material(state.input, prepared, state.job_revision).prepared_input_sha256 == state.prepared_input_sha256


def test_no_consent_cancel_of_prepared_run_is_local_and_unique(tutor):
    from services.api.app.application.tutor_worker import TutorWorker
    database, identity, service, _ = tutor
    _, _, ack = started(tutor)
    provider = NoTransport()
    worker = TutorWorker(database, service.context, provider, build_material)
    worker.run_once()
    current = service.read(identity, ack.run.id)
    result = service.cancel(identity, ack.run.id, TutorRunCancel(expected_revision=current.job_revision), 'cancel')
    assert result.status == 'cancelled' and not worker.run_once() and provider.calls == 0
    assert [event.type for event in service.events(identity, ack.run.id, 0)].count('cancelled') == 1


def test_concurrent_starts_accept_only_one_actual_round(tutor):
    from concurrent.futures import ThreadPoolExecutor
    database, identity, service, create = tutor
    thread = service.create_thread(identity, create, 'thread')
    request = TutorRunCreate(request=dm.TutorRequest(thread_id=thread.id, workspace_id=identity.workspace_id,
        message='并发原创问题', intent='hint', context=create.scope), expected_thread_revision=1, binding=create.binding)
    def run(key):
        try:
            return service.start(identity, request, key)
        except ApiError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(run, ['one', 'two']))
    assert sum(not isinstance(value, str) for value in values) == 1
    assert values.count('THREAD_RUN_ACTIVE') == 1
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM jobs WHERE kind='tutor'").fetchone()[0] == 1
        assert connection.execute('SELECT COUNT(*) FROM messages').fetchone()[0] == 1


def configured(tutor, tmp_path, url, *, proof=True):
    from services.api.app.application.consents import ConsentsService
    from services.api.app.application.provider_budget import ProofRegistry, RequestPreparer
    from services.api.app.application.provider_dispatch import CheckedDispatch
    from services.api.app.application.provider_ports import OutboundSourceRegistry
    from services.api.app.application.providers import ProviderService
    from services.api.app.application.tutor_source import TutorOutboundSource
    from services.api.app.application.tutor_worker import TutorWorker
    from services.api.app.infrastructure.provider_secret_store import FileSecretStore
    from services.api.app.provider_dto import ProviderConfigWrite, ProviderSecretWrite
    from tests.provider_protocol_fixture import MODEL, test_preparer
    database, identity, service, _ = tutor
    secrets = FileSecretStore(tmp_path / 'synthetic-tutor-secrets')
    secrets.initialize()
    preparer = test_preparer(url) if proof else RequestPreparer(ProofRegistry())
    providers = ProviderService(database, secrets, preparer)
    providers.save_config(identity, 'provider_tutor_fixture', ProviderConfigWrite(expected_revision=0,
        adapter='compatible_chat', base_url=url, model=MODEL, embedding_model=None,
        endpoint_policy='explicit_loopback', pricing=None), 'config')
    providers.save_secret(identity, 'provider_tutor_fixture', ProviderSecretWrite(expected_revision=1,
        secret='<SYNTHETIC>'), 'secret')
    registry = OutboundSourceRegistry({'tutor': TutorOutboundSource(service.context)})
    dispatch = CheckedDispatch(database, secrets, registry, preparer)
    consents = ConsentsService(database, secrets, registry, preparer)
    return TutorWorker(database, service.context, dispatch, build_material), consents, dispatch


def approved(tutor, worker, consents):
    from services.api.app.infrastructure.security import expires_after
    from services.api.app.provider_dto import ConsentCreate, ConsentPreviewWrite, OutboundBudget
    _, identity, service, _ = tutor
    thread, request, original = started(tutor)
    assert worker.run_once()
    prepared = service.read(identity, original.run.id)
    proposal = consents.preview(identity, ConsentPreviewWrite(job_id=original.run.id,
        expected_job_revision=prepared.job_revision, provider_id='provider_tutor_fixture', expected_provider_revision=2,
        expires_at=expires_after(300), budget=OutboundBudget(max_input_tokens=20000, max_output_tokens=500,
            max_provider_calls=1, max_search_calls=0, max_tool_calls=0, timeout_seconds=10, max_cost_usd=None)), 'preview')
    current = service.read(identity, original.run.id)
    assert current.latest_proposal_id == proposal.id and current.job_revision == prepared.job_revision
    assert service.events(identity, original.run.id, prepared.run.last_seq)[0].approval_id == proposal.id
    consent_request = ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256)
    grant = consents.grant(identity, consent_request, 'grant')
    queued = service.read(identity, original.run.id)
    assert queued.run.id == original.run.id and queued.run.status == 'queued' and queued.consent_id == grant.id
    return thread, request, original, consent_request, grant


@pytest.mark.parametrize('outcome', ['complete', 'refusal', 'incomplete', 'eof'])
def test_real_local_protocol_owner_chain_preserves_terminal_channels_and_original_replays(tutor, tmp_path, outcome):
    import asyncio
    from tests.provider_protocol_fixture import chat_stream, local_provider
    async def run():
        payload = None if outcome == 'complete' else chat_stream('保留原输出 \n', refusal=outcome == 'refusal',
            finish='length' if outcome == 'incomplete' else 'stop', done=outcome != 'eof')
        async with local_provider(text='模型推导尝试 \n', payload=payload) as server:
            worker, consents, dispatch = configured(tutor, tmp_path, server.base_url)
            thread, request, original, consent_request, grant = await asyncio.to_thread(approved, tutor, worker, consents)
            assert await asyncio.to_thread(worker.run_once)
            database, identity, service, _ = tutor
            current = service.read(identity, original.run.id)
            assert current.run.status == ('completed' if outcome == 'complete' else 'failed')
            assert current.result.provider is not None
            assert current.result.provider.outcome == {'complete': 'complete', 'refusal': 'refused', 'incomplete': 'incomplete', 'eof': 'error'}[outcome]
            assert current.run.citations == []
            assert current.result.refusal_markdown == ('保留原输出 \n' if outcome == 'refusal' else '')
            assert current.run.answer_markdown == ('' if outcome == 'refusal' else '模型推导尝试 \n' if outcome == 'complete' else '保留原输出 \n')
            events = service.events(identity, original.run.id, 0)
            assert [event.seq for event in events] == list(range(1, current.run.last_seq + 1))
            assert sum(event.type in {'completed', 'failed', 'cancelled'} for event in events) == 1
            assert ''.join(event.text for event in events if event.type == 'answer_delta') == current.run.answer_markdown
            messages = service.messages(identity, thread.id)
            assert messages.thread.revision == 3 and len(messages.items) == 2
            assert messages.items[-1].channel == ('refusal' if outcome == 'refusal' else 'answer')
            before = all_rows(database)
            assert service.start(identity, request, 'start') == original
            assert consents.grant(identity, consent_request, 'grant') == grant
            assert service.events(identity, original.run.id, current.run.last_seq) == []
            assert all_rows(database) == before
            assert not await asyncio.to_thread(worker.run_once)
            assert len(server.requests) == 1
            with database.transaction(immediate=False) as connection:
                checked = dispatch.read_result(connection, identity, original.run.id, grant.id)
                assert checked.receipt.id == current.result.provider.receipt_id
    asyncio.run(run())


def test_missing_production_proof_leaves_real_preparation_unapproved_and_zero_network(tutor, tmp_path):
    import asyncio
    from tests.provider_protocol_fixture import local_provider
    async def run():
        async with local_provider() as server:
            worker, consents, _ = configured(tutor, tmp_path, server.base_url, proof=False)
            with pytest.raises(ApiError) as unavailable:
                await asyncio.to_thread(approved, tutor, worker, consents)
            assert unavailable.value.code == 'CAPABILITY_UNSUPPORTED'
            database, identity, service, _ = tutor
            with database.connect() as connection:
                identifier = connection.execute("SELECT id FROM jobs WHERE kind='tutor'").fetchone()[0]
            current = service.read(identity, identifier)
            assert current.run.status == 'awaiting_approval' and current.latest_proposal_id is current.consent_id is None
            assert not any(event.type == 'approval_required' for event in service.events(identity, identifier, 0))
            assert server.requests == [] and server.connections == 0
    asyncio.run(run())


def expire_crashed_lease(database, run_id):
    """Controlled crash fixture: advance only the actual expired lease boundary."""
    with database.transaction() as connection:
        assert connection.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00Z' "
            "WHERE id=? AND status='running' AND lease_owner IS NOT NULL", (run_id,)).rowcount == 1


def test_cancel_during_actual_http_stops_once_and_preserves_real_dispatch_facts(tutor, tmp_path, monkeypatch):
    import asyncio
    from tests.provider_protocol_fixture import local_provider
    async def run():
        async with local_provider(hold=True) as server:
            worker, consents, dispatch = configured(tutor, tmp_path, server.base_url)
            _, _, original, _, grant = await asyncio.to_thread(approved, tutor, worker, consents)
            database, identity, service, _ = tutor
            with database.transaction(immediate=False) as connection:
                source = dispatch.source_registry.resolve(connection, identity, original.run.id)
            source_errors = []
            verify = source.verify_dispatch
            def observed_verify(*args):
                try:
                    return verify(*args)
                except ApiError as error:
                    source_errors.append(error.code)
                    raise
            monkeypatch.setattr(source, 'verify_dispatch', observed_verify)
            running = asyncio.create_task(asyncio.to_thread(worker.run_once))
            try:
                await asyncio.wait_for(server.request_seen.wait(), 5)
                current = service.read(identity, original.run.id)
                with database.transaction(immediate=False) as connection:
                    before = TutorRepository(connection, identity.workspace_id).source_state(original.run.id)
                control = service.cancel(identity, original.run.id,
                    TutorRunCancel(expected_revision=current.job_revision), 'cancel-actual-http')
                assert control.status == 'running' and control.cancel_requested
                with database.transaction(immediate=False) as connection:
                    after = TutorRepository(connection, identity.workspace_id).source_state(original.run.id)
                    assert after.lease_owner == before.lease_owner and after.lease_until == before.lease_until
                assert await asyncio.wait_for(running, 5)
            finally:
                server.release.set()
                if not running.done():
                    await asyncio.wait_for(running, 5)
            current = service.read(identity, original.run.id)
            assert current.run.status == 'cancelled'
            assert current.result.provider.provider_outcome == 'unknown'
            assert current.run.answer_markdown == ''
            assert [event.type for event in service.events(identity, original.run.id, 0)].count('cancelled') == 1
            with database.transaction(immediate=False) as connection:
                checked = dispatch.read_result(connection, identity, original.run.id, grant.id)
                assert checked.receipt.id == current.result.provider.receipt_id
                # Either the abort signal or the actual source check can win
                # after the same cancellation. Preserve the original fact.
                if checked.receipt.terminal.error_code != 'PROVIDER_CANCELLED':
                    assert checked.receipt.terminal.error_code == 'OUTBOUND_SOURCE_UNAVAILABLE'
                    assert checked.receipt.terminal.error_code in source_errors
            assert not await asyncio.to_thread(worker.run_once)
            assert len(server.requests) == 1
    asyncio.run(run())


def test_provider_terminal_survives_crash_before_tutor_commit_and_restart_does_not_send(tutor, tmp_path, monkeypatch):
    import asyncio
    from services.api.app.application.tutor_worker import TutorWorker
    from tests.provider_protocol_fixture import local_provider
    class CrashBeforeTutorCommit(Exception):
        pass
    def crash(*args, **kwargs):
        raise CrashBeforeTutorCommit()
    async def run():
        async with local_provider(text='真实已收到并冻结的完整回答。\n') as server:
            worker, consents, dispatch = configured(tutor, tmp_path, server.base_url)
            thread, _, original, _, grant = await asyncio.to_thread(approved, tutor, worker, consents)
            database, identity, service, create = tutor
            monkeypatch.setattr(worker, '_finish', crash)
            with pytest.raises(CrashBeforeTutorCommit):
                await asyncio.to_thread(worker.run_once)
            with database.transaction(immediate=False) as connection:
                durable = dispatch.read_result(connection, identity, original.run.id, grant.id)
                assert durable.receipt.terminal.outcome == 'complete'
                assert durable.answer.text == '真实已收到并冻结的完整回答。\n'
            assert service.read(identity, original.run.id).run.status == 'running'
            restarted = TutorWorker(database, service.context, dispatch, build_material)
            assert not await asyncio.to_thread(restarted.run_once), 'a still-live crashed lease is not stolen'
            expire_crashed_lease(database, original.run.id)
            assert await asyncio.to_thread(restarted.run_once)
            current = service.read(identity, original.run.id)
            assert current.run.status == 'completed' and current.run.answer_markdown == durable.answer.text
            assert current.result.provider.receipt_id == durable.receipt.id
            assert [event.type for event in service.events(identity, original.run.id, 0)].count('completed') == 1
            assert len(server.requests) == 1 and not await asyncio.to_thread(restarted.run_once)
            messages = service.messages(identity, thread.id)
            followup = TutorRunCreate(request=dm.TutorRequest(thread_id=thread.id, workspace_id=identity.workspace_id,
                message='针对原回答继续解释。', intent='explain', context=create.scope),
                expected_thread_revision=messages.thread.revision, binding=create.binding)
            next_run = service.start(identity, followup, 'followup')
            with database.transaction(immediate=False) as connection:
                history = TutorRepository(connection, identity.workspace_id).source_state(next_run.run.id).input.history
                assert [(item.message_id, item.content_markdown) for item in history] == [
                    (message.id, message.content_markdown) for message in messages.items]
            service.cancel(identity, next_run.run.id, TutorRunCancel(expected_revision=1), 'cancel-followup')
            assert len(server.requests) == 1
    asyncio.run(run())


def test_crash_after_dispatch_reservation_recovers_unknown_without_a_first_or_second_send(tutor, tmp_path):
    import asyncio
    from services.api.app.application.tutor_worker import TutorWorker
    from tests.provider_protocol_fixture import local_provider
    async def run():
        async with local_provider() as server:
            worker, consents, dispatch = configured(tutor, tmp_path, server.base_url)
            _, _, original, _, grant = await asyncio.to_thread(approved, tutor, worker, consents)
            database, identity, service, _ = tutor
            lease = worker.claim()
            # Actual source/proof/secret checks and atomic dispatch-start, then
            # controlled process loss before transport. No fake terminal/body.
            dispatch._start(identity, original.run.id, grant.id, lease.dispatch(), asyncio.Event())
            assert not await asyncio.to_thread(worker.run_once)
            expire_crashed_lease(database, original.run.id)
            restarted = TutorWorker(database, service.context, dispatch, build_material)
            assert await asyncio.to_thread(restarted.run_once)
            current = service.read(identity, original.run.id)
            assert current.run.status == 'failed' and current.result.error_code == 'PROVIDER_OUTCOME_UNKNOWN'
            assert current.result.provider.provider_outcome == 'unknown'
            assert current.run.answer_markdown == '' and current.result.usage.input_tokens is None
            assert [event.type for event in service.events(identity, original.run.id, 0)].count('failed') == 1
            assert not await asyncio.to_thread(restarted.run_once)
            assert server.requests == [] and server.connections == 0
    asyncio.run(run())


@pytest.mark.parametrize('fault', ['missing_user_message', 'missing_thread_command'])
def test_worker_must_not_prepare_a_run_whose_original_conversation_is_incomplete(tutor, fault):
    from services.api.app.application.tutor_worker import TutorWorker
    database, identity, service, _ = tutor
    _, _, original = started(tutor)
    with database.transaction() as connection:
        if fault == 'missing_user_message':
            connection.execute('DELETE FROM tutor_messages WHERE message_id IN (SELECT id FROM messages WHERE run_id=?)',
                (original.run.id,))
            connection.execute('DELETE FROM messages WHERE run_id=?', (original.run.id,))
        else:
            connection.execute("DELETE FROM tutor_commands WHERE route='POST /threads'")
    before = all_rows(database)
    worker = TutorWorker(database, service.context, NoTransport(), build_material)
    with pytest.raises(ApiError) as corrupt:
        worker.run_once()
    assert corrupt.value.code == 'TUTOR_INTEGRITY_ERROR'
    assert all_rows(database) == before
