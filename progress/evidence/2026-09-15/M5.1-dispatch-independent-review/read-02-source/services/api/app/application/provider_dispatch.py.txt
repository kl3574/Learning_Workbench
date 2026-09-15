"""Durable single dispatch with worker-thread transactions and bounded waiting.

Only a transaction which has not begun may be retried for SQLite busy. Neither
an entered transaction nor an HTTP request is restarted. Academic delivery has
its own current Policy guard, separate from unconditional stop persistence.
"""
import asyncio
from collections.abc import AsyncGenerator, Callable, Iterator
from contextlib import aclosing, contextmanager
from dataclasses import dataclass, field
import sqlite3
import time
from typing import TypeVar, cast

from packages.contracts.canonical import sha256_bytes
from packages.contracts import domain_models as dm
from ..infrastructure.consent_repository import ConsentRepository
from ..infrastructure.database import Database, utc_now
from ..infrastructure.provider_repository import ProviderRepository
from ..infrastructure.provider_secret_store import SecretStore
from ..infrastructure.provider_sse import ProtocolDecoder
from ..infrastructure.provider_transport import ProviderTransport
from ..infrastructure.security import SessionIdentity, guard_subject_access
from ..provider_dto import FrozenOutboundSummary, ProviderConfigView, ProviderFailureCode
from .errors import ApiError
from .policy import Policy
from .jobs import outbound_lease_active
from .provider_budget import check_usage
from .provider_models import (
    CheckedProviderError, CheckedProviderEvent, CheckedProviderTerminal, DispatchLease,
    PreparedOutboundMaterial, ProviderTerminalReceipt, UsageSnapshot,
)
from .provider_ports import AbortSignal, DispatchRecord, OutboundSourceRegistry, ProviderRequestPreparer

T = TypeVar('T')
FAILURE_CODES = {
    'CAPABILITY_UNSUPPORTED', 'PROVIDER_CONFIGURATION_CHANGED', 'PROVIDER_SECRET_UNAVAILABLE',
    'OUTBOUND_SOURCE_CHANGED', 'OUTBOUND_SOURCE_UNAVAILABLE', 'CONSENT_REQUIRED', 'CONSENT_REVOKED',
    'CONSENT_EXPIRED', 'OUTBOUND_BUDGET_EXCEEDED', 'PROVIDER_TIMEOUT', 'PROVIDER_CANCELLED',
    'PROVIDER_TRANSPORT_ERROR', 'PROVIDER_PROTOCOL_ERROR', 'PROVIDER_OUTCOME_UNKNOWN',
    'PROVIDER_USAGE_INCONSISTENT', 'PROVIDER_REFUSAL', 'PROVIDER_INCOMPLETE',
}


def stopped() -> ApiError:
    return ApiError(409, 'PROVIDER_CANCELLED', '提供商派发已请求停止。')


def timed_out() -> ApiError:
    return ApiError(504, 'PROVIDER_TIMEOUT', '提供商请求超过总时限。')


@dataclass(frozen=True)
class _Started:
    record: DispatchRecord
    summary: FrozenOutboundSummary
    material: PreparedOutboundMaterial = field(repr=False)
    config: ProviderConfigView
    body: bytes = field(repr=False)
    secret: bytes = field(repr=False)
    deadline: float


