"""Explicit numeric preview and separate approval; no process runs in HTTP calls."""
from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from ..authoring_dto import NumericCheckDecisionAck, NumericCheckPreviewWrite, NumericCheckView
from ..import_dto import JobCancelRequest, JobSnapshot
from ..infrastructure.authoring_job_repository import integrity
from ..infrastructure.authoring_numeric_repository import NumericRepository
from ..infrastructure.authoring_numeric_runtime import NumericRuntime, NumericRuntimeError
from ..infrastructure.database import Database, utc_now
from ..infrastructure.security import SessionIdentity
from .authoring import AuthoringService
from .authoring_context import AuthoringContext
from .authoring_numeric import NumericError, validate_plan
from .errors import ApiError


class NumericService:
    def __init__(self, database: Database, context: AuthoringContext, runtime: NumericRuntime,
                 authoring: AuthoringService | None = None):
        self.database, self.context, self.runtime = database, context, runtime
        self.authoring = authoring

    def _control_history(self, conn, identity, repo, draft_id):
        candidate = repo.candidate(draft_id)
        generation = repo.authoring.load(candidate.source_job_id)
        self.context.verify_history(conn, identity, generation.input, generation.view.preparation)
        return candidate

    def _candidate_history(self, conn, identity, repo, draft_id):
        candidate = self._control_history(conn, identity, repo, draft_id)
        if self.authoring is None:
            raise ApiError(503, 'AUTHORING_OUTPUT_UNAVAILABLE', '原生成结果当前无法核验。')
        generation = self.authoring.verify_history(conn, identity, candidate.source_job_id)
        if generation.view.summary.candidate != candidate.candidate:
            raise integrity()
        return candidate

    @staticmethod
    def _error(error: NumericRuntimeError | NumericError) -> ApiError:
        codes = {'BLOCKED_ENVIRONMENT', 'NUMERIC_RUNTIME_CHANGED', 'NUMERIC_INPUT_LIMIT',
                 'NUMERIC_RUNTIME_BUSY', 'NUMERIC_PLAN_UNSUPPORTED', 'NUMERIC_NONFINITE'}
        code = error.code if error.code in codes else 'BLOCKED_ENVIRONMENT'
        return ApiError(409, code, '数值检查准备或受信运行环境当前不可用；未开始执行。')

    def preview(self, identity: SessionIdentity, draft_id: str,
                body: NumericCheckPreviewWrite, key: str) -> NumericCheckView:
        route = f'POST /authoring/drafts/{draft_id}/numeric-checks'
        with self.database.transaction() as conn:
            self.context.check_access(conn, identity)
            repo = NumericRepository(conn, identity.workspace_id)
            original = self._candidate_history(conn, identity, repo, draft_id)
            previous = repo.replay(identity, route, key, body, NumericCheckView)
            if previous is not None:
                return previous
            if (body.candidate.draft_id != draft_id or body.candidate.entity != original.candidate.entity):
                raise ApiError(409, 'NUMERIC_CANDIDATE_MISMATCH', '数值检查必须使用该原候选的完整身份。')
            if body.candidate.draft_revision != original.candidate.draft_revision:
                raise ApiError(412, 'REVISION_MISMATCH', '草稿候选已变化，请读取后明确选择。')
            if body.candidate.candidate_sha256 != original.candidate.candidate_sha256:
                raise ApiError(409, 'NUMERIC_CANDIDATE_MISMATCH', '候选正文身份不匹配。')
            try:
                validate_plan(original.payload.numeric_plan.model_dump(mode='json'))
                runtime = self.runtime.prepare()
                manifest = self.runtime.manifest_document()
                if sha256_bytes(manifest) != runtime.runtime_manifest_sha256:
                    raise NumericRuntimeError('NUMERIC_RUNTIME_CHANGED')
            except (NumericRuntimeError, NumericError) as error:
                raise self._error(error) from None
            record = repo.create(identity, body.candidate, runtime, manifest)
            repo.command(identity, route, key, body, record.view, record.view.id, recorded_at=record.view.created_at)
            repo.load(record.view.id)
            return record.view

    def read(self, identity: SessionIdentity, identifier: str) -> NumericCheckView:
        with self.database.transaction(immediate=False) as conn:
            self.context.check_access(conn, identity)
            repo = NumericRepository(conn, identity.workspace_id)
            record = repo.load(identifier)
            self._candidate_history(conn, identity, repo, record.view.candidate.draft_id)
            return repo.current(identifier)

    def decide(self, identity: SessionIdentity, identifier: str,
               body: dm.ApprovalDecision, key: str) -> NumericCheckDecisionAck:
        route = f'POST /authoring/numeric-checks/{identifier}/decision'
        with self.database.transaction() as conn:
            self.context.check_access(conn, identity)
            repo = NumericRepository(conn, identity.workspace_id)
            record = repo.load(identifier)
            self._candidate_history(conn, identity, repo, record.view.candidate.draft_id)
            previous = repo.replay(identity, route, key, body, NumericCheckDecisionAck)
            if previous is not None:
                return previous
            if record.view.decision != 'pending':
                raise ApiError(409, 'NUMERIC_DECISION_EXISTS', '该预览已有唯一决定。')
            if record.view.revision != body.expected_revision:
                raise ApiError(412, 'REVISION_MISMATCH', '批准对象已变化，请读取原决定。')
            if body.operation_sha256 != record.view.operation_sha256:
                raise ApiError(409, 'NUMERIC_OPERATION_MISMATCH', '待批准操作身份不匹配。')
            if body.decision == 'approve_once':
                if record.view.expires_at <= utc_now():
                    raise ApiError(409, 'NUMERIC_APPROVAL_EXPIRED', '数值预览已过期，请明确新建预览。')
                try:
                    self.runtime.check(record.view.runtime)
                except NumericRuntimeError as error:
                    raise self._error(error) from None
            decided_at = utc_now()
            if body.decision == 'approve_once' and record.view.expires_at <= decided_at:
                raise ApiError(409, 'NUMERIC_APPROVAL_EXPIRED', '数值预览已过期，请明确新建预览。')
            record = repo.decide(record, identity, body.decision)
            result = repo.decision_ack(record)
            repo.command(identity, route, key, body, result, identifier,
                         job_revision=1 if result.job else None, recorded_at=decided_at)
            repo.load(identifier)
            return result

    def job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        with self.database.transaction(immediate=False) as conn:
            repo = NumericRepository(conn, identity.workspace_id)
            record = repo.load(repo.check_for_job(identifier))
            self._control_history(conn, identity, repo, record.view.candidate.draft_id)
            return repo.jobs.snapshot(identifier)

    def cancel_job(self, identity: SessionIdentity, identifier: str,
                   body: JobCancelRequest, key: str) -> JobSnapshot:
        route = f'POST /jobs/{identifier}/cancel'
        with self.database.transaction() as conn:
            repo = NumericRepository(conn, identity.workspace_id)
            record = repo.load(repo.check_for_job(identifier))
            self._control_history(conn, identity, repo, record.view.candidate.draft_id)
            previous = repo.replay(identity, route, key, body, JobSnapshot)
            if previous is not None:
                return previous
            row = repo.jobs.load(identifier)
            basis = row['revision']
            if row['status'] not in {'completed', 'failed', 'cancelled'} and basis != body.expected_revision:
                raise ApiError(412, 'REVISION_MISMATCH', '数值任务已变化，请读取原状态。')
            if row['status'] == 'queued':
                repo.cancel_queued(record)
            else:
                repo.jobs.cancel(identifier, body.expected_revision)
            result = repo.jobs.snapshot(identifier)
            repo.command(identity, route, key, body, result, record.view.id,
                         job_revision=result.revision, basis_revision=basis)
            repo.load(record.view.id)
            if result.result_refs or result.warnings or result.error is not None:
                raise integrity()
            return result
