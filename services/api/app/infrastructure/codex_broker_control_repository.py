"""Complete Broker head/members and authoritative existing-turn witnesses."""
from dataclasses import dataclass, field

from packages.contracts.canonical import strict_json
from ..application.codex_broker_control_models import (
    BrokerControlEnvelope, BrokerMapping, BrokerMappingBound, BrokerInterruptPrepared,
    BrokerInterruptStarted, BrokerFrameObserved, BrokerControlClosed, TurnBrokerControlBound,
)
from ..application.codex_interrupt_protocol_models import InterruptExchange
from ..application.codex_turn_context import damaged
from ..serialization import canonical_json, content_sha256
from .codex_interrupt_protocol import prepare_interrupt, observe_interrupt


@dataclass
class CheckedBrokerControl:
    mapping: BrokerMapping
    records: list[BrokerControlEnvelope] = field(default_factory=list)
    prepared: BrokerInterruptPrepared | None = None
    started: BrokerInterruptStarted | None = None
    exchange: InterruptExchange | None = None
    closed: BrokerControlClosed | None = None


def first_stop(state, turn_id):
    for envelope in state.envelopes:
        event = envelope.event
        if event.kind == 'interrupt_recorded':
            event = event.stop
        if event.kind == 'cancel_requested' and event.turn_id == turn_id:
            return envelope
    return None


class CodexBrokerControlRepository:
    def __init__(self, conn, workspace, source):
        if not conn.in_transaction:
            raise damaged()
        self.conn, self.workspace, self.source = conn, workspace, source

    def checked(self, originals, history):
        try:
            return self._checked(originals, history)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            raise damaged() from None

    def _checked(self, originals, history):
        records = self.conn.execute('SELECT * FROM codex_broker_records WHERE workspace_id=?', (self.workspace,)).fetchall()
        members = self.conn.execute('SELECT * FROM codex_broker_members WHERE workspace_id=?', (self.workspace,)).fetchall()
        heads = self.conn.execute('SELECT * FROM codex_broker_heads WHERE workspace_id=?', (self.workspace,)).fetchall()
        expected = {(turn.control.id, ref.ordinal, ref.record_sha256)
            for state in history.values() for turn in state.turns.values() for ref in turn.broker_bindings}
        if (expected != {(r['turn_id'], r['ordinal'], r['record_sha256']) for r in records}
                or expected != {(r['turn_id'], r['ordinal'], r['record_sha256']) for r in members}
                or {r['turn_id'] for r in heads} != {item[0] for item in expected}):
            raise damaged()
        result = {}
        for state in history.values():
            for turn in state.turns.values():
                if not turn.broker_bindings:
                    continue
                selected = sorted((r for r in records if r['turn_id'] == turn.control.id), key=lambda r:r['ordinal'])
                head = next(r for r in heads if r['turn_id'] == turn.control.id)
                if (head['event_count'] != len(selected) or head['head_sha256'] != selected[-1]['record_sha256']):
                    raise damaged()
                previous, snapshot = None, None
                for ordinal, row in enumerate(selected, 1):
                    value = BrokerControlEnvelope.model_validate(strict_json(row['record_json']))
                    digest = content_sha256(value)
                    if (canonical_json(value) != row['record_json'] or digest != row['record_sha256']
                            or value.workspace_id != self.workspace or value.turn_id != turn.control.id
                            or value.ordinal != ordinal or value.previous_sha256 != previous):
                        raise damaged()
                    event = value.event
                    if isinstance(event, BrokerMappingBound):
                        mapping = event.mapping
                        original = originals[state.anchor.session_id]
                        claim = next((item for item in turn.lifecycle if item.phase == 'claim'), None)
                        if (ordinal != 1 or snapshot is not None or claim is None
                                or original.finished is None or original.finished.outcome.status != 'ready'
                                or mapping.upstream_thread_id != original.finished.outcome.thread_id
                                or mapping.bootstrap_sha256 != content_sha256(original)
                                or mapping.local_thread_id != state.anchor.thread_id
                                or mapping.workspace_id != self.workspace or mapping.session_id != state.anchor.session_id
                                or mapping.turn_id != turn.control.id or mapping.job_id != turn.control.job.id
                                or mapping.actor_session_id != turn.prepared.input.actor_session_id
                                or mapping.preparation_sha256 != turn.prepared.command.ack.preparation_sha256
                                or mapping.claim_provider_sha256 != claim.provider_sha256):
                            raise damaged()
                        snapshot = CheckedBrokerControl(mapping)
                    elif snapshot is None or snapshot.closed is not None:
                        raise damaged()
                    elif isinstance(event, BrokerInterruptPrepared):
                        intent = first_stop(state, turn.control.id)
                        if snapshot.prepared is not None or intent is None or (event.intent_seq, event.intent_sha256) != (intent.seq, content_sha256(intent)):
                            raise damaged()
                        exchange = prepare_interrupt(self.source, event.request.raw)
                        if (exchange.request.wire.params.thread_id != snapshot.mapping.upstream_thread_id
                                or exchange.request.wire.params.turn_id != snapshot.mapping.upstream_turn_id):
                            raise damaged()
                        snapshot.prepared, snapshot.exchange = event, exchange
                    elif isinstance(event, BrokerInterruptStarted):
                        if snapshot.prepared is None or snapshot.started is not None or event.request_sha256 != snapshot.prepared.request.sha256:
                            raise damaged()
                        snapshot.started = event
                    elif isinstance(event, BrokerFrameObserved):
                        if snapshot.started is None or snapshot.exchange is None:
                            raise damaged()
                        observed = observe_interrupt(self.source, snapshot.exchange, event.frame.raw)
                        if (observed.accepted, observed.reason) != (event.accepted, event.reason):
                            raise damaged()
                        snapshot.exchange = observed.exchange
                    elif isinstance(event, BrokerControlClosed):
                        snapshot.closed = event
                    else:
                        raise damaged()
                    if snapshot is None:
                        raise damaged()
                    snapshot.records.append(value)
                    previous = digest
                result[turn.control.id] = snapshot
        return result

    def append(self, turn_repo, state, turn, snapshot, event, now):
        records = snapshot.records if snapshot else []
        value = BrokerControlEnvelope(version='codex-broker-control-event-v1', workspace_id=self.workspace,
            turn_id=turn.control.id, ordinal=len(records)+1,
            previous_sha256=content_sha256(records[-1]) if records else None, occurred_at=now, event=event)
        digest = content_sha256(value)
        self.conn.execute('INSERT INTO codex_broker_records VALUES(?,?,?,?,?)',
            (self.workspace, turn.control.id, value.ordinal, canonical_json(value), digest))
        self.conn.execute('INSERT INTO codex_broker_members VALUES(?,?,?,?)',
            (self.workspace, turn.control.id, value.ordinal, digest))
        if records:
            changed = self.conn.execute('UPDATE codex_broker_heads SET event_count=?,head_sha256=? WHERE turn_id=? AND workspace_id=? AND event_count=? AND head_sha256=?',
                (value.ordinal,digest,turn.control.id,self.workspace,len(records),value.previous_sha256)).rowcount
            if changed != 1:
                raise damaged()
        else:
            self.conn.execute('INSERT INTO codex_broker_heads VALUES(?,?,?,?)', (self.workspace,turn.control.id,1,digest))
        witness = TurnBrokerControlBound(kind='broker_control_bound', turn_id=turn.control.id,
            ordinal=value.ordinal, record_sha256=digest)
        state.envelopes.append(turn_repo.append(state,witness,now))
        return value