class _CombinedAbort:
    def __init__(self, original: AbortSignal):
        self.original = original
        self.local = asyncio.Event()

    def is_set(self) -> bool:
        return self.original.is_set() or self.local.is_set()

    async def wait(self) -> object:
        first, second = asyncio.create_task(self.original.wait()), asyncio.create_task(self.local.wait())
        try:
            await asyncio.wait({first, second}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            first.cancel()
            second.cancel()
            await asyncio.gather(first, second, return_exceptions=True)
        return None


class CheckedDispatch:
    def __init__(self, database: Database, secret_store: SecretStore,
                 source_registry: OutboundSourceRegistry, preparer: ProviderRequestPreparer,
                 transport: ProviderTransport | None = None):
        self.database, self.secret_store = database, secret_store
        self.source_registry, self.preparer = source_registry, preparer
        self.transport = transport if transport is not None else ProviderTransport()

    @contextmanager
    def _transaction(self, *, readonly: bool = False) -> Iterator[sqlite3.Connection]:
        entered = False
        try:
            with self.database.transaction(busy_timeout_ms=50, immediate=not readonly) as conn:
                entered = True
                yield conn
        except sqlite3.OperationalError:
            if entered:
                # Includes commit uncertainty: never retry an entered operation.
                raise ApiError(503, 'PROVIDER_OUTCOME_UNKNOWN', '本机记录暂不可确认，请回读原派发状态。') from None
            raise

    async def _db(self, operation: Callable[[], T], *, abort: AbortSignal | None = None,
                  deadline: float | None = None) -> T:
        until = deadline if deadline is not None else time.monotonic() + 1
        while True:
            if abort is not None and abort.is_set():
                raise stopped()
            if time.monotonic() >= until:
                raise timed_out()
            try:
                # Entire transaction and all owned-port checks stay on one thread.
                return await asyncio.to_thread(operation)
            except sqlite3.OperationalError as error:
                if getattr(error, 'sqlite_errorcode', None) not in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
                    raise ApiError(503, 'PROVIDER_OUTCOME_UNKNOWN', '本机派发记录暂不可用。') from None
                await asyncio.sleep(0.005)

    def _output_allowed(self, identity: SessionIdentity) -> None:
        with self._transaction(readonly=True) as conn:
            Policy(conn, identity.workspace_id).check('private_artifact')

    def terminal(self, identity: SessionIdentity, dispatch_id: str) -> ProviderTerminalReceipt | None:
        with self._transaction(readonly=True) as conn:
            Policy(conn, identity.workspace_id).check('private_artifact')
            return ConsentRepository(conn, identity.workspace_id).read_terminal(dispatch_id)

    def _start(self, identity: SessionIdentity, job_id: str, consent_id: str,
               lease: DispatchLease, abort: AbortSignal) -> _Started | ProviderTerminalReceipt:
        with self._transaction() as conn:
            if abort.is_set():
                raise stopped()
            guard_subject_access(conn, identity.workspace_id)
            repo = ConsentRepository(conn, identity.workspace_id)
            summary, material, body = repo.dispatch_material(consent_id)
            if summary.job_id != job_id:
                raise ApiError(409, 'OUTBOUND_SOURCE_CHANGED', '许可不属于此任务。')
            previous = repo.dispatch_for_consent(consent_id)
            if previous is not None:
                Policy(conn, identity.workspace_id).check('private_artifact')
                if previous.terminal is None:
                    raise ApiError(409, 'PROVIDER_OUTCOME_UNKNOWN', '原调用结果尚未确认，不能重新派发。')
                return previous.terminal
            source = self.source_registry.resolve(conn, identity, job_id)
            source.verify_dispatch(conn, identity, material, lease, consent_id)
            providers = ProviderRepository(conn, identity.workspace_id)
            config = providers.config(summary.provider_id)
            self.preparer.verify(config, material, summary, body)
            locator = providers.secret_locator(config.id, config.revision)
            if locator is None:
                raise ApiError(409, 'PROVIDER_SECRET_UNAVAILABLE', '提供商秘密不可用。')
            secret = self.secret_store.read(locator).encode()
            if abort.is_set():
                raise stopped()
            deadline = time.monotonic() + summary.budget.timeout_seconds
            record, created = repo.begin_dispatch(consent_id, job_id, sha256_bytes(body), utc_now())
            if not created:
                raise ApiError(409, 'PROVIDER_OUTCOME_UNKNOWN', '许可已经消耗，不能重新派发。')
            return _Started(record, summary, material, config, body, secret, deadline)

    def _guard(self, identity: SessionIdentity, start: _Started, lease: DispatchLease, abort: AbortSignal) -> None:
        if abort.is_set():
            raise stopped()
        if time.monotonic() >= start.deadline:
            raise timed_out()
        with self._transaction(readonly=True) as conn:
            guard_subject_access(conn, identity.workspace_id)
            repo = ConsentRepository(conn, identity.workspace_id)
            if repo.check_dispatch(start.record.id, utc_now()).terminal is not None:
                raise ApiError(409, 'PROVIDER_OUTCOME_UNKNOWN', '此派发已有持久终态。')
            source = self.source_registry.resolve(conn, identity, start.record.job_id)
            source.verify_dispatch(conn, identity, start.material, lease, start.record.consent_id)
            providers = ProviderRepository(conn, identity.workspace_id)
            config = providers.config(start.summary.provider_id)
            self.preparer.verify(config, start.material, start.summary, start.body)
            locator = providers.secret_locator(config.id, config.revision)
            if locator is None or self.secret_store.read(locator).encode() != start.secret:
                raise ApiError(409, 'PROVIDER_SECRET_UNAVAILABLE', '冻结的提供商秘密不可用。')
        if abort.is_set():
            raise stopped()
        if time.monotonic() >= start.deadline:
            raise timed_out()

    def _finish(self, identity: SessionIdentity, start: _Started, terminal: CheckedProviderTerminal,
                answer: bytes, refusal: bytes) -> ProviderTerminalReceipt:
        with self._transaction() as conn:
            return ConsentRepository(conn, identity.workspace_id).finish_dispatch(
                start.record.id, terminal, answer, refusal, utc_now())

    def _usage(self, identity: SessionIdentity, start: _Started, usage: UsageSnapshot) -> None:
        with self._transaction() as conn:
            ConsentRepository(conn, identity.workspace_id).record_usage(start.record.id, usage)

    async def dispatch(self, identity: SessionIdentity, job_id: str, consent_id: str,
                       lease: DispatchLease, abort: AbortSignal) -> AsyncGenerator[CheckedProviderEvent, None]:
        # Independent producer keeps the total deadline running while a consumer
        # pauses between deltas. SSE bytes and output are bounded by the decoder.
        combined = _CombinedAbort(abort)
        queue: asyncio.Queue[CheckedProviderEvent | BaseException | None] = asyncio.Queue()
        async def produce() -> None:
            try:
                async with aclosing(self._run(identity, job_id, consent_id, lease, combined)) as stream:
                    async for event in stream:
                        queue.put_nowait(event)
            except BaseException as error:
                queue.put_nowait(error)
            finally:
                queue.put_nowait(None)
        task = asyncio.create_task(produce())
        try:
            while (item := await queue.get()) is not None:
                if isinstance(item, BaseException):
                    raise item
                await self._db(lambda: self._output_allowed(identity))
                yield item
        finally:
            combined.local.set()
            # No task cancellation while a transaction may still commit. Its
            # short busy wait and repeated abort guard let it finish safely.
            await asyncio.shield(task)

    async def _run(self, identity: SessionIdentity, job_id: str, consent_id: str,
                   lease: DispatchLease, abort: AbortSignal) -> AsyncGenerator[CheckedProviderEvent, None]:
        result = await self._db(lambda: self._start(identity, job_id, consent_id, lease, abort),
                                abort=abort, deadline=time.monotonic() + 180)
        if isinstance(result, ProviderTerminalReceipt):
            yield result.terminal
            return
        start = result
        decoder = ProtocolDecoder(start.config.adapter, start.config.model)
        answer, refusal = bytearray(), bytearray()
        usage = UsageSnapshot(input_tokens=None, output_tokens=None)
        saved = False
        pending: asyncio.Task[CheckedProviderEvent] | None = None
        abort_wait = asyncio.create_task(abort.wait())
        terminal: CheckedProviderTerminal | None = None
        async def guard() -> None:
            await self._db(lambda: self._guard(identity, start, lease, abort), abort=abort, deadline=start.deadline)
        try:
            await guard()
            async with aclosing(self.transport.stream(start.config, start.body, start.secret, guard=guard)) as chunks:
                stream = decoder.stream(chunks)
                async def next_event() -> CheckedProviderEvent:
                    return await anext(stream)
                try:
                    while terminal is None:
                        await guard()
                        remaining = start.deadline - time.monotonic()
                        if remaining <= 0:
                            raise timed_out()
                        if pending is None:
                            pending = asyncio.create_task(next_event())
                        done, _ = await asyncio.wait({pending, abort_wait}, timeout=min(0.1, remaining),
                                                     return_when=asyncio.FIRST_COMPLETED)
                        if abort_wait in done or abort.is_set():
                            raise stopped()
                        if pending not in done:
                            continue
                        event = pending.result()
                        pending = None
                        # Received, checked facts belong to the private ledger
                        # even if a concurrent stop now forbids their delivery.
                        if event.type == 'delta':
                            (answer if event.channel == 'answer' else refusal).extend(event.text.encode())
                        elif event.type == 'usage':
                            usage = UsageSnapshot(input_tokens=event.input_tokens, output_tokens=event.output_tokens)
                        else:
                            usage = event.usage
                        await guard()
                        if event.type == 'delta':
                            yield event
                        elif event.type == 'usage':
                            await self._db(lambda: self._usage(identity, start, usage), abort=abort, deadline=start.deadline)
                            check_usage(usage, start.summary.input_token_assurance, start.summary.budget)
                            yield event
                        else:
                            usage = event.usage
                            check_usage(usage, start.summary.input_token_assurance, start.summary.budget)
                            terminal = event
                    receipt = await self._db(lambda: self._finish(identity, start, cast(CheckedProviderTerminal, terminal), bytes(answer), bytes(refusal)))
                    saved = True
                finally:
                    if pending is not None:
                        pending.cancel()
                        await asyncio.gather(pending, return_exceptions=True)
                        pending = None
                    await stream.aclose()
            yield receipt.terminal
        except ApiError as exc:
            # Joined parser state can include other validated fields in the
            # same received frame; no such fact is discarded on a local stop.
            answer, refusal = bytearray(decoder.state.answer.encode()), bytearray(decoder.state.refusal.encode())
            usage = decoder.state.usage
            code = cast(ProviderFailureCode, exc.code if exc.code in FAILURE_CODES else 'OUTBOUND_SOURCE_UNAVAILABLE')
            terminal = CheckedProviderError(type='error', error_code=code,
                provider_outcome=decoder.state.provider_outcome,
                output_state='partial' if answer or refusal else 'none', usage=usage)
            receipt = await self._db(lambda: self._finish(identity, start, cast(CheckedProviderTerminal, terminal), bytes(answer), bytes(refusal)))
            saved = True
            yield receipt.terminal
        finally:
            if pending is not None:
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            abort_wait.cancel()
            await asyncio.gather(abort_wait, return_exceptions=True)
            if not saved:
                answer, refusal = bytearray(decoder.state.answer.encode()), bytearray(decoder.state.refusal.encode())
                usage = decoder.state.usage
                terminal = CheckedProviderError(type='error', error_code='PROVIDER_OUTCOME_UNKNOWN',
                    provider_outcome=decoder.state.provider_outcome,
                    output_state='partial' if answer or refusal else 'none', usage=usage)
                await self._db(lambda: self._finish(identity, start, cast(CheckedProviderTerminal, terminal), bytes(answer), bytes(refusal)))

    async def core_events(self, identity: SessionIdentity, job_id: str, consent_id: str,
                          lease: DispatchLease, abort: AbortSignal) -> AsyncGenerator[dm.ProviderEvent, None]:
        """Coarse core projection; consumers still own their result transaction."""
        async with aclosing(self.dispatch(identity, job_id, consent_id, lease, abort)) as events:
            async for event in events:
                if event.type == 'delta':
                    if event.channel == 'answer':
                        yield dm.ProviderEvent(type='delta', text=event.text)
                elif event.type == 'usage':
                    yield dm.ProviderEvent(type='usage', input_tokens=event.input_tokens,
                                           output_tokens=event.output_tokens)
                else:
                    def verified() -> None:
                        with self._transaction(readonly=True) as conn:
                            Policy(conn, identity.workspace_id).check('private_artifact')
                            record = ConsentRepository(conn, identity.workspace_id).dispatch_for_consent(consent_id)
                            if (record is None or record.job_id != job_id or record.terminal is None
                                    or record.terminal.terminal != event):
                                raise ApiError(409, 'PROVIDER_OUTCOME_UNKNOWN', '原派发终态尚不可核验。')
                    await self._db(verified)
                    if event.type == 'finished' and event.outcome == 'complete':
                        yield dm.ProviderEvent(type='finished')
                    else:
                        code = (event.error_code if event.type == 'error' else
                                'PROVIDER_REFUSAL' if event.outcome == 'refused' else 'PROVIDER_INCOMPLETE')
                        yield dm.ProviderEvent(type='error', error_code=code)

    def recover_unfinished(self, workspace_id: str) -> list[ProviderTerminalReceipt]:
        """Explicit recovery; no network, credential read, or regenerated call.

        Active real Jobs leases are skipped, even after cancel/status changes.
        An expired lease can be recovered; no claim of immediate recovery is made
        for crashed workers whose lease has not yet expired.
        """
        with self._transaction() as conn:
            repo = ConsentRepository(conn, workspace_id)
            receipts = []
            for record in repo.unfinished_dispatches():
                if outbound_lease_active(conn, workspace_id, record.job_id, utc_now()):
                    continue
                terminal = CheckedProviderError(type='error', error_code='PROVIDER_OUTCOME_UNKNOWN',
                    provider_outcome='unknown', output_state='none', usage=repo.usage(record.id))
                receipts.append(repo.finish_dispatch(record.id, terminal, b'', b'', utc_now()))
            return receipts
