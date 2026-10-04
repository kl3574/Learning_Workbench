"""Local Codex preparation and safe control owner; no execution adapter is wired."""
import base64
import hashlib
import hmac
import secrets
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import strict_json
from ..codex_turn_dto import (
    CodexCurrentSessionView, CodexTurnPrepareWrite, CodexTurnPreparationView, CodexTurnControlView, CodexTurnPage,
)
from ..import_dto import JobCancelRequest, JobSnapshot
from ..infrastructure.codex_turn_repository import CodexTurnRepository, CheckedSession, CheckedTurn
from ..infrastructure.database import Database, utc_now
from ..infrastructure.security import SessionIdentity
from ..serialization import canonical_json, content_sha256
from .codex_bootstrap import CodexBootstrapService
from .codex_bootstrap_access import current_control_access
from .codex_turn_context import CodexTurnContext, damaged
from .codex_turn_models import (
    SessionAnchor, TurnRuntimeBinding, TurnInput, TurnPrepared, TurnCancelled, PrepareCommand, CancelCommand,
    preparation_digest,
)
from .errors import ApiError
from .providers import checked_provider_configuration, validate_key


def missing() -> ApiError:
    return ApiError(404, 'REFERENCE_MISSING', '本工作区没有此本地任务记录。')


class CodexTurnService:
    def __init__(self, database: Database, bootstrap: CodexBootstrapService):
        self.database, self.bootstrap = database, bootstrap
        self.context = CodexTurnContext(database)
        self._cursor_key = secrets.token_bytes(32)

    def _state(self, conn, identity, *, subject=False):
        current = current_control_access(conn, identity, write=subject)
        original = self.bootstrap.checked_sessions(conn, current)
        repository = CodexTurnRepository(conn, current, self.context)
        return current, original, repository, repository.checked(original)

    @staticmethod
    def _find(history, identifier, *, job=False, preparation=False) -> tuple[CheckedSession, CheckedTurn]:
        for state in history.values():
            for turn in state.turns.values():
                value = turn.prepared.command.ack
                key = value.job.id if job else value.id if preparation else value.turn_id
                if key == identifier:
                    return state, turn
        raise missing()

    def prepare_turn(self, identity: SessionIdentity, session_id: str,
                     body: CodexTurnPrepareWrite, key: str) -> CodexTurnPreparationView:
        key = validate_key(key)
        body = CodexTurnPrepareWrite.model_validate(body.model_dump(mode='json'))
        with self.database.transaction() as conn:
            current, originals, repo, history = self._state(conn, identity, subject=True)
            replay = repo.replay(history, current, 'prepare', session_id, key, body)
            if replay is not None:
                return CodexTurnPreparationView.model_validate(replay.model_dump())
            original = originals.get(session_id)
            if original is None or original.session is None:
                raise missing()
            if original.session.status != 'ready' or original.finished is None:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '原本地会话尚无受检的 ready 映射。')
            if original.operation.actor_session_id != current.id:
                raise ApiError(403, 'POLICY_DENIED', '新操作者不能接管原本地会话的准备权限。')
            state = history.get(session_id)
            revision = state.revision if state else original.session.revision
            if body.expected_session_revision != revision:
                raise ApiError(412, 'REVISION_MISMATCH', '会话控制修订已改变，请读取当前事实。')
            if state and state.active_turn_id is not None:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '此会话已有未结束任务。')
            provider = checked_provider_configuration(conn, current, body.provider_id)
            now = utc_now()
            if state is None:
                state = repo.establish(SessionAnchor(version='codex-turn-session-v1', workspace_id=current.workspace_id,
                    session_id=session_id, actor_session_id=current.id, bootstrap_sha256=content_sha256(original),
                    thread_id='thread_' + uuid4().hex, created_at=now))
            runtime = TurnRuntimeBinding(version='codex-turn-unavailable-profile-v1', implemented=False,
                bootstrap_sha256=state.anchor.bootstrap_sha256, template_version='codex-local-task-v1', tools=body.tools,
                cpu_seconds=60, memory_bytes=2147483648, file_bytes=16777216, protocol_output_bytes=16777216,
                file_descriptors=128, processes=16, core_bytes=0, command_network='denied', writable_area='turn_outputs')
            value = TurnInput(version='codex-turn-input-v1', workspace_id=current.workspace_id,
                actor_session_id=current.id, session_id=session_id, turn_id='turn_' + uuid4().hex,
                job_id='job_' + uuid4().hex, request=body, provider=provider, runtime=runtime)
            repo.jobs.create(value.job_id, 'codex_turn', value)
            context = self.context.prepare_turn(conn, current, value, now)
            summary = self.context.summary(context)
            ack = CodexTurnPreparationView(id='turnprep_' + uuid4().hex, preparation_sha256='0' * 64,
                actor_session_id=current.id, session_id=session_id, session_revision=revision + 1,
                turn_id=value.turn_id, job=dm.JobRef(id=value.job_id, status='awaiting_approval'), request=body,
                summary=summary, created_at=now, proposal_id=None, consent_id=None, validity='unavailable')
            ack.preparation_sha256 = preparation_digest(current.workspace_id, ack)
            event = TurnPrepared(kind='prepared', input=value, command=PrepareCommand(workspace_id=current.workspace_id,
                actor_session_id=current.id, route='prepare', target_id=session_id, key=key, body=body, ack=ack))
            repo.append(state, event, now)
            # Verify the actual graph before committing: Job/Run/context and
            # immutable command must either all survive or all roll back.
            repo.checked(originals)
            current_control_access(conn, current, write=True)
            return ack

    def read_preparation(self, identity: SessionIdentity, identifier: str) -> CodexTurnPreparationView:
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current, _, _, history = self._state(conn, identity, subject=True)
            _, turn = self._find(history, identifier, preparation=True)
            ack, value = turn.prepared.command.ack, turn.prepared.input
            validity = 'closed' if turn.control.execution == 'terminal' else 'unavailable'
            if validity != 'closed':
                context = self.context.verify_turn(conn, current, value, ack.summary)
                provider = checked_provider_configuration(conn, current, value.provider.id)
                if provider != value.provider or not self.context.current(conn, current, context):
                    validity = 'changed'
            return CodexTurnPreparationView.model_validate({**ack.model_dump(), 'job': turn.control.job.model_dump(),
                'validity': validity})

    def read_control(self, identity: SessionIdentity, identifier: str) -> CodexTurnControlView:
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            _, _, _, history = self._state(conn, identity)
            return self._find(history, identifier)[1].control

    def read_session(self, identity: SessionIdentity, identifier: str) -> CodexCurrentSessionView:
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            _, original, _, history = self._state(conn, identity)
            snapshot = original.get(identifier)
            if snapshot is None or snapshot.session is None:
                raise missing()
            value = snapshot.session.model_dump()
            state = history.get(identifier)
            if state:
                value.update(revision=state.revision, active_turn_id=state.active_turn_id)
            return CodexCurrentSessionView.model_validate(value)

    def job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            _, _, repo, history = self._state(conn, identity)
            self._find(history, identifier, job=True)
            return repo.jobs.snapshot(identifier)

    def cancel_job(self, identity: SessionIdentity, identifier: str, body: JobCancelRequest, key: str) -> JobSnapshot:
        key = validate_key(key)
        body = JobCancelRequest.model_validate(body.model_dump())
        with self.database.transaction() as conn:
            current, original, repo, history = self._state(conn, identity)
            replay = repo.replay(history, current, 'cancel', identifier, key, body)
            if replay is not None:
                return JobSnapshot.model_validate(replay.model_dump())
            state, turn = self._find(history, identifier, job=True)
            if body.expected_revision != turn.control.job_revision:
                raise ApiError(412, 'REVISION_MISMATCH', '任务修订已改变，请读取当前事实。')
            terminal = turn.control.execution == 'terminal'
            if not terminal:
                if state.active_turn_id != turn.control.id or turn.control.execution != 'not_started':
                    raise damaged()
                repo.jobs.cancel(identifier, body.expected_revision)
            ack = repo.jobs.snapshot(identifier)
            event = TurnCancelled(kind='cancel_observed' if terminal else 'cancelled', turn_id=turn.control.id,
                requested_session_revision=None if terminal else state.revision + 1,
                terminal_session_revision=None if terminal else state.revision + 2,
                command=CancelCommand(workspace_id=current.workspace_id, actor_session_id=current.id, route='cancel',
                    target_id=identifier, key=key, body=body, ack=ack))
            repo.append(state, event, ack.updated_at if not terminal else utc_now())
            repo.checked(original)
            current_control_access(conn, current, write=False)
            return ack

    def turns(self, identity: SessionIdentity, session_id: str, cursor: str | None = None, limit: int = 20) -> CodexTurnPage:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ApiError(422, 'SCHEMA_INVALID', '分页数量须为1至100。')
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current, original, _, history = self._state(conn, identity)
            if session_id not in original:
                raise missing()
            state = history.get(session_id)
            turns = sorted(state.turns.values(), key=lambda item: item.sequence, reverse=True) if state else []
            high = turns[0].sequence if turns else 0
            position = high + 1
            if cursor is not None:
                try:
                    if not isinstance(cursor, str) or not 1 <= len(cursor) <= 2048:
                        raise ValueError('length')
                    raw = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
                    if not hmac.compare_digest(raw[:32], hmac.new(self._cursor_key, raw[32:], hashlib.sha256).digest()):
                        raise ValueError('signature')
                    value = strict_json(raw[32:])
                    if (set(value) != {'workspace', 'session', 'limit', 'high', 'position'}
                            or value['workspace'] != current.workspace_id or value['session'] != session_id
                            or type(value['limit']) is not int or value['limit'] != limit
                            or type(value['high']) is not int or type(value['position']) is not int
                            or not 0 < value['position'] <= value['high'] <= high):
                        raise ValueError('binding')
                    high, position = value['high'], value['position']
                except (ValueError, TypeError, KeyError):
                    raise ApiError(400, 'CURSOR_INVALID', '分页游标无效，请重新读取第一页。') from None
            selected = [item for item in turns if item.sequence <= high and item.sequence < position]
            next_cursor = None
            if len(selected) > limit:
                raw = canonical_json({'workspace': current.workspace_id, 'session': session_id,
                    'limit': limit, 'high': high, 'position': selected[limit - 1].sequence}).encode()
                next_cursor = base64.urlsafe_b64encode(hmac.new(self._cursor_key, raw, hashlib.sha256).digest() + raw).decode().rstrip('=')
            return CodexTurnPage(items=[item.control for item in selected[:limit]], next_cursor=next_cursor)
