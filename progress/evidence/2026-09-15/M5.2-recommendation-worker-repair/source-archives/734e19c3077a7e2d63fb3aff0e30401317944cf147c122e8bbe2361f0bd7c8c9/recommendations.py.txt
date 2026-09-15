"""Local persistent Recommendation service; GET performs no writes or enqueue."""

import base64
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import re
import secrets
import sqlite3
from typing import Literal

from pydantic import TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json

from ..infrastructure.content_repository import ContentRepository
from ..infrastructure.database import Database, utc_now
from ..infrastructure.idempotency import execute_idempotent
from ..infrastructure.recommendation_repository import (
    FrozenRecommendationSnapshot, RecommendationRepository, invalid_recommendations,
)
from ..infrastructure.security import SessionIdentity, guard_subject_access
from ..recommendation_dto import (
    RecommendationActivityRef, RecommendationDecisionWrite, RecommendationEvidenceRef,
    RecommendationPage, RecommendationRuleParameters,
)
from .errors import ApiError
from .recommendation_rules import RULE_VERSION, RecommendationInputs, RecommendationRuleObservation, derive_recommendations


def inputs_changed(connection: sqlite3.Connection, workspace_id: str, source: str) -> None:
    """Source owners call this inside their successful native write transaction."""
    RecommendationRepository(connection, workspace_id).inputs_changed(source)


def load_inputs(connection: sqlite3.Connection, workspace_id: str) -> RecommendationInputs:
    """Public module ports compose one checked read snapshot; no foreign SQL."""
    from .assessment_activity_access import assessment_submissions
    from .assessment_recommendation_access import checked_recommendation_observations
    from .concept_states import read_concept_states
    from .content_recommendation_access import recommendation_catalog
    from .practice_activity_access import practice_participation
    from .profile import read_profile
    from .route_progress import checked_reading_activities, route_step_projection

    activities = [RecommendationActivityRef(kind='read_marked', event_id=item.event_id,
        target_ref=item.ref, source_id=None, occurred_at=item.occurred_at)
        for item in checked_reading_activities(connection, workspace_id) if item.value and item.ref.entity in {'lesson', 'block'}]
    for item in [*practice_participation(connection, workspace_id).submissions,
                 *assessment_submissions(connection, workspace_id)]:
        activities.append(RecommendationActivityRef(kind='practice_submitted' if item.target_ref.entity == 'practice_set' else 'test_submitted',
            event_id=item.event_id, target_ref=item.target_ref, source_id=item.source_id, occurred_at=item.submitted_at))
    observations = []
    for observed in checked_recommendation_observations(connection, workspace_id):
        source = observed.source
        observations.append(RecommendationRuleObservation(source=RecommendationEvidenceRef(evidence=source.evidence,
            question_ref=source.question_ref, concept_ref=source.concept_ref, assessment_ref=source.assessment_ref,
            attempt_id=source.attempt_id, grading_revision=source.grading_revision, submitted_at=source.submitted_at,
            applicability=observed.applicability.status, grading_origin=observed.grading_origin), outcome=observed.outcome))
    return RecommendationInputs(catalog=recommendation_catalog(connection, workspace_id),
        profile=read_profile(connection, workspace_id), concept_states=read_concept_states(connection, workspace_id),
        observations=sorted(observations, key=lambda item: item.source.evidence.id),
        activities=sorted(activities, key=lambda item: item.event_id), route_states=route_step_projection(connection, workspace_id))


def parameters(database: Database) -> RecommendationRuleParameters:
    return RecommendationRuleParameters(review_after_days=database.settings.recommendation_review_after_days, calibration='uncalibrated')


def basis_current(snapshot: FrozenRecommendationSnapshot, inputs: RecommendationInputs,
                  current_parameters: RecommendationRuleParameters, now: str) -> bool:
    return (snapshot.basis_sha256 == sha256_bytes(canonical_bytes(inputs))
        and snapshot.rule_version == RULE_VERSION and snapshot.rule_parameters == current_parameters
        and (snapshot.valid_until is None or datetime.fromisoformat(snapshot.valid_until.replace('Z', '+00:00'))
             > datetime.fromisoformat(now.replace('Z', '+00:00'))))


