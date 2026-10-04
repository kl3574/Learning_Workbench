"""Provider-owned append-only Codex consent and single-dispatch ledger."""
from dataclasses import dataclass, field
import sqlite3
from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.canonical import strict_json, sha256_bytes
from ..application.codex_turn_context import damaged
from ..application.errors import ApiError
from ..application.provider_codex_models import (
    CodexProviderEnvelope, CodexProposed, CodexGranted, CodexRevoked,
    CodexDispatchQueued, CodexDispatchStarted, CodexDispatchFinished,
)
from ..codex_turn_dto import CodexConsentView, CodexDispatchView, CodexConsentControl
from ..provider_dto import MessageSummary, UnknownUsageCost
from ..serialization import canonical_json, content_sha256
from .consent_repository import instant
from .provider_repository import ProviderRepository
from .security import historical_session_belongs_to


@dataclass
class CodexProviderState:
    proposed: CodexProposed
    envelopes: list[CodexProviderEnvelope] = field(default_factory=list)
    granted: CodexGranted | None = None
    granted_at: str | None = None
    revoked_at: str | None = None
    queued: CodexDispatchQueued | None = None
    started: CodexDispatchStarted | None = None
    started_at: str | None = None
    finished: CodexDispatchFinished | None = None
    finished_at: str | None = None

    @property
    def revision(self) -> int:
        return 2 if self.revoked_at else 1

    @property
    def digest(self) -> str:
        return content_sha256(self.envelopes[-1])

    def consent_control(self, now: str) -> CodexConsentControl | None:
        if self.granted is None:
            return None
        status: Literal['active', 'revoked', 'expired'] = 'revoked' if self.revoked_at else ('expired' if instant(now) >= instant(self.proposed.command.ack.summary.expires_at) else 'active')
        return CodexConsentControl(id=self.granted.command.ack.id, revision=self.revision, status=status)

    def consent_view(self, now: str, job: dm.JobRef) -> CodexConsentView:
        control = self.consent_control(now)
        if control is None or self.granted is None or self.granted_at is None:
            raise damaged()
        ack = self.granted.command.ack
        dispatch = None
        if self.queued is not None:
            terminal = self.finished
            dispatch = CodexDispatchView(id=self.queued.dispatch_id, job=job, started_at=self.started_at,
                finished_at=self.finished_at, consumed_provider_calls=int(self.started is not None),
                input_tokens=terminal.usage.input_tokens if terminal else None,
                output_tokens=terminal.usage.output_tokens if terminal else None,
                elapsed_ms=terminal.elapsed_ms if terminal else None, cost=UnknownUsageCost(kind='unknown', currency='USD'),
                outcome=terminal.outcome if terminal else None, error_code=terminal.error_code if terminal else None)
        return CodexConsentView(id=control.id, revision=control.revision, status=control.status,
            actor_session_id=ack.actor_session_id, proposal_id=ack.proposal_id,
            proposal_sha256=ack.proposal_sha256, summary=ack.summary, created_at=self.granted_at,
            expires_at=ack.summary.expires_at, revoked_at=self.revoked_at, dispatch=dispatch)


