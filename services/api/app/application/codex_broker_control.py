"""Broker controls wired to real owners, with a synthetic-only live boundary.

HTTP only stages durable intent. The exact current worker callback owns a
process-free peer; conservative start commits before its one control request.
Neither empty replies nor paired terminal frames are a local terminal proof.
"""
from collections.abc import Callable
from dataclasses import dataclass
import threading
from uuid import uuid4

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from ..infrastructure.codex_broker_control_repository import CodexBrokerControlRepository, first_stop
from ..infrastructure.codex_interrupt_protocol import read_interrupt_source, observe_interrupt
from ..infrastructure.database import utc_now
from ..infrastructure.security import SessionIdentity
from ..serialization import content_sha256
from .codex_bootstrap_access import current_control_access
from .codex_turn_context import damaged
from .codex_broker_control_models import (
    BrokerMapping, BrokerMappingBound, BrokerRawFrame, BrokerInterruptPrepared,
    BrokerInterruptStarted, BrokerFrameObserved, BrokerControlClosed,
)
from .errors import ApiError


@dataclass(frozen=True)
class _LivePeer:
    mapping: BrokerMapping
    callback_thread: int
    transport: Callable[[bytes], list[bytes]]


class CodexBrokerControls:
    def __init__(self, turns, provider):
        self.turns, self.provider = turns, provider
        self.source = read_interrupt_source()
        self._live: dict[str, _LivePeer] = {}
        self._lock = threading.RLock()

    def verify_history(self, conn, workspace, originals, history):
        return CodexBrokerControlRepository(conn, workspace, self.source).checked(originals, history)

    @staticmethod
    def verify_started(snapshots, provider_states):
        for turn_id, snapshot in snapshots.items():
            state = provider_states.get(turn_id)
            started = state.started if state else None
            if (started is None or snapshot.mapping.execution_owner_id != started.execution_owner_id
                    or snapshot.mapping.claim_lease != started.lease):
                raise damaged()

    def _owned(self, conn, workspace):
        originals, repo, history = self.turns._owned_state(conn, workspace)
        snapshots = self.verify_history(conn, workspace, originals, history)
        provider_states, _ = self.provider.owned_states(conn, workspace)
        self.verify_started(snapshots, provider_states)
        return originals, repo, history, snapshots, provider_states

    @staticmethod
    def _active(turns, conn, workspace, state, turn, provider_state, owner):
        started = provider_state.started if provider_state else None
        lease = turns.dispatch_lease(conn, workspace, turn.control.job.id)
        return (turn.control.execution == 'active' and state.active_turn_id == turn.control.id
            and started is not None and started.execution_owner_id == owner and lease is not None
            and lease.owner_id == started.lease.owner_id and lease.expires_at > utc_now())

    def bind_peer(self, workspace, turn_id, owner, callback_thread, upstream_turn_id, transport):
        """Called only by the exact synthetic worker's current callback port."""
        if callback_thread != threading.get_ident() or not callable(transport):
            raise ApiError(409, 'CODEX_BINDING_INVALID', '没有原执行实例控制映射。')
        with self._lock:
            with self.turns.database.transaction() as conn:
                originals, repo, history, snapshots, states = self._owned(conn, workspace)
                state, turn = self.turns._find(history, turn_id)
                provider_state = states.get(turn_id)
                if turn_id in snapshots or not self._active(self.turns, conn, workspace, state, turn, provider_state, owner):
                    raise ApiError(409, 'CODEX_BINDING_INVALID', '没有原执行实例控制映射。')
                original = originals[state.anchor.session_id]
                if original.finished is None or original.finished.outcome.thread_id is None:
                    raise damaged()
                claim = next(item for item in turn.lifecycle if item.phase == 'claim')
                mapping = BrokerMapping(version='codex-synthetic-broker-mapping-v1', scope='synthetic_peer_only',
                    production_qualified=False, workspace_id=workspace, session_id=state.anchor.session_id,
                    turn_id=turn_id, job_id=turn.control.job.id, actor_session_id=turn.prepared.input.actor_session_id,
                    local_thread_id=state.anchor.thread_id, upstream_thread_id=original.finished.outcome.thread_id,
                    upstream_turn_id=upstream_turn_id, bootstrap_sha256=content_sha256(original),
                    preparation_sha256=turn.prepared.command.ack.preparation_sha256,
                    claim_provider_sha256=claim.provider_sha256, execution_owner_id=owner,
                    claim_lease=provider_state.started.lease)
                CodexBrokerControlRepository(conn, workspace, self.source).append(repo, state, turn, None,
                    BrokerMappingBound(kind='mapping_bound', mapping=mapping), utc_now())
                self._owned(conn, workspace)
            self._live[turn_id] = _LivePeer(mapping, callback_thread, transport)

    def read_control(self, conn, identity: SessionIdentity, turn_id):
        current = current_control_access(conn, identity, write=False)
        _, _, history, snapshots, _ = self._owned(conn, current.workspace_id)
        self.turns._find(history, turn_id)
        return snapshots.get(turn_id)

    def request_interrupt(self, conn, identity: SessionIdentity, turn_id):
        """Caller transaction: freeze one request from durable stop + live owner."""
        current = current_control_access(conn, identity, write=False)
        with self._lock:
            _, repo, history, snapshots, states = self._owned(conn, current.workspace_id)
            state, turn = self.turns._find(history, turn_id)
            snapshot, live = snapshots.get(turn_id), self._live.get(turn_id)
            if (snapshot is None or snapshot.prepared is not None or snapshot.closed is not None
                    or live is None or live.mapping != snapshot.mapping or not turn.control.cancel_requested
                    or not self._active(self.turns, conn, current.workspace_id, state, turn, states.get(turn_id), live.mapping.execution_owner_id)):
                return False
            intent = first_stop(state, turn_id)
            if intent is None:
                raise damaged()
            raw = canonical_bytes({'id':'codex_interrupt_'+uuid4().hex, 'method':'turn/interrupt',
                'params':{'threadId':snapshot.mapping.upstream_thread_id,'turnId':snapshot.mapping.upstream_turn_id}})
            event = BrokerInterruptPrepared(kind='interrupt_prepared', intent_seq=intent.seq,
                intent_sha256=content_sha256(intent), request=BrokerRawFrame(raw_hex=raw.hex(), sha256=sha256_bytes(raw)))
            CodexBrokerControlRepository(conn, current.workspace_id, self.source).append(repo, state, turn, snapshot, event, utc_now())
            self._owned(conn, current.workspace_id)
            return True

    def _close_owned(self, conn, workspace, turn_id, reason):
        _, repo, history, snapshots, _ = self._owned(conn, workspace)
        snapshot = snapshots.get(turn_id)
        if snapshot is None or snapshot.closed is not None:
            return False
        state, turn = self.turns._find(history, turn_id)
        CodexBrokerControlRepository(conn, workspace, self.source).append(repo, state, turn, snapshot,
            BrokerControlClosed(kind='control_closed', reason=reason), utc_now())
        self._owned(conn, workspace)
        return True

    def recover_control(self, conn, identity: SessionIdentity, turn_id):
        current = current_control_access(conn, identity, write=False)
        with self._lock:
            _, _, history, snapshots, states = self._owned(conn, current.workspace_id)
            state, turn = self.turns._find(history, turn_id)
            snapshot, live = snapshots.get(turn_id), self._live.get(turn_id)
            if snapshot is None or snapshot.closed is not None:
                return False
            if (live is not None and live.mapping == snapshot.mapping
                    and self._active(self.turns, conn, current.workspace_id, state, turn, states.get(turn_id), live.mapping.execution_owner_id)):
                return False
            return self._close_owned(conn, current.workspace_id, turn_id, 'live_mapping_lost')

    def release(self, workspace, turn_id, owner):
        with self._lock:
            live = self._live.get(turn_id)
            if live is None or live.mapping.execution_owner_id != owner:
                return
            del self._live[turn_id]
            with self.turns.database.transaction() as conn:
                self._close_owned(conn, workspace, turn_id, 'execution_finished')

    def interrupt_once(self, workspace, turn_id, owner, callback_thread):
        # The same worker callback is the only sender. HTTP/GET has no transport.
        if callback_thread != threading.get_ident():
            return False
        with self._lock:
            with self.turns.database.transaction() as conn:
                _, repo, history, snapshots, states = self._owned(conn, workspace)
                state, turn = self.turns._find(history, turn_id)
                snapshot, live = snapshots.get(turn_id), self._live.get(turn_id)
                if snapshot is None or snapshot.prepared is None or snapshot.started is not None or snapshot.closed is not None:
                    return False
                if (live is None or live.mapping != snapshot.mapping or live.callback_thread != callback_thread
                        or live.mapping.execution_owner_id != owner
                        or not self._active(self.turns, conn, workspace, state, turn, states.get(turn_id), owner)):
                    self._close_owned(conn, workspace, turn_id, 'live_mapping_lost')
                    return False
                raw = snapshot.prepared.request.raw
                CodexBrokerControlRepository(conn, workspace, self.source).append(repo, state, turn, snapshot,
                    BrokerInterruptStarted(kind='interrupt_started', request_sha256=snapshot.prepared.request.sha256), utc_now())
                self._owned(conn, workspace)
            # Possible-send is durable. Failure or missing ACK never retries.
            try:
                frames = live.transport(raw)
                if type(frames) not in (list, tuple) or len(frames) > 64:
                    raise ValueError('A bounded complete pure-peer frame batch is required')
                for raw_frame in frames:
                    with self.turns.database.transaction() as conn:
                        _, repo, history, snapshots, _ = self._owned(conn, workspace)
                        state, turn = self.turns._find(history, turn_id)
                        snapshot = snapshots[turn_id]
                        observed = observe_interrupt(self.source, snapshot.exchange, raw_frame)
                        event = BrokerFrameObserved(kind='frame_observed',
                            frame=BrokerRawFrame(raw_hex=raw_frame.hex(), sha256=sha256_bytes(raw_frame)),
                            accepted=observed.accepted, reason=observed.reason)
                        CodexBrokerControlRepository(conn, workspace, self.source).append(repo, state, turn, snapshot, event, utc_now())
                        self._owned(conn, workspace)
            except Exception:
                # Preserve every committed prior frame and the possible-send.
                with self.turns.database.transaction() as conn:
                    self._close_owned(conn, workspace, turn_id, 'transport_unknown')
            return True
