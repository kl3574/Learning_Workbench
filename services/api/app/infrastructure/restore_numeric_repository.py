"""Append-only Restore numeric ledger with independent heads and memberships."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import base64
import sqlite3
from uuid import uuid4
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json
from ..authoring_dto import NumericCheckDecisionAck, NumericCheckResult, numeric_result_sha256
from ..restore_numeric_dto import RestoreNumericMaterialView, RestoreNumericCheckView, RestoreNumericCheckPreviewWrite
from ..import_dto import JobCancelRequest, JobSnapshot
from ..application.errors import ApiError
from ..application.restore_numeric_models import (
    RestoreNumericRecord, RestoreNumericEvent, RestoreNumericCommand, RestoreNumericJobInput,
    bind_material, event_payload, operation_sha256,
)
from .content_restore_repository import RestoreRepository
from .authoring_job_repository import AuthoringJobRepository, AuthoringLease, TERMINAL
from .authoring_numeric_repository import NumericStart, NumericEnd
from .security import historical_session_belongs_to
from .database import utc_now


def integrity():
    return ApiError(409, 'RESTORE_NUMERIC_INTEGRITY_ERROR', '恢复数值材料或原始账本无法完整核验。')


def model(cls, value):
    try:
        return cls.model_validate(value)
    except (ValueError, TypeError, KeyError):
        raise integrity() from None


@dataclass
class RestoreNumericHistory:
    material: RestoreNumericMaterialView | None
    events: list[RestoreNumericEvent] = field(default_factory=list)
    records: dict[str, RestoreNumericRecord] = field(default_factory=dict)
    commands: dict[str, list[RestoreNumericCommand]] = field(default_factory=dict)
    starts: dict[str, NumericStart] = field(default_factory=dict)
    ends: dict[str, NumericEnd] = field(default_factory=dict)

    @property
    def endpoint(self):
        return {'sequence': len(self.events), 'event_sha256': metadata_sha256(self.events[-1]) if self.events else '0' * 64}


class RestoreNumericRepository:
    def __init__(self, conn: sqlite3.Connection, workspace_id: str):
        if not conn.in_transaction:
            raise integrity()
        self.conn, self.workspace_id = conn, workspace_id
        self.jobs = AuthoringJobRepository(conn, workspace_id)

    def _rows(self, table, draft):
        return self.conn.execute(f'SELECT * FROM restore_numeric_{table} WHERE draft_id=? AND workspace_id=?',
                                 (draft, self.workspace_id)).fetchall()

    def history(self, draft: str) -> RestoreNumericHistory:
        original = RestoreRepository(self.conn, self.workspace_id).load(draft)
        materials, heads = self._rows('materials', draft), self._rows('heads', draft)
        rows, members, commands = self._rows('events', draft), self._rows('checks', draft), self._rows('commands', draft)
        if not materials:
            if heads or rows or members or commands or self.jobs.numeric_members('restore-numeric-job-v1', draft):
                raise integrity()
            return RestoreNumericHistory(None)
        if len(materials) != 1 or len(heads) != 1 or not rows:
            raise integrity()
        stored = materials[0]
        material = model(RestoreNumericMaterialView, self._bytes(stored['material_json'], stored['material_sha256']))
        try:
            expected = bind_material(original, material.material)
        except (ApiError, ValueError):
            raise integrity() from None
        if material != expected or original.payload.proposed_block.kind != 'worked_example':
            raise integrity()
        history = RestoreNumericHistory(material)
        rows = sorted(rows, key=lambda row: row['sequence'])
        previews: list[tuple[str, str, str, int, int]] = []
        command_members = []
        for index, row in enumerate(rows, 1):
            event = model(RestoreNumericEvent, self._bytes(row['event_json'], row['event_sha256']))
            if (event.workspace_id != self.workspace_id or event.draft_id != draft or event.sequence != index
                    or row['sequence'] != index or event.check_id != row['check_id']
                    or event.previous_sha256 != history.endpoint['event_sha256']):
                raise integrity()
            payload = event_payload(event)
            identifier = event.check_id
            if event.kind in {'preview', 'decision'}:
                record = model(RestoreNumericRecord, payload)
                view = record.view
                if (record.workspace_id != self.workspace_id or view.id != identifier or view.candidate != material.candidate
                        or view.plan != material.material.plan or view.numeric_material_sha256 != material.numeric_material_sha256
                        or not historical_session_belongs_to(self.conn, self.workspace_id, record.actor_id)):
                    raise integrity()
                if event.kind == 'preview':
                    if identifier in history.records or view.revision != 1 or view.decision != 'pending' or event.recorded_at != view.created_at:
                        raise integrity()
                    previews.append((identifier, self.workspace_id, draft, len(previews) + 1, index))
                    history.commands[identifier] = []
                else:
                    previous = history.records.get(identifier)
                    if (previous is None or previous.view.decision != 'pending' or view.revision != 2
                            or view.decision == 'pending' or not record.decision_actor_id
                            or not historical_session_belongs_to(self.conn, self.workspace_id, record.decision_actor_id)
                            or record.actor_id != previous.actor_id or record.runtime_manifest_json != previous.runtime_manifest_json
                            or view.model_dump(exclude={'revision', 'decision', 'job', 'job_revision'}) != previous.view.model_dump(exclude={'revision', 'decision', 'job', 'job_revision'})
                            or view.decision == 'approve_once' and event.recorded_at >= view.expires_at):
                        raise integrity()
                history.records[identifier] = record
            elif identifier not in history.records:
                raise integrity()
            elif event.kind in {'admission', 'start'}:
                start = model(NumericStart, payload)
                record = history.records[identifier]
                if (record.view.job is None or start.workspace_id != self.workspace_id or start.job_id != record.view.job.id
                        or start.check_id != identifier or start.operation_sha256 != record.view.operation_sha256
                        or identifier in history.ends):
                    raise integrity()
                previous_start = history.starts.get(identifier)
                if event.kind == 'admission':
                    if previous_start is not None or start.actual_started_at is not None:
                        raise integrity()
                elif (previous_start is None or previous_start.actual_started_at is not None or start.actual_started_at is None
                        or start.model_dump(exclude={'actual_started_at'}) != previous_start.model_dump(exclude={'actual_started_at'})):
                    raise integrity()
                history.starts[identifier] = start
            elif event.kind == 'terminal':
                end = model(NumericEnd, payload)
                start = history.starts.get(identifier)
                if (identifier in history.ends or start is None or end.result.job_id != start.job_id
                        or end.result.input_sha256 != start.input_sha256 or end.result.operation_sha256 != start.operation_sha256
                        or end.result.started_at != start.actual_started_at or end.result.finished_at > event.recorded_at):
                    raise integrity()
                history.ends[identifier] = end
            elif event.kind == 'command':
                command = model(RestoreNumericCommand, payload)
                if not historical_session_belongs_to(self.conn, self.workspace_id, command.actor_id) or command.created_at != event.recorded_at:
                    raise integrity()
                history.commands[identifier].append(command)
                command_members.append((self.workspace_id, command.actor_id, command.route, command.key, draft, index))
            history.events.append(event)
        head = heads[0]
        if (head['sequence'] != len(rows) or head['check_count'] != len(previews) or len(previews) > 100
                or head['event_sha256'] != history.endpoint['event_sha256']
                or sorted(tuple(row) for row in members) != sorted(previews)
                or sorted(tuple(row) for row in commands) != sorted(command_members)):
            raise integrity()
        actual_jobs = self.jobs.numeric_members('restore-numeric-job-v1', draft)
        expected_jobs = {r.view.job.id for r in history.records.values() if r.view.job is not None}
        job_members = {row[0] for row in self.conn.execute(
            'SELECT j.job_id FROM restore_numeric_jobs j JOIN restore_numeric_checks c ON j.check_id=c.check_id WHERE c.draft_id=?', (draft,))}
        if actual_jobs != expected_jobs or job_members != expected_jobs:
            raise integrity()
        for identifier, record in history.records.items():
            self._commands(history, identifier)
            if record.view.job is not None:
                self._job(history, identifier)
            elif identifier in history.starts or identifier in history.ends:
                raise integrity()
        return history

    @staticmethod
    def _bytes(raw, digest):
        try:
            value = strict_json(raw)
            if canonical_bytes(value).decode() != raw or sha256_bytes(raw.encode()) != digest:
                raise integrity()
            return value
        except (ValueError, TypeError):
            raise integrity() from None

    def _commands(self, history, identifier):
        record = history.records[identifier]
        previews = [event for event in history.events if event.check_id == identifier and event.kind == 'preview']
        original = model(RestoreNumericRecord, event_payload(previews[0]))
        decisions = [event for event in history.events if event.check_id == identifier and event.kind == 'decision']
        seen = []
        for command in history.commands[identifier]:
            body, ack = strict_json(command.request_json), strict_json(command.ack_json)
            if command.route == f'POST /content/restore-drafts/{record.view.candidate.draft_id}/numeric-checks':
                request = model(RestoreNumericCheckPreviewWrite, body)
                if (request.candidate != record.view.candidate or request.material != history.material.material
                        or model(RestoreNumericCheckView, ack) != original.view or command.actor_id != record.actor_id
                        or command.created_at != original.view.created_at or command.job_revision is not None or command.basis_revision is not None):
                    raise integrity()
                seen.append('preview')
            elif command.route == f'POST /content/restore-numeric-checks/{identifier}/decision':
                request = model(dm.ApprovalDecision, body)
                if (len(decisions) != 1 or request.expected_revision != 1 or request.operation_sha256 != record.view.operation_sha256
                        or request.decision != record.view.decision or command.actor_id != record.decision_actor_id
                        or model(NumericCheckDecisionAck, ack) != self.decision_ack(record)
                        or command.created_at != decisions[0].recorded_at or command.basis_revision != 1
                        or command.job_revision != (1 if record.view.job else None)):
                    raise integrity()
                seen.append('decision')
            elif record.view.job and command.route == f'POST /jobs/{record.view.job.id}/cancel':
                request = model(JobCancelRequest, body)
                result = model(JobSnapshot, ack)
                self.jobs.verify_cancel_ack(record.view.job.id, request.expected_revision, result,
                                            command.basis_revision, command.created_at)
                if command.job_revision != result.revision:
                    raise integrity()
            else:
                raise integrity()
        if seen != (['preview'] if record.view.decision == 'pending' else ['preview', 'decision']):
            raise integrity()

    def _job(self, history, identifier):
        record = history.records[identifier]
        job_id = record.view.job.id
        row = self.jobs.load(job_id)
        membership = self.conn.execute('SELECT * FROM restore_numeric_jobs WHERE job_id=?', (job_id,)).fetchone()
        if membership is None:
            raise integrity()
        value = model(RestoreNumericJobInput, self._bytes(membership['input_json'], membership['input_sha256']))
        if (row['kind'] != 'authoring_numeric_check' or value != self.input_for(record, history.material, job_id)
                or membership['workspace_id'] != self.workspace_id or membership['check_id'] != identifier
                or membership['actor_id'] != record.decision_actor_id or membership['input_json'] != row['input_json']
                or membership['input_sha256'] != row['input_sha256']):
            raise integrity()
        self.jobs.verify_restore_numeric_membership(job_id, record.decision_actor_id, value)
        start, end = history.starts.get(identifier), history.ends.get(identifier)
        if start is not None:
            basis = self.jobs.snapshot(job_id, start.job_revision)
            if (start.input_sha256 != row['input_sha256'] or start.admitted_at is not None and (
                    basis.status != 'running' or start.admitted_at < basis.updated_at)
                    or start.admitted_at is None and end is None):
                raise integrity()
        if (row['status'] in TERMINAL) != (end is not None):
            raise integrity()
        if end is not None:
            expected_status = ('completed' if end.result.outcome in {'passed', 'mismatch', 'evaluation_error'} else
                               'cancelled' if end.result.outcome == 'cancelled' else 'failed')
            if (row['status'] != expected_status or strict_json(row['result_json']) != {'numeric_result_sha256': end.result.result_sha256}
                    or end.result.outcome in {'passed', 'mismatch', 'evaluation_error'} and (
                        start is None or start.actual_started_at is None or end.result.exit_code != 0 or not end.output_complete
                        or [item.id for item in end.result.assertions] != [item.id for item in value.plan.assertions])):
                raise integrity()
            if end.result.outcome in {'passed', 'mismatch', 'evaluation_error'}:
                from .authoring_numeric_runtime import verify_execution_output
                try:
                    verify_execution_output(end.result, base64.b64decode(end.stdout_base64, validate=True))
                except ValueError:
                    raise integrity() from None
        self.project(history, identifier)
        return value

    def draft_for_check(self, identifier):
        row = self.conn.execute('SELECT draft_id FROM restore_numeric_checks WHERE check_id=? AND workspace_id=?',
                                 (identifier, self.workspace_id)).fetchone()
        if row is None:
            if self.conn.execute('SELECT 1 FROM restore_numeric_events WHERE check_id=? AND workspace_id=?', (identifier, self.workspace_id)).fetchone():
                raise integrity()
            raise ApiError(404, 'NUMERIC_CHECK_MISSING', '数值检查不存在或不可访问。')
        return row[0]

    def load(self, identifier):
        history = self.history(self.draft_for_check(identifier))
        if identifier not in history.records:
            raise integrity()
        return history.records[identifier]

    def current(self, identifier):
        history = self.history(self.draft_for_check(identifier))
        return self.project(history, identifier)

    def project(self, history, identifier, observed_at=None, job_revision=None):
        record = history.records[identifier]
        raw = record.view.model_dump(mode='json')
        raw['expired'] = record.view.expires_at <= (observed_at or utc_now())
        if record.view.job is not None:
            job = self.jobs.snapshot(record.view.job.id, job_revision)
            end = history.ends.get(identifier)
            raw.update(job={'id': job.id, 'status': job.status}, job_revision=job.revision,
                       result=end.result if end else None)
        return model(RestoreNumericCheckView, raw)

    def check_for_job(self, identifier):
        row = self.conn.execute('SELECT check_id FROM restore_numeric_jobs WHERE job_id=? AND workspace_id=?',
                                (identifier, self.workspace_id)).fetchone()
        if row is None:
            self.jobs.load(identifier)
            raise integrity()
        return row[0]

    def verified_input(self, history: RestoreNumericHistory, identifier: str) -> RestoreNumericJobInput:
        """Numeric-owner read port for an already fully verified ledger snapshot."""
        return self._job(history, identifier)

    def job_input(self, identifier):
        check_id = self.check_for_job(identifier)
        history = self.history(self.draft_for_check(check_id))
        return self._job(history, check_id)

    @staticmethod
    def input_for(record, material, identifier):
        return RestoreNumericJobInput(version='restore-numeric-job-v1', workspace_id=record.workspace_id,
            job_id=identifier, check_id=record.view.id, candidate=record.view.candidate.model_dump(mode='json'),
            restore_record_sha256=material.restore_record_sha256, numeric_material_sha256=material.numeric_material_sha256,
            plan=record.view.plan, runtime=record.view.runtime, operation_sha256=record.view.operation_sha256)

    def append(self, draft, identifier, kind, payload, now=None):
        head = self._rows('heads', draft)[0]
        raw = canonical_bytes(payload)
        event = RestoreNumericEvent(version='restore-numeric-event-v1', workspace_id=self.workspace_id,
            draft_id=draft, sequence=head['sequence'] + 1, previous_sha256=head['event_sha256'], check_id=identifier,
            kind=kind, payload_json=raw.decode(), payload_sha256=sha256_bytes(raw), recorded_at=now or utc_now())
        digest = metadata_sha256(event)
        self.conn.execute('INSERT INTO restore_numeric_events VALUES(?,?,?,?,?,?)',
            (draft, self.workspace_id, event.sequence, identifier, canonical_bytes(event).decode(), digest))
        changed = self.conn.execute('UPDATE restore_numeric_heads SET sequence=?,check_count=?,event_sha256=? WHERE draft_id=? AND workspace_id=? AND sequence=?',
            (event.sequence, head['check_count'] + int(kind == 'preview'), digest, draft, self.workspace_id, head['sequence']))
        if changed.rowcount != 1:
            raise integrity()
        return event

    def create(self, identity, material, runtime, manifest):
        draft = material.candidate.draft_id
        history = self.history(draft)
        if history.material is not None and history.material != material:
            raise ApiError(409, 'RESTORE_NUMERIC_MATERIAL_CONFLICT', '此恢复候选已有唯一数值材料；修改材料需要新建恢复候选。')
        if len(history.records) >= 100:
            raise ApiError(413, 'NUMERIC_PREVIEW_LIMIT', '此恢复候选的预览次数已达上限。')
        if history.material is None:
            raw = canonical_bytes(material)
            self.conn.execute('INSERT INTO restore_numeric_materials VALUES(?,?,?,?)', (draft, self.workspace_id, raw.decode(), sha256_bytes(raw)))
            self.conn.execute('INSERT INTO restore_numeric_heads VALUES(?,?,0,0,?)', (draft, self.workspace_id, '0' * 64))
        identifier, now = 'restore_numeric_' + uuid4().hex, utc_now()
        expires = (datetime.fromisoformat(now.replace('Z', '+00:00')) + timedelta(minutes=10)).isoformat().replace('+00:00', 'Z')
        view = RestoreNumericCheckView(owner='authoring_restore', id=identifier, revision=1, candidate=material.candidate,
            numeric_material_sha256=material.numeric_material_sha256, plan=material.material.plan, runtime=runtime,
            operation_sha256=operation_sha256(self.workspace_id, identifier, material.candidate, material.numeric_material_sha256, material.material.plan, runtime),
            decision='pending', created_at=now, expires_at=expires, expired=False, job=None, job_revision=None, result=None, warnings=[])
        record = RestoreNumericRecord(version='restore-numeric-check-record-v1', workspace_id=self.workspace_id,
            actor_id=identity.id, decision_actor_id=None, runtime_manifest_json=manifest.decode(), view=view)
        event = self.append(draft, identifier, 'preview', record, now)
        self.conn.execute('INSERT INTO restore_numeric_checks VALUES(?,?,?,?,?)',
                          (identifier, self.workspace_id, draft, len(history.records) + 1, event.sequence))
        return record

    def command(self, identity, route, key, body, ack, identifier, *, job_revision=None, basis_revision=None, recorded_at=None):
        request, result = canonical_bytes(body), canonical_bytes(ack)
        command = RestoreNumericCommand(actor_id=identity.id, route=route, key=key, request_json=request.decode(),
            request_sha256=sha256_bytes(request), ack_json=result.decode(), ack_sha256=sha256_bytes(result),
            job_revision=job_revision, basis_revision=basis_revision, created_at=recorded_at or utc_now())
        draft = self.draft_for_check(identifier)
        event = self.append(draft, identifier, 'command', command, command.created_at)
        self.conn.execute('INSERT INTO restore_numeric_commands VALUES(?,?,?,?,?,?)',
                          (self.workspace_id, identity.id, route, key, draft, event.sequence))

    def replay(self, identity, route, key, body, cls):
        row = self.conn.execute('SELECT draft_id,sequence FROM restore_numeric_commands WHERE workspace_id=? AND actor_id=? AND route=? AND command_key=?',
            (self.workspace_id, identity.id, route, key)).fetchone()
        if row is None:
            return None
        history = self.history(row['draft_id'])
        command = model(RestoreNumericCommand, event_payload(history.events[row['sequence'] - 1]))
        if canonical_bytes(body).decode() != command.request_json:
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原命令键已用于不同的完整命令。')
        return model(cls, strict_json(command.ack_json))

    @staticmethod
    def decision_ack(record):
        return NumericCheckDecisionAck(id=record.view.id, revision=2, decision=record.view.decision,
            operation_sha256=record.view.operation_sha256, job=record.view.job, applied=True)

    def decide(self, record, identity, decision, now):
        history = self.history(record.view.candidate.draft_id)
        if history.records[record.view.id] != record:
            raise integrity()
        raw = record.model_dump(mode='json')
        raw['decision_actor_id'] = identity.id
        raw['view'].update(revision=2, decision=decision)
        if decision == 'approve_once':
            job_id = 'restore_numeric_job_' + uuid4().hex
            raw['view'].update(job={'id': job_id, 'status': 'queued'}, job_revision=1)
            changed = model(RestoreNumericRecord, raw)
            value = self.input_for(changed, history.material, job_id)
            self.jobs.create(job_id, 'authoring_numeric_check', value)
            self.jobs.register_restore_numeric(job_id, identity.id, value)
            data = canonical_bytes(value)
            self.conn.execute('INSERT INTO restore_numeric_jobs VALUES(?,?,?,?,?,?)',
                (job_id, self.workspace_id, record.view.id, identity.id, data.decode(), sha256_bytes(data)))
        changed = model(RestoreNumericRecord, raw)
        self.append(record.view.candidate.draft_id, record.view.id, 'decision', changed, now)
        return changed

    def execution_state(self, job):
        identifier = self.check_for_job(job)
        history = self.history(self.draft_for_check(identifier))
        return history.starts.get(identifier), history.ends.get(identifier)

    def claim(self, job):
        record = self.load(self.check_for_job(job))
        value = self.job_input(job)
        return self.jobs.claim(job), value, record.decision_actor_id

    def begin(self, lease: AuthoringLease, admitted_at):
        identifier = self.check_for_job(lease.job_id)
        history = self.history(self.draft_for_check(identifier))
        row = self.jobs.load(lease.job_id)
        if not self.jobs.owned(row, lease):
            raise ApiError(409, 'AUTHORING_LEASE_LOST', '数值执行许可已失效。')
        if identifier in history.starts:
            return False
        start = NumericStart(version='numeric-start-v1', workspace_id=self.workspace_id, job_id=lease.job_id,
            check_id=identifier, input_sha256=row['input_sha256'], operation_sha256=history.records[identifier].view.operation_sha256,
            lease_owner=lease.owner, job_revision=row['revision'], admitted_at=admitted_at, actual_started_at=None)
        self.append(history.records[identifier].view.candidate.draft_id, identifier, 'admission', start)
        return True

    def mark_started(self, lease, actual):
        identifier = self.check_for_job(lease.job_id)
        history = self.history(self.draft_for_check(identifier))
        start = history.starts.get(identifier)
        if (not self.jobs.owned(self.jobs.load(lease.job_id), lease, allow_cancel=True) or start is None
                or identifier in history.ends or start.lease_owner != lease.owner or start.admitted_at is None):
            raise ApiError(409, 'AUTHORING_LEASE_LOST', '数值执行许可已失效。')
        if start.actual_started_at is not None:
            if start.actual_started_at != actual:
                raise integrity()
            return
        self.append(history.records[identifier].view.candidate.draft_id, identifier, 'start',
                    model(NumericStart, {**start.model_dump(), 'actual_started_at': actual}))

    def finish(self, lease, result, stdout=b'', stderr=b'', output_complete=False, manifest_json=b''):
        identifier = self.check_for_job(lease.job_id)
        history = self.history(self.draft_for_check(identifier))
        row = self.jobs.load(lease.job_id)
        if not self.jobs.owned(row, lease, allow_cancel=True):
            raise ApiError(409, 'AUTHORING_LEASE_LOST', '数值执行许可已失效。')
        if manifest_json and manifest_json.decode() != history.records[identifier].runtime_manifest_json:
            raise integrity()
        return self._finish(history, identifier, result, stdout, stderr, output_complete)

    def _finish(self, history, identifier, result, stdout=b'', stderr=b'', output_complete=False):
        savepoint = 'restore_numeric_finish_' + uuid4().hex
        self.conn.execute(f'SAVEPOINT {savepoint}')
        try:
            record = history.records[identifier]
            row = self.jobs.load(record.view.job.id)
            if row['status'] in TERMINAL or identifier in history.ends:
                raise ApiError(409, 'JOB_TERMINAL', '数值任务已经结束。')
            start = history.starts.get(identifier)
            if start is None:
                start = NumericStart(version='numeric-start-v1', workspace_id=self.workspace_id, job_id=row['id'],
                    check_id=identifier, input_sha256=row['input_sha256'], operation_sha256=record.view.operation_sha256,
                    lease_owner=None, job_revision=row['revision'], admitted_at=None, actual_started_at=None)
                self.append(record.view.candidate.draft_id, identifier, 'admission', start)
            if (result.job_id != row['id'] or result.input_sha256 != row['input_sha256']
                    or result.operation_sha256 != record.view.operation_sha256 or result.started_at != start.actual_started_at):
                raise integrity()
            end = NumericEnd(version='numeric-end-v1', result=result, stdout_base64=base64.b64encode(stdout).decode(),
                             stderr_base64=base64.b64encode(stderr).decode(), output_complete=output_complete)
            self.append(record.view.candidate.draft_id, identifier, 'terminal', end)
            status = ('completed' if result.outcome in {'passed', 'mismatch', 'evaluation_error'} else
                      'cancelled' if result.outcome == 'cancelled' else 'failed')
            self.jobs.transition(row, status, result={'numeric_result_sha256': result.result_sha256}, cancel=True if status == 'cancelled' else None)
            current = self.current(identifier)
        except BaseException:
            self.conn.execute(f'ROLLBACK TO {savepoint}')
            self.conn.execute(f'RELEASE {savepoint}')
            raise
        self.conn.execute(f'RELEASE {savepoint}')
        return current

    def cancel_queued(self, record):
        history = self.history(record.view.candidate.draft_id)
        row = self.jobs.load(record.view.job.id)
        if row['status'] != 'queued':
            raise integrity()
        raw = dict(job_id=row['id'], input_sha256=row['input_sha256'], operation_sha256=record.view.operation_sha256,
            outcome='cancelled', verdict='BLOCKED', started_at=None, finished_at=utc_now(), exit_code=None,
            assertions=[], output_sha256=None)
        raw['result_sha256'] = numeric_result_sha256(raw)
        return self._finish(history, record.view.id, NumericCheckResult.model_validate(raw))
