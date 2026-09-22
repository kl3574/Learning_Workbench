"""Group producer: freeze a valid plan, then atomically persist its checked complete candidate."""
import asyncio
from contextlib import aclosing
import sqlite3
import threading
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..authoring_group_dto import AuthoringGroupCandidate, AuthoringContentPlanRef, AuthoringGroupGenerated
from ..infrastructure.authoring_job_repository import AuthoringLease, TERMINAL, integrity
from ..infrastructure.authoring_group_repository import AuthoringGroupRepository, group_not_run
from ..infrastructure.database import Database, utc_now
from ..infrastructure.draft_candidate_repository import DraftCandidateRepository
from ..infrastructure.security import SessionIdentity, author_execution_identity, expires_after
from .authoring_group_context import AuthoringGroupContext
from .authoring_group_models import AuthoringGroupCandidateRecord, AuthoringContentPlanRecord
from .authoring_group_validation import (parse_group_plan, parse_group_generated, build_group_candidate_payload,
    plan_sha256, group_candidate_sha256)
from .authoring_group_source import AuthoringGroupOutboundSource
from .errors import ApiError
from .draft_candidate_models import ResolvedDraftCandidate
from .provider_models import CheckedProviderFinished
from .tutor_worker import TutorProviderPort


class AuthoringGroupWorker:
    def __init__(self, database: Database, context: AuthoringGroupContext, provider: TutorProviderPort):
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
        self._thread = threading.Thread(target=self._loop, name='learning-authoring-group-worker', daemon=True)
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
            query = "SELECT created_at,id FROM jobs WHERE workspace_id=? AND kind='authoring' AND json_extract(input_json,'$.version')='authoring-group-job-v1' AND (status='queued' OR (status='running' AND lease_until<=?))"
            rows = conn.execute(query + ' ORDER BY created_at,id', (workspace, utc_now())).fetchall()
            if self._cursor is not None:
                rows = [row for row in rows if tuple(row) > self._cursor] + [row for row in rows if tuple(row) <= self._cursor]
            repo = AuthoringGroupRepository(conn, workspace)
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
        record = AuthoringGroupRepository(conn, lease.workspace_id).load(lease.job_id)
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
            repo = AuthoringGroupRepository(conn, identity.workspace_id)
            record = repo.load(lease.job_id)
            prepared = self.context.read_group(conn, identity, record.view.preparation.context_snapshot_id)
            self.context.verify_group(conn, identity, prepared)
            return repo.jobs.renew(lease)

    def _finish(self, lease: AuthoringLease, fallback: str = 'AUTHORING_OUTCOME_UNKNOWN') -> None:
        with self.database.transaction() as conn:
            repo = AuthoringGroupRepository(conn, lease.workspace_id)
            record, row = repo.load(lease.job_id), repo.jobs.load(lease.job_id)
            if row['status'] in TERMINAL or not repo.jobs.owned(row, lease, allow_cancel=True):
                return
            result, receipt, access_error = None, None, None
            try:
                identity = self._identity(conn, lease)
                if AuthoringGroupOutboundSource(self.context).resume_before_dispatch(conn, identity, lease):
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
            view.validation = group_not_run()
            view.error_code = fallback
            status = 'failed'
            payload = None
            plan = None
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
                        raw_answer = view.raw_answer or ''
                        try:
                            plan = parse_group_plan(raw_answer, record.input.request)
                        except (ValueError, TypeError):
                            view.validation.plan_membership = 'FAIL'
                            view.error_code = 'AUTHORING_PLAN_INVALID'
                        else:
                            view.validation.plan_membership = 'PASS'
                            try:
                                AuthoringGroupGenerated.model_validate(strict_json(raw_answer))
                            except (ValueError, TypeError):
                                view.validation.schema_check = 'FAIL'
                                view.error_code = 'AUTHORING_OUTPUT_INVALID'
                            else:
                                view.validation.schema_check = 'PASS'
                                try:
                                    generated = parse_group_generated(raw_answer, record.input.request,
                                        view.preparation.targets, view.preparation.materials)
                                    payload, validation = build_group_candidate_payload(generated, record.input.request,
                                        view.preparation.targets, view.preparation.materials)
                                except (ValueError, TypeError):
                                    # The complete strict shape was parsed, but at least one
                                    # request/plan/reference/private linkage is invalid. No
                                    # individual PASS is inferred from this combined failure.
                                    view.error_code = 'AUTHORING_GROUP_BINDING_INVALID'
                                    view.validation.issues.append(dm.Warning(
                                            code='AUTHORING_GROUP_BINDING_INVALID', severity='error',
                                            message='草稿未通过计划、引用或私解绑定检查。'))
                                else:
                                    view.validation = validation
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
                # The control-only cause must survive cancellation so a later
                # authorized read can recover the original output, never a draft.
                view.error_code = access_error or 'PROVIDER_CANCELLED'
            if access_error is not None or row['cancel_requested']:
                plan = None
            if plan is not None and receipt is not None:
                plan_ref = AuthoringContentPlanRef(source_job_id=lease.job_id, plan_sha256=plan_sha256(plan))
                repo.store_plan(AuthoringContentPlanRecord(version='authoring-content-plan-record-v1',
                    workspace_id=lease.workspace_id, source_job_id=lease.job_id, provider_receipt_id=receipt.id,
                    job_input_sha256=view.preparation.job_input_sha256, plan_ref=plan_ref, plan=plan, created_at=utc_now()))
                view.plan_ref, view.content_plan = plan_ref, plan
                if payload is not None:
                    candidate = AuthoringGroupCandidate(draft_id='authoring_group_' + uuid4().hex,
                        draft_revision=1, entity=payload.root.entity, candidate_sha256=group_candidate_sha256(payload))
                    repo.store_candidate(AuthoringGroupCandidateRecord(version='authoring-group-record-v1',
                        workspace_id=lease.workspace_id, candidate=candidate, source_job_id=lease.job_id,
                        provider_receipt_id=receipt.id, plan_ref=plan_ref, payload=payload,
                        validation=view.validation, created_at=utc_now()))
                    view.summary.candidate = candidate
                    DraftCandidateRepository(conn).register(ResolvedDraftCandidate(
                        lease.workspace_id, 'authoring', 'authoring_group', candidate))
            terminal_result = {'result_sha256': sha256_bytes(canonical_bytes(view.model_dump(mode='json', exclude={'summary'}))),
                               'candidate': view.summary.candidate.model_dump() if view.summary.candidate else None}
            repo.jobs.transition(row, status, result=terminal_result)
            repo.sync(record)

    async def process(self, lease: AuthoringLease) -> None:
        try:
            with self.database.transaction() as conn:
                identity = self._identity(conn, lease)
                if AuthoringGroupOutboundSource(self.context).resume_before_dispatch(conn, identity, lease):
                    return
                record = AuthoringGroupRepository(conn, lease.workspace_id).load(lease.job_id)
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
            if error.code == 'DRAFT_IDENTITY_CONFLICT':
                # Keep the candidate/catalog/terminal transaction rolled back.
                # An expired lease may recover the same checked Provider result;
                # this process must not immediately retry with a different ID.
                raise
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