class CodexProviderRepository:
    def __init__(self, connection: sqlite3.Connection, workspace: str):
        if not connection.in_transaction:
            raise damaged()
        self.conn, self.workspace = connection, workspace

    def rows(self, name: str):
        return self.conn.execute(f'SELECT * FROM provider_codex_{name} WHERE workspace_id=?', (self.workspace,)).fetchall()

    def checked(self) -> dict[str, CodexProviderState]:
        try:
            return self._checked()
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            raise damaged() from None

    def _checked(self):
        heads, rows, witnesses, commands = (self.rows(name) for name in ('heads', 'events', 'members', 'commands'))
        ids = {row['turn_id'] for row in heads}
        if (ids != {row['turn_id'] for row in rows}
                or {(row['turn_id'], row['seq'], row['record_sha256']) for row in rows}
                    != {(row['turn_id'], row['seq'], row['record_sha256']) for row in witnesses}):
            raise damaged()
        states, seen_commands = {}, set()
        for head in heads:
            selected = sorted((row for row in rows if row['turn_id'] == head['turn_id']), key=lambda row: row['seq'])
            if len(selected) != head['event_count']:
                raise damaged()
            state, previous = None, None
            for seq, row in enumerate(selected, 1):
                envelope = CodexProviderEnvelope.model_validate(strict_json(row['record_json']))
                if (canonical_json(envelope) != row['record_json'] or content_sha256(envelope) != row['record_sha256']
                        or envelope.workspace_id != self.workspace or envelope.turn_id != head['turn_id']
                        or envelope.seq != seq or row['seq'] != seq or envelope.previous_sha256 != previous):
                    raise damaged()
                event = envelope.event
                command = getattr(event, 'command', None)
                if command is not None:
                    actual = next((r for r in commands if r['turn_id'] == envelope.turn_id and r['seq'] == seq), None)
                    if (actual is None or actual['actor_session_id'] != command.actor_session_id
                            or actual['route'] != command.route or actual['command_key'] != command.key
                            or actual['command_sha256'] != content_sha256(command)
                            or not historical_session_belongs_to(self.conn, self.workspace, command.actor_session_id)):
                        raise damaged()
                    seen_commands.add((envelope.turn_id, seq))
                if isinstance(event, CodexProposed):
                    if state is not None or seq != 1:
                        raise damaged()
                    self._proposal(envelope)
                    state = CodexProviderState(event)
                elif state is None:
                    raise damaged()
                else:
                    self._reduce(state, envelope)
                state.envelopes.append(envelope)
                previous = row['record_sha256']
            if state is None or previous != head['head_sha256']:
                raise damaged()
            states[head['turn_id']] = state
        if seen_commands != {(r['turn_id'], r['seq']) for r in commands}:
            raise damaged()
        return states

    def _proposal(self, envelope):
        event = envelope.event
        material, command = event.material, event.command
        view, source = command.ack, material.preparation
        summary, config = view.summary, material.input.provider
        if (material.workspace_id != self.workspace or material.actor_session_id != source.actor_session_id
                or command.actor_session_id != material.actor_session_id or envelope.turn_id != source.turn_id
                or command.body.preparation_id != source.id or command.body.preparation_sha256 != source.preparation_sha256
                or command.body.expected_job_revision != material.job_revision
                or command.body.expected_provider_revision != config.revision
                or summary.preparation_id != source.id or summary.preparation_sha256 != source.preparation_sha256
                or summary.session_id != source.session_id or summary.turn_id != source.turn_id
                or summary.job_id != source.job.id or summary.source_job_revision != material.job_revision
                or summary.source_input_sha256 != source.summary.job_input_sha256
                or (summary.provider_id, summary.provider_revision, summary.config_sha256, summary.model, summary.endpoint_policy)
                    != (config.id, config.revision, config.config_sha256, config.model, config.endpoint_policy)
                or summary.context_snapshot_id != material.context.snapshot.id
                or summary.context_snapshot_sha256 != material.context.snapshot.snapshot_sha256
                or summary.input_sha256 != source.summary.prepared_input_sha256
                or summary.request_body_sha256 != sha256_bytes(event.request_body.encode())
                or summary.messages != [MessageSummary(role=m.role, character_count=len(m.content), content_sha256=sha256_bytes(m.content.encode())) for m in material.context.messages]
                or summary.references != source.summary.materials or summary.tools != source.request.tools
                or summary.runtime != source.summary.runtime or summary.budget != command.body.budget
                or summary.created_at != envelope.occurred_at or summary.expires_at != command.body.expires_at
                or view.validity != 'current' or view.consent_id is not None
                or view.proposal_sha256 != content_sha256({'version':'codex-consent-proposal-v1',
                    'workspace_id':self.workspace,'actor_session_id':material.actor_session_id,'summary':summary.model_dump(mode='json')})):
            raise damaged()

    def _reduce(self, state: CodexProviderState, envelope: CodexProviderEnvelope):
        event, original = envelope.event, state.proposed.command.ack
        if isinstance(event, CodexGranted):
            command, ack = event.command, event.command.ack
            if (state.granted is not None or command.actor_session_id != state.proposed.command.actor_session_id
                    or command.body.proposal_id != original.id or command.body.proposal_sha256 != original.proposal_sha256
                    or ack.actor_session_id != command.actor_session_id or ack.proposal_id != original.id
                    or ack.proposal_sha256 != original.proposal_sha256 or ack.summary != original.summary
                    or not instant(original.summary.created_at) <= instant(envelope.occurred_at) < instant(original.summary.expires_at)):
                raise damaged()
            state.granted, state.granted_at = event, envelope.occurred_at
        elif isinstance(event, CodexRevoked):
            if (state.granted is None or event.command.body.expected_revision != state.revision
                    or event.command.ack.id != state.granted.command.ack.id):
                raise damaged()
            applied = state.revoked_at is None
            if (event.kind != ('revoked' if applied else 'revoke_observed')
                    or event.command.ack != dm.MutationAck(id=state.granted.command.ack.id, revision=2, applied=applied)):
                raise damaged()
            if applied:
                state.revoked_at = envelope.occurred_at
        elif isinstance(event, CodexDispatchQueued):
            if (state.queued is not None or state.granted is None or event.consent_id != state.granted.command.ack.id
                    or state.revoked_at is not None or instant(envelope.occurred_at) >= instant(original.summary.expires_at)):
                raise damaged()
            state.queued = event
        elif isinstance(event, CodexDispatchStarted):
            if (state.queued is None or event.dispatch_id != state.queued.dispatch_id or state.started is not None
                    or state.finished is not None or state.revoked_at is not None
                    or event.request_body_sha256 != original.summary.request_body_sha256
                    or instant(envelope.occurred_at) >= instant(original.summary.expires_at)
                    or instant(event.lease.expires_at) <= instant(envelope.occurred_at)):
                raise damaged()
            state.started, state.started_at = event, envelope.occurred_at
        elif isinstance(event, CodexDispatchFinished):
            if (state.queued is None or event.dispatch_id != state.queued.dispatch_id or state.finished is not None
                    or state.started is None and (event.outcome == 'completed' or event.answer or event.usage.input_tokens is not None or event.usage.output_tokens is not None)
                    or (event.outcome == 'completed') != (event.error_code is None)
                    or state.started_at is not None and instant(envelope.occurred_at) < instant(state.started_at)):
                raise damaged()
            state.finished, state.finished_at = event, envelope.occurred_at
        else:
            raise damaged()

    def append(self, turn_id: str, event, now: str, state: CodexProviderState | None) -> CodexProviderEnvelope:
        ProviderRepository(self.conn, self.workspace).writable()
        seq, previous = (len(state.envelopes)+1, state.digest) if state else (1, None)
        envelope = CodexProviderEnvelope(version='provider-codex-ledger-v1', workspace_id=self.workspace,
            turn_id=turn_id, seq=seq, previous_sha256=previous, occurred_at=now, event=event)
        digest = content_sha256(envelope)
        self.conn.execute('INSERT INTO provider_codex_events VALUES(?,?,?,?,?)', (self.workspace,turn_id,seq,canonical_json(envelope),digest))
        self.conn.execute('INSERT INTO provider_codex_members VALUES(?,?,?,?)', (self.workspace,turn_id,seq,digest))
        command = getattr(event, 'command', None)
        if command is not None:
            self.conn.execute('INSERT INTO provider_codex_commands VALUES(?,?,?,?,?,?,?)',
                (self.workspace,command.actor_session_id,command.route,command.key,turn_id,seq,content_sha256(command)))
        if state is None:
            self.conn.execute('INSERT INTO provider_codex_heads VALUES(?,?,?,?)', (self.workspace,turn_id,seq,digest))
        elif self.conn.execute('UPDATE provider_codex_heads SET event_count=?,head_sha256=? WHERE workspace_id=? AND turn_id=? AND event_count=? AND head_sha256=?',
                (seq,digest,self.workspace,turn_id,seq-1,previous)).rowcount != 1:
            raise damaged()
        return envelope

    @staticmethod
    def replay(states, actor: str, route: str, key: str, body):
        for state in states.values():
            for envelope in state.envelopes:
                command = getattr(envelope.event, 'command', None)
                if command is not None and (command.actor_session_id,command.route,command.key)==(actor,route,key):
                    if canonical_json(command.body)!=canonical_json(body):
                        raise ApiError(409,'IDEMPOTENCY_CONFLICT','原命令与本次完整输入不一致。')
                    return command.ack
        return None
