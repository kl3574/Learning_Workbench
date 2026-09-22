"""One real Authoring producer; checked Provider waiting holds no SQLite lock."""
import asyncio
from contextlib import aclosing
import sqlite3
import threading
from uuid import uuid4

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from ..authoring_dto import AuthoringCandidate, candidate_sha256, parse_worked_example, validate_declared_sources
from ..infrastructure.authoring_job_repository import AuthoringLease, TERMINAL, integrity
from ..infrastructure.authoring_repository import AuthoringRepository, not_run
from ..infrastructure.database import Database, utc_now
from ..infrastructure.draft_candidate_repository import DraftCandidateRepository
from ..infrastructure.security import SessionIdentity, author_execution_identity, expires_after
from .authoring_context import AuthoringContext
from .authoring_models import AuthoringCandidateRecord
from .authoring_source import AuthoringOutboundSource
from .draft_candidate_models import ResolvedDraftCandidate
from .errors import ApiError
from .provider_models import CheckedProviderFinished
from .tutor_worker import TutorProviderPort


class AuthoringWorker:
    def __init__(self, database: Database, context: AuthoringContext, provider: TutorProviderPort):
        self.database, self.context, self.provider = database, context, provider
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._cursor: tuple[str, str] | None = None
        self.last_error_code: str | None = None

    def start(self) -> None:
        if self.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name='learning-authoring-worker', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                worked = self.run_once()
                self.last_error_code = None
            except (ApiError, sqlite3.Error) as error:
                self.last_error_code = error.code if isinstance(error, ApiError) else 'AUTHORING_INTEGRITY_ERROR'
                worked = False
            if not worked:
                self._stop.wait(0.25)

    def claim(self) -> AuthoringLease | None:
        workspace = self.database.workspace_id()
        with self.database.transaction() as conn:
            query = "SELECT created_at,id FROM jobs WHERE workspace_id=? AND kind='authoring' AND json_extract(input_json,'$.version')='authoring-job-v1' AND (status='queued' OR (status='running' AND lease_until<=?))"
            rows = conn.execute(query + ' ORDER BY created_at,id', (workspace, utc_now())).fetchall()
            if self._cursor is not None:
                rows = [row for row in rows if tuple(row) > self._cursor] + [row for row in rows if tuple(row) <= self._cursor]
            repo = AuthoringRepository(conn, workspace)
            first_error = None
            for row in rows[:32]:
                self._cursor = tuple(row)
                try:
                    record = repo.load(row['id'])
                except ApiError as error:
                    first_error = first_error or error
                    continue
                lease = repo.jobs.claim(row['id'])
                repo.sync(record)
                return lease
            if first_error is not None:
                raise first_error
            return None

    def _identity(self, conn: sqlite3.Connection, lease: AuthoringLease) -> SessionIdentity:
        record = AuthoringRepository(conn, lease.workspace_id).load(lease.job_id)
        if record.execution_actor_id is None:
            raise integrity()
        identity = author_execution_identity(conn, lease.workspace_id, record.execution_actor_id)
        self.context.check_access(conn, identity)
        return identity

    def _watch(self, lease: AuthoringLease) -> bool:
        if self._stop.is_set():
            return False
        with self.database.transaction() as conn:
            identity = self._identity(conn, lease)
            repo = AuthoringRepository(conn, identity.workspace_id)
            record = repo.load(lease.job_id)
            prepared = self.context.read(conn, identity, record.view.preparation.context_snapshot_id)
            self.context.verify(conn, identity, prepared)
            return repo.jobs.renew(lease)

    def _finish(self, lease: AuthoringLease, fallback: str = 'AUTHORING_OUTCOME_UNKNOWN') -> None:
        with self.database.transaction() as conn:
            repo = AuthoringRepository(conn, lease.workspace_id)
            record, row = repo.load(lease.job_id), repo.jobs.load(lease.job_id)
            if row['status'] in TERMINAL or not repo.jobs.owned(row, lease, allow_cancel=True):
                return
            result, receipt, access_error = None, None, None
            try:
                identity = self._identity(conn, lease)
                if AuthoringOutboundSource(self.context).resume_before_dispatch(conn, identity, lease):
                    return
                if record.view.consent_id is not None:
                    result = self.provider.read_result(conn, identity, lease.job_id, record.view.consent_id)
                    receipt = result.receipt if result is not None else None
            except ApiError as error:
                if error.code not in {'POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'}:
                    raise
                access_error = error.code
                if record.view.consent_id is not None:
                    # Pure control identity has no academic permission. Only the
                    # Provider-owned terminal control receipt is accessible here.
                    control = SessionIdentity('authoring_worker_control', lease.workspace_id, 'learner', '', expires_after(30))
                    receipt = self.provider.read_control_result(conn, control, lease.job_id, record.view.consent_id)
            view = record.view
            view.validation = not_run()
            view.error_code = fallback
            status = 'failed'
            payload = None
            if receipt is not None:
                view.provider_receipt_id = receipt.id
                terminal = receipt.terminal
                view.usage = terminal.usage
                if result is not None:
                    view.raw_answer = result.answer.text if result.answer is not None else None
                    view.raw_refusal = result.refusal.text if result.refusal is not None else None
                if isinstance(terminal, CheckedProviderFinished):
                    view.provider_outcome = 'incomplete' if terminal.outcome == 'incomplete' else 'completed'
                    if terminal.outcome == 'complete' and result is not None and not row['cancel_requested']:
                        try:
                            payload = parse_worked_example(view.raw_answer or '')
                        except (ValueError, TypeError):
                            view.validation.schema_check = 'FAIL'
                            view.error_code = 'AUTHORING_OUTPUT_INVALID'
                        else:
                            view.validation.schema_check = view.validation.symbol_declarations = 'PASS'
                            try:
                                validate_declared_sources(payload, view.preparation.materials)
                            except ValueError:
                                view.validation.references = 'FAIL'
                                view.error_code = 'AUTHORING_REFERENCES_INVALID'
                                payload = None
                            else:
                                view.validation.references = 'PASS'
                                view.error_code = None
                                status = 'completed'
                    elif terminal.outcome != 'complete':
                        view.error_code = 'PROVIDER_REFUSAL' if terminal.outcome == 'refused' else 'PROVIDER_INCOMPLETE'
                else:
                    view.provider_outcome = terminal.provider_outcome
                    view.error_code = terminal.error_code
            if access_error is not None:
                view.error_code, status, payload = access_error, 'failed', None
            if row['cancel_requested']:
                status, payload = 'cancelled', None
                # Preserve why only the control receipt was acquired. A later
                # authorized read may project the original checked output while
                # keeping cancellation and the absent candidate unchanged.
                view.error_code = access_error or 'PROVIDER_CANCELLED'
            if payload is not None and receipt is not None:
                candidate = AuthoringCandidate(draft_id='authoring_draft_' + uuid4().hex,
                    draft_revision=1, entity='block', candidate_sha256=candidate_sha256(payload))
                saved = AuthoringCandidateRecord(version='authoring-candidate-v1', workspace_id=lease.workspace_id,
                    candidate=candidate, source_job_id=lease.job_id, provider_receipt_id=receipt.id,
                    payload=payload, body_sha256=sha256_bytes(payload.body_markdown.encode()),
                    validation=view.validation, created_at=utc_now())
                raw = canonical_bytes(saved).decode()
                conn.execute('INSERT INTO authoring_candidates VALUES(?,?,?,?,?)',
                    (candidate.draft_id, lease.workspace_id, lease.job_id, raw, sha256_bytes(raw.encode())))
                view.summary.candidate = candidate
                DraftCandidateRepository(conn).register(ResolvedDraftCandidate(
                    lease.workspace_id, 'authoring', 'authoring_single', candidate))
            terminal_result = {'result_sha256': sha256_bytes(canonical_bytes(view.model_dump(mode='json', exclude={'summary'}))),
                               'candidate': view.summary.candidate.model_dump() if view.summary.candidate else None}
            repo.jobs.transition(row, status, result=terminal_result)
            repo.sync(record)

    async def process(self, lease: AuthoringLease) -> None:
        try:
            with self.database.transaction() as conn:
                identity = self._identity(conn, lease)
                if AuthoringOutboundSource(self.context).resume_before_dispatch(conn, identity, lease):
                    return
                record = AuthoringRepository(conn, lease.workspace_id).load(lease.job_id)
                consent = record.view.consent_id
                if consent is None:
                    raise integrity()
                existing = self.provider.read_result(conn, identity, lease.job_id, consent)
            if existing is not None:
                await asyncio.to_thread(self._finish, lease)
                return
            abort = asyncio.Event()

            async def watch() -> None:
                while not abort.is_set():
                    try:
                        if not await asyncio.to_thread(self._watch, lease):
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
                    async for _ in stream:
                        # Only the original checked terminal artifacts are adopted;
                        # streamed fragments never become an independently valid draft.
                        pass
            finally:
                abort.set()
                await watcher
            await asyncio.to_thread(self._finish, lease)
        except ApiError as error:
            code = error.code if error.code in {'POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED',
                'CAPABILITY_UNSUPPORTED', 'PROVIDER_CANCELLED'} else 'AUTHORING_CONTEXT_UNAVAILABLE'
            await asyncio.to_thread(self._finish, lease, code)

    def run_once(self) -> bool:
        if self._stop.is_set() or not self._lock.acquire(blocking=False):
            return False
        try:
            self.provider.recover_unfinished(self.database.workspace_id())
            lease = self.claim()
            if lease is None:
                return False
            asyncio.run(self.process(lease))
            return True
        finally:
            self._lock.release()
