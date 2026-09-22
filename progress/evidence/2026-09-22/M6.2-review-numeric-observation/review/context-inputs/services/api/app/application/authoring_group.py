"""Group preparation, protected plan/member reads and original command replay."""
import sqlite3
from uuid import uuid4

from packages.contracts import domain_models as dm
from ..authoring_group_dto import (AuthoringGroupDraftView, AuthoringGroupJobView,
    AuthoringGroupPrepareWrite, AuthoringPrivateSolutionView)
from ..import_dto import JobCancelRequest, JobSnapshot
from ..infrastructure.authoring_job_repository import integrity
from ..infrastructure.authoring_group_repository import AuthoringGroupRepository, AuthoringGroupRecord
from ..infrastructure.database import Database
from ..infrastructure.security import SessionIdentity, author_execution_identity
from .authoring_group_context import AuthoringGroupContext
from .authoring_group_models import AuthoringGroupCandidateRecord, AuthoringGroupJobInput
from .authoring_group_source import group_preparation
from .authoring_group_validation import group_private_solution_view
from .errors import ApiError
from .draft_candidate_models import ResolvedDraftCandidate, match_candidate
from .provider_models import CheckedProviderFinished
from .tutor_worker import TutorProviderPort
from .review_material_models import CheckedReviewMaterial, GroupReviewMaterial, checked_material


