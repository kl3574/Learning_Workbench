"""Local preparation, one approval and one persisted control instance.

Only consume calls the execution port, outside every database transaction.
Original facts survive later access loss; delivery rechecks current authority.
"""
from datetime import datetime, timedelta
from contextlib import ExitStack
from uuid import uuid4

from packages.contracts import domain_models as dm
from ..codex_bootstrap_dto import (
    CodexBootstrapPreparationWrite, CodexBootstrapPreparationView, CodexBootstrapDecisionAck,
    CodexSessionCreateWrite, CodexSessionCreateAck, CodexSessionView,
)
from ..infrastructure.database import Database, utc_now
from ..infrastructure.security import SessionIdentity
from ..infrastructure.codex_bootstrap_execution import CodexExecutionOwners
from ..infrastructure.codex_bootstrap_repository import CodexBootstrapRepository, NO_FEATURES
from ..serialization import canonical_json, content_sha256
from .codex_bootstrap_access import current_control_access
from .codex_bootstrap_models import (
    BootstrapCommand, BootstrapOperation, BootstrapSnapshot, PreparedEvent, DecidedEvent, ConsumedEvent, FinishedEvent,
    BootstrapOutcome, uncertain_outcome,
)
from .codex_bootstrap_ports import CodexBootstrapRuntime
from .errors import ApiError


def conflict(code: str = 'CODEX_BOOTSTRAP_BINDING') -> ApiError:
    return ApiError(409, code, '原本地控制操作的状态或绑定不再符合本次命令；请读取原记录。')


