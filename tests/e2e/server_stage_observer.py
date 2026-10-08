"""Opt-in E2E metadata; never imported by the production app factory."""
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from itertools import count
from pathlib import Path
from threading import Lock, local
from time import monotonic_ns
from typing import Any


class Phase(str, Enum):
    TICK = "import-tick"
    EVIDENCE = "maintenance-evidence"
    RECOMMENDATION = "maintenance-recommendation"
    RETRIEVAL = "maintenance-retrieval"
    RECOVER = "grading-recover"
    CLAIM = "grading-claim"
    COMPUTE = "grading-compute"
    FINISH = "grading-finish"
    REGRADE = "regrade"
    RESULT = "get-result"
    WAL = "result-wal"
    POLICY = "result-policy"


class Edge(str, Enum):
    ENTER = "enter"
    READY = "transaction-ready"
    EXIT = "exit"
    STATUS = "existing-status-read"
    COMMITTED = "new-enqueue-committed"


class Outcome(str, Enum):
    RETURNED = "returned"
    RAISED = "raised"
    NO_WORK = "no-work"


class Status(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNOBSERVED = "unobserved"


class Boundary(str, Enum):
    COLLECTOR = "collector-freeze"
    LIFESPAN_RETURNED = "original-lifespan-returned"
    LIFESPAN_RAISED = "original-lifespan-raised"


class Collector:
    """Bounded RAM events, non-blocking admission, one cleanup write."""

    def __init__(self, *, limit: int = 512, clock: Callable[[], int] = monotonic_ns):
        if type(limit) is not int or not 1 <= limit <= 512:
            raise ValueError("invalid event limit")
        self._limit, self._clock = limit, clock
        self._lock = Lock()
        self._tickets, self._dropped, self._errors, self._scopes = count(1), count(), count(), count(1)
        self._events: list[dict[str, Any]] = []
        self._jobs: dict[tuple[str, str], int] = {}
        self._armed = self._frozen = False
        self._snapshot: dict[str, Any] | None = None
        self._origin = self.elapsed(raw=True)

    def __repr__(self) -> str:
        return "<E2EServerStageCollector metadata-only>"

    @property
    def armed(self) -> bool:
        return self._armed and not self._frozen

    def arm(self) -> None:
        if not self._frozen:
            self._armed = True

    def error(self) -> None:
        if not self._frozen:
            next(self._errors)

    def elapsed(self, *, raw: bool = False) -> int | None:
        try:
            value = self._clock()
            if type(value) is not int:
                raise ValueError("invalid clock")
            if raw:
                return value
            if self._origin is None or value < self._origin:
                raise ValueError("unavailable clock")
            return value - self._origin
        except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
            self.error()
            return None

    def scope(self) -> int | None:
        value = next(self._scopes)
        return value if value <= 4096 else None

    def job(self, workspace: Any, identifier: Any) -> int | None:
        """Pseudonymize only an existing owned result/lease; never export its IDs."""
        if not self.armed:
            return None
        if (type(workspace) is not str or type(identifier) is not str
                or not 1 <= len(workspace) <= 256 or not 1 <= len(identifier) <= 256):
            return None
        if not self._lock.acquire(blocking=False):
            next(self._dropped)
            return None
        try:
            if self._frozen:
                return None
            key = (workspace, identifier)
            known = self._jobs.get(key)
            if known is not None:
                return known
            if len(self._jobs) >= 64:
                self.error()
                return None
            ordinal = len(self._jobs) + 1
            self._jobs[key] = ordinal
            return ordinal
        finally:
            self._lock.release()

    def emit(self, phase: Phase, edge: Edge, *, scope: int | None = None,
             parent: int | None = None, duration_ns: int | None = None,
             outcome: Outcome | None = None, status: Status | None = None,
             job: int | None = None) -> None:
        if not self.armed:
            return
        try:
            if not isinstance(phase, Phase) or not isinstance(edge, Edge):
                raise TypeError("invalid phase")
            if outcome is not None and not isinstance(outcome, Outcome):
                raise ValueError("invalid outcome")
            if status is not None and not isinstance(status, Status):
                raise ValueError("invalid status")
            for value in (scope, parent):
                if value is not None and (type(value) is not int or not 1 <= value <= 4096):
                    raise ValueError("invalid scope")
            if job is not None and (type(job) is not int or not 1 <= job <= 64):
                raise ValueError("invalid job ordinal")
            if duration_ns is not None and (type(duration_ns) is not int or duration_ns < 0):
                raise ValueError("invalid duration")
            if not self._lock.acquire(blocking=False):
                next(self._dropped)
                return
            try:
                if self._frozen:
                    return
                sequence = next(self._tickets)
                if sequence > self._limit:
                    next(self._dropped)
                    return
                elapsed = self.elapsed()
                if elapsed is None:
                    return
                event = {"seq": sequence, "elapsed_ns": elapsed, "phase": phase.value, "edge": edge.value}
                for key, value in (("scope", scope), ("parent", parent),
                                   ("duration_ns", duration_ns), ("job", job)):
                    if value is not None:
                        event[key] = value
                if outcome is not None:
                    event["outcome"] = outcome.value
                if status is not None:
                    event["status"] = status.value
                self._events.append(event)
            finally:
                self._lock.release()
        except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
            self.error()

    def freeze(self, boundary: Boundary = Boundary.COLLECTOR) -> dict[str, Any]:
        if self._snapshot is not None:
            return deepcopy(self._snapshot)
        if not isinstance(boundary, Boundary):
            self.error()
            boundary = Boundary.COLLECTOR
        self._frozen = True
        acquired = self._lock.acquire(blocking=False)
        try:
            self._snapshot = {
                "version": "e2e-server-stage-metadata-v2",
                "clock": "same-server-process monotonic_ns since observer construction",
                "capture_state": "frozen" if acquired else "finalize-contended",
                "armed": self._armed, "events": deepcopy(self._events) if acquired else [],
                "limit": self._limit, "dropped": next(self._dropped), "diagnostic_errors": next(self._errors),
                "finally_marker": boundary.value,
                "scope": "Fixed enums/durations and task-local scopes with bounded server-local job ordinals. Raw IDs remain only in the private RAM association map, never in output. Missing ordinals cannot correlate jobs. No body, headers, SQL or exception text. Queued is an existing WAL read snapshot, not permanent inactivity.",
            }
        finally:
            if acquired:
                self._jobs.clear()
                self._lock.release()
        return deepcopy(self._snapshot)

    def save(self, path: Path, *, writer: Callable[..., Any] | None = None,
             boundary: Boundary = Boundary.COLLECTOR) -> bool:
        try:
            snapshot = self.freeze(boundary)
            with (writer if writer is not None else path.open)("x", encoding="utf-8") as output:
                json.dump(snapshot, output, ensure_ascii=True, separators=(",", ":"))
                output.write("\n")
            return True
        except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
            return False


@dataclass
class _Scope:
    phase: Phase
    ordinal: int | None
    parent: int | None
    transactions: int = 0
    enqueued: bool = False
    job: int | None = None


class OwnedBindings:
    """Bind the composed test app; no owner/process/storage discovery."""

    def __init__(self, collector: Collector, database: Any, worker: Any,
                 grading_service_type: type, grading_repository_type: type):
        self.collector, self.database, self.worker = collector, database, worker
        self.service_type, self.repository_type = grading_service_type, grading_repository_type
        self._local = local()
        self._restores: list[tuple[Any, str, Any, Any, bool]] = []

    def _current(self) -> _Scope | None:
        return getattr(self._local, "scope", None)

    def _safe(self, method: str, *args: Any, **kwargs: Any) -> Any:
        try:
            return getattr(self.collector, method)(*args, **kwargs)
        except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
            if method != "error":
                try:
                    self.collector.error()
                except BaseException:  # noqa: BLE001, S110 - A broken diagnostic counter cannot replace business outcome.
                    pass
            return None

    def _enabled(self) -> bool:
        try:
            return self.collector.armed
        except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
            return False

    def _duration(self, started: int | None) -> int | None:
        finished = self._safe("elapsed")
        return finished - started if type(started) is int and type(finished) is int and finished >= started else None

    def _lease_job(self, lease: Any) -> int | None:
        try:
            return self._safe("job", getattr(lease, "workspace_id", None),
                              getattr(lease, "job_id", None))
        except BaseException:  # noqa: BLE001 - Diagnostic access cannot replace the original outcome.
            self._safe("error")
            return None

    def _call(self, phase: Phase, original: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if phase is Phase.REGRADE:
            self._safe("arm")
        if not self._enabled():
            return original(*args, **kwargs)
        try:
            previous = self._current()
            scope = _Scope(phase, self._safe("scope"), previous.ordinal if previous else None)
            if phase in (Phase.COMPUTE, Phase.FINISH):
                scope.job = self._lease_job(args[0] if args else kwargs.get("lease"))
            started = self._safe("elapsed")
            self._local.scope = scope
            self._safe("emit", phase, Edge.ENTER, scope=scope.ordinal, parent=scope.parent, job=scope.job)
        except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
            return original(*args, **kwargs)
        try:
            value = original(*args, **kwargs)
        except BaseException:
            self._safe("emit", phase, Edge.EXIT, scope=scope.ordinal, parent=scope.parent,
                       duration_ns=self._duration(started), outcome=Outcome.RAISED, job=scope.job)
            raise
        else:
            if phase is Phase.CLAIM and value is not None:
                scope.job = self._lease_job(value)
            if phase is Phase.REGRADE and scope.enqueued:
                self._safe("emit", phase, Edge.COMMITTED, scope=scope.ordinal, parent=scope.parent, job=scope.job)
            no_work = (phase is Phase.CLAIM and value is None) or (
                phase in (Phase.TICK, Phase.EVIDENCE, Phase.RECOMMENDATION, Phase.RETRIEVAL) and value is False)
            self._safe("emit", phase, Edge.EXIT, scope=scope.ordinal, parent=scope.parent,
                       duration_ns=self._duration(started), outcome=Outcome.NO_WORK if no_work else Outcome.RETURNED,
                       job=scope.job)
            return value
        finally:
            self._local.scope = previous

    def _replace(self, owner: Any, name: str, wrapped: Any) -> None:
        original, own = getattr(owner, name), name in vars(owner)
        setattr(owner, name, wrapped)
        self._restores.append((owner, name, original, wrapped, own))

    def install(self) -> bool:
        try:
            for owner, name, phase in (
                (self.worker, "run_once", Phase.TICK),
                (self.worker.evidence_recovery, "run_once", Phase.EVIDENCE),
                (self.worker.recommendations, "run_once", Phase.RECOMMENDATION),
                (self.worker.retrieval, "run_once", Phase.RETRIEVAL),
                (self.worker.grading, "recover", Phase.RECOVER),
                (self.worker.grading, "claim", Phase.CLAIM),
                (self.worker.grading, "compute", Phase.COMPUTE),
                (self.worker.grading, "finish", Phase.FINISH),
            ):
                original = getattr(owner, name)
                def bind(original: Any, phase: Phase) -> Any:
                    return lambda *a, **kw: self._call(phase, original, *a, **kw)
                self._replace(owner, name, bind(original, phase))
            original_transaction = self.database.transaction

            @contextmanager
            def observed_transaction(*args: Any, **kwargs: Any) -> Iterator[Any]:
                scope = self._current()
                if scope is None or not self._enabled():
                    with original_transaction(*args, **kwargs) as connection:
                        yield connection
                    return
                scope.transactions += 1
                phase = (Phase.WAL if scope.transactions == 1 else Phase.POLICY) if scope.phase is Phase.RESULT else scope.phase
                started = self._safe("elapsed")
                self._safe("emit", phase, Edge.ENTER, scope=scope.ordinal, parent=scope.parent, job=scope.job)
                try:
                    with original_transaction(*args, **kwargs) as connection:
                        self._safe("emit", phase, Edge.READY, scope=scope.ordinal, parent=scope.parent,
                                   duration_ns=self._duration(started), job=scope.job)
                        yield connection
                except BaseException:
                    self._safe("emit", phase, Edge.EXIT, scope=scope.ordinal, parent=scope.parent,
                               duration_ns=self._duration(started), outcome=Outcome.RAISED, job=scope.job)
                    raise
                else:
                    self._safe("emit", phase, Edge.EXIT, scope=scope.ordinal, parent=scope.parent,
                               duration_ns=self._duration(started), outcome=Outcome.RETURNED, job=scope.job)

            self._replace(self.database, "transaction", observed_transaction)
            for name, phase in (("regrade", Phase.REGRADE), ("result", Phase.RESULT)):
                original = getattr(self.service_type, name)
                def bind_service(original: Any, phase: Phase) -> Any:
                    def service(receiver: Any, *args: Any, **kwargs: Any) -> Any:
                        if receiver.database is not self.database:
                            return original(receiver, *args, **kwargs)
                        return self._call(phase, original, receiver, *args, **kwargs)
                    return service
                self._replace(self.service_type, name, bind_service(original, phase))
            original_enqueue = self.repository_type.enqueue

            def enqueue(receiver: Any, *args: Any, **kwargs: Any) -> Any:
                value = original_enqueue(receiver, *args, **kwargs)
                try:
                    scope = self._current()
                    if scope is not None and scope.phase is Phase.REGRADE:
                        scope.enqueued = True
                        scope.job = self._safe("job", getattr(receiver, "workspace_id", None),
                                               getattr(value, "id", None))
                except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
                    self._safe("error")
                return value

            self._replace(self.repository_type, "enqueue", enqueue)
            original_latest = self.repository_type.latest_job

            def latest_job(receiver: Any, *args: Any, **kwargs: Any) -> Any:
                value = original_latest(receiver, *args, **kwargs)
                try:
                    scope = self._current()
                    if scope is not None and scope.phase is Phase.RESULT:
                        try:
                            status = Status(value["status"]) if value is not None else Status.UNOBSERVED
                        except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
                            status = Status.UNOBSERVED
                            self._safe("error")
                        scope.job = self._safe("job", getattr(receiver, "workspace_id", None),
                                               value["id"] if value is not None else None)
                        self._safe("emit", Phase.WAL, Edge.STATUS, scope=scope.ordinal, parent=scope.parent,
                                   status=status, job=scope.job)
                except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
                    self._safe("error")
                return value

            self._replace(self.repository_type, "latest_job", latest_job)
            return True
        except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
            self._safe("error")
            self.restore()
            return False

    def restore(self) -> None:
        for owner, name, original, wrapped, own in reversed(self._restores):
            try:
                if getattr(owner, name) is wrapped:
                    if own:
                        setattr(owner, name, original)
                    else:
                        delattr(owner, name)
            except BaseException:  # noqa: BLE001 - Diagnostic faults must preserve the original outcome.
                self._safe("error")
        self._restores.clear()
