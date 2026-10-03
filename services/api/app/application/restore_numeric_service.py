"""Explicit Restore material binding, preview and one separately approved Job."""
from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from ..authoring_dto import NumericCheckDecisionAck
from ..restore_numeric_dto import RestoreNumericCheckPreviewWrite, RestoreNumericCheckView
from ..import_dto import JobCancelRequest, JobSnapshot
from ..infrastructure.restore_numeric_repository import RestoreNumericRepository, integrity
from ..infrastructure.publication_repository import PublicationRepository
from ..infrastructure.authoring_numeric_runtime import NumericRuntime, NumericRuntimeError
from ..infrastructure.security import SessionIdentity, current_session_identity
from ..infrastructure.database import utc_now
from .content_restore import ContentRestoreService
from .draft_candidate_models import match_candidate
from .authoring_numeric import NumericError
from .authoring_numeric_service import NumericService
from .restore_numeric_models import bind_material
from .providers import validate_key
from .errors import ApiError


class RestoreNumericService:
    def __init__(self, database, restores: ContentRestoreService, runtime: NumericRuntime):
        self.database, self.restores, self.runtime = database, restores, runtime

    def subject(self, conn, identity, draft):
        return self.restores.record(conn, identity, draft)

    def current_candidate(self, conn, identity, candidate):
        candidate = dm.DraftCandidate.model_validate(candidate.model_dump(mode='json'))
        self.restores.require_current_candidate(conn, identity, candidate)
        if PublicationRepository(conn, identity.workspace_id).for_candidate(candidate) is not None:
            raise ApiError(409, 'RESTORE_ALREADY_PUBLISHED', '已发布的恢复候选不能再新建或批准数值执行。')

    def projection(self, conn, identity, record):
        history = RestoreNumericRepository(conn, identity.workspace_id).history(record.candidate.draft_id)
        return history.material, list(history.records)

    def preview(self, identity: SessionIdentity, draft_id: str, body: RestoreNumericCheckPreviewWrite,
                key: str) -> RestoreNumericCheckView:
        key = validate_key(key)
        route = f'POST /content/restore-drafts/{draft_id}/numeric-checks'
        with self.database.transaction() as conn:
            record = self.subject(conn, identity, draft_id)
            repo = RestoreNumericRepository(conn, identity.workspace_id)
            repo.history(draft_id)
            previous = repo.replay(identity, route, key, body, RestoreNumericCheckView)
            if previous is not None:
                return previous
            match_candidate(dm.DraftCandidate.model_validate(body.candidate.model_dump(mode='json')), record.candidate)
            if record.payload.proposed_block.kind != 'worked_example':
                raise ApiError(409, 'RESTORE_NUMERIC_KIND_UNSUPPORTED', '只有历史公开例题恢复候选支持数值材料。')
            self.current_candidate(conn, identity, body.candidate)
            try:
                material = bind_material(record, body.material)
                history = repo.history(draft_id)
                if history.material is not None and history.material != material:
                    raise ApiError(409, 'RESTORE_NUMERIC_MATERIAL_CONFLICT', '此恢复候选已有唯一数值材料；修改需要新建候选。')
                if len(history.records) >= 100:
                    raise ApiError(413, 'NUMERIC_PREVIEW_LIMIT', '此恢复候选的数值预览次数已达上限。')
                runtime = self.runtime.prepare()
                manifest = self.runtime.manifest_document()
                if sha256_bytes(manifest) != runtime.runtime_manifest_sha256:
                    raise NumericRuntimeError('NUMERIC_RUNTIME_CHANGED')
                preview = repo.create(identity, material, runtime, manifest)
            except (NumericError, NumericRuntimeError) as error:
                raise NumericService._error(error) from None
            repo.command(identity, route, key, body, preview.view, preview.view.id, recorded_at=preview.view.created_at)
            repo.load(preview.view.id)
            return preview.view

    def read(self, identity: SessionIdentity, identifier: str) -> RestoreNumericCheckView:
        with self.database.transaction(immediate=False) as conn:
            self.restores.identity(conn, identity)
            repo = RestoreNumericRepository(conn, identity.workspace_id)
            self.subject(conn, identity, repo.draft_for_check(identifier))
            return repo.current(identifier)

    def decide(self, identity: SessionIdentity, identifier: str, body: dm.ApprovalDecision,
               key: str) -> NumericCheckDecisionAck:
        key = validate_key(key)
        route = f'POST /content/restore-numeric-checks/{identifier}/decision'
        with self.database.transaction() as conn:
            self.restores.identity(conn, identity)
            repo = RestoreNumericRepository(conn, identity.workspace_id)
            self.subject(conn, identity, repo.draft_for_check(identifier))
            record = repo.load(identifier)
            previous = repo.replay(identity, route, key, body, NumericCheckDecisionAck)
            if previous is not None:
                return previous
            if record.view.decision != 'pending':
                raise ApiError(409, 'NUMERIC_DECISION_EXISTS', '此预览已有唯一决定。')
            if body.expected_revision != record.view.revision:
                raise ApiError(412, 'REVISION_MISMATCH', '数值批准对象已变化，请重新读取。')
            if body.operation_sha256 != record.view.operation_sha256:
                raise ApiError(409, 'NUMERIC_OPERATION_MISMATCH', '待批准操作的完整身份不匹配。')
            if body.decision == 'approve_once':
                self.current_candidate(conn, identity, record.view.candidate)
                if record.view.expires_at <= utc_now():
                    raise ApiError(409, 'NUMERIC_APPROVAL_EXPIRED', '数值预览已过期，请明确新建预览。')
                try:
                    self.runtime.check(record.view.runtime)
                except NumericRuntimeError as error:
                    raise NumericService._error(error) from None
            now = utc_now()
            if body.decision == 'approve_once' and record.view.expires_at <= now:
                raise ApiError(409, 'NUMERIC_APPROVAL_EXPIRED', '数值预览已过期，请明确新建预览。')
            record = repo.decide(record, identity, body.decision, now)
            ack = repo.decision_ack(record)
            repo.command(identity, route, key, body, ack, identifier, job_revision=1 if ack.job else None,
                         basis_revision=1, recorded_at=now)
            repo.load(identifier)
            return ack

    def control_in_transaction(self, conn, identity, identifier):
        # Safe control is permitted to the current local learner too; never
        # exposes material/plan or requires subject Policy access to cancel.
        current_session_identity(conn, identity)
        repo = RestoreNumericRepository(conn, identity.workspace_id)
        repo.load(repo.check_for_job(identifier))
        return repo.jobs.snapshot(identifier)

    def job(self, identity, identifier):
        with self.database.transaction(immediate=False) as conn:
            return self.control_in_transaction(conn, identity, identifier)

    def cancel_job(self, identity, identifier, body: JobCancelRequest, key: str) -> JobSnapshot:
        key = validate_key(key)
        route = f'POST /jobs/{identifier}/cancel'
        with self.database.transaction() as conn:
            self.control_in_transaction(conn, identity, identifier)
            repo = RestoreNumericRepository(conn, identity.workspace_id)
            record = repo.load(repo.check_for_job(identifier))
            previous = repo.replay(identity, route, key, body, JobSnapshot)
            if previous is not None:
                return previous
            row = repo.jobs.load(identifier)
            if row['status'] not in {'completed', 'failed', 'cancelled'} and row['revision'] != body.expected_revision:
                raise ApiError(412, 'REVISION_MISMATCH', '数值任务已变化，请重新读取。')
            if row['status'] == 'queued':
                repo.cancel_queued(record)
            else:
                repo.jobs.cancel(identifier, body.expected_revision)
            result = repo.jobs.snapshot(identifier)
            repo.command(identity, route, key, body, result, record.view.id,
                         job_revision=result.revision, basis_revision=row['revision'])
            repo.load(record.view.id)
            return result

    def read_review_numeric(self, connection, identity, candidate):
        from .restore_review_numeric import read_observation
        self.subject(connection, identity, candidate.draft_id)
        return read_observation(RestoreNumericRepository(connection, identity.workspace_id), candidate)

    def verify_review_numeric(self, connection, identity, observation):
        from .restore_review_numeric import read_observation
        self.subject(connection, identity, observation.candidate.draft_id)
        if read_observation(RestoreNumericRepository(connection, identity.workspace_id), observation.candidate, observation) != observation:
            raise integrity()
