"""Authoring application owner: actual preparation and safe durable job control."""
import base64
import hashlib
import hmac
import secrets
import sqlite3
from collections.abc import Callable
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .restore_numeric_service import RestoreNumericService
    from .publication_models import PublicationHistory
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..authoring_dto import AuthoringDraftView, AuthoringJobPage, AuthoringJobView, AuthoringPreparationSummary, AuthoringPrepareWrite
from ..import_dto import JobCancelRequest, JobSnapshot
from ..infrastructure.authoring_job_repository import integrity
from ..infrastructure.authoring_repository import AuthoringRepository, AuthoringRecord
from ..infrastructure.database import Database
from ..infrastructure.publication_repository import PublicationRepository
from ..infrastructure.security import SessionIdentity, author_execution_identity
from .authoring_context import AuthoringContext
from .authoring_models import AuthoringCandidateRecord, AuthoringJobInput
from .authoring_source import build_outbound
from .errors import ApiError
from .draft_candidate_models import ResolvedDraftCandidate, match_candidate
from .provider_models import CheckedProviderFinished
from .tutor_worker import TutorProviderPort
from .review_material_models import CheckedReviewMaterial, SingleReviewMaterial, checked_material


class AuthoringService:
    def __init__(self, database: Database, context: AuthoringContext | None = None,
                 provider: TutorProviderPort | None = None):
        self.database = database
        self.context = context or AuthoringContext(database)
        self.provider = provider
        self.restore_numeric: RestoreNumericService | None = None
        self.verify_publication: Callable[[sqlite3.Connection, SessionIdentity, 'PublicationHistory'], dm.ContentRef] | None = None
        self._cursor_key = secrets.token_bytes(32)

    def resolve_candidate(self, connection: sqlite3.Connection, identity: SessionIdentity,
                          candidate: dm.DraftCandidate) -> ResolvedDraftCandidate:
        return self._candidate_history(connection, identity, candidate)[0]

    def _candidate_history(self, connection: sqlite3.Connection, identity: SessionIdentity,
                           candidate: dm.DraftCandidate) -> tuple[ResolvedDraftCandidate, AuthoringCandidateRecord, AuthoringRecord]:
        self.context.check_access(connection, identity)
        repository = AuthoringRepository(connection, identity.workspace_id)
        actual = repository.candidate(candidate.draft_id)
        history = self.verify_history(connection, identity, actual.source_job_id)
        expected = dm.DraftCandidate.model_validate(candidate.model_dump(mode='python'))
        actual_identity = dm.DraftCandidate.model_validate(actual.candidate.model_dump(mode='python'))
        match_candidate(expected, actual_identity)
        resolved = ResolvedDraftCandidate(identity.workspace_id, 'authoring', 'authoring_single', actual_identity)
        return resolved, actual, history

    def read_review_material(self, connection: sqlite3.Connection, identity: SessionIdentity,
                             candidate: dm.DraftCandidate) -> CheckedReviewMaterial:
        self.context.check_access(connection, identity)
        current = author_execution_identity(connection, identity.workspace_id, identity.id)
        resolved, actual, history = self._candidate_history(connection, current, candidate)
        context = self.context.read(connection, current, history.view.preparation.context_snapshot_id)
        self.context.verify(connection, current, context)
        return checked_material(resolved, SingleReviewMaterial(version='authoring-single-review-material-v1',
            record=actual, input=history.input, context=context))

    def verify_history(self, conn: sqlite3.Connection, identity: SessionIdentity, identifier: str) -> AuthoringRecord:
        """Verify protected source and Provider history within the caller's transaction."""
        if not conn.in_transaction:
            raise integrity()
        record = AuthoringRepository(conn, identity.workspace_id).load(identifier)
        context = self.context.read(conn, identity, record.view.preparation.context_snapshot_id)
        actual = build_outbound(record.input, context, record.view.summary.job_revision)
        summary = AuthoringPreparationSummary(context_snapshot_id=context.snapshot.id,
            snapshot_sha256=context.snapshot.snapshot_sha256, job_input_sha256=actual.job_input_sha256,
            prepared_input_sha256=actual.prepared_input_sha256, character_count=context.snapshot.character_count,
            materials=context.materials, warnings=context.warnings)
        if summary != record.view.preparation:
            raise integrity()
        view = record.view
        if view.provider_receipt_id is not None:
            if self.provider is None or view.consent_id is None:
                raise ApiError(503, 'AUTHORING_OUTPUT_UNAVAILABLE', '原生成结果当前无法核验。')
            original = self.provider.read_result(conn, identity, identifier, view.consent_id)
            if original is None or original.receipt.id != view.provider_receipt_id:
                raise integrity()
            terminal = original.receipt.terminal
            outcome = ('incomplete' if terminal.outcome == 'incomplete' else 'completed') if isinstance(
                terminal, CheckedProviderFinished) else terminal.provider_outcome
            if view.provider_outcome != outcome or view.usage != terminal.usage:
                raise integrity()
            answer = original.answer.text if original.answer else None
            refusal = original.refusal.text if original.refusal else None
            withheld = (view.summary.status in {'failed', 'cancelled'} and view.summary.candidate is None
                and view.raw_answer is None and view.raw_refusal is None
                and view.error_code in {'POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'})
            if withheld:
                # A control-only terminal never acquired the private bytes.
                # Current permission now permits this checked, read-only projection;
                # the original failed job and absence of a candidate stay intact.
                record = record.model_copy(deep=True)
                record.view.raw_answer, record.view.raw_refusal = answer, refusal
            elif view.raw_answer != answer or view.raw_refusal != refusal:
                raise integrity()
        return record

    def prepare(self, identity: SessionIdentity, body: AuthoringPrepareWrite, key: str) -> dm.JobRef:
        with self.database.transaction() as conn:
            self.context.check_access(conn, identity)
            repo = AuthoringRepository(conn, identity.workspace_id)
            previous = repo.replay(identity, 'POST /authoring/jobs', key, body, dm.JobRef)
            if previous is not None:
                self.verify_history(conn, identity, previous.id)
                return previous
            identifier = 'authoring_' + uuid4().hex
            value = AuthoringJobInput(version='authoring-job-v1', workspace_id=identity.workspace_id,
                                      job_id=identifier, request=body)
            repo.jobs.create(identifier, 'authoring', value)
            context = self.context.prepare(conn, identity, value)
            material = build_outbound(value, context, 1)
            summary = AuthoringPreparationSummary(context_snapshot_id=context.snapshot.id,
                snapshot_sha256=context.snapshot.snapshot_sha256, job_input_sha256=sha256_bytes(canonical_bytes(value)),
                prepared_input_sha256=material.prepared_input_sha256, character_count=context.snapshot.character_count,
                materials=context.materials, warnings=context.warnings)
            repo.create(identity, value, summary)
            ack = dm.JobRef(id=identifier, status='awaiting_approval')
            repo.record_command(identity, 'POST /authoring/jobs', key, body, ack, identifier, 1)
            self.verify_history(conn, identity, identifier)
            return ack

    def read(self, identity: SessionIdentity, identifier: str) -> AuthoringJobView:
        with self.database.transaction(immediate=False) as conn:
            self.context.check_access(conn, identity)
            return self.verify_history(conn, identity, identifier).view

    def draft(self, identity: SessionIdentity, identifier: str) -> AuthoringDraftView:
        with self.database.transaction(immediate=False) as conn:
            self.context.check_access(conn, identity)
            repo = AuthoringRepository(conn, identity.workspace_id)
            result = repo.draft(identifier)
            self.verify_history(conn, identity, result.source_job_id)
            from ..infrastructure.authoring_numeric_repository import NumericRepository
            numeric = NumericRepository(conn, identity.workspace_id)
            if numeric.candidate_checks(identifier) != result.numeric_check_ids:
                raise integrity()
            for check_id in result.numeric_check_ids:
                numeric.current(check_id)
            published = self.published_ref_in_transaction(conn, identity,
                dm.DraftCandidate.model_validate(result.candidate.model_dump()))
            if published is not None:
                result = AuthoringDraftView.model_validate({**result.model_dump(), 'state': 'published',
                    'published_ref': published.model_dump(), 'warnings': [
                        {**warning.model_dump(), 'message': '原生成阶段未执行数学、来源或教学审核；当前发布以绑定的发布记录为准。'}
                        if warning.code == 'AUTHORING_REVIEW_NOT_RUN' else warning.model_dump()
                        for warning in result.warnings]})
            return result

    def published_ref_in_transaction(self, conn: sqlite3.Connection, identity: SessionIdentity,
                                     candidate: dm.DraftCandidate) -> dm.ContentRef | None:
        """Current Single projection; source, publication and actual Content stay checked."""
        from .publication_models import SinglePublicationRecord
        resolved, _, _ = self._candidate_history(conn, identity, candidate)
        publication = PublicationRepository(conn, identity.workspace_id).single_for_candidate(resolved.candidate)
        if publication is None:
            return None
        if not isinstance(publication.record, SinglePublicationRecord):
            raise integrity()
        if self.verify_publication is None:
            raise ApiError(503, 'PUBLICATION_OWNER_UNAVAILABLE', '生成候选的真实发布记录当前无法核验。')
        return self.verify_publication(conn, identity, publication)

    def require_unpublished_candidate(self, conn: sqlite3.Connection, identity: SessionIdentity,
                                      candidate: dm.DraftCandidate) -> None:
        """Call in the same write transaction as new preview/approval/start permission."""
        if self.published_ref_in_transaction(conn, identity, candidate) is not None:
            raise ApiError(409, 'DRAFT_ALREADY_PUBLISHED', '此生成候选已发布，不能新增数值批准或启动许可。')

    def job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        with self.database.transaction(immediate=False) as conn:
            return self._control(conn, identity, identifier)

    def _control(self, conn: sqlite3.Connection, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        repo = AuthoringRepository(conn, identity.workspace_id)
        if repo.jobs.input_version(identifier) == 'restore-numeric-job-v1':
            if self.restore_numeric is None:
                raise ApiError(503, 'NUMERIC_OWNER_UNAVAILABLE', '恢复数值安全控制服务当前不可用。')
            return self.restore_numeric.control_in_transaction(conn, identity, identifier)
        if repo.jobs.input_version(identifier) in {'authoring-group-job-v1', 'authoring-group-numeric-job-v1'}:
            from .authoring_group import AuthoringGroupService
            return AuthoringGroupService(self.database)._control(conn, identity, identifier)
        row = repo.jobs.load(identifier)
        if row['kind'] == 'authoring':
            record = repo.load(identifier)
        else:
            from ..infrastructure.authoring_numeric_repository import NumericRepository
            numeric = NumericRepository(conn, identity.workspace_id)
            view = numeric.current(numeric.check_for_job(identifier))
            candidate = numeric.candidate(view.candidate.draft_id)
            record = repo.load(candidate.source_job_id)
        self.context.verify_history(conn, identity, record.input, record.view.preparation)
        return repo.jobs.snapshot(identifier)

    def cancel_job(self, identity: SessionIdentity, identifier: str, body: JobCancelRequest, key: str) -> JobSnapshot:
        with self.database.transaction() as conn:
            repo = AuthoringRepository(conn, identity.workspace_id)
            record = repo.load(identifier)
            self.context.verify_history(conn, identity, record.input, record.view.preparation)
            route = f'POST /jobs/{identifier}/cancel'
            previous = repo.replay(identity, route, key, body, JobSnapshot)
            if previous is not None:
                return previous
            result = repo.jobs.cancel(identifier, body.expected_revision)
            basis = record.view.summary.job_revision
            repo.sync(record)
            repo.record_command(identity, route, key, body, result, identifier, result.revision, basis)
            return result

    def jobs(self, identity: SessionIdentity, cursor: str | None = None, limit: int = 20) -> AuthoringJobPage:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ApiError(400, 'CURSOR_INVALID', '分页数量须为1至100的整数。')
        with self.database.transaction(immediate=False) as conn:
            repo = AuthoringRepository(conn, identity.workspace_id)
            actual_members = repo.jobs.member_ids()
            memberships = {row[0] for row in conn.execute('SELECT job_id FROM authoring_records WHERE workspace_id=?',
                                                         (identity.workspace_id,))}
            if actual_members != memberships:
                raise integrity()
            high = conn.execute('SELECT COALESCE(MAX(sequence),0) FROM authoring_records WHERE workspace_id=?',
                                (identity.workspace_id,)).fetchone()[0]
            position = high + 1
            if cursor is not None:
                try:
                    if not isinstance(cursor, str) or not 1 <= len(cursor) <= 2048:
                        raise ValueError('length')
                    raw = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
                    if not hmac.compare_digest(raw[:32], hmac.new(self._cursor_key, raw[32:], hashlib.sha256).digest()):
                        raise ValueError('signature')
                    value = strict_json(raw[32:])
                    if (set(value) != {'workspace', 'kinds', 'limit', 'high', 'position'}
                            or value['workspace'] != identity.workspace_id or value['limit'] != limit
                            or value['kinds'] != ['authoring', 'authoring_numeric_check']
                            or type(value['high']) is not int or type(value['position']) is not int
                            or not 0 < value['position'] <= value['high'] <= high):
                        raise ValueError('binding')
                    high, position = value['high'], value['position']
                except (ValueError, TypeError, KeyError):
                    raise ApiError(400, 'CURSOR_INVALID', '分页游标无效，请重新读取第一页。') from None
            rows = conn.execute('SELECT sequence,job_id FROM authoring_records WHERE workspace_id=? AND sequence<=? AND sequence<? ORDER BY sequence DESC LIMIT ?',
                                (identity.workspace_id, high, position, limit + 1)).fetchall()
            items = []
            for row in rows[:limit]:
                items.append(self._control(conn, identity, row['job_id']))
            next_cursor = None
            if len(rows) > limit:
                raw = canonical_bytes({'workspace': identity.workspace_id, 'kinds': ['authoring', 'authoring_numeric_check'],
                                       'limit': limit, 'high': high, 'position': rows[limit - 1]['sequence']})
                next_cursor = base64.urlsafe_b64encode(hmac.new(self._cursor_key, raw, hashlib.sha256).digest() + raw).decode().rstrip('=')
            return AuthoringJobPage(items=items, next_cursor=next_cursor)
