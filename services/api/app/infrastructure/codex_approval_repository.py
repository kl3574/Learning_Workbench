"""Checked approval history and core projection in the caller's transaction."""
from dataclasses import dataclass
from packages.contracts import domain_models as dm
from packages.contracts.canonical import strict_json, sha256_bytes
from ..application.codex_approval_models import (
    ApprovalEnvelope, ApprovalCreated, ApprovalDecided, ApprovalClosed, ApprovalOperation,
    SyntheticOperationCallback, TurnApprovalBound,
)
from ..application.codex_operation_models import (SupportedOperation, SupportedCreated, OperationStarted, OperationFinished, OperationEnvelope, TurnOperationBound)
from ..application.codex_operation_profile import CodexOperationRegistry
from ..infrastructure.consent_repository import instant
from ..application.codex_turn_context import damaged
from ..codex_turn_dto import CodexApprovalControl
from ..serialization import canonical_json, content_sha256
from .codex_turn_repository import decode
from .security import historical_session_belongs_to


@dataclass
class CheckedApproval:
    operation: ApprovalOperation | SupportedOperation
    events: list[ApprovalEnvelope | OperationEnvelope]
    decided: ApprovalDecided | None = None
    closed: ApprovalClosed | None = None

    started: OperationStarted | None = None
    finished: OperationFinished | None = None

    @property
    def supported(self):
        return isinstance(self.operation, SupportedOperation)

    @property
    def status(self):
        if self.decided is not None:
            return "approved" if self.decided.command.body.decision == "approve_once" else "declined"
        return "expired" if self.closed else "pending"

    @property
    def revision(self):
        return len(self.events)

    @property
    def control(self):
        return CodexApprovalControl(id=self.operation.approval_id, revision=self.revision,
            operation_sha256=content_sha256(self.operation),
            decision=self.decided.command.body.decision if self.decided else 'pending',
            validity='closed' if self.closed or self.started or self.decided and self.status == 'declined' else 'current' if self.supported else 'unavailable')


