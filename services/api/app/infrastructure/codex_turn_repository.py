"""Codex-owned append-only control chain and actual local Run projections."""
from dataclasses import dataclass, field
import sqlite3

from pydantic import BaseModel
from packages.contracts import domain_models as dm
from packages.contracts.canonical import strict_json
from ..application.codex_bootstrap_models import BootstrapSnapshot
from ..application.codex_turn_context import CodexTurnContext, damaged
from ..application.codex_turn_models import (
    SessionAnchor, EventEnvelope, TurnPrepared, TurnProviderBound, TurnStarted, TurnLifecycle, TurnCancelRequested, CancelCommand, preparation_digest,
)
from ..application.codex_turn_execution_models import ControlEventEnvelope, RunnableTurnPrepared
from ..application.codex_approval_models import ApprovalControlEnvelope, TurnApprovalBound
from ..application.codex_operation_models import OperationControlEnvelope, TurnOperationBound
from ..application.errors import ApiError
from ..application.providers import retained_provider_configuration
from ..codex_turn_dto import CodexTurnControlView, CodexConsentControl
from ..serialization import canonical_json, content_sha256
from .codex_turn_jobs import CodexTurnJobs
from .security import SessionIdentity, historical_session_belongs_to


@dataclass
class CheckedTurn:
    prepared: TurnPrepared | RunnableTurnPrepared
    control: CodexTurnControlView
    sequence: int
    provider_bindings: list[TurnProviderBound] = field(default_factory=list)
    start: TurnStarted | None = None
    lifecycle: list[TurnLifecycle] = field(default_factory=list)
    approval_bindings: list[TurnApprovalBound | TurnOperationBound] = field(default_factory=list)


@dataclass
class CheckedSession:
    anchor: SessionAnchor
    revision: int
    active_turn_id: str | None
    envelopes: list[EventEnvelope | ControlEventEnvelope | ApprovalControlEnvelope | OperationControlEnvelope] = field(default_factory=list)
    turns: dict[str, CheckedTurn] = field(default_factory=dict)


def decode(model, raw: str):
    try:
        result = model.model_validate(strict_json(raw))
        if canonical_json(result) != raw:
            raise damaged()
        return result
    except (ValueError, TypeError, KeyError, RecursionError):
        raise damaged() from None


def turn_control(prepared: TurnPrepared | RunnableTurnPrepared, finished: str | None = None) -> CodexTurnControlView:
    view = prepared.command.ack
    terminal = finished is not None
    return CodexTurnControlView(id=view.turn_id, session_id=view.session_id,
        actor_session_id=view.actor_session_id,
        job=dm.JobRef(id=view.job.id, status='cancelled' if terminal else 'awaiting_approval'),
        job_revision=2 if terminal else 1, run_revision=2 if terminal else 1, last_seq=2 if terminal else 1,
        cancel_requested=terminal, execution='terminal' if terminal else 'not_started',
        outcome='cancelled' if terminal else None, approval_ids=[], approval_controls=[], consent_control=None,
        manifest_id=None, created_at=view.created_at, started_at=None, finished_at=finished,
        error_code='CODEX_CANCELLED' if terminal else None)