class RecommendationService:
    def __init__(self, database: Database):
        self.database = database
        self._cursor_key = secrets.token_bytes(32)

    def _cursor(self, context: str, snapshot_id: str, position: int) -> str:
        value = canonical_bytes({'context': context, 'snapshot_id': snapshot_id, 'position': position})
        signature = hmac.new(self._cursor_key, value, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(signature + value).decode().rstrip('=')

    def _position(self, cursor: str | None, context: str, snapshot_id: str | None) -> int:
        if cursor is None:
            return 0
        try:
            if not 1 <= len(cursor) <= 1024 or re.fullmatch('[A-Za-z0-9_-]+', cursor) is None:
                raise ValueError('invalid cursor')
            raw = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
            if not hmac.compare_digest(raw[:32], hmac.new(self._cursor_key, raw[32:], hashlib.sha256).digest()):
                raise ValueError('invalid signature')
            value = strict_json(raw[32:])
            if (not isinstance(value, dict) or set(value) != {'context', 'snapshot_id', 'position'}
                    or value['context'] != context or type(value['position']) is not int or value['position'] < 0):
                raise ValueError('invalid cursor context')
            if value['snapshot_id'] != snapshot_id:
                raise ApiError(409, 'CURSOR_EXPIRED', '推荐批次已更新，请从第一页重新读取。')
            return value['position']
        except (ValueError, TypeError, KeyError):
            raise ApiError(422, 'CURSOR_INVALID', '推荐分页游标无效或不属于本次查询。') from None

    def page(self, workspace_id: str, course_id: str | None = None,
             recommendation_id: str | None = None, cursor: str | None = None,
             limit: int = 20) -> RecommendationPage:
        if (type(limit) is not int or not 1 <= limit <= 100
                or recommendation_id is not None and (course_id is not None or cursor is not None)):
            raise ApiError(422, 'SCHEMA_INVALID', '推荐查询范围或分页数量无效。')
        context = sha256_bytes(canonical_bytes({'workspace_id': workspace_id, 'course_id': course_id, 'limit': limit}))
        try:
            for identifier in (course_id, recommendation_id):
                if identifier is not None:
                    TypeAdapter(dm.Id).validate_python(identifier)
            with self.database.transaction() as connection:
                guard_subject_access(connection, workspace_id)
                ContentRepository(connection, workspace_id).require_workspace()
                repository = RecommendationRepository(connection, workspace_id)
                state, snapshots, decisions = repository.checked()
                snapshot = snapshots[-1] if snapshots else None
                if recommendation_id is not None:
                    snapshot = next((batch for batch in snapshots if any(item.id == recommendation_id for item in batch.items)), None)
                    if snapshot is None:
                        raise ApiError(404, 'RECOMMENDATION_MISSING', '指定推荐不存在或不属于当前工作区。')
                position = self._position(cursor, context, snapshot.id if snapshot else None)
                rule_parameters = snapshot.rule_parameters if snapshot else parameters(self.database)
                warnings = list(snapshot.warnings) if snapshot else []
                status: Literal['missing', 'pending_refresh', 'ready', 'stale', 'failed'] = 'missing'
                current = False
                if snapshot is not None:
                    inputs = load_inputs(connection, workspace_id)
                    if course_id is not None and course_id not in {ref.id for ref in inputs.catalog.course_refs}:
                        raise ApiError(404, 'REFERENCE_MISSING', '指定课程不存在或不可访问。')
                    current = bool(state is not None and snapshot.id == state['snapshot_id']
                        and state['generation'] == state['completed_generation']
                        and state['failure_json'] is None
                        and basis_current(snapshot, inputs, parameters(self.database), utc_now()))
                    status = 'ready' if current else 'stale'
                if state is not None and not current and not (recommendation_id is not None and snapshot is not None
                                                             and snapshot.id != state['snapshot_id']):
                    if state['failure_json'] is not None:
                        status = 'failed'
                        warnings.append(dm.Warning.model_validate(strict_json(state['failure_json'])))
                    elif state['generation'] != state['completed_generation']:
                        status = 'pending_refresh'
                        warnings.append(dm.Warning(code='RECOMMENDATIONS_PENDING_REFRESH',
                            message='来源已变化，后台刷新已登记；保留的推荐依据已过期。', locator=None, severity='info'))
                items = []
                for original in snapshot.items if snapshot else []:
                    if recommendation_id is not None and original.id != recommendation_id:
                        continue
                    if course_id is not None and not any(option.course_ref is not None and option.course_ref.id == course_id
                                                        for option in original.navigation_options):
                        continue
                    decision = decisions[original.id]
                    items.append(original.model_copy(update={'decision': decision['decision'],
                        'decision_revision': decision['revision'], 'decision_reason': decision['reason'],
                        'decision_sha256': decision['decision_sha256'], 'staleness': 'current' if current else 'stale'}))
                selected = items[position:position + limit]
                return RecommendationPage(items=selected,
                    next_cursor=self._cursor(context, snapshot.id, position + limit) if snapshot and position + limit < len(items) else None,
                    total_hint=len(items), projection_state=status, warnings=warnings,
                    snapshot_id=snapshot.id if snapshot else None, generated_at=snapshot.generated_at if snapshot else None,
                    rule_version=snapshot.rule_version if snapshot else RULE_VERSION, rule_parameters=rule_parameters)
        except sqlite3.Error:
            raise ApiError(503, 'RECOMMENDATION_STORAGE_UNAVAILABLE', '推荐存储暂不可读取。', True) from None
        except (ValueError, TypeError, KeyError):
            raise invalid_recommendations() from None

    def decide(self, identity: SessionIdentity, id: str, request: RecommendationDecisionWrite,
               key: str | None, expected_sha256: str) -> dm.MutationAck:
        try:
            request = RecommendationDecisionWrite.model_validate(request.model_dump(mode='json'))
            TypeAdapter(dm.Id).validate_python(id)
        except (ValueError, TypeError):
            raise ApiError(422, 'SCHEMA_INVALID', '推荐决定请求不符合规范。') from None
        if not isinstance(expected_sha256, str) or re.fullmatch('[0-9a-f]{64}', expected_sha256) is None:
            raise ApiError(400, 'IF_MATCH_REQUIRED', '推荐决定需要所读决定的有效强 If-Match。')
        payload = {'body': request.model_dump(mode='json'), 'if_match': expected_sha256}
        request_hash = sha256_bytes(canonical_bytes(payload))
        route = f'POST /recommendations/{id}/decision'
        try:
            with self.database.transaction() as connection:
                guard_subject_access(connection, identity.workspace_id)
                ContentRepository(connection, identity.workspace_id).require_workspace()
                repository = RecommendationRepository(connection, identity.workspace_id)
                state, snapshots, heads = repository.checked()
                snapshot = next((batch for batch in snapshots if any(item.id == id for item in batch.items)), None)
                if snapshot is None:
                    raise ApiError(404, 'RECOMMENDATION_MISSING', '指定推荐不存在或不属于当前工作区。')
                item = next(item for item in snapshot.items if item.id == id)
                executed = False

                def operation():
                    nonlocal executed
                    if heads[id]['decision_sha256'] != expected_sha256:
                        raise ApiError(412, 'REVISION_CONFLICT', '推荐决定已更新，请读取原推荐后比较。')
                    if (state is None or state['snapshot_id'] != snapshot.id
                            or state['generation'] != state['completed_generation']):
                        raise ApiError(409, 'RECOMMENDATION_STALE', '该推荐依据已过期；请保留原决定候选并查看最新推荐。')
                    inputs = load_inputs(connection, identity.workspace_id)
                    if not basis_current(snapshot, inputs, parameters(self.database), utc_now()):
                        raise ApiError(409, 'RECOMMENDATION_STALE', '该推荐依据已过期；请保留原决定候选并查看最新推荐。')
                    executed = True
                    return repository.decide(snapshot, item, heads[id], request).model_dump(mode='json')

                result = execute_idempotent(connection, actor=identity.workspace_id, route=route, key=key,
                                            payload=payload, operation=operation)
                assert key is not None
                return repository.checked_receipt(route=route, key=key, request_hash=request_hash, result=result, applied=executed)
        except sqlite3.Error:
            raise ApiError(503, 'RECOMMENDATION_STORAGE_UNAVAILABLE', '推荐决定暂不可保存。', True) from None
        except (ValueError, TypeError, KeyError):
            raise invalid_recommendations() from None


class _RefreshStopped(Exception):
    pass


class RecommendationWorker:
    """One local atomic refresh per maintenance tick; SQLite owns crash rollback."""

    def __init__(self, database: Database, stopping: Callable[[], bool] = lambda: False):
        self.database = database
        self.stopping = stopping

    def _no_work(self, workspace_id: str) -> bool:
        # A checked no-work snapshot neither publishes subject data nor clears
        # dirty state. Concurrent changes may defer work until the next tick.
        # Any work below starts a separate writer transaction and rechecks all
        # current facts; no read-snapshot inputs cross that admission boundary.
        with self.database.transaction(immediate=False) as connection:
            guard_subject_access(connection, workspace_id)
            state, snapshots, _ = RecommendationRepository(connection, workspace_id).checked()
            if state is None:
                return False
            if state['retry_at'] is not None and state['retry_at'] > utc_now():
                return True
            if (not snapshots or state['generation'] != state['completed_generation']
                    or state['failure_json'] is not None):
                return False
            inputs = load_inputs(connection, workspace_id)
            return basis_current(snapshots[-1], inputs, parameters(self.database), utc_now())

    def run_once(self) -> bool:
        if self.stopping():
            return False
        workspace_id = self.database.workspace_id()
        try:
            if self._no_work(workspace_id):
                return False
            with self.database.transaction() as connection:
                guard_subject_access(connection, workspace_id)
                repository = RecommendationRepository(connection, workspace_id)
                state, snapshots, _ = repository.checked()
                if state is None:
                    repository.inputs_changed('worker.startup')
                    state = repository.state()
                assert state is not None
                if state['retry_at'] is not None and state['retry_at'] > utc_now():
                    return False
                inputs = load_inputs(connection, workspace_id)
                now = utc_now()
                current_parameters = parameters(self.database)
                if (snapshots and state['generation'] == state['completed_generation']
                        and state['failure_json'] is None
                        and basis_current(snapshots[-1], inputs, current_parameters, now)):
                    return False
                generation = state['generation']
                plan = derive_recommendations(inputs, generated_at=now, parameters=current_parameters)
                if self.stopping():
                    raise _RefreshStopped()
                fresh = load_inputs(connection, workspace_id)
                if self.stopping():
                    raise _RefreshStopped()
                if canonical_bytes(fresh) != canonical_bytes(inputs):
                    return True
                repository.publish(generation=generation, basis=inputs.model_dump(mode='json'), generated_at=now,
                    valid_until=plan.valid_until, rule_version=RULE_VERSION, parameters=current_parameters,
                    items=plan.items, warnings=plan.warnings)
                if self.stopping():
                    raise _RefreshStopped()
                return True
        except _RefreshStopped:
            return False
        except (ApiError, ValueError, TypeError, KeyError, sqlite3.Error) as error:
            if isinstance(error, ApiError) and error.code == 'ASSESSMENT_ACTIVE':
                return False
            try:
                with self.database.transaction() as connection:
                    guard_subject_access(connection, workspace_id)
                    repository = RecommendationRepository(connection, workspace_id)
                    state, _, _ = repository.checked()
                    if state is None:
                        repository.inputs_changed('worker.recovery')
                    warning = dm.Warning(code='RECOMMENDATION_REFRESH_FAILED', message='本地推荐刷新实际失败，旧快照保留；等待后台重试。',
                                         locator=None, severity='error')
                    retry_at = (datetime.now(UTC) + timedelta(seconds=15)).isoformat(timespec='microseconds').replace('+00:00', 'Z')
                    connection.execute('UPDATE recommendation_projection_state SET failure_json=?,retry_at=? WHERE workspace_id=?',
                                       (canonical_bytes(warning).decode(), retry_at, workspace_id))
            except (ApiError, ValueError, TypeError, KeyError, sqlite3.Error):
                pass
            return False
