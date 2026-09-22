"""Numeric approval, launch and immutable result ledger in caller transactions."""
import base64
import sqlite3
from datetime import datetime, timedelta
from typing import Literal, Self, TypeVar
from uuid import uuid4

from pydantic import BaseModel, TypeAdapter, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from ..application.authoring_models import NumericJobInput, numeric_operation_sha256
from ..application.errors import ApiError
from ..authoring_dto import (
    AuthoringCandidate, AuthoringModel, NumericCheckDecisionAck, NumericCheckPreviewWrite,
    NumericCheckResult, NumericCheckView, NumericRuntimeProfile, numeric_result_sha256,
)
from ..import_dto import JobCancelRequest, JobSnapshot
from .authoring_job_repository import AuthoringJobRepository, AuthoringLease, checked, integrity
from .authoring_repository import AuthoringRepository
from .database import utc_now
from .security import SessionIdentity

M = TypeVar('M', bound=BaseModel)


class NumericRecord(AuthoringModel):
    version: Literal['numeric-check-record-v1']
    workspace_id: dm.Id
    actor_id: dm.Id
    decision_actor_id: dm.Id | None
    runtime_manifest_json: str
    view: NumericCheckView

    @model_validator(mode='after')
    def original_projection(self) -> Self:
        if (self.decision_actor_id is None) != (self.view.decision == 'pending'):
            raise ValueError('a decision must retain its actual acting session identity')
        checked(self.runtime_manifest_json, self.view.runtime.runtime_manifest_sha256)
        if self.view.expired or self.view.result is not None:
            raise ValueError('persisted approval view is the original command projection')
        if self.view.job is not None and (self.view.job.status != 'queued' or self.view.job_revision != 1):
            raise ValueError('persisted approval view keeps original queued ACK')
        expected = numeric_operation_sha256(self.workspace_id, self.view.id, self.view.candidate,
                                             self.view.plan, self.view.runtime)
        if self.view.operation_sha256 != expected:
            raise ValueError('approval must bind its complete original operation')
        return self


class NumericMembership(AuthoringModel):
    version: Literal['numeric-membership-v1']
    input: NumericJobInput


class NumericStart(AuthoringModel):
    version: Literal['numeric-start-v1']
    workspace_id: dm.Id
    job_id: dm.Id
    check_id: dm.Id
    input_sha256: dm.Sha256
    operation_sha256: dm.Sha256
    lease_owner: dm.Id | None
    job_revision: dm.Revision
    admitted_at: dm.UTC | None
    actual_started_at: dm.UTC | None

    @model_validator(mode='after')
    def actual_start(self) -> Self:
        if self.admitted_at is None and (self.actual_started_at is not None or self.lease_owner is not None):
            raise ValueError('a non-admitted execution cannot claim an actual process')
        if self.admitted_at is not None and self.lease_owner is None:
            raise ValueError('launch admission must retain its actual owner')
        if (self.actual_started_at is not None and self.admitted_at is not None
                and datetime.fromisoformat(self.actual_started_at.replace('Z', '+00:00'))
                < datetime.fromisoformat(self.admitted_at.replace('Z', '+00:00'))):
            raise ValueError('process observation cannot precede launch permission')
        return self


class NumericEnd(AuthoringModel):
    version: Literal['numeric-end-v1']
    result: NumericCheckResult
    stdout_base64: str
    stderr_base64: str
    output_complete: bool

    @model_validator(mode='after')
    def output_bytes(self) -> Self:
        try:
            stdout = base64.b64decode(self.stdout_base64, validate=True)
            stderr = base64.b64decode(self.stderr_base64, validate=True)
        except ValueError:
            raise ValueError('numeric output must contain its exact preserved bytes') from None
        if len(stdout) + len(stderr) > 65536:
            raise ValueError('numeric output exceeds the actual preserved resource limit')
        expected = sha256_bytes(stdout) if self.output_complete and stdout else None
        if self.result.output_sha256 != expected:
            raise ValueError('output hash must identify the full actual stdout bytes only')
        return self


class NumericRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.conn, self.workspace_id = connection, workspace_id
        self.jobs = AuthoringJobRepository(connection, workspace_id)
        self.authoring = AuthoringRepository(connection, workspace_id)

    def candidate(self, identifier: str):
        candidate = self.authoring.candidate(identifier)
        self.authoring.load(candidate.source_job_id)
        return candidate

    def load(self, identifier: str, *, commands: bool = True) -> NumericRecord:
        row = self.conn.execute('SELECT * FROM authoring_numeric_checks WHERE check_id=? AND workspace_id=?',
                                (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, 'NUMERIC_CHECK_MISSING', '数值检查不存在或不可访问。')
        try:
            record = NumericRecord.model_validate(checked(row['record_json'], row['record_sha256']))
            view = record.view
            candidate = self.candidate(row['draft_id'])
            if (record.workspace_id != self.workspace_id or view.id != identifier
                    or view.candidate != candidate.candidate or view.plan != candidate.payload.numeric_plan
                    or (view.job.id if view.job else None) != row['job_id']):
                raise integrity()
            if view.job is not None:
                self._job_input(record)
                self._execution(record)
            elif self.conn.execute("SELECT 1 FROM authoring_records WHERE workspace_id=? AND json_extract(record_json,'$.version')='numeric-membership-v1' AND json_extract(record_json,'$.input.check_id')=?",
                                   (self.workspace_id, identifier)).fetchone():
                raise integrity()
            if commands:
                self._commands(record)
            return record
        except (ValueError, TypeError, KeyError):
            raise integrity() from None

    def _job_input(self, record: NumericRecord) -> NumericJobInput:
        view = record.view
        if view.job is None:
            raise integrity()
        row = self.jobs.load(view.job.id)
        membership = self.conn.execute('SELECT * FROM authoring_records WHERE job_id=? AND workspace_id=?',
                                        (view.job.id, self.workspace_id)).fetchone()
        if membership is None or row['kind'] != 'authoring_numeric_check':
            raise integrity()
        value = NumericJobInput.model_validate(checked(row['input_json'], row['input_sha256']))
        original = NumericMembership.model_validate(checked(membership['record_json'], membership['record_sha256']))
        if (original.input != value or membership['actor_id'] != record.decision_actor_id
                or value.job_id != view.job.id or value.workspace_id != self.workspace_id
                or value.check_id != view.id or value.candidate != view.candidate
                or value.plan != view.plan or value.runtime != view.runtime
                or value.operation_sha256 != view.operation_sha256):
            raise integrity()
        return value

    def check_for_job(self, identifier: str) -> str:
        row = self.conn.execute('SELECT check_id FROM authoring_numeric_checks WHERE job_id=? AND workspace_id=?',
                                (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, 'JOB_MISSING', '任务不存在或不可访问。')
        return row[0]

    def job_input(self, identifier: str) -> NumericJobInput:
        return self._job_input(self.load(self.check_for_job(identifier)))

    def execution_state(self, identifier: str) -> tuple[NumericStart | None, NumericEnd | None]:
        """Read checked admission/process/result facts without starting or repairing work."""
        record = self.load(self.check_for_job(identifier))
        return self._execution(record)

    def _execution(self, record: NumericRecord) -> tuple[NumericStart | None, NumericEnd | None]:
        if record.view.job is None:
            return None, None
        job_id = record.view.job.id
        job = self.jobs.load(job_id)
        row = self.conn.execute('SELECT * FROM authoring_numeric_executions WHERE job_id=?', (job_id,)).fetchone()
        if row is None:
            if job['status'] in {'completed', 'failed', 'cancelled'}:
                raise integrity()
            return None, None
        start = NumericStart.model_validate(checked(row['start_json'], row['start_sha256']))
        if (start.workspace_id != self.workspace_id or start.job_id != job_id or start.check_id != record.view.id
                or start.input_sha256 != job['input_sha256'] or start.operation_sha256 != record.view.operation_sha256):
            raise integrity()
        basis = self.jobs.snapshot(job_id, start.job_revision)
        if start.admitted_at is not None:
            if basis.status != 'running' or start.admitted_at < basis.updated_at:
                raise integrity()
        elif basis.status not in {'queued', 'running'}:
            raise integrity()
        if (row['end_json'] is None) != (row['end_sha256'] is None):
            raise integrity()
        end = NumericEnd.model_validate(checked(row['end_json'], row['end_sha256'])) if row['end_json'] else None
        if (job['status'] in {'completed', 'failed', 'cancelled'}) != (end is not None):
            raise integrity()
        if end is not None:
            result = end.result
            if (result.job_id != job_id or result.input_sha256 != job['input_sha256']
                    or result.operation_sha256 != record.view.operation_sha256
                    or result.started_at != start.actual_started_at
                    or job['result_json'] != canonical_bytes({'numeric_result_sha256': result.result_sha256}).decode()):
                raise integrity()
            self._projection(record, result)
        return start, end

    def _projection(self, record: NumericRecord, result: NumericCheckResult | None) -> NumericCheckView:
        value = record.view.model_dump(mode='json')
        value['expired'] = record.view.expires_at <= utc_now()
        if record.view.job is not None:
            job = self.jobs.load(record.view.job.id)
            value['job'] = {'id': job['id'], 'status': job['status']}
            value['job_revision'] = job['revision']
        value['result'] = result.model_dump(mode='json') if result else None
        return NumericCheckView.model_validate(value)

    def current(self, identifier: str) -> NumericCheckView:
        record = self.load(identifier)
        _, end = self._execution(record)
        return self._projection(record, end.result if end else None)

    @staticmethod
    def preview_ack(record: NumericRecord) -> NumericCheckView:
        value = record.view.model_dump(mode='json')
        value.update(revision=1, decision='pending', job=None, job_revision=None, result=None, expired=False)
        return NumericCheckView.model_validate(value)

    def _commands(self, record: NumericRecord) -> None:
        view = record.view
        rows = self.conn.execute('SELECT * FROM authoring_commands WHERE workspace_id=? AND owner_id=?',
                                 (self.workspace_id, view.id)).fetchall()
        previews = decisions = 0
        for row in rows:
            TypeAdapter(dm.UTC).validate_python(row['created_at'])
            TypeAdapter(dm.Id).validate_python(row['actor_id'])
            request, ack = checked(row['request_json'], row['request_sha256']), checked(row['ack_json'], row['ack_sha256'])
            if row['route'] == f'POST /authoring/drafts/{view.candidate.draft_id}/numeric-checks':
                previews += 1
                if (NumericCheckPreviewWrite.model_validate(request).candidate != view.candidate
                        or NumericCheckView.model_validate(ack) != self.preview_ack(record)
                        or row['job_revision'] is not None or row['basis_revision'] is not None
                        or row['actor_id'] != record.actor_id or row['created_at'] != view.created_at):
                    raise integrity()
            elif row['route'] == f'POST /authoring/numeric-checks/{view.id}/decision':
                decisions += 1
                body = dm.ApprovalDecision.model_validate(request)
                result = NumericCheckDecisionAck.model_validate(ack)
                expected = self.decision_ack(record)
                if (view.decision == 'pending' or body.expected_revision != 1
                        or body.operation_sha256 != view.operation_sha256 or body.decision != view.decision
                        or result != expected or row['actor_id'] != record.decision_actor_id or row['basis_revision'] is not None
                        or row['job_revision'] != (1 if view.job else None)
                        or row['created_at'] < view.created_at
                        or view.decision == 'approve_once' and row['created_at'] >= view.expires_at):
                    raise integrity()
            elif view.job is not None and row['route'] == f'POST /jobs/{view.job.id}/cancel':
                cancel_body = JobCancelRequest.model_validate(request)
                cancel_ack = JobSnapshot.model_validate(ack)
                if row['job_revision'] != cancel_ack.revision:
                    raise integrity()
                self.jobs.verify_cancel_ack(view.job.id, cancel_body.expected_revision, cancel_ack,
                                            row['basis_revision'], row['created_at'])
            else:
                raise integrity()
        if previews != 1 or decisions != (0 if view.decision == 'pending' else 1):
            raise integrity()

    @staticmethod
    def decision_ack(record: NumericRecord) -> NumericCheckDecisionAck:
        if record.view.decision == 'pending':
            raise integrity()
        return NumericCheckDecisionAck(id=record.view.id, revision=2,
            operation_sha256=record.view.operation_sha256, decision=record.view.decision,
            applied=True, job=record.view.job)

    def replay(self, identity: SessionIdentity, route: str, key: str, body: BaseModel, model: type[M]) -> M | None:
        row = self.conn.execute('SELECT * FROM authoring_commands WHERE workspace_id=? AND actor_id=? AND route=? AND key=?',
                                (self.workspace_id, identity.id, route, key)).fetchone()
        if row is None:
            return None
        self.load(row['owner_id'])
        if canonical_bytes(body).decode() != row['request_json']:
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原命令键已用于不同的完整命令。')
        try:
            return model.model_validate(checked(row['ack_json'], row['ack_sha256']))
        except (ValueError, TypeError):
            raise integrity() from None

    def command(self, identity: SessionIdentity, route: str, key: str, body: BaseModel,
                ack: BaseModel, owner_id: str, *, job_revision: int | None = None,
                basis_revision: int | None = None, recorded_at: str | None = None) -> None:
        request, result = canonical_bytes(body).decode(), canonical_bytes(ack).decode()
        self.conn.execute('INSERT INTO authoring_commands(workspace_id,actor_id,route,key,owner_id,request_json,request_sha256,ack_json,ack_sha256,job_revision,basis_revision,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (self.workspace_id, identity.id, route, key, owner_id, request, sha256_bytes(request.encode()),
             result, sha256_bytes(result.encode()), job_revision, basis_revision, recorded_at or utc_now()))

    def candidate_checks(self, draft_id: str) -> list[str]:
        """Bounded exact membership: missing rows cannot silently free quota."""
        self.candidate(draft_id)
        rows = self.conn.execute('SELECT check_id FROM authoring_numeric_checks WHERE workspace_id=? AND draft_id=? ORDER BY rowid',
                                 (self.workspace_id, draft_id)).fetchall()
        commands = self.conn.execute('SELECT owner_id FROM authoring_commands WHERE workspace_id=? AND route=?',
            (self.workspace_id, f'POST /authoring/drafts/{draft_id}/numeric-checks')).fetchall()
        identities = [row[0] for row in rows]
        if (len(identities) > 100 or len(commands) != len(identities)
                or {row[0] for row in commands} != set(identities)):
            raise integrity()
        for identifier in identities:
            self.load(identifier)
        return identities

    def create(self, identity: SessionIdentity, candidate: AuthoringCandidate, runtime: NumericRuntimeProfile,
               runtime_manifest: bytes) -> NumericRecord:
        original = self.candidate(candidate.draft_id)
        count = len(self.candidate_checks(candidate.draft_id))
        if count >= 100:
            raise ApiError(413, 'NUMERIC_PREVIEW_LIMIT', '该候选已达到数值预览上限；既有记录仍可读取与取消。')
        now, identifier = utc_now(), 'numeric_' + uuid4().hex
        expires = (datetime.fromisoformat(now.replace('Z', '+00:00')) + timedelta(minutes=10)).isoformat().replace('+00:00', 'Z')
        plan = original.payload.numeric_plan
        digest = numeric_operation_sha256(self.workspace_id, identifier, candidate, plan, runtime)
        view = NumericCheckView(id=identifier, revision=1, candidate=candidate, plan=plan, runtime=runtime,
            operation_sha256=digest, decision='pending', created_at=now, expires_at=expires, expired=False,
            job=None, job_revision=None, result=None, warnings=[])
        record = NumericRecord(version='numeric-check-record-v1', workspace_id=self.workspace_id, actor_id=identity.id, decision_actor_id=None,
                               runtime_manifest_json=runtime_manifest.decode('utf-8'), view=view)
        raw = canonical_bytes(record).decode()
        self.conn.execute('INSERT INTO authoring_numeric_checks(check_id,workspace_id,draft_id,job_id,record_json,record_sha256) VALUES(?,?,?,NULL,?,?)',
                          (identifier, self.workspace_id, candidate.draft_id, raw, sha256_bytes(raw.encode())))
        return record

    def decide(self, record: NumericRecord, identity: SessionIdentity, decision: Literal['approve_once', 'decline']) -> NumericRecord:
        value = record.view.model_dump(mode='json')
        value.update(revision=2, decision=decision)
        if decision == 'approve_once':
            identifier = 'numeric_job_' + uuid4().hex
            job = NumericJobInput(version='authoring-numeric-job-v1', workspace_id=self.workspace_id,
                job_id=identifier, check_id=record.view.id, operation_sha256=record.view.operation_sha256,
                candidate=record.view.candidate, plan=record.view.plan, runtime=record.view.runtime)
            self.jobs.create(identifier, 'authoring_numeric_check', job)
            membership = canonical_bytes(NumericMembership(version='numeric-membership-v1', input=job)).decode()
            self.conn.execute('INSERT INTO authoring_records(job_id,workspace_id,actor_id,record_json,record_sha256) VALUES(?,?,?,?,?)',
                (identifier, self.workspace_id, identity.id, membership, sha256_bytes(membership.encode())))
            value.update(job={'id': identifier, 'status': 'queued'}, job_revision=1)
        record = NumericRecord(version=record.version, workspace_id=self.workspace_id, actor_id=record.actor_id, decision_actor_id=identity.id,
                               runtime_manifest_json=record.runtime_manifest_json, view=NumericCheckView.model_validate(value))
        raw = canonical_bytes(record).decode()
        self.conn.execute('UPDATE authoring_numeric_checks SET job_id=?,record_json=?,record_sha256=? WHERE check_id=? AND workspace_id=?',
            (record.view.job.id if record.view.job else None, raw, sha256_bytes(raw.encode()), record.view.id, self.workspace_id))
        return record

    def claim(self, identifier: str) -> tuple[AuthoringLease, NumericJobInput, str]:
        record = self.load(self.check_for_job(identifier))
        value = self._job_input(record)
        lease = self.jobs.claim(identifier)
        assert record.decision_actor_id is not None
        return lease, value, record.decision_actor_id

    def begin(self, lease: AuthoringLease, admitted_at: str) -> bool:
        record = self.load(self.check_for_job(lease.job_id))
        job = self.jobs.load(lease.job_id)
        if not self.jobs.owned(job, lease):
            raise ApiError(409, 'AUTHORING_LEASE_LOST', '数值执行许可已失效。')
        start, _ = self._execution(record)
        if start is not None:
            return False
        start = NumericStart(version='numeric-start-v1', workspace_id=self.workspace_id, job_id=lease.job_id,
            check_id=record.view.id, input_sha256=job['input_sha256'], operation_sha256=record.view.operation_sha256,
            lease_owner=lease.owner, job_revision=job['revision'], admitted_at=admitted_at, actual_started_at=None)
        if admitted_at < job['updated_at']:
            raise integrity()
        raw = canonical_bytes(start).decode()
        self.conn.execute('INSERT INTO authoring_numeric_executions(job_id,start_json,start_sha256) VALUES(?,?,?)',
                          (lease.job_id, raw, sha256_bytes(raw.encode())))
        return True

    def mark_started(self, lease: AuthoringLease, started_at: str) -> None:
        record = self.load(self.check_for_job(lease.job_id))
        job = self.jobs.load(lease.job_id)
        start, end = self._execution(record)
        if (not self.jobs.owned(job, lease, allow_cancel=True) or start is None or end is not None
                or start.lease_owner != lease.owner or start.admitted_at is None):
            raise ApiError(409, 'AUTHORING_LEASE_LOST', '数值执行许可已失效。')
        if start.actual_started_at is not None:
            if start.actual_started_at != started_at:
                raise integrity()
            return
        value = start.model_dump(mode='json')
        value['actual_started_at'] = started_at
        raw = canonical_bytes(NumericStart.model_validate(value)).decode()
        self.conn.execute('UPDATE authoring_numeric_executions SET start_json=?,start_sha256=? WHERE job_id=? AND end_json IS NULL',
                          (raw, sha256_bytes(raw.encode()), lease.job_id))

    def finish(self, lease: AuthoringLease, result: NumericCheckResult, stdout: bytes = b'',
               stderr: bytes = b'', output_complete: bool = False,
               manifest_json: bytes = b'') -> NumericCheckView:
        record = self.load(self.check_for_job(lease.job_id))
        job = self.jobs.load(lease.job_id)
        if not self.jobs.owned(job, lease, allow_cancel=True):
            raise ApiError(409, 'AUTHORING_LEASE_LOST', '数值执行许可已失效。')
        if manifest_json and manifest_json != record.runtime_manifest_json.encode('utf-8'):
            raise integrity()
        return self._finish(record, result, stdout, stderr, output_complete)

    def _finish(self, record: NumericRecord, result: NumericCheckResult, stdout: bytes,
                stderr: bytes, output_complete: bool) -> NumericCheckView:
        # Keep result bytes and the Jobs terminal indivisible even when a caller
        # handles a validation/SQL failure and commits its surrounding transaction.
        savepoint = 'numeric_finish_' + uuid4().hex
        self.conn.execute(f'SAVEPOINT {savepoint}')
        try:
            view = self._finish_checked(record, result, stdout, stderr, output_complete)
        except BaseException as error:
            self.conn.execute(f'ROLLBACK TO {savepoint}')
            self.conn.execute(f'RELEASE {savepoint}')
            if isinstance(error, (ValueError, TypeError)):
                raise integrity() from None
            raise
        self.conn.execute(f'RELEASE {savepoint}')
        return view

    def _finish_checked(self, record: NumericRecord, result: NumericCheckResult, stdout: bytes,
                        stderr: bytes, output_complete: bool) -> NumericCheckView:
        assert record.view.job is not None
        job = self.jobs.load(record.view.job.id)
        start, end = self._execution(record)
        if end is not None or job['status'] in {'completed', 'failed', 'cancelled'}:
            raise ApiError(409, 'JOB_TERMINAL', '数值任务已经结束。')
        if result.job_id != job['id'] or result.input_sha256 != job['input_sha256'] or result.operation_sha256 != record.view.operation_sha256:
            raise integrity()
        if start is None:
            if result.started_at is not None:
                raise integrity()
            start = NumericStart(version='numeric-start-v1', workspace_id=self.workspace_id,
                job_id=job['id'], check_id=record.view.id, input_sha256=job['input_sha256'],
                operation_sha256=record.view.operation_sha256, lease_owner=None, job_revision=job['revision'],
                admitted_at=None, actual_started_at=None)
            raw = canonical_bytes(start).decode()
            self.conn.execute('INSERT INTO authoring_numeric_executions(job_id,start_json,start_sha256) VALUES(?,?,?)',
                              (job['id'], raw, sha256_bytes(raw.encode())))
        if result.started_at != start.actual_started_at:
            raise integrity()
        terminal = NumericEnd(version='numeric-end-v1', result=result,
            stdout_base64=base64.b64encode(stdout).decode(), stderr_base64=base64.b64encode(stderr).decode(),
            output_complete=output_complete)
        status = ('completed' if result.outcome in {'passed', 'mismatch', 'evaluation_error'} else
                  'cancelled' if result.outcome == 'cancelled' else 'failed')
        raw = canonical_bytes(terminal).decode()
        changed = self.conn.execute('UPDATE authoring_numeric_executions SET end_json=?,end_sha256=? WHERE job_id=? AND end_json IS NULL',
                                     (raw, sha256_bytes(raw.encode()), job['id']))
        if changed.rowcount != 1:
            raise integrity()
        self.jobs.transition(job, status, result={'numeric_result_sha256':result.result_sha256},
                             cancel=True if status == 'cancelled' else None)
        return self._projection(record, result)

    def cancel_queued(self, record: NumericRecord) -> NumericCheckView:
        assert record.view.job is not None
        job = self.jobs.load(record.view.job.id)
        if job['status'] != 'queued':
            raise integrity()
        result = {'job_id':job['id'],'input_sha256':job['input_sha256'],
                  'operation_sha256':record.view.operation_sha256,'outcome':'cancelled','verdict':'BLOCKED',
                  'started_at':None,'finished_at':utc_now(),'exit_code':None,'assertions':[],
                  'output_sha256':None,'result_sha256':'0'*64}
        result['result_sha256'] = numeric_result_sha256(result)
        return self._finish(record, NumericCheckResult.model_validate(result), b'', b'', False)
