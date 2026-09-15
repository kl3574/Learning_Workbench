"""Tutor-owned durable conversations, original commands and ordered Run events."""

from dataclasses import dataclass
import re
import sqlite3
from typing import Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json

from ..application.errors import ApiError
from ..application.provider_models import DispatchLease, UsageSnapshot
from ..application.tutor_models import TutorFrozenHistoryItem, TutorJobInput
from ..import_dto import JobCancelRequest, JobSnapshot
from ..tutor_dto import (
    TutorContextSummary, TutorMessage, TutorResultSummary, TutorRunControlView,
    TutorRunCreate, TutorRunView, TutorSSEEvent, TutorThreadCreate, TutorThreadView,
)
from .database import utc_now
from .tutor_job_repository import TERMINAL, TutorJobRepository, TutorLease, integrity

M = TypeVar('M', bound=BaseModel)
events_adapter: TypeAdapter[TutorSSEEvent] = TypeAdapter(TutorSSEEvent)


def digest(value: object) -> str:
    return sha256_bytes(canonical_bytes(value))


def checked(model: type[M], raw: str, expected: str | None = None) -> M:
    try:
        result = model.model_validate(strict_json(raw))
        if canonical_bytes(result).decode() != raw or expected is not None and sha256_bytes(raw.encode()) != expected:
            raise integrity()
        return result
    except (ValueError, TypeError, KeyError):
        raise integrity() from None


@dataclass(frozen=True)
class TutorSourceState:
    input: TutorJobInput
    input_sha256: str
    job_revision: int
    status: str
    cancel_requested: bool
    lease_owner: str | None
    lease_until: str | None
    context_id: str | None
    context_sha256: str | None
    prepared_input_sha256: str | None
    latest_proposal_id: str | None
    consent_id: str | None


class TutorRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection, self.workspace_id = connection, workspace_id
        self.jobs = TutorJobRepository(connection, workspace_id)

    def _write(self) -> None:
        if not self.connection.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '助教状态变更需要有效事务。')

    def create_thread(self, body: TutorThreadCreate) -> TutorThreadView:
        self._write()
        identifier, now = f'thread_{uuid4().hex}', utc_now()
        self.connection.execute('INSERT INTO threads VALUES(?,?,?,?,?)',
            (identifier, self.workspace_id, canonical_bytes(body.scope).decode(), body.title, now))
        self.connection.execute('INSERT INTO tutor_threads VALUES(?,?,?,?,?,?)',
            (identifier, self.workspace_id, canonical_bytes(body.binding).decode(), 1, canonical_bytes(body).decode(), digest(body)))
        return TutorThreadView(id=identifier, scope=body.scope, binding=body.binding, title=body.title, revision=1, created_at=now)

    def thread(self, identifier: str, *, commands: bool = True) -> TutorThreadView:
        row = self.connection.execute('SELECT t.*,s.binding_json,s.revision,s.create_json,s.create_sha256 FROM threads t JOIN tutor_threads s ON s.thread_id=t.id AND s.workspace_id=t.workspace_id WHERE t.id=? AND t.workspace_id=?',
                                      (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, 'THREAD_MISSING', '对话不存在或不可访问。')
        body = checked(TutorThreadCreate, row['create_json'], row['create_sha256'])
        if canonical_bytes(body.scope).decode() != row['scope_json'] or canonical_bytes(body.binding).decode() != row['binding_json'] or body.title != row['title']:
            raise integrity()
        view = TutorThreadView(id=identifier, scope=body.scope, binding=body.binding, title=body.title,
                               revision=row['revision'], created_at=row['created_at'])
        if commands:
            original = self.connection.execute("SELECT * FROM tutor_commands WHERE workspace_id=? AND thread_id=? AND route='POST /threads'", (self.workspace_id, identifier)).fetchall()
            if len(original) != 1 or original[0]['request_json'] != row['create_json'] or original[0]['request_sha256'] != row['create_sha256']:
                raise integrity()
            ack = checked(TutorThreadView, original[0]['ack_json'], original[0]['ack_sha256'])
            if ack != view.model_copy(update={'revision': 1}) or original[0]['run_id'] is not None:
                raise integrity()
            runs = self.connection.execute('SELECT run_id FROM tutor_runs WHERE workspace_id=? AND thread_id=? ORDER BY thread_revision', (self.workspace_id, identifier)).fetchall()
            revision, active = 1, 0
            for entry in runs:
                job, record, _, _ = self._load(entry['run_id'])
                revision += 1
                if record['thread_revision'] != revision:
                    raise integrity()
                revision += int(job['status'] in TERMINAL)
                active += job['status'] not in TERMINAL
            if revision != view.revision or active > 1:
                raise integrity()
        return view

    def thread_ids(self) -> list[str]:
        return [row['id'] for row in self.connection.execute('SELECT t.id FROM threads t JOIN tutor_threads s ON s.thread_id=t.id WHERE t.workspace_id=? ORDER BY t.created_at,t.id', (self.workspace_id,))]

    def messages(self, thread_id: str) -> list[TutorMessage]:
        self.thread(thread_id)
        records = self.connection.execute('SELECT m.*,s.seq,s.message_json,s.message_sha256 FROM messages m JOIN tutor_messages s ON s.message_id=m.id AND s.thread_id=m.thread_id WHERE m.thread_id=? ORDER BY s.seq', (thread_id,)).fetchall()
        if len(records) != self.connection.execute('SELECT COUNT(*) FROM messages WHERE thread_id=?', (thread_id,)).fetchone()[0]:
            raise integrity()
        values = []
        for seq, row in enumerate(records, 1):
            value = checked(TutorMessage, row['message_json'], row['message_sha256'])
            if (row['seq'] != seq or value.seq != seq or value.id != row['id'] or value.run_id != row['run_id']
                    or value.role != row['role'] or value.status != row['status'] or value.content_markdown != row['content_markdown']
                    or value.context_snapshot_id != row['context_snapshot_id'] or canonical_bytes(value.citations).decode() != row['citations_json']
                    or value.created_at != row['created_at']):
                raise integrity()
            job, record, snapshot, result = self._load(value.run_id)
            if record['thread_id'] != thread_id:
                raise integrity()
            original = checked(TutorJobInput, job['input_json'], job['input_sha256'])
            if value.role == 'user':
                if value.content_markdown != original.request.request.message or value.channel is not None or value.status != 'stored' or value.citations or value.context_snapshot_id is not None:
                    raise integrity()
            elif (job['status'] not in TERMINAL or value.status != job['status'] or value.context_snapshot_id != snapshot.context_snapshot_id
                  or value.citations != snapshot.citations or value.content_markdown != (snapshot.answer_markdown if value.channel == 'answer' else result.refusal_markdown)):
                raise integrity()
            values.append(value)
        for entry in self.connection.execute('SELECT run_id FROM tutor_runs WHERE workspace_id=? AND thread_id=?', (self.workspace_id, thread_id)):
            _, _, snapshot, result = self._load(entry['run_id'])
            group = [value for value in values if value.run_id == entry['run_id']]
            if len([value for value in group if value.role == 'user']) != 1:
                raise integrity()
            expected = ([('answer', snapshot.answer_markdown)] if snapshot.answer_markdown else []) + ([('refusal', result.refusal_markdown)] if result.refusal_markdown else [])
            actual = [(value.channel, value.content_markdown) for value in group if value.role == 'assistant']
            if actual != (expected if snapshot.status in TERMINAL else []):
                raise integrity()
        return values

    def history(self, thread_id: str) -> list[TutorFrozenHistoryItem]:
        values = self.messages(thread_id)
        completed = {entry['run_id'] for entry in self.connection.execute("SELECT t.run_id FROM tutor_runs t JOIN jobs j ON j.id=t.run_id WHERE t.workspace_id=? AND t.thread_id=? AND j.status='completed'", (self.workspace_id, thread_id))}
        items = [value for value in values if value.run_id in completed and (value.role == 'user' or value.channel == 'answer')][-4:]
        return [TutorFrozenHistoryItem(message_id=value.id, source_run_id=value.run_id, role=value.role,
            content_markdown=value.content_markdown, content_sha256=sha256_bytes(value.content_markdown.encode())) for value in items]

    def _message(self, thread_id: str, run_id: str, role: Literal['user', 'assistant'], channel: Literal['answer', 'refusal'] | None,
                 status: Literal['stored', 'completed', 'failed', 'cancelled'],
                 text: str, context_id: str | None, citations: list[dm.Citation]) -> None:
        seq = self.connection.execute('SELECT COALESCE(MAX(seq),0)+1 FROM tutor_messages WHERE thread_id=?', (thread_id,)).fetchone()[0]
        value = TutorMessage(id=f'message_{uuid4().hex}', seq=seq, run_id=run_id, role=role, channel=channel,
            status=status, content_markdown=text, context_snapshot_id=context_id, citations=citations, created_at=utc_now())
        self.connection.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)',
            (value.id, thread_id, role, context_id, run_id, text, canonical_bytes(citations).decode(), status, value.created_at))
        self.connection.execute('INSERT INTO tutor_messages VALUES(?,?,?,?,?)',
            (value.id, thread_id, seq, canonical_bytes(value).decode(), digest(value)))

    @staticmethod
    def _integrity(row: dict, snapshot: dm.RunSnapshot) -> str:
        return digest({'record': {key: value for key, value in row.items() if key != 'integrity_sha256'}, 'snapshot': snapshot.model_dump(mode='json')})

    def _store(self, record: dict, snapshot: dm.RunSnapshot, result: TutorResultSummary) -> None:
        self._write()
        record = dict(record)
        record['result_json'] = canonical_bytes(result).decode()
        record['integrity_sha256'] = self._integrity(record, snapshot)
        self.connection.execute('UPDATE runs SET context_snapshot_id=?,snapshot_json=? WHERE id=? AND thread_id=?',
            (snapshot.context_snapshot_id, canonical_bytes(snapshot).decode(), snapshot.id, snapshot.thread_id))
        self.connection.execute('UPDATE tutor_runs SET context_json=?,prepared_input_sha256=?,latest_proposal_id=?,consent_id=?,result_json=?,integrity_sha256=? WHERE run_id=? AND workspace_id=?',
            (record['context_json'], record['prepared_input_sha256'], record['latest_proposal_id'], record['consent_id'],
             record['result_json'], record['integrity_sha256'], record['run_id'], self.workspace_id))

    def _load(self, identifier: str) -> tuple[sqlite3.Row, dict, dm.RunSnapshot, TutorResultSummary]:
        job = self.jobs.load(identifier)
        row = self.connection.execute('SELECT * FROM tutor_runs WHERE run_id=? AND workspace_id=?', (identifier, self.workspace_id)).fetchone()
        base = self.connection.execute('SELECT * FROM runs WHERE id=?', (identifier,)).fetchone()
        if row is None or base is None:
            raise integrity()
        record = dict(row)
        snapshot = checked(dm.RunSnapshot, base['snapshot_json'])
        result = checked(TutorResultSummary, record['result_json'])
        value = checked(TutorJobInput, job['input_json'], job['input_sha256'])
        if (value.run_id != identifier or value.workspace_id != self.workspace_id or value.request.request.workspace_id != self.workspace_id
                or value.request.request.thread_id != record['thread_id'] or snapshot.id != identifier
                or snapshot.thread_id != record['thread_id'] or base['thread_id'] != record['thread_id']
                or snapshot.context_snapshot_id != base['context_snapshot_id'] or snapshot.status != job['status']
                or record['input_sha256'] != job['input_sha256'] or self._integrity(record, snapshot) != record['integrity_sha256']):
            raise integrity()
        # A self-consistent hash of fabricated history is not proof that this
        # owner ever stored those completed messages before accepting this run.
        history_sequences = []
        for item in value.history:
            original_message = self.connection.execute('SELECT * FROM tutor_messages WHERE message_id=? AND thread_id=?',
                (item.message_id, record['thread_id'])).fetchone()
            if original_message is None:
                raise integrity()
            message = checked(TutorMessage, original_message['message_json'], original_message['message_sha256'])
            source_job = self.jobs.load(item.source_run_id)
            if (message.run_id != item.source_run_id or message.role != item.role or message.content_markdown != item.content_markdown
                    or source_job['status'] != 'completed' or source_job['updated_at'] > job['created_at']
                    or message.role == 'assistant' and (message.channel != 'answer' or message.status != 'completed')):
                raise integrity()
            history_sequences.append(message.seq)
        if history_sequences != sorted(set(history_sequences)):
            raise integrity()
        context = checked(TutorContextSummary, record['context_json']) if record['context_json'] is not None else None
        if (context is None) != (snapshot.context_snapshot_id is None) or (context is None) != (record['prepared_input_sha256'] is None):
            raise integrity()
        if context is not None and (context.snapshot.id != snapshot.context_snapshot_id or context.snapshot.request_sha256 != digest(value.request)):
            raise integrity()
        original = self.connection.execute("SELECT * FROM tutor_commands WHERE workspace_id=? AND run_id=? AND route='POST /tutor/runs'", (self.workspace_id, identifier)).fetchall()
        if len(original) != 1 or original[0]['request_json'] != canonical_bytes(value.request).decode() or original[0]['request_sha256'] != digest(value.request) or original[0]['thread_id'] != record['thread_id']:
            raise integrity()
        ack = checked(TutorRunView, original[0]['ack_json'], original[0]['ack_sha256'])
        expected = self._initial_view(identifier, record['thread_id'], record['thread_revision'])
        if ack != expected:
            raise integrity()
        events = self.events_raw(identifier)
        if not events or events[0].type != 'queued' or snapshot.last_seq != len(events):
            raise integrity()
        terminal = [event for event in events if event.type in TERMINAL]
        if len(terminal) != int(snapshot.status in TERMINAL) or terminal and (terminal[0] != events[-1] or terminal[0].type != snapshot.status):
            raise integrity()
        answer = ''.join(event.text for event in events if event.type == 'answer_delta')
        if answer != snapshot.answer_markdown or snapshot.citations:
            raise integrity()
        contexts = [event.context_snapshot_id for event in events if event.type == 'context_ready']
        if contexts != ([snapshot.context_snapshot_id] if context else []):
            raise integrity()
        proposals = [event.approval_id for event in events if event.type == 'approval_required']
        if len(proposals) != len(set(proposals)) or (proposals[-1] if proposals else None) != record['latest_proposal_id']:
            raise integrity()
        if record['consent_id'] is not None and (not proposals or context is None):
            raise integrity()
        usage = UsageSnapshot(input_tokens=None, output_tokens=None)
        for event in events:
            if event.type == 'usage':
                for name in ('input_tokens', 'output_tokens'):
                    new, old = getattr(event, name), getattr(usage, name)
                    if old is not None and (new is None or new < old):
                        raise integrity()
                usage = UsageSnapshot(input_tokens=event.input_tokens, output_tokens=event.output_tokens)
        if usage != result.usage:
            raise integrity()
        if terminal and terminal[0].type == 'failed' and terminal[0].error_code != result.error_code:
            raise integrity()
        if job['status'] in TERMINAL and strict_json(job['result_json']) != {'run_id': identifier, 'last_seq': snapshot.last_seq, 'result_sha256': digest(result)}:
            raise integrity()
        return job, record, snapshot, result

    @staticmethod
    def _empty_result() -> TutorResultSummary:
        return TutorResultSummary(refusal_markdown='', usage=UsageSnapshot(input_tokens=None, output_tokens=None), provider=None, error_code=None)

    @classmethod
    def _initial_view(cls, identifier: str, thread_id: str, revision: int) -> TutorRunView:
        return TutorRunView(run=dm.RunSnapshot(id=identifier, thread_id=thread_id, status='queued', context_snapshot_id=None,
            last_seq=1, answer_markdown='', citations=[], search_status='not_requested'), job_revision=1,
            thread_revision=revision, context=None, latest_proposal_id=None, consent_id=None, result=cls._empty_result())

    def start(self, body: TutorRunCreate, history: list[TutorFrozenHistoryItem]) -> TutorRunView:
        self._write()
        thread = self.thread(body.request.thread_id)
        if any(self.jobs.load(row['run_id'])['status'] not in TERMINAL for row in self.connection.execute('SELECT run_id FROM tutor_runs WHERE workspace_id=? AND thread_id=?', (self.workspace_id, thread.id))):
            raise ApiError(409, 'THREAD_RUN_ACTIVE', '此线程仍有未结束任务，请先结束或明确取消。')
        if body.expected_thread_revision != thread.revision:
            raise ApiError(412, 'REVISION_MISMATCH', '对话已有新轮次，请先读取并比较。')
        identifier = f'run_{uuid4().hex}'
        value = TutorJobInput(version='tutor-job-v1', workspace_id=self.workspace_id, run_id=identifier, request=body, history=history)
        raw = canonical_bytes(value).decode()
        self.jobs.enqueue(identifier, raw)
        view = self._initial_view(identifier, thread.id, thread.revision + 1)
        self.connection.execute('INSERT INTO runs VALUES(?,?,?,?)', (identifier, thread.id, None, canonical_bytes(view.run).decode()))
        record = {'run_id': identifier, 'workspace_id': self.workspace_id, 'thread_id': thread.id,
            'input_sha256': sha256_bytes(raw.encode()), 'thread_revision': thread.revision + 1,
            'context_json': None, 'prepared_input_sha256': None, 'latest_proposal_id': None, 'consent_id': None,
            'result_json': canonical_bytes(view.result).decode()}
        record['integrity_sha256'] = self._integrity(record, view.run)
        self.connection.execute('INSERT INTO tutor_runs VALUES(?,?,?,?,?,?,?,?,?,?,?)', tuple(record.values()))
        self.connection.execute('UPDATE tutor_threads SET revision=revision+1 WHERE thread_id=?', (thread.id,))
        self._event(identifier, 'queued')
        self._message(thread.id, identifier, 'user', None, 'stored', body.request.message, None, [])
        return view

    def view(self, identifier: str) -> TutorRunView:
        job, row, snapshot, result = self._load(identifier)
        thread = self.thread(row['thread_id'])
        return TutorRunView(run=snapshot, job_revision=job['revision'], thread_revision=thread.revision,
            context=checked(TutorContextSummary, row['context_json']) if row['context_json'] is not None else None,
            latest_proposal_id=row['latest_proposal_id'], consent_id=row['consent_id'], result=result)

    def source_state(self, identifier: str) -> TutorSourceState:
        job, row, snapshot, _ = self._load(identifier)
        # Worker/Provider admission must verify the same original conversation
        # as a user read; a valid job hash alone cannot replace missing messages
        # or the original thread creation receipt.
        self.messages(row['thread_id'])
        value = checked(TutorJobInput, job['input_json'], job['input_sha256'])
        context = checked(TutorContextSummary, row['context_json']) if row['context_json'] is not None else None
        return TutorSourceState(value, job['input_sha256'], job['revision'], job['status'], bool(job['cancel_requested']),
            job['lease_owner'], job['lease_until'], snapshot.context_snapshot_id, context.snapshot.snapshot_sha256 if context else None,
            row['prepared_input_sha256'], row['latest_proposal_id'], row['consent_id'])

    def events_raw(self, identifier: str) -> list[TutorSSEEvent]:
        events = []
        for seq, row in enumerate(self.connection.execute('SELECT * FROM tutor_events WHERE run_id=? ORDER BY seq', (identifier,)), 1):
            try:
                event = events_adapter.validate_python(strict_json(row['event_json']))
                if row['seq'] != seq or event.seq != seq or event.run_id != identifier or canonical_bytes(event).decode() != row['event_json'] or digest(event) != row['event_sha256']:
                    raise integrity()
                events.append(event)
            except (ValueError, TypeError):
                raise integrity() from None
        return events

    def _event(self, identifier: str, kind: str, **payload: object) -> int:
        seq = self.connection.execute('SELECT COALESCE(MAX(seq),0)+1 FROM tutor_events WHERE run_id=?', (identifier,)).fetchone()[0]
        event = events_adapter.validate_python({'run_id': identifier, 'seq': seq, 'type': kind, 'occurred_at': utc_now(), **payload})
        self.connection.execute('INSERT INTO tutor_events VALUES(?,?,?,?)', (identifier, seq, canonical_bytes(event).decode(), digest(event)))
        return int(seq)

    def sync_job(self, identifier: str) -> None:
        # Called only adjacent to this owner's verified Jobs transition; the old
        # projection intentionally precedes the new Jobs state in this transaction.
        row = dict(self.connection.execute('SELECT * FROM tutor_runs WHERE run_id=? AND workspace_id=?', (identifier, self.workspace_id)).fetchone())
        base = self.connection.execute('SELECT snapshot_json FROM runs WHERE id=?', (identifier,)).fetchone()
        snapshot = checked(dm.RunSnapshot, base['snapshot_json'])
        job = self.jobs.load(identifier)
        self._store(row, snapshot.model_copy(update={'status': job['status']}), checked(TutorResultSummary, row['result_json']))

    def prepared(self, lease: TutorLease, context: TutorContextSummary, prepared_sha256: str, *, retrieved: bool = False) -> None:
        job, row, snapshot, result = self._load(lease.job_id)
        if not self.jobs.owned(job, lease) or snapshot.context_snapshot_id is not None:
            raise ApiError(409, 'TUTOR_LEASE_LOST', '任务已变化，不能替换原上下文。')
        TypeAdapter(dm.Sha256).validate_python(prepared_sha256)
        row['context_json'], row['prepared_input_sha256'] = canonical_bytes(context).decode(), prepared_sha256
        seq = self._event(lease.job_id, 'context_ready', context_snapshot_id=context.snapshot.id)
        if retrieved:
            seq = self._event(lease.job_id, 'retrieval_completed')
        self.jobs.transition(job, 'awaiting_approval')
        self._store(row, snapshot.model_copy(update={'status': 'awaiting_approval', 'context_snapshot_id': context.snapshot.id, 'last_seq': seq}), result)

    def record_proposal(self, run_id: str, prepared_input_sha256: str, proposal_id: str) -> None:
        job, row, snapshot, result = self._load(run_id)
        if row['prepared_input_sha256'] != prepared_input_sha256 or row['context_json'] is None:
            raise ApiError(409, 'OUTBOUND_SOURCE_CHANGED', '原任务准备材料不匹配。')
        if any(event.type == 'approval_required' and event.approval_id == proposal_id for event in self.events_raw(run_id)):
            return
        if job['status'] != 'awaiting_approval' or job['cancel_requested'] or row['consent_id'] is not None:
            raise ApiError(409, 'OUTBOUND_SOURCE_CHANGED', '当前任务不可批准。')
        seq = self._event(run_id, 'approval_required', approval_id=proposal_id)
        row['latest_proposal_id'] = proposal_id
        self._store(row, snapshot.model_copy(update={'last_seq': seq}), result)

    def bind_authorization(self, run_id: str, prepared_input_sha256: str, consent_id: str) -> None:
        job, row, snapshot, result = self._load(run_id)
        if (row['prepared_input_sha256'] != prepared_input_sha256 or not row['latest_proposal_id']
                or row['consent_id'] is not None or job['status'] != 'awaiting_approval' or job['cancel_requested']):
            raise ApiError(409, 'OUTBOUND_SOURCE_CHANGED', '当前任务与原授权准备不匹配。')
        row['consent_id'] = consent_id
        self.jobs.transition(job, 'queued')
        self._store(row, snapshot.model_copy(update={'status': 'queued'}), result)

    def verify_lease(self, run_id: str, lease: DispatchLease, consent_id: str) -> dm.JobRef:
        value = self.source_state(run_id)
        if (value.status != 'running' or value.cancel_requested or value.consent_id != consent_id
                or value.job_revision != lease.job_revision or value.lease_owner != lease.owner_id
                or value.lease_until is None or value.lease_until <= utc_now() or lease.expires_at > value.lease_until):
            raise ApiError(409, 'OUTBOUND_SOURCE_CHANGED', '当前任务租约、授权或取消状态已改变。')
        return dm.JobRef(id=run_id, status='running')

    def delta(self, lease: TutorLease, text: str) -> None:
        job, row, snapshot, result = self._load(lease.job_id)
        if not self.jobs.owned(job, lease):
            raise ApiError(409, 'TUTOR_LEASE_LOST', '任务已变化，停止写入回答。')
        seq = self._event(lease.job_id, 'answer_delta', text=text)
        self._store(row, snapshot.model_copy(update={'answer_markdown': snapshot.answer_markdown + text, 'last_seq': seq}), result)

    def usage(self, lease: TutorLease, usage: UsageSnapshot) -> None:
        job, row, snapshot, result = self._load(lease.job_id)
        if not self.jobs.owned(job, lease, allow_cancel=True):
            raise ApiError(409, 'TUTOR_LEASE_LOST', '任务已变化，停止写入计量。')
        for name in ('input_tokens', 'output_tokens'):
            old, new = getattr(result.usage, name), getattr(usage, name)
            if old is not None and (new is None or new < old):
                raise integrity()
        if usage == result.usage:
            return
        seq = self._event(lease.job_id, 'usage', input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)
        self._store(row, snapshot.model_copy(update={'last_seq': seq}), result.model_copy(update={'usage': usage}))

    def finish(self, run_id: str, status: Literal['completed', 'failed', 'cancelled'], result: TutorResultSummary, answer: str, *, lease: TutorLease | None = None) -> None:
        job, row, snapshot, old = self._load(run_id)
        if job['status'] in TERMINAL:
            return
        if lease is not None and not self.jobs.owned(job, lease, allow_cancel=True):
            raise ApiError(409, 'TUTOR_LEASE_LOST', '任务租约已失效，不能提交终态。')
        if not answer.startswith(snapshot.answer_markdown):
            raise integrity()
        seq = snapshot.last_seq
        if answer != snapshot.answer_markdown:
            seq = self._event(run_id, 'answer_delta', text=answer[len(snapshot.answer_markdown):])
        for name in ('input_tokens', 'output_tokens'):
            previous, current = getattr(old.usage, name), getattr(result.usage, name)
            if previous is not None and (current is None or current < previous):
                raise integrity()
        if result.usage != old.usage:
            seq = self._event(run_id, 'usage', input_tokens=result.usage.input_tokens, output_tokens=result.usage.output_tokens)
        seq = self._event(run_id, status, **({'error_code': result.error_code} if status == 'failed' else {}))
        final = snapshot.model_copy(update={'status': status, 'answer_markdown': answer, 'last_seq': seq})
        self.jobs.transition(job, status, result={'run_id': run_id, 'last_seq': seq, 'result_sha256': digest(result)}, cancel=status == 'cancelled' or bool(job['cancel_requested']))
        channels: tuple[tuple[Literal['answer', 'refusal'], str], ...] = (('answer', answer), ('refusal', result.refusal_markdown))
        for channel, text in channels:
            if text:
                self._message(snapshot.thread_id, run_id, 'assistant', channel, status, text, snapshot.context_snapshot_id, [])
        self.connection.execute('UPDATE tutor_threads SET revision=revision+1 WHERE thread_id=?', (snapshot.thread_id,))
        self._store(row, final, result)

    def control(self, identifier: str) -> TutorRunControlView:
        job, _, _, _ = self._load(identifier)
        return TutorRunControlView(id=identifier, status=job['status'], job_revision=job['revision'], cancel_requested=bool(job['cancel_requested']))

    def cancel(self, identifier: str, expected: int) -> TutorRunControlView:
        job, _, snapshot, result = self._load(identifier)
        if job['status'] in TERMINAL:
            return self.control(identifier)
        if expected != job['revision']:
            raise ApiError(412, 'REVISION_MISMATCH', '任务已变化，请重新读取后明确取消。')
        if job['status'] == 'running':
            if not job['cancel_requested']:
                self.jobs.transition(job, 'running', cancel=True, retain_lease=True)
                self.sync_job(identifier)
        else:
            self.finish(identifier, 'cancelled', result, snapshot.answer_markdown)
        return self.control(identifier)

    def replay(self, route: str, key: str, body: BaseModel, model: type[M]) -> M | None:
        if re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key) is None:
            raise ApiError(400, 'IDEMPOTENCY_KEY_REQUIRED', '需要单个有效的原命令幂等键。')
        row = self.connection.execute('SELECT * FROM tutor_commands WHERE workspace_id=? AND route=? AND key=?', (self.workspace_id, route, key)).fetchone()
        if row is None:
            return None
        if sha256_bytes(row['request_json'].encode()) != row['request_sha256'] or canonical_bytes(strict_json(row['request_json'])).decode() != row['request_json']:
            raise integrity()
        # An original ACK cannot stand in for the conversation whose side
        # effects it acknowledges. Apply the same owned-history admission as
        # reads and worker preparation before replay or payload comparison.
        self.messages(row['thread_id'])
        if canonical_bytes(body).decode() != row['request_json']:
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '同一幂等键不能用于不同请求。')
        ack = checked(model, row['ack_json'], row['ack_sha256'])
        if row['run_id'] is not None:
            job, _, _, _ = self._load(row['run_id'])
            if isinstance(ack, JobSnapshot):
                if route != f"POST /jobs/{row['run_id']}/cancel":
                    raise integrity()
                original = checked(JobCancelRequest, row['request_json'], row['request_sha256'])
                self.jobs.verify_cancel_ack(row['run_id'], original.expected_revision, ack, row['created_at'])
            elif isinstance(ack, TutorRunControlView):
                event = self.connection.execute('SELECT payload_json FROM job_events WHERE job_id=? AND seq=?', (row['run_id'], ack.job_revision)).fetchone()
                if (ack.id != row['run_id'] or event is None or strict_json(event['payload_json']) != {
                        'revision': ack.job_revision, 'status': ack.status, 'cancel_requested': ack.cancel_requested}):
                    raise integrity()
            elif not isinstance(ack, TutorRunView) or ack.run.id != job['id']:
                raise integrity()
        return ack

    def record_command(self, route: str, key: str, body: BaseModel, ack: BaseModel, thread_id: str, run_id: str | None = None) -> None:
        self._write()
        self.connection.execute('INSERT INTO tutor_commands VALUES(?,?,?,?,?,?,?,?,?,?)',
            (self.workspace_id, route, key, thread_id, run_id, canonical_bytes(body).decode(), digest(body), canonical_bytes(ack).decode(), digest(ack), utc_now()))
