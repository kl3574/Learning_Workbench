"""Quality-owned persistence in the caller transaction; no authority from JSON.

Jobs mutations remain with Jobs. Each write's savepoint protects this method's
Quality changes; the caller must cover earlier Jobs writes in its outer operation.
"""
from contextlib import contextmanager
import sqlite3
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel, TypeAdapter
from pydantic_core import PydanticSerializationError
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json
from ..application.errors import ApiError
from ..application.review_history_models import (
    ReviewBinding, ReviewCommand, ReviewCreateCommand, ReviewCancelCommand, ReviewCancelAck,
    ReviewDecisionCommand, ReviewArtifactBinding, ReviewMachineRecord, ReviewDecisionRecord,
    ReviewRecord, ReviewHistory, StoredReviewReceipt, instant, machine_job_result,
)
from ..application.review_checks import review_structure
from ..application.review_material_models import ImportReviewMaterial, EditReviewMaterial
from ..application.review_models import ReviewJobInput
from ..import_dto import JobSnapshot
from .draft_candidate_repository import DraftCandidateRepository
from .review_job_repository import ReviewJobRepository

M = TypeVar('M', bound=BaseModel)
COMMAND: TypeAdapter[ReviewCommand] = TypeAdapter(ReviewCommand)
RECORD: TypeAdapter[ReviewRecord] = TypeAdapter(ReviewRecord)


def integrity() -> ApiError:
    return ApiError(409, 'REVIEW_INTEGRITY_ERROR', '审核持久历史未通过完整性校验。')


def checked(raw: str, digest: str) -> dict:
    try:
        value = strict_json(raw)
        if not isinstance(value, dict) or canonical_bytes(value).decode() != raw or sha256_bytes(raw.encode()) != digest:
            raise integrity()
        return value
    except (ValueError, TypeError, UnicodeError):
        raise integrity() from None


def validated(model: type[M], value: object) -> M:
    try:
        return model.model_validate(value.model_dump(mode='python', warnings='error') if isinstance(value, BaseModel) else value)
    except (ValueError, TypeError, AttributeError, PydanticSerializationError):
        raise integrity() from None


class ReviewRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.conn, self.workspace_id = connection, workspace_id
        self.jobs = ReviewJobRepository(connection, workspace_id)

    def _transaction(self) -> None:
        if not self.conn.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '审核持久操作需要当前事务。')

    @contextmanager
    def _write(self):
        self._transaction()
        point = 'quality_write_' + uuid4().hex
        self.conn.execute(f'SAVEPOINT {point}')
        try:
            yield
        except BaseException as error:
            self.conn.execute(f'ROLLBACK TO {point}')
            self.conn.execute(f'RELEASE {point}')
            if isinstance(error, sqlite3.Error):
                raise integrity() from None
            raise
        self.conn.execute(f'RELEASE {point}')

    def _binding(self, identifier: str) -> ReviewBinding:
        self._transaction()
        row = self.conn.execute('SELECT * FROM review_jobs WHERE review_id=? AND workspace_id=?',
                                (identifier, self.workspace_id)).fetchone()
        if row is None:
            if self.conn.execute('SELECT 1 FROM reviews WHERE id=? AND workspace_id=?',
                                 (identifier, self.workspace_id)).fetchone():
                raise ApiError(409, 'REVIEW_LEGACY_HISTORY_UNVERIFIABLE', '原审核记录保留，但缺少可认证的审核历史。')
            raise ApiError(404, 'REVIEW_MISSING', '审核不存在或不可访问。')
        value = validated(ReviewJobInput, checked(row['input_json'], row['input_sha256']))
        job = self.jobs.load(identifier)
        resolved = DraftCandidateRepository(self.conn).lookup(self.workspace_id, value.candidate.draft_id,
                                                              value.candidate.draft_revision)
        if (value.review_id != identifier or value.workspace_id != self.workspace_id
                or row['job_kind'] != 'draft_review' or row['owner'] != resolved.owner
                or row['source_kind'] != resolved.source_kind or value.source_kind != resolved.source_kind
                or value.candidate != resolved.candidate or row['creator_actor_id'] != value.creator_session_id
                or row['created_at'] != value.created_at or canonical_bytes(value).decode() != row['input_json']
                or row['input_json'] != job['input_json'] or row['input_sha256'] != job['input_sha256']
                or any(row[key] != getattr(value.candidate, key) for key in
                       ('draft_id', 'draft_revision', 'entity', 'candidate_sha256'))
                or instant(value.created_at) > instant(job['created_at'])):
            raise integrity()
        return ReviewBinding(input=value, owner=resolved.owner,
                             job=validated(ReviewCancelAck, self.jobs.snapshot(identifier)))

    def binding(self, identifier: str) -> ReviewBinding:
        """Internal binding read, including queued/cancelled jobs with no receipt."""
        return self.load(identifier).binding

    def _command(self, row: sqlite3.Row) -> ReviewCommand:
        try:
            value = COMMAND.validate_python({key: row[key] for key in
                ('workspace_id', 'actor_id', 'route', 'command_key', 'review_id', 'command_kind',
                 'basis_revision', 'resulting_revision', 'recorded_at')} | {
                'request': checked(row['request_json'], row['request_sha256']),
                'ack': checked(row['ack_json'], row['ack_sha256'])})
            if (canonical_bytes(value.request).decode() != row['request_json']
                    or canonical_bytes(value.ack).decode() != row['ack_json']):
                raise integrity()
            return value
        except (ValueError, TypeError, KeyError):
            raise integrity() from None

    def _verify_command(self, command: ReviewCommand, binding: ReviewBinding,
                        records: list[ReviewRecord] | None = None) -> None:
        value = binding.input
        if (command.workspace_id != self.workspace_id or command.review_id != value.review_id
                or instant(command.recorded_at) < instant(value.created_at)):
            raise integrity()
        if isinstance(command, ReviewCreateCommand):
            original = self.jobs.snapshot(value.review_id, 1)
            if (command.actor_id != value.creator_session_id or command.request != value.request
                    or command.route != f'POST /drafts/{value.candidate.draft_id}/review'
                    or original.status != command.ack.status
                    or instant(command.recorded_at) < instant(original.updated_at)
                    or any(instant(event.occurred_at) < instant(command.recorded_at)
                           for event in self.jobs.event_prefix(value.review_id, binding.job.revision)[1:])):
                raise integrity()
        elif isinstance(command, ReviewCancelCommand):
            self.jobs.verify_cancel_ack(value.review_id, command.request.expected_revision,
                validated(JobSnapshot, command.ack), command.basis_revision, command.recorded_at)
        else:
            matches = [record for record in records or [] if isinstance(record, ReviewDecisionRecord)
                       and record.receipt.revision == command.resulting_revision]
            if len(matches) != 1:
                raise integrity()
            record = matches[0]
            if (command.actor_id != record.actor_session_id or command.request != record.request
                    or command.ack != record.receipt or command.recorded_at != record.decided_at):
                raise integrity()

    def _commands(self, binding: ReviewBinding, records: list[ReviewRecord] | None = None) -> list[ReviewCommand]:
        rows = self.conn.execute('SELECT * FROM review_commands WHERE review_id=? ORDER BY rowid',
                                 (binding.input.review_id,)).fetchall()
        commands = [self._command(row) for row in rows]
        for command in commands:
            self._verify_command(command, binding, records)
        decisions = [command.resulting_revision for command in commands if isinstance(command, ReviewDecisionCommand)]
        if (sum(isinstance(command, ReviewCreateCommand) for command in commands) != 1
                or sorted(decisions) != list(range(2, len(records or []) + 1))):
            raise integrity()
        return commands

    def _insert_command(self, command: ReviewCommand) -> None:
        request, ack = canonical_bytes(command.request).decode(), canonical_bytes(command.ack).decode()
        self.conn.execute('INSERT INTO review_commands(workspace_id,actor_id,route,command_key,command_kind,'
            'review_id,request_json,request_sha256,ack_json,ack_sha256,basis_revision,resulting_revision,recorded_at) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (self.workspace_id, command.actor_id, command.route,
            command.command_key, command.command_kind, command.review_id, request, sha256_bytes(request.encode()),
            ack, sha256_bytes(ack.encode()), command.basis_revision, command.resulting_revision, command.recorded_at))

    def bind(self, value: ReviewJobInput, command: ReviewCreateCommand) -> None:
        with self._write():
            value, command = validated(ReviewJobInput, value), validated(ReviewCreateCommand, command)
            row = self.jobs.load(value.review_id)
            if (value.workspace_id != self.workspace_id or row['revision'] != 1 or row['status'] != 'queued'
                    or canonical_bytes(value).decode() != row['input_json']
                    or self.conn.execute('SELECT 1 FROM reviews WHERE id=?', (value.review_id,)).fetchone()):
                raise integrity()
            candidate = value.candidate
            owner = 'import' if value.source_kind == 'import' else 'authoring'
            raw = canonical_bytes(value).decode()
            self.conn.execute('INSERT INTO review_jobs(review_id,workspace_id,owner,source_kind,draft_id,'
                'draft_revision,entity,candidate_sha256,creator_actor_id,input_json,input_sha256,created_at) '
                'VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', (value.review_id, self.workspace_id, owner, value.source_kind,
                candidate.draft_id, candidate.draft_revision, candidate.entity, candidate.candidate_sha256,
                value.creator_session_id, raw, sha256_bytes(raw.encode()), value.created_at))
            binding = self._binding(value.review_id)
            self._verify_command(command, binding)
            self._insert_command(command)
            self.binding(value.review_id)

    def record_cancel(self, command: ReviewCancelCommand) -> None:
        with self._write():
            command = validated(ReviewCancelCommand, command)
            binding = self.binding(command.review_id)
            self._verify_command(command, binding)
            self._insert_command(command)
            self.binding(command.review_id)

    def replay(self, actor_id: str, route: str, key: str, body: BaseModel) -> ReviewCommand | None:
        self._transaction()
        row = self.conn.execute('SELECT * FROM review_commands WHERE workspace_id=? AND actor_id=? '
                                'AND route=? AND command_key=?', (self.workspace_id, actor_id, route, key)).fetchone()
        if row is None:
            return None
        self.binding(row['review_id'])
        command = self._command(row)
        try:
            body = type(command.request).model_validate(body.model_dump(mode='python', warnings='error'))
        except (ValueError, TypeError, AttributeError, PydanticSerializationError):
            raise integrity() from None
        if canonical_bytes(body) != canonical_bytes(command.request):
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原命令键已用于不同的完整命令。')
        return command

    def _verify_artifact(self, value: ReviewArtifactBinding) -> None:
        row = self.conn.execute('SELECT a.*,b.size AS blob_size FROM artifacts a JOIN content_blobs b '
            'ON a.blob_sha256=b.sha256 WHERE a.id=? AND a.workspace_id=?',
            (value.artifact.artifact_id, self.workspace_id)).fetchone()
        if (row is None or value.workspace_id != self.workspace_id or row['job_id'] != value.source_job_id
                or row['profile'] != value.profile or row['blob_sha256'] != value.artifact.sha256
                or row['blob_size'] != value.artifact.size
                or sha256_bytes(row['manifest_json'].encode()) != value.manifest_sha256):
            raise integrity()
        # This is a durable byte/row association, not physical file validation,
        # profile/owner authentication or permission to download the artifact.

    def _verify_machine(self, record: ReviewMachineRecord, binding: ReviewBinding) -> None:
        value = binding.input
        row = self.jobs.load(value.review_id)
        if (record.workspace_id != self.workspace_id or record.review_id != value.review_id
                or record.input_sha256 != metadata_sha256(value) or record.material.candidate != value.candidate
                or record.material.owner != binding.owner or record.material.source_kind != value.source_kind
                or record.receipt.created_at != value.created_at
                or record.structural_report != review_structure(record.material, requested='structure' in value.request.checks)
                or row['status'] != 'completed' or row['revision'] != record.job_revision or row['cancel_requested']
                or row['result_json'] != canonical_bytes(machine_job_result(record)).decode()
                or instant(record.checked_at) < instant(row['created_at'])
                or instant(record.checked_at) > instant(row['updated_at'])):
            raise integrity()
        payload = record.material.payload
        if not isinstance(payload, (ImportReviewMaterial, EditReviewMaterial)):
            if (record.numeric.candidate_record_sha256 != record.material.owner_record_sha256
                    or record.numeric.source_job_id != payload.record.source_job_id
                    or record.numeric.provider_receipt_id != payload.record.provider_receipt_id):
                raise integrity()
        self._verify_artifact(record.report)

    def _verify_decision(self, record: ReviewDecisionRecord, machine: ReviewMachineRecord,
                         previous: ReviewRecord, binding: ReviewBinding) -> None:
        if (record.workspace_id != self.workspace_id or record.review_id != binding.input.review_id
                or record.candidate != binding.input.candidate
                or record.previous_receipt_sha256 != metadata_sha256(previous.receipt)
                or record.machine_record_sha256 != metadata_sha256(machine)
                or record.material_descriptor_sha256 != machine.material.descriptor_sha256
                or record.receipt.revision != previous.receipt.revision + 1
                or record.receipt.created_at != machine.receipt.created_at
                or record.receipt.structural != machine.receipt.structural
                or instant(record.decided_at) < instant(previous.checked_at if isinstance(previous, ReviewMachineRecord)
                                                         else previous.decided_at)
                or record.receipt.evidence_paths != [machine.report.artifact.download_path,
                                                    *[item.artifact.download_path for item in record.evidence]]
                or machine.report.artifact.artifact_id in record.request.evidence_artifact_ids):
            raise integrity()
        for value in record.evidence:
            self._verify_artifact(value)

    @staticmethod
    def _artifacts(record: ReviewRecord, machine: ReviewMachineRecord) -> list[ReviewArtifactBinding]:
        return [machine.report] + (record.evidence if isinstance(record, ReviewDecisionRecord) else [])

    def _records(self, binding: ReviewBinding) -> list[ReviewRecord]:
        identifier = binding.input.review_id
        rows = self.conn.execute('SELECT * FROM review_revisions WHERE review_id=? ORDER BY revision',
                                 (identifier,)).fetchall()
        projection = self.conn.execute('SELECT * FROM reviews WHERE id=?', (identifier,)).fetchone()
        if not rows:
            if projection is not None or binding.job.status == 'completed' or self.conn.execute(
                    'SELECT 1 FROM review_artifact_bindings WHERE review_id=?', (identifier,)).fetchone():
                raise integrity()
            return []
        records: list[ReviewRecord] = []
        for revision, row in enumerate(rows, 1):
            try:
                record = RECORD.validate_python(checked(row['record_json'], row['record_sha256']))
                receipt = validated(StoredReviewReceipt, checked(row['receipt_json'], row['receipt_sha256']))
            except (ValueError, TypeError, KeyError):
                raise integrity() from None
            machine = record if isinstance(record, ReviewMachineRecord) else records[0] if records else None
            if not isinstance(machine, ReviewMachineRecord):
                raise integrity()
            first = isinstance(record, ReviewMachineRecord)
            if (row['revision'] != revision or record.receipt.revision != revision or record.receipt != receipt
                    or canonical_bytes(record).decode() != row['record_json']
                    or canonical_bytes(receipt).decode() != row['receipt_json']
                    or first != (revision == 1) or row['record_kind'] != ('machine' if first else 'human_decision')
                    or row['recorded_at'] != (record.checked_at if isinstance(record, ReviewMachineRecord) else record.decided_at)
                    or row['previous_revision'] != (None if first else revision - 1)
                    or row['previous_receipt_sha256'] != (None if first else metadata_sha256(records[-1].receipt))):
                raise integrity()
            if isinstance(record, ReviewMachineRecord):
                self._verify_machine(record, binding)
            else:
                self._verify_decision(record, machine, records[-1], binding)
            bindings = self.conn.execute('SELECT * FROM review_artifact_bindings WHERE review_id=? '
                'AND review_revision=? ORDER BY ordinal', (identifier, revision)).fetchall()
            expected = self._artifacts(record, machine)
            if len(bindings) != len(expected):
                raise integrity()
            for ordinal, (stored, item) in enumerate(zip(bindings, expected, strict=True)):
                parsed = validated(ReviewArtifactBinding, checked(stored['binding_json'], stored['binding_sha256']))
                if (parsed != item or canonical_bytes(parsed).decode() != stored['binding_json']
                        or stored['ordinal'] != ordinal or stored['workspace_id'] != self.workspace_id
                        or stored['artifact_id'] != item.artifact.artifact_id or stored['artifact_owner'] != item.artifact_owner
                        or stored['artifact_sha256'] != item.artifact.sha256 or stored['manifest_sha256'] != item.manifest_sha256):
                    raise integrity()
            records.append(record)
        last = records[-1].receipt
        actor = records[-1].actor_session_id if isinstance(records[-1], ReviewDecisionRecord) else None
        if (projection is None or projection['workspace_id'] != self.workspace_id or projection['owner'] != binding.owner
                or projection['revision'] != last.revision or projection['receipt_json'] != canonical_bytes(last).decode()
                or projection['created_at'] != last.created_at
                or projection['reviewer_session_id'] not in (None, actor)
                or any(projection[key] != getattr(last.candidate, key) for key in
                       ('draft_id', 'draft_revision', 'entity', 'candidate_sha256'))):
            raise integrity()
        if self.conn.execute('SELECT 1 FROM review_artifact_bindings WHERE review_id=? AND review_revision>?',
                             (identifier, len(records))).fetchone():
            raise integrity()
        return records

    def load(self, identifier: str) -> ReviewHistory:
        binding = self._binding(identifier)
        records = self._records(binding)
        self._commands(binding, records)
        return ReviewHistory(state='ready' if records else 'pending', binding=binding, records=records,
                             receipt=records[-1].receipt if records else None)

    def _insert_revision(self, record: ReviewRecord, machine: ReviewMachineRecord) -> None:
        first = isinstance(record, ReviewMachineRecord)
        previous = None if isinstance(record, ReviewMachineRecord) else record.previous_receipt_sha256
        recorded_at = record.checked_at if isinstance(record, ReviewMachineRecord) else record.decided_at
        receipt, raw = canonical_bytes(record.receipt).decode(), canonical_bytes(record).decode()
        self.conn.execute('INSERT INTO review_revisions(review_id,revision,receipt_json,receipt_sha256,'
            'record_kind,record_json,record_sha256,previous_receipt_sha256,recorded_at) VALUES(?,?,?,?,?,?,?,?,?)',
            (record.review_id, record.receipt.revision, receipt, sha256_bytes(receipt.encode()),
             'machine' if first else 'human_decision', raw, sha256_bytes(raw.encode()),
             previous, recorded_at))
        for ordinal, value in enumerate(self._artifacts(record, machine)):
            raw = canonical_bytes(value).decode()
            self.conn.execute('INSERT INTO review_artifact_bindings(review_id,workspace_id,review_revision,ordinal,'
                'artifact_id,artifact_owner,artifact_sha256,manifest_sha256,binding_json,binding_sha256) '
                'VALUES(?,?,?,?,?,?,?,?,?,?)', (record.review_id, self.workspace_id, record.receipt.revision, ordinal,
                value.artifact.artifact_id, value.artifact_owner, value.artifact.sha256, value.manifest_sha256,
                raw, sha256_bytes(raw.encode())))

    def append_machine(self, record: ReviewMachineRecord) -> None:
        with self._write():
            record = validated(ReviewMachineRecord, record)
            binding = self._binding(record.review_id)
            self._commands(binding)
            if self.conn.execute('SELECT 1 FROM reviews WHERE id=?', (record.review_id,)).fetchone() or self.conn.execute(
                    'SELECT 1 FROM review_revisions WHERE review_id=?', (record.review_id,)).fetchone():
                raise integrity()
            self._verify_machine(record, binding)
            receipt = record.receipt
            self.conn.execute('INSERT INTO reviews(id,draft_id,draft_revision,candidate_sha256,revision,receipt_json,'
                'reviewer_session_id,created_at,workspace_id,owner,entity) VALUES(?,?,?,?,?,?,NULL,?,?,?,?)',
                (record.review_id, receipt.candidate.draft_id, receipt.candidate.draft_revision,
                 receipt.candidate.candidate_sha256, 1, canonical_bytes(receipt).decode(), receipt.created_at,
                 self.workspace_id, binding.owner, receipt.candidate.entity))
            self._insert_revision(record, record)
            self.load(record.review_id)

    def append_decision(self, record: ReviewDecisionRecord, command: ReviewDecisionCommand) -> None:
        with self._write():
            record, command = validated(ReviewDecisionRecord, record), validated(ReviewDecisionCommand, command)
            history = self.load(record.review_id)
            if not history.records or not isinstance(history.records[0], ReviewMachineRecord) or history.receipt is None:
                raise ApiError(409, 'REVIEW_NOT_READY', '审核尚无机器回执。')
            if record.request.expected_revision != history.receipt.revision:
                raise ApiError(412, 'REVIEW_REVISION_MISMATCH', '审核回执已更新，请重新读取。')
            machine = history.records[0]
            self._verify_decision(record, machine, history.records[-1], history.binding)
            self._verify_command(command, history.binding, [*history.records, record])
            changed = self.conn.execute('UPDATE reviews SET revision=?,receipt_json=?,reviewer_session_id=? '
                'WHERE id=? AND workspace_id=? AND revision=? AND receipt_json=?',
                (record.receipt.revision, canonical_bytes(record.receipt).decode(), record.actor_session_id,
                 record.review_id, self.workspace_id, history.receipt.revision, canonical_bytes(history.receipt).decode()))
            if changed.rowcount != 1:
                raise ApiError(412, 'REVIEW_REVISION_MISMATCH', '审核回执已更新，请重新读取。')
            self._insert_revision(record, machine)
            self._insert_command(command)
            self.load(record.review_id)
