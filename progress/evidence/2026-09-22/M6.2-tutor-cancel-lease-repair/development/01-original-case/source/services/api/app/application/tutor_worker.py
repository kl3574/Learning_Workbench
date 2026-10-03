"""One local Tutor owner loop; remote waiting never holds a SQLite transaction."""

import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import aclosing
import sqlite3
import threading
from typing import Literal, Protocol

from ..infrastructure.database import Database
from ..infrastructure.security import SessionIdentity, expires_after
from ..infrastructure.tutor_job_repository import TERMINAL, TutorLease
from ..infrastructure.tutor_repository import TutorRepository
from ..tutor_dto import TutorContextSummary, TutorFailureCode, TutorProviderResult, TutorResultSummary
from .errors import ApiError
from .provider_models import (
    CheckedProviderEvent, CheckedProviderFinished, CheckedProviderResult,
    DispatchLease, PreparedOutboundMaterial, ProviderTerminalReceipt,
)
from .provider_ports import AbortSignal
from .tutor import TutorContextPort
from .tutor_models import PreparedTutorContext, TutorJobInput


class TutorProviderPort(Protocol):
    def dispatch(self, identity: SessionIdentity, job_id: str, consent_id: str,
                 lease: DispatchLease, abort: AbortSignal) -> AsyncGenerator[CheckedProviderEvent, None]: ...

    def read_result(self, connection: sqlite3.Connection, identity: SessionIdentity,
                    job_id: str, consent_id: str) -> CheckedProviderResult | None: ...

    def read_control_result(self, connection: sqlite3.Connection, identity: SessionIdentity,
                            job_id: str, consent_id: str) -> ProviderTerminalReceipt | None: ...

    def recover_unfinished(self, workspace_id: str) -> list[ProviderTerminalReceipt]: ...


def summarize(context: PreparedTutorContext) -> TutorContextSummary:
    return TutorContextSummary(snapshot=context.snapshot, included=context.included,
        history_message_ids=context.history_message_ids, omissions=context.omissions, warnings=context.warnings)


