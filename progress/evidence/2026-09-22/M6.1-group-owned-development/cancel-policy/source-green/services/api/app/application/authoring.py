"""Authoring application owner: actual preparation and safe durable job control."""
import base64
import hashlib
import hmac
import secrets
import sqlite3
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..authoring_dto import AuthoringDraftView, AuthoringJobPage, AuthoringJobView, AuthoringPreparationSummary, AuthoringPrepareWrite
from ..import_dto import JobCancelRequest, JobSnapshot
from ..infrastructure.authoring_job_repository import integrity
from ..infrastructure.authoring_repository import AuthoringRepository
from ..infrastructure.database import Database
from ..infrastructure.security import SessionIdentity
from .authoring_context import AuthoringContext
from .authoring_models import AuthoringJobInput
from .authoring_source import build_outbound
from .errors import ApiError
from .provider_models import CheckedProviderFinished
from .tutor_worker import TutorProviderPort


class AuthoringService:
    def __init__(self, database: Database, context: AuthoringContext | None = None,
                 provider: TutorProviderPort | None = None):
        self.database = database
        self.context = context or AuthoringContext(database)
        self.provider = provider
        self._cursor_key = secrets.token_bytes(32)

    def _history(self, conn: sqlite3.Connection, identity: SessionIdentity, identifier: str):
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
                self._history(conn, identity, previous.id)
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
            self._history(conn, identity, identifier)
            return ack

    def read(self, identity: SessionIdentity, identifier: str) -> AuthoringJobView:
        with self.database.transaction(immediate=False) as conn:
            self.context.check_access(conn, identity)
            return self._history(conn, identity, identifier).view

    def draft(self, identity: SessionIdentity, identifier: str) -> AuthoringDraftView:
        with self.database.transaction(immediate=False) as conn:
            self.context.check_access(conn, identity)
            repo = AuthoringRepository(conn, identity.workspace_id)
            result = repo.draft(identifier)
            self._history(conn, identity, result.source_job_id)
            from ..infrastructure.authoring_numeric_repository import NumericRepository
            numeric = NumericRepository(conn, identity.workspace_id)
            if numeric.candidate_checks(identifier) != result.numeric_check_ids:
                raise integrity()
            for check_id in result.numeric_check_ids:
                numeric.current(check_id)
            return result

    def job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        with self.database.transaction(immediate=False) as conn:
            return self._control(conn, identity, identifier)

    def _control(self, conn: sqlite3.Connection, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        repo = AuthoringRepository(conn, identity.workspace_id)
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
