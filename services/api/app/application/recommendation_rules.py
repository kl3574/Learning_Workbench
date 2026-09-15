"""Local explainable rules over checked owner facts, with original source times."""

from datetime import datetime, timedelta
from typing import Literal

from pydantic import TypeAdapter, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes

from ..concept_state_dto import ConceptStateResponse
from ..learning_dto import RouteStepState
from ..recommendation_dto import (
    RecommendationAction, RecommendationActivityRef, RecommendationEvidenceRef, RecommendationProfileBasis,
    RecommendationNavigation, RecommendationReason, RecommendationRouteBasis, RecommendationRuleParameters, RecommendationView,
)
from .recommendation_content_models import RecommendationCandidate, RecommendationCatalog

RULE_VERSION = 'recommendation-rules-v1'
PRIORITY = {'assessment_error': 0, 'prerequisite_gap': 1, 'read_without_practice': 2,
            'practice_without_independent': 3, 'review_due': 4, 'user_goal': 5, 'next_route_step': 5}


def ref_key(ref: dm.ContentRef) -> tuple[str, str, int, str]:
    return ref.entity, ref.id, ref.revision, ref.sha256


class RecommendationRuleObservation(dm.StrictModel):
    source: RecommendationEvidenceRef
    outcome: Literal['correct', 'incorrect', 'unanswered', 'invalid_input', 'needs_review'] | None


class RecommendationInputs(dm.StrictModel):
    catalog: RecommendationCatalog
    profile: dm.LearnerProfile
    concept_states: ConceptStateResponse
    observations: list[RecommendationRuleObservation]
    activities: list[RecommendationActivityRef]
    route_states: list[RouteStepState]

    @model_validator(mode='after')
    def unique_sources(self):
        if (len({item.source.evidence.id for item in self.observations}) != len(self.observations)
                or len({item.event_id for item in self.activities}) != len(self.activities)
                or len({(ref_key(item.route_ref), item.step_id) for item in self.route_states}) != len(self.route_states)):
            raise ValueError('recommendation inputs require unique source identities')
        return self


class RecommendationPlan(dm.StrictModel):
    items: list[RecommendationView]
    warnings: list[dm.Warning]
    valid_until: dm.UTC | None


def _reading_for(candidate: RecommendationCandidate, inputs: RecommendationInputs) -> list[RecommendationActivityRef]:
    return [activity for activity in inputs.activities if activity.kind == 'read_marked'
            and (activity.target_ref in candidate.lesson_refs or activity.target_ref in candidate.block_refs)]