class CodexBootstrapService:
    def __init__(self, database: Database, runtime: CodexBootstrapRuntime):
        self.database, self.runtime = database, runtime
        self.owners = CodexExecutionOwners(database.settings.data_dir)

    def _command(self, identity: SessionIdentity, route, target, key, body) -> BootstrapCommand:
        return BootstrapCommand(workspace_id=identity.workspace_id, actor_session_id=identity.id,
            route=route, target_id=target, key=key, body_json=canonical_json(body))

    def _history(self, connection, identity, *, write):
        current_control_access(connection, identity, write=write)
        repository = CodexBootstrapRepository(connection, identity.workspace_id, self.runtime)
        return repository, repository.checked()

    @staticmethod
    def _replay(history, command):
        for snapshot in history.values():
            for event in (snapshot.prepared, snapshot.decided, snapshot.consumed):
                if event is None:
                    continue
                original = event.command
                if (original.actor_session_id, original.route, original.target_id, original.key) == (
                        command.actor_session_id, command.route, command.target_id, command.key):
                    if original != command:
                        raise conflict('IDEMPOTENCY_CONFLICT')
                    return snapshot, event
        return None

    @staticmethod
    def _find(history, identifier):
        value = history.get(identifier)
        if value is None:
            raise ApiError(404, 'REFERENCE_MISSING', '本工作区没有此本地控制记录。')
        return value

    def _validity(self, snapshot: BootstrapSnapshot):
        if snapshot.consumed is not None or snapshot.decided is not None and snapshot.decided.ack.decision == 'decline':
            return 'closed'
        if datetime.fromisoformat(utc_now()) >= datetime.fromisoformat(snapshot.operation.expires_at):
            return 'expired'
        return self.runtime.validity(snapshot.operation.runtime)

    def _view(self, snapshot: BootstrapSnapshot) -> CodexBootstrapPreparationView:
        original = snapshot.prepared.ack
        decided, consumed = snapshot.decided, snapshot.consumed
        return CodexBootstrapPreparationView(**{**original.model_dump(),
            'revision': 3 if consumed else 2 if decided else 1,
            'status': 'consumed' if consumed else ('approved' if decided.ack.decision == 'approve_once' else 'declined') if decided else 'pending',
            'consent_id': decided.ack.consent_id if decided else None,
            'session_id': consumed.session_id if consumed else None,
            'validity': self._validity(snapshot)})

    def prepare(self, identity: SessionIdentity, body: CodexBootstrapPreparationWrite, key: str) -> CodexBootstrapPreparationView:
        command = self._command(identity, 'prepare', None, key, body)
        with self.database.transaction() as connection:
            _, history = self._history(connection, identity, write=True)
            replay = self._replay(history, command)
            if replay:
                return replay[0].prepared.ack
        # File inspection is not an execution grant. No CLI is called here.
        frozen = self.runtime.freeze(body.sandbox_root_id)
        self.runtime.validate_frozen(frozen)
        with self.database.transaction() as connection:
            repository, history = self._history(connection, identity, write=True)
            replay = self._replay(history, command)
            if replay:
                return replay[0].prepared.ack
            created = utc_now()
            expires = (datetime.fromisoformat(created) + timedelta(minutes=10)).isoformat(timespec='microseconds').replace('+00:00', 'Z')
            operation = BootstrapOperation(version='codex-bootstrap-operation-v1', workspace_id=identity.workspace_id,
                preparation_id='codex_prepare_' + uuid4().hex, actor_session_id=identity.id, created_at=created,
                expires_at=expires, runtime=frozen)
            ack = CodexBootstrapPreparationView(id=operation.preparation_id, revision=1, actor_session_id=identity.id,
                status='pending', scope=frozen.scope, operation_sha256=content_sha256(operation), created_at=created,
                expires_at=expires, consent_id=None, session_id=None, validity='current' if frozen.available else 'unavailable')
            repository.insert(operation, PreparedEvent(kind='prepared', command=command, ack=ack))
            repository.checked()
            return ack

    def read_preparation(self, identity: SessionIdentity, identifier: str) -> CodexBootstrapPreparationView:
        with self.database.transaction(immediate=False) as connection:
            connection.execute('PRAGMA query_only=ON')
            _, history = self._history(connection, identity, write=False)
            return self._view(self._find(history, identifier))

    def decide(self, identity: SessionIdentity, identifier: str, body: dm.ApprovalDecision, key: str) -> CodexBootstrapDecisionAck:
        command = self._command(identity, 'decision', identifier, key, body)
        with self.database.transaction() as connection:
            repository, history = self._history(connection, identity, write=True)
            replay = self._replay(history, command)
            if replay:
                assert replay[0].decided is not None
                return replay[0].decided.ack
            snapshot = self._find(history, identifier)
            if snapshot.operation.actor_session_id != identity.id:
                raise conflict()
            if snapshot.decided is not None:
                raise conflict()
            if body.expected_revision != 1:
                raise ApiError(412, 'REVISION_CONFLICT', '准备修订与原命令不一致。')
            if body.operation_sha256 != snapshot.operation_sha256:
                raise conflict()
            validity = self._validity(snapshot)
            if validity == 'expired' or body.decision == 'approve_once' and validity != 'current':
                raise conflict('CODEX_BOOTSTRAP_NOT_CURRENT')
            ack = CodexBootstrapDecisionAck(preparation_id=identifier, revision=2, actor_session_id=identity.id,
                decision=body.decision, operation_sha256=body.operation_sha256, decided_at=utc_now(),
                consent_id='codex_consent_' + uuid4().hex if body.decision == 'approve_once' else None)
            repository.append(identifier, DecidedEvent(kind='decided', command=command, ack=ack))
            repository.checked()
            return ack

    @staticmethod
    def _session_result(snapshot: BootstrapSnapshot) -> CodexSessionCreateAck:
        if snapshot.finished is None:
            raise conflict('CODEX_SESSION_INITIALIZING')
        if snapshot.finished.ack is not None:
            return snapshot.finished.ack
        code = snapshot.finished.outcome.error_code
        assert code is not None
        message = ('原控制实例的外部结果未知；请读取原准备和会话，不会再次启动。'
                   if code == 'CODEX_SESSION_OUTCOME_UNKNOWN' else '受限本地控制未能开始建会话；原许可已消费。')
        raise ApiError(503, code, message, False)

    def create_session(self, identity: SessionIdentity, body: CodexSessionCreateWrite, key: str) -> CodexSessionCreateAck:
        command = self._command(identity, 'session', None, key, body)
        owner_id = 'codex_owner_' + uuid4().hex
        with ExitStack() as ownership:
            with self.database.transaction() as connection:
                repository, history = self._history(connection, identity, write=True)
                replay = self._replay(history, command)
                if replay:
                    return self._session_result(replay[0])
                matches = [item for item in history.values() if item.decided is not None
                           and item.decided.ack.consent_id == body.consent_id]
                if len(matches) != 1:
                    raise conflict()
                snapshot = matches[0]
                if (snapshot.operation.actor_session_id != identity.id or snapshot.consumed is not None
                        or snapshot.operation.runtime.scope.sandbox_root_id != body.sandbox_root_id
                        or self._validity(snapshot) != 'current'):
                    raise conflict()
                # Do not create even an execution lock for rejected commands or
                # original replays. Hold it before the unique permit commits.
                if not ownership.enter_context(self.owners.hold(owner_id)):
                    raise conflict('CODEX_SESSION_INITIALIZING')
                identifier = snapshot.operation.preparation_id
                consumed = ConsumedEvent(kind='consumed', command=command, session_id='codex_session_' + uuid4().hex,
                    consent_id=body.consent_id, started_at=utc_now(), owner_id=owner_id)
                repository.append(identifier, consumed)
                repository.project_session(snapshot, consumed, None)
                repository.checked()
            try:
                outcome = self.runtime.execute(snapshot.operation.runtime, owner_id)
                self.runtime.validate_outcome(snapshot.operation.runtime, owner_id, outcome)
            except Exception:
                # The registered permit is spent even if the runtime cannot
                # prove where it stopped. No unexpected exception text escapes.
                outcome = uncertain_outcome()
            self._finish(identity.workspace_id, identifier, consumed, outcome)
            # Persisting external facts does not give an expired/revoked/learner
            # caller authority to receive a successful creation response.
            with self.database.transaction(immediate=False) as connection:
                connection.execute('PRAGMA query_only=ON')
                _, history = self._history(connection, identity, write=True)
                return self._session_result(self._find(history, identifier))

    def _finish(self, workspace_id: str, identifier: str, consumed: ConsumedEvent, outcome: BootstrapOutcome) -> None:
        with self.database.transaction() as connection:
            repository = CodexBootstrapRepository(connection, workspace_id, self.runtime)
            snapshot = self._find(repository.checked(), identifier)
            if snapshot.consumed != consumed or snapshot.finished is not None:
                raise conflict()
            ack = CodexSessionCreateAck(id=consumed.session_id, revision=2, status='ready',
                capabilities=NO_FEATURES, adapter_version=snapshot.operation.runtime.scope.adapter_version) if outcome.status == 'ready' else None
            event = FinishedEvent(kind='finished', session_id=consumed.session_id, finished_at=utc_now(), outcome=outcome, ack=ack)
            repository.append(identifier, event)
            repository.project_session(snapshot, consumed, event)
            repository.checked()

    def read_session(self, identity: SessionIdentity, identifier: str) -> CodexSessionView:
        with self.database.transaction(immediate=False) as connection:
            connection.execute('PRAGMA query_only=ON')
            _, history = self._history(connection, identity, write=False)
            matches = [item.session for item in history.values() if item.session is not None and item.session.id == identifier]
            if len(matches) != 1:
                raise ApiError(404, 'REFERENCE_MISSING', '本工作区没有此本地控制会话。')
            return matches[0]

    def recover(self, workspace_id: str) -> int:
        # Explicit lifecycle work, never a GET side effect. File locks prove
        # whether the registered execution owner still holds its instance.
        with self.database.transaction(immediate=False) as connection:
            connection.execute('PRAGMA query_only=ON')
            history = CodexBootstrapRepository(connection, workspace_id, self.runtime).checked()
        recovered = 0
        for identifier, snapshot in history.items():
            if snapshot.consumed is None or snapshot.finished is not None:
                continue
            with self.owners.hold(snapshot.consumed.owner_id) as ended:
                if not ended:
                    continue
                with self.database.transaction(immediate=False) as connection:
                    current = CodexBootstrapRepository(connection, workspace_id, self.runtime).checked()[identifier]
                if current.finished is None:
                    self._finish(workspace_id, identifier, snapshot.consumed, uncertain_outcome())
                    recovered += 1
        return recovered