class AuthoringGroupService:
    def __init__(self, database: Database, context: AuthoringGroupContext | None = None,
                 provider: TutorProviderPort | None = None):
        self.database = database
        self.context = context or AuthoringGroupContext(database)
        self.provider = provider

    def resolve_candidate(self, connection: sqlite3.Connection, identity: SessionIdentity,
                          candidate: dm.DraftCandidate) -> ResolvedDraftCandidate:
        return self._candidate_history(connection, identity, candidate)[0]

    def _candidate_history(self, connection: sqlite3.Connection, identity: SessionIdentity,
                           candidate: dm.DraftCandidate) -> tuple[ResolvedDraftCandidate, AuthoringGroupCandidateRecord, AuthoringGroupRecord]:
        self.context.check_access(connection, identity)
        repository = AuthoringGroupRepository(connection, identity.workspace_id)
        actual = repository.candidate(candidate.draft_id)
        history = self.verify_history(connection, identity, actual.source_job_id)
        expected = dm.DraftCandidate.model_validate(candidate.model_dump(mode='python'))
        actual_identity = dm.DraftCandidate.model_validate(actual.candidate.model_dump(mode='python'))
        match_candidate(expected, actual_identity)
        resolved = ResolvedDraftCandidate(identity.workspace_id, 'authoring', 'authoring_group', actual_identity)
        return resolved, actual, history

    def read_review_material(self, connection: sqlite3.Connection, identity: SessionIdentity,
                             candidate: dm.DraftCandidate) -> CheckedReviewMaterial:
        self.context.check_access(connection, identity)
        current = author_execution_identity(connection, identity.workspace_id, identity.id)
        resolved, actual, history = self._candidate_history(connection, current, candidate)
        context = self.context.read_group(connection, current, history.view.preparation.context_snapshot_id)
        self.context.verify_group(connection, current, context)
        plan = AuthoringGroupRepository(connection, current.workspace_id).validate_plan(history)
        if plan is None:
            raise integrity()
        return checked_material(resolved, GroupReviewMaterial(version='authoring-group-review-material-v1',
            record=actual, input=history.input, context=context, plan=plan,
            private_solution_coverage='included_in_complete_root_sha'))

    def verify_history(self, conn: sqlite3.Connection, identity: SessionIdentity, identifier: str) -> AuthoringGroupRecord:
        """Verify protected source and Provider history within the caller's transaction."""
        if not conn.in_transaction:
            raise integrity()
        record = AuthoringGroupRepository(conn, identity.workspace_id).load(identifier)
        context = self.context.read_group(conn, identity, record.view.preparation.context_snapshot_id)
        summary = group_preparation(record.input, context)
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

    def prepare(self, identity: SessionIdentity, body: AuthoringGroupPrepareWrite, key: str) -> dm.JobRef:
        with self.database.transaction() as conn:
            self.context.check_access(conn, identity)
            repo = AuthoringGroupRepository(conn, identity.workspace_id)
            previous = repo.replay(identity, 'POST /authoring/group-jobs', key, body, dm.JobRef)
            if previous is not None:
                self.verify_history(conn, identity, previous.id)
                return previous
            identifier = 'authoring_' + uuid4().hex
            value = AuthoringGroupJobInput(version='authoring-group-job-v1', workspace_id=identity.workspace_id,
                                      job_id=identifier, request=body)
            repo.jobs.create(identifier, 'authoring', value)
            context = self.context.prepare_group(conn, identity, value)
            summary = group_preparation(value, context)
            repo.create(identity, value, summary)
            ack = dm.JobRef(id=identifier, status='awaiting_approval')
            repo.record_command(identity, 'POST /authoring/group-jobs', key, body, ack, identifier, 1)
            self.verify_history(conn, identity, identifier)
            return ack

    def read(self, identity: SessionIdentity, identifier: str) -> AuthoringGroupJobView:
        with self.database.transaction(immediate=False) as conn:
            self.context.check_access(conn, identity)
            return self.verify_history(conn, identity, identifier).view

    def draft(self, identity: SessionIdentity, identifier: str) -> AuthoringGroupDraftView:
        with self.database.transaction(immediate=False) as conn:
            self.context.check_access(conn, identity)
            repo = AuthoringGroupRepository(conn, identity.workspace_id)
            result = repo.draft(identifier)
            self.verify_history(conn, identity, result.source_job_id)
            from ..infrastructure.authoring_group_numeric_repository import GroupNumericRepository
            numeric = GroupNumericRepository(conn, identity.workspace_id)
            if numeric.candidate_checks(identifier) != result.numeric_check_ids:
                raise integrity()
            for check_id in result.numeric_check_ids:
                numeric.current(check_id)
            return result

    def job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        with self.database.transaction(immediate=False) as conn:
            return self._control(conn, identity, identifier)

    def _control(self, conn: sqlite3.Connection, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        repo = AuthoringGroupRepository(conn, identity.workspace_id)
        row = repo.jobs.load(identifier)
        if row['kind'] == 'authoring':
            record = repo.load(identifier)
        else:
            from ..infrastructure.authoring_group_numeric_repository import GroupNumericRepository
            numeric = GroupNumericRepository(conn, identity.workspace_id)
            view = numeric.current(numeric.check_for_job(identifier))
            candidate = numeric.candidate(view.candidate.draft_id)
            record = repo.load(candidate.source_job_id)
        self.context.verify_group_history(conn, identity, record.input, record.view.preparation)
        return repo.jobs.snapshot(identifier)

    def cancel_job(self, identity: SessionIdentity, identifier: str, body: JobCancelRequest, key: str) -> JobSnapshot:
        with self.database.transaction() as conn:
            repo = AuthoringGroupRepository(conn, identity.workspace_id)
            record = repo.load(identifier)
            self.context.verify_group_history(conn, identity, record.input, record.view.preparation)
            route = f'POST /jobs/{identifier}/cancel'
            previous = repo.replay(identity, route, key, body, JobSnapshot)
            if previous is not None:
                return previous
            result = repo.jobs.cancel(identifier, body.expected_revision)
            basis = record.view.summary.job_revision
            repo.sync(record)
            repo.record_command(identity, route, key, body, result, identifier, result.revision, basis)
            return result

    def solution(self, identity: SessionIdentity, identifier: str, member_key: str) -> AuthoringPrivateSolutionView:
        with self.database.transaction(immediate=False) as conn:
            self.context.check_access(conn, identity)
            repo = AuthoringGroupRepository(conn, identity.workspace_id)
            candidate = repo.candidate(identifier)
            self.verify_history(conn, identity, candidate.source_job_id)
            try:
                return group_private_solution_view(candidate, member_key)
            except (ValueError, KeyError):
                raise ApiError(404, 'AUTHORING_SOLUTION_MISSING', '该草稿题目的私解不存在或不可访问。') from None