class TutorWorker:
    def __init__(self, database: Database, context: TutorContextPort, provider: TutorProviderPort,
                 build_outbound: Callable[[TutorJobInput, PreparedTutorContext, int], PreparedOutboundMaterial],
                 *, stopping: Callable[[], bool] | None = None):
        self.database, self.context, self.provider, self.build_outbound = database, context, provider, build_outbound
        self._stop = threading.Event()
        self.stopping = stopping or self._stop.is_set
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.lease_seconds = 30
        self.last_error_code: str | None = None
        self._candidate_cursor: tuple[str, str] | None = None

    def start(self) -> None:
        if self.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name='learning-tutor-worker', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set() and not self.stopping():
            try:
                worked = self.run_once()
                self.last_error_code = None
            except (ApiError, sqlite3.Error) as error:
                self.last_error_code = error.code if isinstance(error, ApiError) else 'TUTOR_INTEGRITY_ERROR'
                worked = False
            if not worked:
                self._stop.wait(0.25)

    @staticmethod
    def _identity(workspace: str) -> SessionIdentity:
        # Trusted worker identity derived from its actual Jobs-owned lease. This
        # is not a browser-controlled role or a production Provider proof.
        return SessionIdentity('tutor_worker', workspace, 'learner', '', expires_after(86400))

    def claim(self) -> TutorLease | None:
        if self._stop.is_set() or self.stopping():
            return None
        workspace = self.database.workspace_id()
        with self.database.transaction() as connection:
            repo = TutorRepository(connection, workspace)
            first_error: ApiError | None = None
            for position in repo.jobs.candidates(self._candidate_cursor):
                # Advance even after a rejected original record; otherwise one
                # damaged oldest job can prevent every other thread progressing.
                self._candidate_cursor = position
                identifier = position[1]
                try:
                    repo.source_state(identifier)
                except ApiError as error:
                    if error.code not in {'TUTOR_INTEGRITY_ERROR', 'THREAD_MISSING', 'JOB_MISSING'}:
                        raise
                    first_error = first_error or error
                    continue
                lease = repo.jobs.claim(repo.jobs.load(identifier), self.lease_seconds)
                repo.sync_job(identifier)
                return lease
            if first_error is not None:
                # Preserve the original explicit failure if nothing can advance.
                # This does not create a fake terminal or permanent quarantine.
                raise first_error
            return None

    def _prepare(self, identity: SessionIdentity, lease: TutorLease) -> bool:
        with self.database.transaction() as connection:
            repo = TutorRepository(connection, identity.workspace_id)
            source = repo.source_state(lease.job_id)
            if not repo.jobs.owned(repo.jobs.load(lease.job_id), lease):
                return False
            self.context.check_access(connection, identity)
            if source.context_id is not None:
                return source.consent_id is not None
            context = self.context.prepare(connection, identity, source.input)
            self.context.verify(connection, identity, context)
            material = self.build_outbound(source.input, context, source.job_revision)
            repo.prepared(lease, summarize(context), material.prepared_input_sha256)
            return False

    def _watch(self, identity: SessionIdentity, lease: TutorLease) -> bool:
        if self._stop.is_set() or self.stopping():
            return False
        with self.database.transaction() as connection:
            repo = TutorRepository(connection, identity.workspace_id)
            source = repo.source_state(lease.job_id)
            if source.cancel_requested or not repo.jobs.owned(repo.jobs.load(lease.job_id), lease):
                return False
            self.context.check_access(connection, identity)
            return repo.jobs.renew(lease, self.lease_seconds)

    def _consume(self, identity: SessionIdentity, lease: TutorLease, event: CheckedProviderEvent) -> None:
        with self.database.transaction() as connection:
            self.context.check_access(connection, identity)
            repo = TutorRepository(connection, identity.workspace_id)
            source = repo.source_state(lease.job_id)
            self.context.check_scope(connection, identity, source.input.request.request.context, source.input.request.binding)
            if event.type == 'delta' and event.channel == 'answer':
                repo.delta(lease, event.text)
                if source.input.request.binding.practice is not None:
                    from .practice_model_help import record_model_help
                    record_model_help(connection, identity, lease.job_id)
            elif event.type == 'usage':
                from .provider_models import UsageSnapshot
                repo.usage(lease, UsageSnapshot(input_tokens=event.input_tokens, output_tokens=event.output_tokens))
            # Refusal text and terminal facts are adopted from the Provider-owned
            # checked original artifacts, not guessed from a projection.

    def _finish(self, identity: SessionIdentity, lease: TutorLease, fallback: TutorFailureCode | None = None) -> None:
        with self.database.transaction() as connection:
            repo = TutorRepository(connection, identity.workspace_id)
            source = repo.source_state(lease.job_id)
            if source.status in TERMINAL or not repo.jobs.owned(repo.jobs.load(lease.job_id), lease, allow_cancel=True):
                return
            view = repo.view(lease.job_id)
            checked = None
            receipt = None
            access_error = None
            if source.consent_id:
                try:
                    checked = self.provider.read_result(connection, identity, lease.job_id, source.consent_id)
                    receipt = checked.receipt if checked is not None else None
                except ApiError as error:
                    if error.code not in {'POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'}:
                        raise
                    access_error = 'ASSESSMENT_ACTIVE' if error.code == 'ASSESSMENT_ACTIVE' else 'POLICY_DENIED'
                    receipt = self.provider.read_control_result(connection, identity, lease.job_id, source.consent_id)
            answer, result = view.run.answer_markdown, view.result
            code: TutorFailureCode | None = fallback or 'TUTOR_OUTCOME_UNKNOWN'
            status: Literal['completed', 'failed', 'cancelled'] = 'failed'
            outcome: Literal['complete', 'refused', 'incomplete', 'error']
            provider_outcome: Literal['completed', 'failed', 'incomplete', 'cancelled', 'unknown']
            if receipt is not None:
                terminal = receipt.terminal
                refusal = result.refusal_markdown
                if checked is not None:
                    answer = checked.answer.text if checked.answer is not None else ''
                    refusal = checked.refusal.text if checked.refusal is not None else ''
                if isinstance(terminal, CheckedProviderFinished):
                    outcome = terminal.outcome
                    provider_outcome = 'incomplete' if outcome == 'incomplete' else 'completed'
                    if outcome == 'complete':
                        code = None if answer.strip() and '\x00' not in answer else 'TUTOR_OUTPUT_EMPTY' if not answer.strip() else 'TUTOR_OUTPUT_INVALID'
                        status = 'completed' if code is None else 'failed'
                    else:
                        code = 'PROVIDER_REFUSAL' if outcome == 'refused' else 'PROVIDER_INCOMPLETE'
                else:
                    outcome, provider_outcome, code = 'error', terminal.provider_outcome, terminal.error_code
                result = TutorResultSummary(refusal_markdown=refusal, usage=terminal.usage,
                    provider=TutorProviderResult(receipt_id=receipt.id, receipt_sha256=receipt.receipt_sha256,
                        outcome=outcome, provider_outcome=provider_outcome, output_state=terminal.output_state), error_code=code)
            else:
                result = result.model_copy(update={'error_code': code})
            if access_error is not None:
                status = 'failed'
                result = result.model_copy(update={'error_code': access_error})
            if source.cancel_requested:
                status = 'cancelled'
            repo.finish(lease.job_id, status, result, answer, lease=lease)
            if access_error is None and source.input.request.binding.practice is not None:
                from .practice_model_help import record_model_help
                record_model_help(connection, identity, lease.job_id)

    def _has_result(self, identity: SessionIdentity, lease: TutorLease, consent_id: str) -> bool:
        with self.database.transaction(immediate=False) as connection:
            return self.provider.read_result(connection, identity, lease.job_id, consent_id) is not None

    async def process(self, lease: TutorLease) -> None:
        identity = self._identity(lease.workspace_id)
        try:
            if not await asyncio.to_thread(self._prepare, identity, lease):
                # A concurrent cancel during preparation still needs a terminal;
                # a successful preparation released its lease awaiting approval.
                with self.database.transaction(immediate=False) as connection:
                    source = TutorRepository(connection, identity.workspace_id).source_state(lease.job_id)
                if source.cancel_requested:
                    await asyncio.to_thread(self._finish, identity, lease, 'PROVIDER_CANCELLED')
                return
            with self.database.transaction(immediate=False) as connection:
                source = TutorRepository(connection, identity.workspace_id).source_state(lease.job_id)
            consent = source.consent_id
            if consent is None:
                raise ApiError(409, 'TUTOR_CONTEXT_INVALID', '任务尚未绑定真实授权。')
            if await asyncio.to_thread(self._has_result, identity, lease, consent):
                await asyncio.to_thread(self._finish, identity, lease)
                return
            abort = asyncio.Event()

            async def watch() -> None:
                while not abort.is_set():
                    try:
                        if not await asyncio.to_thread(self._watch, identity, lease):
                            abort.set()
                            return
                    except (ApiError, sqlite3.Error):
                        abort.set()
                        return
                    try:
                        await asyncio.wait_for(abort.wait(), timeout=0.25)
                    except TimeoutError:
                        pass

            watcher = asyncio.create_task(watch())
            try:
                async with aclosing(self.provider.dispatch(identity, lease.job_id, consent, lease.dispatch(), abort)) as stream:
                    async for event in stream:
                        await asyncio.to_thread(self._consume, identity, lease, event)
            finally:
                abort.set()
                await watcher
            await asyncio.to_thread(self._finish, identity, lease)
        except ApiError as error:
            from pydantic import TypeAdapter, ValidationError
            try:
                code: TutorFailureCode = TypeAdapter(TutorFailureCode).validate_python(error.code)
            except ValidationError:
                code = 'TUTOR_CONTEXT_UNAVAILABLE'
            await asyncio.to_thread(self._finish, identity, lease, code)

    def run_once(self) -> bool:
        if not self._lock.acquire(blocking=False):
            return False
        try:
            if self._stop.is_set() or self.stopping():
                return False
            # Recover before claiming: a new lease must not make an old unknown
            # dispatch appear to have a live producer. This operation never sends.
            self.provider.recover_unfinished(self.database.workspace_id())
            lease = self.claim()
            if lease is None:
                return False
            asyncio.run(self.process(lease))
            return True
        finally:
            self._lock.release()