def derive_recommendations(inputs: RecommendationInputs, *, generated_at: str,
                           parameters: RecommendationRuleParameters) -> RecommendationPlan:
    inputs = RecommendationInputs.model_validate(inputs.model_dump(mode='json'))
    TypeAdapter(dm.UTC).validate_python(generated_at)
    parameters = RecommendationRuleParameters.model_validate(parameters.model_dump(mode='json'))
    input_identity = sha256_bytes(canonical_bytes(inputs))
    values: dict[str, RecommendationView] = {}
    warnings: dict[tuple[str, str | None], dm.Warning] = {}
    goals = set(inputs.profile.goal_concept_ids)
    now = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
    future_due: list[datetime] = []

    def warn(code: str, message: str, locator: str | None = None) -> None:
        warnings[code, locator] = dm.Warning(code=code, message=message, locator=locator, severity='warning')

    if inputs.profile.goals and not goals:
        warn('EXACT_MAPPING_UNRESOLVED', '已保存文字目标，但尚未关联本地概念；本地规则不会自动猜测其语义，请选择目标概念。')

    def add(candidate: RecommendationCandidate, action: RecommendationAction, reason: RecommendationReason,
            explanation: str, *, evidence: list[RecommendationEvidenceRef] | None = None,
            activities: list[RecommendationActivityRef] | None = None, gaps: list[dm.ContentRef] | None = None,
            profile: bool = False, route: RecommendationRouteBasis | None = None) -> None:
        identifier = 'recommendation_' + sha256_bytes(canonical_bytes({'workspace': inputs.profile.workspace_id,
            'target': candidate.target_ref.model_dump(mode='json'), 'generated_at': generated_at,
            'input_identity': input_identity, 'parameters': parameters.model_dump(mode='json'),
            'reason': reason, 'action': action, 'route': route.model_dump(mode='json') if route else None}))[:48]
        value = RecommendationView(id=identifier, target_ref=candidate.target_ref, target_title=candidate.title,
            action=action, reason_codes=[reason], explanation=explanation + ' 材料未审核；不承诺评分、独立证据资格或已验证补弱效果。',
            evidence_refs=sorted({item.evidence.id: item for item in evidence or []}.values(), key=lambda item: item.evidence.id),
            activity_refs=sorted({item.event_id: item for item in activities or []}.values(), key=lambda item: item.event_id),
            profile_basis=RecommendationProfileBasis(revision=inputs.profile.revision, goal_concept_ids=inputs.profile.goal_concept_ids,
                goals=inputs.profile.goals, self_assessments=inputs.profile.self_assessments) if profile else None,
            route_basis=route, prerequisite_gaps=sorted({ref_key(ref): ref for ref in gaps or []}.values(), key=ref_key),
            navigation_options=TypeAdapter(list[RecommendationNavigation]).validate_python(
                [item.model_dump(mode='json') for item in candidate.navigation_options]), estimated_minutes=None,
            rule_version=RULE_VERSION, generated_at=generated_at, staleness='current', decision='pending', decision_revision=1,
            decision_sha256='0' * 64, decision_reason=None)
        if identifier in values:
            previous = values[identifier]
            value = value.model_copy(update={
                'evidence_refs': sorted({item.evidence.id: item for item in [*previous.evidence_refs, *value.evidence_refs]}.values(), key=lambda item: item.evidence.id),
                'activity_refs': sorted({item.event_id: item for item in [*previous.activity_refs, *value.activity_refs]}.values(), key=lambda item: item.event_id),
                'profile_basis': value.profile_basis or previous.profile_basis,
                'prerequisite_gaps': sorted({ref_key(ref): ref for ref in [*previous.prerequisite_gaps, *value.prerequisite_gaps]}.values(), key=ref_key)})
        values[identifier] = value

    trusted_errors = [item.source for item in inputs.observations if item.source.grading_origin == 'deterministic'
                      and item.outcome == 'incorrect' and item.source.applicability == 'usable']
    for source in trusted_errors:
        matches = [item for item in inputs.catalog.candidates if item.available and item.mapping_state == 'complete'
                   and item.target_ref.entity in {'lesson', 'block'} and source.concept_ref in item.concept_refs]
        for candidate in matches:
            add(candidate, 'read', 'assessment_error', '当前成功评分版本有确定性判错；建议回看该题精确关联概念的材料。',
                evidence=[source])
        if not matches:
            warn('NO_LOCAL_MATERIAL', '确定性错题关联概念暂无可用本地教材。', source.concept_ref.id)

    independent = {(ref_key(item.source.concept_ref), item.source.evidence.skill) for item in inputs.observations
                   if item.source.applicability == 'usable' and item.source.evidence.eligible
                   and item.source.evidence.score is not None}
    concepts = {ref_key(item.ref): item for item in inputs.catalog.concepts}
    original_route_states = {(ref_key(item.route_ref), item.step_id): item for item in inputs.route_states}
    route_needs: dict[tuple[str, str, int, str], list[RecommendationRouteBasis]] = {}
    for original_route in inputs.catalog.routes:
        original_ref = dm.ContentRef(entity='route', id=original_route.id, revision=original_route.revision,
                                    sha256=metadata_sha256(original_route))
        for original_step in original_route.steps:
            original_state = original_route_states.get((ref_key(original_ref), original_step.id))
            if original_state is not None and not original_state.completed:
                route_needs.setdefault(ref_key(original_step.target), []).append(RecommendationRouteBasis(
                    route_ref=original_ref, step_id=original_step.id, source_event_ids=original_state.source_event_ids))
    for dependent in inputs.catalog.candidates:
        if not dependent.available:
            continue
        goal_need = bool(goals.intersection(ref.id for ref in dependent.concept_refs))
        activity_need = [item for item in inputs.activities if item.target_ref == dependent.target_ref]
        activity_need.extend(_reading_for(dependent, inputs))
        evidence_need = [item.source for item in inputs.observations if item.source.concept_ref in dependent.concept_refs
                         and item.source.applicability == 'usable' and item.source.evidence.score is not None]
        route_need = route_needs.get(ref_key(dependent.target_ref), [])
        if not goal_need and not activity_need and not evidence_need and not route_need:
            continue
        if dependent.mapping_state != 'complete':
            warn('EXACT_MAPPING_UNRESOLVED', '相关材料的精确概念或先修映射待核验，未猜测缺口。', dependent.target_ref.id)
            continue
        for prerequisite in dependent.prerequisite_refs:
            concept = concepts.get(ref_key(prerequisite))
            if concept is None or concept.mapping_state != 'complete':
                warn('EXACT_MAPPING_UNRESOLVED', '相关材料的原精确先修无法完整解析。', dependent.target_ref.id)
                continue
            skills = concept.skill_dimensions
            if skills and all((ref_key(prerequisite), skill) in independent for skill in skills):
                continue
            matches = [candidate for candidate in inputs.catalog.candidates if candidate.available
                       and candidate.mapping_state == 'complete' and candidate.target_ref.entity in {'lesson', 'block'}
                       and prerequisite in candidate.concept_refs]
            for candidate in matches:
                contexts: list[RecommendationRouteBasis | None] = list(route_need)
                if goal_need or activity_need or evidence_need:
                    contexts.append(None)
                for context in contexts:
                    add(candidate, 'read', 'prerequisite_gap', f'材料“{dependent.title}”的原精确先修尚缺可用独立证据；建议先查看基础材料。',
                        gaps=[prerequisite], profile=goal_need, activities=activity_need, evidence=evidence_need, route=context)
            if not matches:
                warn('NO_LOCAL_MATERIAL', '已声明的精确先修缺少可用本地基础教材。', prerequisite.id)

    by_target = {ref_key(candidate.target_ref): candidate for candidate in inputs.catalog.candidates}
    for activity in inputs.activities:
        if activity.kind != 'practice_submitted':
            continue
        practice = by_target.get(ref_key(activity.target_ref))
        if practice is None or practice.mapping_state != 'complete' or not practice.concept_skills:
            warn('EXACT_MAPPING_UNRESOLVED', '该真实练习提交的概念/技能映射无法完整解析，未猜测测试资格。', activity.target_ref.id)
            continue
        missing = {(ref_key(item.concept_ref), item.skill) for item in practice.concept_skills} - independent
        if not missing:
            continue
        matched = set()
        for candidate in inputs.catalog.candidates:
            coverage = {(ref_key(item.concept_ref), item.skill) for item in candidate.concept_skills} & missing
            if candidate.target_ref.entity != 'assessment' or not coverage or not candidate.test_ready:
                continue
            matched.update(coverage)
            add(candidate, 'test', 'practice_without_independent',
                '已有真实练习提交，但相应概念/技能尚无可用独立证据；该测试当前通过已审答案、完整映射及全工作区新颖性检查。',
                activities=[activity])
        if matched != missing:
            warn('NO_REVIEWED_ASSESSMENT', '练习涉及的部分概念/技能缺少当前具备独立资格的已审测试。', activity.target_ref.id)

    latest: dict[tuple[tuple[str, str, int, str], str], RecommendationEvidenceRef] = {}
    for observation in inputs.observations:
        source = observation.source
        if source.applicability != 'usable' or source.evidence.score is None:
            continue
        key = ref_key(source.concept_ref), source.evidence.skill
        previous = latest.get(key)
        if previous is None or (datetime.fromisoformat(source.submitted_at.replace('Z', '+00:00')), source.attempt_id,
                                source.grading_revision, source.evidence.id) > (
                datetime.fromisoformat(previous.submitted_at.replace('Z', '+00:00')), previous.attempt_id,
                previous.grading_revision, previous.evidence.id):
            latest[key] = source
    for source in latest.values():
        due = datetime.fromisoformat(source.submitted_at.replace('Z', '+00:00')) + timedelta(days=parameters.review_after_days)
        if due > now:
            future_due.append(due)
            continue
        matches = [candidate for candidate in inputs.catalog.candidates if candidate.available
                   and candidate.mapping_state == 'complete' and source.concept_ref in candidate.concept_refs]
        for candidate in matches:
            add(candidate, 'review', 'review_due',
                f'原提交证据已达到 {parameters.review_after_days} 天复习提醒；间隔是未校准规则，不是掌握概率。', evidence=[source])
        if not matches:
            warn('NO_LOCAL_MATERIAL', '已到复习时点的原精确概念缺少可用本地材料。', source.concept_ref.id)

    route_states = {(ref_key(item.route_ref), item.step_id): item for item in inputs.route_states}
    for route in inputs.catalog.routes:
        route_ref = dm.ContentRef(entity='route', id=route.id, revision=route.revision, sha256=metadata_sha256(route))
        states = {step.id: route_states.get((ref_key(route_ref), step.id)) for step in route.steps}
        if any(value is None for value in states.values()):
            raise ValueError('route projection must cover every exact native step')
        for step in route.steps:
            state = states[step.id]
            assert state is not None
            dependencies = [states.get(identifier) for identifier in step.requires_steps]
            if state.completed or any(value is None or not value.completed for value in dependencies):
                continue
            route_candidate = by_target.get(ref_key(step.target))
            if route_candidate is None or not route_candidate.available:
                warn('NO_LOCAL_MATERIAL', '下一路线步骤的原精确目标当前缺少可用本地材料或导航父链。', step.target.id)
                break
            action: RecommendationAction = 'read' if step.target.entity in {'lesson', 'block'} else (
                'practice' if step.target.entity == 'practice_set' else 'test')
            if action == 'test' and not route_candidate.test_ready:
                warn('NO_REVIEWED_ASSESSMENT', '下一路线测试尚未具备当前已审、完整映射及独立新颖性资格。', step.target.id)
                break
            event_ids = set(state.source_event_ids)
            for identifier in step.requires_steps:
                dependency = states[identifier]
                assert dependency is not None
                event_ids.update(dependency.source_event_ids)
            add(route_candidate, action, 'next_route_step', f'路线“{route.title}”中前置步骤已完成，这是下一个未完成步骤；可自行跳过。',
                route=RecommendationRouteBasis(route_ref=route_ref, step_id=step.id, source_event_ids=sorted(event_ids)))
            break

    for candidate in inputs.catalog.candidates:
        if not candidate.available:
            continue
        if candidate.target_ref.entity == 'practice_set':
            reading = _reading_for(candidate, inputs)
            practiced = any(item.kind == 'practice_submitted' and item.target_ref == candidate.target_ref for item in inputs.activities)
            if reading and not practiced:
                add(candidate, 'practice', 'read_without_practice', '已有真实阅读记录，尚未提交本题组练习。', activities=reading)
        if candidate.mapping_state == 'complete' and goals.intersection(ref.id for ref in candidate.concept_refs):
            action = 'read' if candidate.target_ref.entity in {'lesson', 'block'} else (
                'practice' if candidate.target_ref.entity == 'practice_set' else 'test')
            if action != 'test' or candidate.test_ready:
                add(candidate, action, 'user_goal', '材料覆盖你明确设置的目标概念；自报基础保留为自报，不作为独立证据。', profile=True)
    for goal in goals:
        if not any(item.available and item.mapping_state == 'complete' and goal in {ref.id for ref in item.concept_refs}
                   for item in inputs.catalog.candidates):
            warn('NO_LOCAL_MATERIAL', '当前工作区缺少覆盖该目标概念的可用本地材料。', goal)
    if values:
        warn('UNREVIEWED_MATERIAL_ONLY', '推荐中包含未审核材料；阅读或练习不承诺评分、独立证据资格或已验证补弱效果。')
    candidate_by_ref = {ref_key(item.target_ref): item for item in inputs.catalog.candidates}

    def rank(item: RecommendationView):
        candidate = candidate_by_ref[ref_key(item.target_ref)]
        recent = max((datetime.fromisoformat(source.submitted_at.replace('Z', '+00:00')).timestamp()
            for source in trusted_errors if source.concept_ref in candidate.concept_refs), default=0)
        route_identity = (ref_key(item.route_basis.route_ref), item.route_basis.step_id) if item.route_basis else (('', '', 0, ''), '')
        return (PRIORITY[item.reason_codes[0]], -len(goals.intersection(ref.id for ref in candidate.concept_refs)),
                len(item.prerequisite_gaps), -recent, item.estimated_minutes if item.estimated_minutes is not None else float('inf'),
                ref_key(item.target_ref), item.action, item.reason_codes[0], route_identity)

    return RecommendationPlan(items=sorted(values.values(), key=rank), warnings=list(warnings.values()),
        valid_until=min(future_due).isoformat(timespec='microseconds').replace('+00:00', 'Z') if future_due else None)
