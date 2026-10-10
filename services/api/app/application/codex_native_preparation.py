"""Private lifetime staging for server-owned Codex preparation sources.

Keeping a resource here supplies no runtime profile, InputProof, or permission to
send. Only an explicitly injected SDK adapter can produce the retained resource.
"""
from dataclasses import dataclass, field
from threading import RLock
from typing import Protocol

from ..serialization import canonical_json
from ..infrastructure.security import SessionIdentity
from .codex_bootstrap_models import BootstrapSnapshot
from .codex_turn_models import TurnInput
from .codex_turn_execution_models import RunnableTurnInput
from .codex_turn_context import FrozenTurnContext
from .errors import ApiError


@dataclass(frozen=True)
class NativePreparationSources:
    workspace_id: str
    actor_session_id: str
    job_id: str
    bootstrap_json: bytes = field(repr=False)
    turn_json: bytes = field(repr=False)
    context_json: bytes = field(repr=False)


class PreparedNativeResource(Protocol):
    def close(self) -> None: ...


class NativeTurnPreparer(Protocol):
    def prepare(self, sources: NativePreparationSources) -> PreparedNativeResource | None: ...


@dataclass
class _Slot:
    job_id: str
    resource: PreparedNativeResource | None = field(default=None, repr=False)
    closed: bool = False
    committed: bool = False


class NativePreparationStore:
    """Own pending and committed resources without admitting a sender."""

    def __init__(self, preparer: NativeTurnPreparer | None = None):
        self._preparer = preparer
        self._lock = RLock()
        self._slots: dict[str, _Slot] = {}
        self._closed = False

    def staging(self) -> "NativePreparationStage":
        return NativePreparationStage(self)

    def _reserve(self, job_id: str) -> _Slot:
        with self._lock:
            if self._closed or job_id in self._slots:
                raise ApiError(409, 'CODEX_INPUT_PROOF_UNAVAILABLE', '本地准备资源不能重建或替换。')
            slot = _Slot(job_id)
            self._slots[job_id] = slot
            return slot

    @staticmethod
    def _close_resource(resource: PreparedNativeResource) -> None:
        try:
            resource.close()
        except Exception:
            raise ApiError(409, 'CODEX_INPUT_PROOF_UNAVAILABLE', '本地准备资源释放失败；该资源已失效。') from None

    def _attach(self, slot: _Slot, resource: PreparedNativeResource) -> None:
        with self._lock:
            close = slot.closed or self._slots.get(slot.job_id) is not slot
            if not close:
                slot.resource = resource
        if close:
            self._close_resource(resource)

    def _publish(self, slot: _Slot) -> None:
        with self._lock:
            if not slot.closed and self._slots.get(slot.job_id) is slot:
                slot.committed = True

    def _discard(self, slot: _Slot) -> None:
        with self._lock:
            if self._slots.get(slot.job_id) is slot:
                del self._slots[slot.job_id]
            slot.closed = True
            resource, slot.resource = slot.resource, None
        if resource is not None:
            self._close_resource(resource)

    def close_job(self, job_id: str) -> None:
        with self._lock:
            slot = self._slots.get(job_id)
        if slot is not None:
            self._discard(slot)

    def close_all(self) -> None:
        with self._lock:
            self._closed = True
            slots = list(self._slots.values())
        failed = False
        for slot in slots:
            try:
                self._discard(slot)
            except ApiError:
                failed = True
        if failed:
            raise ApiError(409, 'CODEX_INPUT_PROOF_UNAVAILABLE', '本地准备资源释放失败；所有资源已失效。')


class NativePreparationStage:
    def __init__(self, owner: NativePreparationStore):
        self._owner = owner
        self._slots: list[_Slot] = []

    def __enter__(self) -> "NativePreparationStage":
        return self

    def prepare(self, identity: SessionIdentity, bootstrap: BootstrapSnapshot,
                value: TurnInput | RunnableTurnInput, context: FrozenTurnContext) -> None:
        preparer = self._owner._preparer
        if preparer is None:
            return
        # All three snapshots come from the checked private prepare transaction.
        # Their bytes describe platform sources; they are not SDK Prompt proof.
        sources = NativePreparationSources(
            workspace_id=identity.workspace_id, actor_session_id=identity.id, job_id=value.job_id,
            bootstrap_json=canonical_json(bootstrap).encode('utf-8'),
            turn_json=canonical_json(value).encode('utf-8'),
            context_json=canonical_json(context).encode('utf-8'))
        slot = self._owner._reserve(value.job_id)
        self._slots.append(slot)
        resource = preparer.prepare(sources)
        if resource is None:
            self._owner._discard(slot)
        else:
            self._owner._attach(slot, resource)

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        for slot in self._slots:
            if exc_type is None:
                self._owner._publish(slot)
            else:
                try:
                    self._owner._discard(slot)
                except ApiError:
                    # Keep the transaction failure as the primary exception.
                    # Discard invalidates the slot before its close callback.
                    pass