class CodexTurnRepository:
    def __init__(self, conn: sqlite3.Connection, identity: SessionIdentity | str, context: CodexTurnContext):
        if not conn.in_transaction:
            raise damaged()
        self.conn, self.context = conn, context
        self.workspace = identity if isinstance(identity, str) else identity.workspace_id
        self.jobs = CodexTurnJobs(conn, self.workspace)

    def rows(self, suffix: str):
        return self.conn.execute(f'SELECT * FROM codex_turn_{suffix} WHERE workspace_id=?', (self.workspace,)).fetchall()

    @staticmethod
    def thread_scope(anchor: SessionAnchor) -> str:
        return canonical_json({'version': 'codex-turn-thread-v1', 'session_id': anchor.session_id})

    def checked(self, bootstrap: dict[str, BootstrapSnapshot]) -> dict[str, CheckedSession]:
        try:
            return self._checked(bootstrap)
        except ApiError as error:
            if error.code in {"PROVIDER_INTEGRITY_INVALID", "PROVIDER_MISSING", "AUTHORING_INTEGRITY_ERROR", "JOB_MISSING"}:
                raise damaged() from None
            raise
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            raise damaged() from None

    def _checked(self, bootstrap):
        anchors, heads = self.rows('sessions'), self.rows('heads')
        events, witnesses = self.rows('events'), self.rows('event_members')
        members, commands = self.rows('members'), self.rows('commands')
        session_ids = {row['session_id'] for row in anchors}
        if (session_ids != {row['session_id'] for row in heads}
                or session_ids != {row['session_id'] for row in events}
                or session_ids != {row['session_id'] for row in members}
                or {row['job_id'] for row in members} != self.jobs.member_ids()
                or {(row['session_id'], row['seq'], row['record_sha256']) for row in events}
                    != {(row['session_id'], row['seq'], row['record_sha256']) for row in witnesses}
                ):
            raise damaged()
        # Core Run/thread membership independently detects deletion of the
        # entire Codex table family without rebuilding an empty default.
        owned_threads = self.conn.execute("SELECT id FROM threads WHERE workspace_id=? AND json_extract(scope_json,'$.version')='codex-turn-thread-v1'", (self.workspace,)).fetchall()
        if {row['thread_id'] for row in anchors} != {row[0] for row in owned_threads}:
            raise damaged()
        result = {}
        seen_members = set()
        seen_commands = set()
        for row in anchors:
            anchor = decode(SessionAnchor, row['record_json'])
            original = bootstrap.get(anchor.session_id)
            digest = content_sha256(anchor)
            if (anchor.session_id != row['session_id'] or anchor.workspace_id != self.workspace
                    or digest != row['record_sha256'] or anchor.thread_id != row['thread_id']
                    or original is None or original.session is None or original.session.status != 'ready'
                    or original.session.revision != 2 or original.finished is None
                    or anchor.actor_session_id != original.operation.actor_session_id
                    or anchor.bootstrap_sha256 != content_sha256(original)):
                raise damaged()
            thread = self.conn.execute('SELECT * FROM threads WHERE id=?', (anchor.thread_id,)).fetchone()
            if thread is None or tuple(thread) != (anchor.thread_id, self.workspace, self.thread_scope(anchor), 'Codex local turns', anchor.created_at):
                raise damaged()
            state = CheckedSession(anchor, 2, None)
            selected = sorted((item for item in events if item['session_id'] == anchor.session_id), key=lambda item: item['seq'])
            head = next(item for item in heads if item['session_id'] == anchor.session_id)
            if len(selected) != head['event_count']:
                raise damaged()
            for seq, stored in enumerate(selected, 1):
                raw = strict_json(stored['record_json'])
                if not isinstance(raw, dict):
                    raise damaged()
                model = (OperationControlEnvelope if raw.get('version') == 'codex-turn-event-v5' else ApprovalControlEnvelope if raw.get('version') == 'codex-turn-event-v3' else
                    ControlEventEnvelope if raw.get('version') == 'codex-turn-event-v2' else EventEnvelope)
                envelope = decode(model, stored['record_json'])
                if (envelope.session_id != anchor.session_id or envelope.workspace_id != self.workspace
                        or envelope.seq != seq or stored['seq'] != seq or envelope.previous_sha256 != digest
                        or content_sha256(envelope) != stored['record_sha256']):
                    raise damaged()
                event, command = envelope.event, getattr(envelope.event, 'command', None)
                if command is not None:
                    registration = next((item for item in commands if item['session_id'] == anchor.session_id and item['seq'] == seq), None)
                    if (registration is None or command.workspace_id != self.workspace or registration['actor_session_id'] != command.actor_session_id
                        or registration['route'] != command.route or registration['target_id'] != command.target_id
                        or registration['command_key'] != command.key or registration['command_sha256'] != content_sha256(command)
                        or not historical_session_belongs_to(self.conn, self.workspace, command.actor_session_id)):
                        raise damaged()
                    seen_commands.add((anchor.session_id, seq))
                if isinstance(event, (TurnPrepared, RunnableTurnPrepared)):
                    self._prepared(state, event, envelope, members)
                    seen_members.add(event.input.turn_id)
                elif isinstance(event, TurnProviderBound):
                    self._provider_bound(state, event)
                elif isinstance(event, (TurnApprovalBound, TurnOperationBound)):
                    self._approval_bound(state, event)
                elif isinstance(event, TurnStarted):
                    turn = state.turns.get(event.turn_id)
                    if turn is None or turn.start is not None or turn.control.job.status != 'awaiting_approval':
                        raise damaged()
                    command = event.command
                    ack, preparation = command.ack, turn.prepared.command.ack
                    if (state.active_turn_id != event.turn_id or command.actor_session_id != state.anchor.actor_session_id
                            or command.target_id != state.anchor.session_id or command.body.expected_session_revision != state.revision
                            or command.body.preparation_id != preparation.id or command.body.preparation_sha256 != preparation.preparation_sha256
                            or turn.control.consent_control is None or command.body.consent_id != turn.control.consent_control.id
                            or ack.turn_id != event.turn_id or ack.session_revision != state.revision + 1
                            or ack.job != dm.JobRef(id=turn.control.job.id, status='queued')):
                        raise damaged()
                    turn.start, turn.control = event, self.queued_control(turn.control)
                    state.revision += 1
                elif isinstance(event, TurnLifecycle):
                    self._lifecycle(state, event, envelope.occurred_at)
                elif isinstance(event, TurnCancelRequested):
                    turn = state.turns.get(event.turn_id)
                    requested = event.kind == 'cancel_requested'
                    if (turn is None or turn.control.execution != 'active' or turn.control.cancel_requested == requested
                            or state.active_turn_id != event.turn_id or event.session_revision != (state.revision+1 if requested else None)
                            or event.command.target_id != turn.control.job.id
                            or event.command.body.expected_revision != turn.control.job_revision):
                        raise damaged()
                    if requested:
                        turn.control = self.cancel_requested_control(turn.control)
                    if event.command.ack != self.jobs.snapshot(turn.control.job.id,turn.control.job_revision):
                        raise damaged()
                    state.revision += int(requested)
                else:
                    turn = state.turns.get(event.turn_id)
                    if turn is None or not isinstance(command, CancelCommand) or command.target_id != turn.control.job.id:
                        raise damaged()
                    if command.body.expected_revision != turn.control.job_revision:
                        raise damaged()
                    if event.kind == 'cancelled':
                        if state.active_turn_id != event.turn_id or turn.control.execution != 'not_started':
                            raise damaged()
                        turn.control = self.cancelled_control(turn.control, envelope.occurred_at)
                        if (event.requested_session_revision != state.revision + 1
                                or event.terminal_session_revision != state.revision + 2):
                            raise damaged()
                        state.revision += 2
                        state.active_turn_id = None
                    elif (turn.control.execution != 'terminal' or event.requested_session_revision is not None
                          or event.terminal_session_revision is not None):
                        raise damaged()
                    if command.ack != self.jobs.snapshot(turn.control.job.id, turn.control.job_revision):
                        raise damaged()
                state.envelopes.append(envelope)
                digest = stored['record_sha256']
            if (head['revision'] != state.revision or head['active_turn_id'] != state.active_turn_id
                    or head['head_sha256'] != digest):
                raise damaged()
            for turn in state.turns.values():
                self._run(state.anchor, turn)
            result[anchor.session_id] = state
        if (seen_members != {row['turn_id'] for row in members}
                or seen_commands != {(row['session_id'], row['seq']) for row in commands}):
            raise damaged()
        return result

    def _prepared(self, state, event, envelope, members):
        value, command = event.input, event.command
        ack = command.ack
        member = next((row for row in members if row['turn_id'] == value.turn_id), None)
        if (state.active_turn_id is not None or value.turn_id in state.turns or member is None
                or value.workspace_id != self.workspace or value.session_id != state.anchor.session_id
                or value.actor_session_id != state.anchor.actor_session_id
                or value.runtime.bootstrap_sha256 != state.anchor.bootstrap_sha256
                or value.provider.id != value.request.provider_id
                or value.runtime.tools != value.request.tools or command.actor_session_id != value.actor_session_id
                or command.target_id != value.session_id or command.body != value.request
                or value.request.expected_session_revision != state.revision
                or ack.actor_session_id != value.actor_session_id or ack.session_id != value.session_id
                or ack.turn_id != value.turn_id or ack.job != dm.JobRef(id=value.job_id, status='awaiting_approval')
                or ack.request != value.request or ack.summary.tools != value.request.tools
                or ack.session_revision != state.revision + 1
                or ack.validity != ('current' if isinstance(event, RunnableTurnPrepared) else 'unavailable')
                or ack.proposal_id is not None or ack.consent_id is not None
                or ack.created_at != envelope.occurred_at or preparation_digest(self.workspace, ack) != ack.preparation_sha256
                or member['session_id'] != value.session_id or member['job_id'] != value.job_id
                or member['preparation_id'] != ack.id or member['preparation_sha256'] != ack.preparation_sha256
                or member['prepared_seq'] != envelope.seq or member['sequence'] != event.creation_sequence):
            raise damaged()
        row = self.jobs.load(value.job_id)
        if row['input_json'] != canonical_json(value) or row['input_sha256'] != ack.summary.job_input_sha256:
            raise damaged()
        if retained_provider_configuration(self.conn, self.workspace, value.provider.id, value.provider.revision) != value.provider:
            raise damaged()
        context = self.context.verify_owned_turn(self.conn, self.workspace, value, ack.summary)
        if context.snapshot.created_at != ack.created_at:
            raise damaged()
        state.revision += 1
        state.active_turn_id = value.turn_id
        state.turns[value.turn_id] = CheckedTurn(event, turn_control(event), envelope.seq)

    @staticmethod
    def queued_control(control: CodexTurnControlView) -> CodexTurnControlView:
        return CodexTurnControlView.model_validate({**control.model_dump(), 'job': {'id':control.job.id,'status':'queued'},
            'job_revision':control.job_revision+1,'run_revision':control.run_revision+1,'last_seq':control.last_seq+1})

    @staticmethod
    def active_control(control: CodexTurnControlView, now: str) -> CodexTurnControlView:
        return CodexTurnControlView.model_validate({**control.model_dump(), 'job': {'id':control.job.id,'status':'running'},
            'job_revision':control.job_revision+1,'run_revision':control.run_revision+1,'last_seq':control.last_seq+1,
            'execution':'active','started_at':now})

    @staticmethod
    def terminal_control(control: CodexTurnControlView, now: str, outcome, error_code) -> CodexTurnControlView:
        status = 'completed' if outcome == 'completed' else 'cancelled' if outcome == 'cancelled' else 'failed'
        return CodexTurnControlView.model_validate({**control.model_dump(), 'job': {'id':control.job.id,'status':status},
            'job_revision':control.job_revision+1,'run_revision':control.run_revision+1,'last_seq':control.last_seq+1,
            'execution':'terminal','outcome':outcome,'finished_at':now,'error_code':error_code})

    @staticmethod
    def cancel_requested_control(control: CodexTurnControlView) -> CodexTurnControlView:
        return CodexTurnControlView.model_validate({**control.model_dump(),'cancel_requested':True,
            'job_revision':control.job_revision+1,'run_revision':control.run_revision+1,'last_seq':control.last_seq+1})

    @classmethod
    def _lifecycle(cls, state: CheckedSession, event: TurnLifecycle, now: str) -> None:
        turn = state.turns.get(event.turn_id)
        if (turn is None or turn.start is None or state.active_turn_id != event.turn_id
                or turn.control.execution == 'terminal' or not turn.provider_bindings):
            raise damaged()
        bound = turn.provider_bindings[-1]
        if (event.provider_seq,event.provider_sha256) != (bound.provider_seq,bound.provider_sha256):
            raise damaged()
        if event.phase == 'claim':
            if turn.control.job.status != 'queued' or turn.control.started_at is not None:
                raise damaged()
            expected = cls.active_control(turn.control, now)
        else:
            if event.control.outcome is None:
                raise damaged()
            expected = cls.terminal_control(turn.control, now, event.control.outcome, event.control.error_code)
            state.revision += 1
            state.active_turn_id = None
        if event.control != expected:
            raise damaged()
        turn.control = event.control
        turn.lifecycle.append(event)

    @staticmethod
    def cancelled_control(control: CodexTurnControlView, now: str) -> CodexTurnControlView:
        return CodexTurnControlView.model_validate({**control.model_dump(), 'job': {'id':control.job.id,'status':'cancelled'},
            'job_revision':control.job_revision+1,'run_revision':control.run_revision+1,'last_seq':control.last_seq+1,
            'cancel_requested':True,'execution':'terminal','outcome':'cancelled','finished_at':now,'error_code':'CODEX_CANCELLED'})

    @staticmethod
    def _provider_bound(state: CheckedSession, event: TurnProviderBound) -> None:
        turn = state.turns.get(event.turn_id)
        if turn is None:
            raise damaged()
        previous = turn.provider_bindings[-1] if turn.provider_bindings else None
        if (event.provider_seq != (previous.provider_seq+1 if previous else 1)
                or previous is not None and event.proposal_id != previous.proposal_id
                or previous is not None and previous.consent_id is not None and event.consent_id != previous.consent_id
                or (event.consent_id is None) != (event.consent_revision is None)
                or (event.consent_id is None) != (event.consent_status is None)):
            raise damaged()
        control = None
        if event.consent_id is not None:
            if event.consent_revision is None or event.consent_status is None:
                raise damaged()
            control = CodexConsentControl(id=event.consent_id, revision=event.consent_revision, status=event.consent_status)
        turn.control = CodexTurnControlView.model_validate({**turn.control.model_dump(),
            'consent_control':control.model_dump() if control else None})
        turn.provider_bindings.append(event)

    def _run(self, anchor, turn):
        row = self.jobs.load(turn.control.job.id)
        if (row['status'] != turn.control.job.status or row['revision'] != turn.control.job_revision
                or bool(row['cancel_requested']) != turn.control.cancel_requested):
            raise damaged()
        if turn.control.execution == 'terminal':
            terminal = next((event for event in turn.lifecycle if event.phase == 'terminal'), None)
            if terminal is not None and turn.start is None:
                raise damaged()
            expected_result = ({'version':'codex-turn-job-result-v1','turn_id':turn.control.id,
                'outcome':turn.control.outcome,'dispatch_id':turn.start.dispatch_id if turn.start else None}
                if terminal else {'cancelled_before_execution': True})
            if row['result_json'] != canonical_json(expected_result):
                raise damaged()
        run = self.conn.execute('SELECT * FROM runs WHERE id=?', (row['id'],)).fetchone()
        if run is None or tuple(run) != (row['id'], anchor.thread_id,
                turn.prepared.command.ack.summary.context_snapshot_id, canonical_json(turn.control)):
            raise damaged()
        actual_runs = {item[0] for item in self.conn.execute('SELECT id FROM runs WHERE thread_id=?', (anchor.thread_id,))}
        actual_jobs = {item['job_id'] for item in self.rows('members') if item['session_id'] == anchor.session_id}
        if actual_runs != actual_jobs:
            raise damaged()

    @staticmethod
    def _approval_bound(state: CheckedSession, event: TurnApprovalBound | TurnOperationBound) -> None:
        turn = state.turns.get(event.turn_id)
        if turn is None or turn.start is None or turn.control.execution != 'active':
            raise damaged()
        previous = next((item for item in reversed(turn.approval_bindings) if item.control.id == event.control.id), None)
        if (event.approval_seq != (previous.approval_seq + 1 if previous else 1)
                or event.control.revision != event.approval_seq
                or previous is not None and previous.control.operation_sha256 != event.control.operation_sha256
                or previous is None and (event.control.decision != 'pending' or event.control.validity != ('current' if isinstance(event, TurnOperationBound) else 'unavailable'))
                or previous is not None and previous.control.validity == 'closed' and not (
                    isinstance(event, TurnOperationBound) and isinstance(previous, TurnOperationBound)
                    and previous.approval_seq == 3 and previous.control.decision == 'approve_once' and event.approval_seq == 4)
                or previous is not None and type(previous) is not type(event)
                or previous is None and any(event.control.id in other.control.approval_ids for other in state.turns.values())):
            raise damaged()
        controls = list(turn.control.approval_controls)
        if previous is None:
            controls.append(event.control)
        else:
            controls = [event.control if item.id == event.control.id else item for item in controls]
        turn.control = CodexTurnControlView.model_validate({**turn.control.model_dump(),
            'approval_ids': [item.id for item in controls], 'approval_controls': controls})
        turn.approval_bindings.append(event)

    def next_creation_sequence(self) -> int:
        # The allocating writer owns BEGIN IMMEDIATE. Freeze the real sequence
        # into the immutable event; the surrogate is never pagination authority.
        return self.conn.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM codex_turn_members').fetchone()[0]

    def establish(self, anchor: SessionAnchor) -> CheckedSession:
        raw, digest = canonical_json(anchor), content_sha256(anchor)
        self.conn.execute('INSERT INTO threads(id,workspace_id,scope_json,title,created_at) VALUES(?,?,?,?,?)',
            (anchor.thread_id, self.workspace, self.thread_scope(anchor), 'Codex local turns', anchor.created_at))
        self.conn.execute('INSERT INTO codex_turn_sessions VALUES(?,?,?,?,?)',
            (anchor.session_id, self.workspace, anchor.thread_id, raw, digest))
        self.conn.execute('INSERT INTO codex_turn_heads VALUES(?,?,2,0,?,NULL)', (anchor.session_id, self.workspace, digest))
        return CheckedSession(anchor, 2, None)

    def append(self, state: CheckedSession, event, now: str) -> EventEnvelope | ControlEventEnvelope | ApprovalControlEnvelope | OperationControlEnvelope:
        seq = len(state.envelopes) + 1
        previous = content_sha256(state.envelopes[-1]) if state.envelopes else content_sha256(state.anchor)
        extended = isinstance(event, (RunnableTurnPrepared, TurnProviderBound, TurnStarted, TurnLifecycle, TurnCancelRequested))
        envelope: ControlEventEnvelope | EventEnvelope | ApprovalControlEnvelope | OperationControlEnvelope
        if isinstance(event, TurnOperationBound):
            envelope = OperationControlEnvelope(version='codex-turn-event-v5', workspace_id=self.workspace,
                session_id=state.anchor.session_id, seq=seq, previous_sha256=previous, occurred_at=now, event=event)
        elif isinstance(event, TurnApprovalBound):
            envelope = ApprovalControlEnvelope(version='codex-turn-event-v3', workspace_id=self.workspace,
                session_id=state.anchor.session_id, seq=seq, previous_sha256=previous, occurred_at=now, event=event)
        elif extended:
            envelope = ControlEventEnvelope(version='codex-turn-event-v2', workspace_id=self.workspace,
                session_id=state.anchor.session_id, seq=seq, previous_sha256=previous, occurred_at=now, event=event)
        else:
            envelope = EventEnvelope(version='codex-turn-event-v1', workspace_id=self.workspace,
                session_id=state.anchor.session_id, seq=seq, previous_sha256=previous, occurred_at=now, event=event)
        digest = content_sha256(envelope)
        self.conn.execute('INSERT INTO codex_turn_events VALUES(?,?,?,?,?)',
            (state.anchor.session_id, self.workspace, seq, canonical_json(envelope), digest))
        self.conn.execute('INSERT INTO codex_turn_event_members VALUES(?,?,?,?)', (state.anchor.session_id, self.workspace, seq, digest))
        command = getattr(event, 'command', None)
        if command is not None:
            self.conn.execute('INSERT INTO codex_turn_commands VALUES(?,?,?,?,?,?,?,?)',
                (self.workspace, command.actor_session_id, command.route, command.target_id, command.key,
                 state.anchor.session_id, seq, content_sha256(command)))
        if isinstance(event, (TurnPrepared, RunnableTurnPrepared)):
            view = event.command.ack
            self.conn.execute('INSERT INTO codex_turn_members(sequence,turn_id,session_id,workspace_id,job_id,preparation_id,preparation_sha256,prepared_seq) VALUES(?,?,?,?,?,?,?,?)',
                (event.creation_sequence, view.turn_id, view.session_id, self.workspace, view.job.id, view.id, view.preparation_sha256, seq))
            self.conn.execute('INSERT INTO runs VALUES(?,?,?,?)',
                (view.job.id, state.anchor.thread_id, view.summary.context_snapshot_id, canonical_json(turn_control(event))))
            revision, active = state.revision + 1, view.turn_id
        elif event.kind == 'cancelled':
            control = self.cancelled_control(state.turns[event.turn_id].control, now)
            self.conn.execute('UPDATE runs SET snapshot_json=? WHERE id=?', (canonical_json(control), control.job.id))
            revision, active = state.revision + 2, None
        elif isinstance(event, TurnStarted):
            control = self.queued_control(state.turns[event.turn_id].control)
            self.conn.execute('UPDATE runs SET snapshot_json=? WHERE id=?', (canonical_json(control), control.job.id))
            revision, active = state.revision + 1, state.active_turn_id
        elif isinstance(event, TurnLifecycle):
            prior_revision = state.revision
            self._lifecycle(state, event, now)
            control = state.turns[event.turn_id].control
            self.conn.execute('UPDATE runs SET snapshot_json=? WHERE id=?', (canonical_json(control), control.job.id))
            revision, active = state.revision, state.active_turn_id
            # CAS below still compares against the pre-event head.
            state.revision = prior_revision
        elif isinstance(event, TurnCancelRequested):
            requested = event.kind == 'cancel_requested'
            control = self.cancel_requested_control(state.turns[event.turn_id].control) if requested else state.turns[event.turn_id].control
            self.conn.execute('UPDATE runs SET snapshot_json=? WHERE id=?', (canonical_json(control), control.job.id))
            revision, active = state.revision+int(requested), state.active_turn_id
        elif isinstance(event, TurnProviderBound):
            self._provider_bound(state, event)
            control = state.turns[event.turn_id].control
            self.conn.execute('UPDATE runs SET snapshot_json=? WHERE id=?', (canonical_json(control), control.job.id))
            revision, active = state.revision, state.active_turn_id
        elif isinstance(event, (TurnApprovalBound, TurnOperationBound)):
            self._approval_bound(state, event)
            control = state.turns[event.turn_id].control
            self.conn.execute('UPDATE runs SET snapshot_json=? WHERE id=?', (canonical_json(control), control.job.id))
            revision, active = state.revision, state.active_turn_id
        else:
            revision, active = state.revision, state.active_turn_id
        updated = self.conn.execute('UPDATE codex_turn_heads SET revision=?,event_count=?,head_sha256=?,active_turn_id=? WHERE session_id=? AND revision=? AND event_count=? AND head_sha256=?',
            (revision, seq, digest, active, state.anchor.session_id, state.revision, seq - 1, previous))
        if updated.rowcount != 1:
            raise damaged()
        return envelope

    @staticmethod
    def replay(history, identity: SessionIdentity, route: str, target: str, key: str, body: BaseModel):
        for state in history.values():
            for envelope in state.envelopes:
                command = getattr(envelope.event, 'command', None)
                if command is not None and (command.actor_session_id, command.route, command.target_id, command.key) == (identity.id, route, target, key):
                    if canonical_json(command.body) != canonical_json(body):
                        raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原命令与本次完整输入不一致。')
                    return command.ack
        return None