class CodexApprovalRepository:
    def __init__(self, conn, workspace):
        if not conn.in_transaction:
            raise damaged()
        self.conn, self.workspace = conn, workspace

    def rows(self, suffix):
        return self.conn.execute(f'SELECT * FROM codex_approval_{suffix} WHERE workspace_id=?', (self.workspace,)).fetchall()

    def checked(self, history, provider, bootstrap):
        try:
            return self._checked(history, provider, bootstrap)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            raise damaged() from None

    def _checked(self, history, provider, bootstrap):
        turns = {turn.control.id: (state, turn) for state in history.values() for turn in state.turns.values()}
        witnesses = {item.control.id for _, turn in turns.values() for item in turn.approval_bindings}
        heads, events, members, commands = (self.rows(part) for part in ('heads', 'events', 'members', 'commands'))
        core = self.conn.execute("SELECT a.* FROM approvals a JOIN jobs j ON j.id=a.job_id WHERE j.workspace_id=? AND json_extract(a.scope_json,'$.version') IN ('codex-unsupported-operation-v1','codex-supported-memory-operation-v1')", (self.workspace,)).fetchall()
        if (witnesses != {row['approval_id'] for row in heads}
                or witnesses != {row['approval_id'] for row in events}
                or witnesses != {row['id'] for row in core}
                or {(row['approval_id'], row['seq'], row['record_sha256']) for row in events}
                != {(row['approval_id'], row['seq'], row['record_sha256']) for row in members}):
            raise damaged()
        result, seen_commands, callbacks = {}, set(), set()
        for head in heads:
            identifier = head['approval_id']
            selected = sorted((row for row in events if row['approval_id'] == identifier), key=lambda row: row['seq'])
            if len(selected) != head['event_count']:
                raise damaged()
            state = None
            previous = None
            for seq, row in enumerate(selected, 1):
                raw = strict_json(row['record_json'])
                if not isinstance(raw, dict):
                    raise damaged()
                envelope = decode(OperationEnvelope if raw.get('version') == 'codex-generic-approval-event-v2' else ApprovalEnvelope, row['record_json'])
                if (row['seq'] != seq or envelope.seq != seq or envelope.approval_id != identifier
                        or envelope.workspace_id != self.workspace or envelope.previous_sha256 != previous
                        or content_sha256(envelope) != row['record_sha256']):
                    raise damaged()
                event = envelope.event
                if isinstance(event, (ApprovalCreated, SupportedCreated)):
                    if state is not None or seq != 1:
                        raise damaged()
                    operation = event.operation
                    pair = turns.get(operation.turn_id)
                    outbound = provider.get(operation.turn_id)
                    if pair is None or outbound is None or outbound.started is None or outbound.queued is None:
                        raise damaged()
                    session, turn = pair
                    prepared = turn.prepared
                    assurance = outbound.proposed.command.ack.summary.input_token_assurance
                    callback = SyntheticOperationCallback.model_validate(strict_json(operation.callback_json))
                    if (operation.approval_id != identifier or operation.workspace_id != self.workspace
                            or operation.actor_session_id != session.anchor.actor_session_id
                            or operation.session_id != session.anchor.session_id or operation.job_id != turn.control.job.id
                            or operation.job_input_sha256 != prepared.command.ack.summary.job_input_sha256
                            or operation.dispatch_id != outbound.queued.dispatch_id
                            or operation.execution_owner_id != outbound.started.execution_owner_id
                            or operation.lease != outbound.started.lease
                            or operation.profile_sha256 != prepared.command.ack.summary.runtime.profile_sha256
                            or operation.input_proof_sha256 != assurance.proof_sha256
                            or operation.request_sha256 != outbound.started.request_body_sha256
                            or operation.tools != prepared.input.request.tools
                            or operation.callback != callback or callback.turn_id != operation.turn_id
                            or bootstrap[operation.session_id].finished is None
                            or callback.thread_id != bootstrap[operation.session_id].finished.outcome.thread_id
                            or sha256_bytes(operation.callback_json.encode()) != operation.callback_sha256
                            or operation.created_at != envelope.occurred_at
                            or outbound.started_at is None or operation.created_at < outbound.started_at or operation.expires_at <= operation.created_at
                            or operation.expires_at > outbound.proposed.command.ack.summary.expires_at):
                        raise damaged()
                    callback_key = (operation.execution_owner_id, callback.rpc_id)
                    if callback_key in callbacks:
                        raise damaged()
                    callbacks.add(callback_key)
                    state = CheckedApproval(operation, [])
                    self.check_supported(operation)
                elif state is None or state.closed is not None or state.finished is not None:
                    raise damaged()
                elif isinstance(event, ApprovalDecided):
                    command, operation = event.command, state.operation
                    ack = command.ack
                    expected = dm.JobRef(id=operation.job_id, status='running')
                    if (seq != 2 or state.decided is not None or command.body.expected_revision != 1
                            or command.body.decision != 'decline' and not state.supported
                            or command.body.decision == 'approve_once' and command.actor_session_id != operation.actor_session_id
                            or command.body.operation_sha256 != content_sha256(operation)
                            or ack.id != identifier or ack.revision != 2 or ack.decision != command.body.decision
                            or ack.actor_session_id != command.actor_session_id or ack.operation_sha256 != content_sha256(operation)
                            or ack.session_id != operation.session_id or ack.turn_id != operation.turn_id
                            or ack.run_id != operation.job_id or ack.job != expected
                            or not historical_session_belongs_to(self.conn, self.workspace, command.actor_session_id)):
                        raise damaged()
                    registration = next((item for item in commands if item['approval_id'] == identifier and item['seq'] == seq), None)
                    if (registration is None or registration['actor_session_id'] != command.actor_session_id
                            or registration['command_key'] != command.key or registration['command_sha256'] != content_sha256(command)):
                        raise damaged()
                    seen_commands.add((identifier, seq))
                    state.decided = event
                elif isinstance(event, ApprovalClosed):
                    if state.started is not None or seq != (3 if state.decided and state.status == 'approved' else 2) or state.status == 'declined':
                        raise damaged()
                    state.closed = event
                elif isinstance(event, OperationStarted):
                    operation = state.operation
                    if (not state.supported or seq != 3 or state.status != 'approved' or state.started is not None
                            or event.execution_owner_id != operation.execution_owner_id or event.lease != operation.lease
                            or event.operation_sha256 != content_sha256(operation)
                            or event.budget_ordinal > operation.tools.max_tool_calls
                            or instant(envelope.occurred_at) >= instant(operation.expires_at)):
                        raise damaged()
                    state.started = event
                elif isinstance(event, OperationFinished):
                    if not state.supported or seq != 4 or state.started is None:
                        raise damaged()
                    if (event.outcome == 'completed') != (event.result is not None) or (event.outcome == 'completed') != (event.error_code is None):
                        raise damaged()
                    if event.result is not None and (event.result.operation_sha256 != content_sha256(state.operation)
                            or not isinstance(state.operation, SupportedOperation) or event.result.text != state.operation.closure.command.text):
                        raise damaged()
                    state.finished = event
                if state is None:
                    raise damaged()
                if (isinstance(envelope, OperationEnvelope) != state.supported
                        or state.events and instant(envelope.occurred_at) < instant(state.events[-1].occurred_at)):
                    raise damaged()
                state.events.append(envelope)
                bound = next((item for item in turns[state.operation.turn_id][1].approval_bindings
                    if item.control.id == identifier and item.approval_seq == seq), None)
                if bound is None or isinstance(bound, TurnOperationBound) != state.supported or bound.approval_sha256 != row['record_sha256'] or bound.control != state.control:
                    raise damaged()
                previous = row['record_sha256']
            if state is None or head['head_sha256'] != previous:
                raise damaged()
            actual = next(item for item in core if item['id'] == identifier)
            status = state.status
            if tuple(actual) != (identifier, state.operation.job_id, state.revision,
                    content_sha256(state.operation), status, canonical_json(state.operation),
                    state.operation.actor_session_id, state.operation.expires_at):
                raise damaged()
            if len([item for item in turns[state.operation.turn_id][1].approval_bindings if item.control.id == identifier]) != state.revision:
                raise damaged()
            result[identifier] = state
        if seen_commands != {(row['approval_id'], row['seq']) for row in commands}:
            raise damaged()
        # The Codex event order is the independent witness for conservative tool debits.
        for _, turn in turns.values():
            started = [result[b.control.id].started for b in turn.approval_bindings
                if b.approval_seq == 3 and result[b.control.id].started is not None]
            if [item.budget_ordinal for item in started if item is not None] != list(range(1, len(started)+1)):
                raise damaged()
        return result

    @staticmethod
    def check_supported(operation):
        if not isinstance(operation, SupportedOperation):
            return
        closure = operation.closure
        if (closure.workspace_id != operation.workspace_id or closure.turn_id != operation.turn_id
                or closure.argv != ['synthetic-memory-literal-v1', closure.command.text] or closure.environment != {}
                or canonical_json(closure.command) != operation.callback.request_text
                or operation.callback.method != 'command/requestApproval'
                or operation.operation != CodexOperationRegistry.projection(closure)):
            raise damaged()

    def append(self, state, event, now):
        operation = event.operation if isinstance(event, (ApprovalCreated, SupportedCreated)) else state.operation
        seq = 1 if state is None else state.revision + 1
        supported = isinstance(operation, SupportedOperation)
        envelope = (OperationEnvelope(version='codex-generic-approval-event-v2', workspace_id=self.workspace,
            approval_id=operation.approval_id, seq=seq,
            previous_sha256=content_sha256(state.events[-1]) if state else None, occurred_at=now, event=event) if supported else
            ApprovalEnvelope(version='codex-generic-approval-event-v1', workspace_id=self.workspace,
            approval_id=operation.approval_id, seq=seq,
            previous_sha256=content_sha256(state.events[-1]) if state else None, occurred_at=now, event=event))
        digest = content_sha256(envelope)
        identifier = operation.approval_id
        self.conn.execute('INSERT INTO codex_approval_events VALUES(?,?,?,?,?)',
            (self.workspace, identifier, seq, canonical_json(envelope), digest))
        self.conn.execute('INSERT INTO codex_approval_members VALUES(?,?,?,?)', (self.workspace, identifier, seq, digest))
        if state is None:
            self.conn.execute('INSERT INTO codex_approval_heads VALUES(?,?,?,?)', (self.workspace, identifier, seq, digest))
            state = CheckedApproval(operation, [])
            self.conn.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?)', (identifier, operation.job_id, 1,
                content_sha256(operation), 'pending', canonical_json(operation), operation.actor_session_id, operation.expires_at))
        else:
            changed = self.conn.execute('UPDATE codex_approval_heads SET event_count=?,head_sha256=? WHERE approval_id=? AND event_count=? AND head_sha256=?',
                (seq, digest, identifier, seq-1, content_sha256(state.events[-1])))
            if changed.rowcount != 1:
                raise damaged()
            if isinstance(event, ApprovalDecided):
                state.decided = event
                command = event.command
                self.conn.execute('INSERT INTO codex_approval_commands VALUES(?,?,?,?,?,?)',
                    (self.workspace, command.actor_session_id, command.key, identifier, seq, content_sha256(command)))
            elif isinstance(event, ApprovalClosed):
                state.closed = event
            elif isinstance(event, OperationStarted):
                state.started = event
            elif isinstance(event, OperationFinished):
                state.finished = event
            self.conn.execute('UPDATE approvals SET revision=?,status=? WHERE id=?',
                (seq, state.status, identifier))
        state.events.append(envelope)
        if supported:
            return TurnOperationBound(kind='approval_operation_bound', turn_id=operation.turn_id, approval_seq=seq,
                approval_sha256=digest, control=state.control)
        return TurnApprovalBound(kind='approval_bound', turn_id=operation.turn_id, approval_seq=seq,
            approval_sha256=digest, control=state.control)
