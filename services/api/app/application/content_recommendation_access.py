"""Content-owned, read-only exact recommendation catalog.

Availability means checked public metadata, body/blob registrations and active
navigation chains. It does not claim to have read body files: Content.body still
checks the actual bytes/hash when navigating. No material review is inferred.
"""

from collections.abc import Iterable
import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from packages.contracts.validation import PublishedModel, refs_in, validate_dag

from ..infrastructure.content_repository import ContentRepository, StoredRevision, damaged, missing, reference
from ..infrastructure.security import guard_subject_access
from ..route_dto import RouteAssessmentOption, RouteNavigationOption, RoutePracticeOption, RouteReaderOption
from .assessment_recommendation_access import RecommendationAssessmentReadiness, assessment_recommendation_readiness
from .content import concept_ids, key
from .content_learning_access import evidence_applicability, route_values
from .errors import ApiError
from .question_qualification import question_qualification_facts
from .recommendation_content_models import (
    CandidateConcept, CandidateConceptSkill, CandidateCourse, RecommendationCandidate, RecommendationCatalog,
)


def _unique(refs: Iterable[dm.ContentRef]) -> list[dm.ContentRef]:
    return sorted({ref.model_dump_json(): ref for ref in refs}.values(),
                  key=lambda ref: (ref.entity, ref.id, ref.revision, ref.sha256))


class _Catalog:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection, self.workspace_id = connection, workspace_id
        self.repository = ContentRepository(connection, workspace_id)
        self.qualifications: list[tuple[dm.ContentRef, RecommendationAssessmentReadiness]] = []
        self.rows: dict[str, StoredRevision] = {}
        for row in connection.execute(
            "SELECT r.*,o.kind,o.lifecycle FROM revisions r JOIN objects o ON o.id=r.object_id "
            "WHERE o.workspace_id=? AND o.kind NOT IN ('note','route') ORDER BY o.kind,o.id,r.revision",
            (workspace_id,),
        ):
            stored = self.repository.decode(row)
            self.rows[key(stored.value)] = stored
        self.mapped: dict[str, list[dm.ContentRef]] = {}
        self.complete: dict[str, bool] = {}
        self.edges: dict[str, list[str]] = {}
        for identity, stored in self.rows.items():
            value = stored.value
            declared = concept_ids(value)
            mapped = []
            complete = len(declared) == len(set(declared))
            for identifier in dict.fromkeys(declared):
                rows = connection.execute(
                    "SELECT d.target_revision,o.workspace_id,o.kind FROM object_dependencies d "
                    "LEFT JOIN objects o ON o.id=d.target_id WHERE d.owner_id=? AND d.owner_revision=? "
                    "AND d.target_id=? AND d.relation='concept'", (value.id, value.revision, identifier),
                ).fetchall()
                if any(row['workspace_id'] != workspace_id or row['kind'] != 'concept' for row in rows):
                    raise damaged()
                if len(rows) != 1:
                    complete = False
                    continue
                concept = self.repository.load('concept', identifier, rows[0]['target_revision']).value
                if not isinstance(concept, dm.Concept):
                    raise damaged()
                mapped.append(reference(concept))
            self.mapped[identity], self.complete[identity] = _unique(mapped), complete
            direct = list(refs_in(value))
            for ref in direct:
                self.exact(ref)
            self.edges[identity] = [key(ref) for ref in _unique([*direct, *mapped])]
            if isinstance(value, dm.ContentBlock):
                self.repository.body_info(value)
        try:
            validate_dag(self.edges)
        except ValueError:
            raise damaged() from None
        self.courses = [row.value for row in self.rows.values() if isinstance(row.value, dm.Course)]
        self.lessons = [row.value for row in self.rows.values() if isinstance(row.value, dm.Lesson)]
        # Validate parent kinds even when no resulting candidate is selected.
        for course in self.courses:
            for ref in course.lesson_refs:
                if not isinstance(self.exact(ref), dm.Lesson):
                    raise damaged()
            for ref in course.concept_refs:
                if not isinstance(self.exact(ref), dm.Concept):
                    raise damaged()
        for lesson in self.lessons:
            for ref in lesson.block_refs:
                if not isinstance(self.exact(ref), dm.ContentBlock):
                    raise damaged()

    def exact(self, ref: dm.ContentRef) -> PublishedModel:
        stored = self.rows.get(key(ref))
        if stored is None:
            # Repository preserves workspace/nonexistent-reference semantics.
            stored = self.repository.load(ref.entity, ref.id, ref.revision)
        if reference(stored.value) != ref:
            raise damaged()
        return stored.value

    def active(self, ref: dm.ContentRef) -> bool:
        self.exact(ref)
        return self.rows[key(ref)].lifecycle == 'active'

    def closure(self, refs: Iterable[dm.ContentRef]) -> list[dm.ContentRef]:
        identities = {key(ref) for ref in refs}
        queue = list(identities)
        while queue:
            for dependency in self.edges[queue.pop()]:
                if dependency not in identities:
                    identities.add(dependency)
                    queue.append(dependency)
        return _unique(reference(self.rows[identity].value) for identity in identities)

    def concept_closure(self, refs: Iterable[dm.ContentRef]) -> list[dm.ContentRef]:
        return [ref for ref in self.closure(refs) if ref.entity == 'concept']

    def lesson_blocks(self, lesson: dm.Lesson) -> list[dm.ContentBlock]:
        blocks = []
        for ref in lesson.block_refs:
            value = self.exact(ref)
            if not isinstance(value, dm.ContentBlock):
                raise damaged()
            blocks.append(value)
        return blocks

    def candidate(self, value: PublishedModel, course_id: str | None) -> RecommendationCandidate | None:
        target = reference(value)
        lessons: list[dm.Lesson] = []
        blocks: list[dm.ContentBlock] = []
        questions: list[dm.QuestionPublic] = []
        if isinstance(value, dm.Lesson):
            lessons = [value]
            blocks = self.lesson_blocks(value)
        elif isinstance(value, dm.ContentBlock):
            lessons = [lesson for lesson in self.lessons if target in lesson.block_refs]
            blocks = [value]
        elif isinstance(value, dm.PracticeSet):
            lesson = self.exact(value.lesson_ref)
            if not isinstance(lesson, dm.Lesson):
                raise damaged()
            lessons = [lesson]
            blocks = self.lesson_blocks(lesson)
        elif not isinstance(value, dm.AssessmentBlueprint):
            raise damaged()
        if isinstance(value, (dm.PracticeSet, dm.AssessmentBlueprint)):
            for ref in value.question_refs:
                question = self.exact(ref)
                if not isinstance(question, dm.QuestionPublic):
                    raise damaged()
                questions.append(question)
            if len({question.id for question in questions}) != len(questions):
                raise damaged()
        if course_id is not None and not isinstance(value, dm.AssessmentBlueprint):
            lessons = [lesson for lesson in lessons if any(course.id == course_id and reference(lesson) in course.lesson_refs
                       for course in self.courses)]
            if not lessons:
                return None
        material: list[PublishedModel] = list(questions) if isinstance(value, (dm.PracticeSet, dm.AssessmentBlueprint)) else list(blocks)
        concepts = _unique(ref for item in material for ref in self.mapped[key(item)])
        sources = self.closure([target])
        mapped_sources = self.closure(reference(item) for item in material)
        complete = bool(concepts) and all(self.complete[key(ref)] for ref in mapped_sources)
        # Parent lesson prerequisites are exact prerequisites, not taught concepts.
        prerequisite_roots = [ref for lesson in lessons for ref in self.mapped[key(lesson)]]
        prerequisite_roots.extend(ref for concept in concepts for ref in self.mapped[key(concept)])
        prerequisites = self.concept_closure(prerequisite_roots)
        complete = complete and all(self.complete[key(lesson)] for lesson in lessons)
        complete = complete and all(self.complete[key(ref)] for ref in self.closure(prerequisite_roots))
        skills = [CandidateConceptSkill(concept_ref=ref, skill=question.skill)
                  for question in questions for ref in self.mapped[key(question)]]
        skills = list({item.model_dump_json(): item for item in skills}.values())
        skills.sort(key=lambda item: (item.concept_ref.id, item.concept_ref.revision, item.skill))
        if isinstance(value, dm.AssessmentBlueprint):
            # An incomplete map cannot establish a course association from a subset.
            required = {ref.model_dump_json() for ref in concepts}
            courses = [course for course in self.courses if complete and required
                       and required <= {ref.model_dump_json() for ref in course.concept_refs}]
        else:
            courses = [course for course in self.courses if any(reference(lesson) in course.lesson_refs for lesson in lessons)]
        all_courses = courses
        if course_id is not None:
            courses = [course for course in courses if course.id == course_id]
            if not courses:
                return None
            if not isinstance(value, dm.AssessmentBlueprint):
                lessons = [lesson for lesson in lessons if any(reference(lesson) in course.lesson_refs for course in courses)]
        options: list[RouteNavigationOption] = []
        for course in courses:
            if not self.active(reference(course)):
                continue
            if isinstance(value, dm.AssessmentBlueprint):
                options.append(RouteAssessmentOption(kind='assessment', assessment_ref=target, course_ref=reference(course)))
            else:
                for lesson in lessons:
                    if reference(lesson) not in course.lesson_refs or not self.active(reference(lesson)):
                        continue
                    if isinstance(value, dm.PracticeSet):
                        options.append(RoutePracticeOption(kind='practice', course_ref=reference(course),
                            lesson_ref=reference(lesson), practice_ref=target))
                    else:
                        options.append(RouteReaderOption(kind='reader', course_ref=reference(course),
                            lesson_ref=reference(lesson), block_ref=target if isinstance(value, dm.ContentBlock) else None))
        if isinstance(value, dm.AssessmentBlueprint) and not all_courses and course_id is None:
            options.append(RouteAssessmentOption(kind='assessment', assessment_ref=target, course_ref=None))
        reasons = []
        if not self.active(target):
            reasons.append('TARGET_ARCHIVED')
        if any(not self.active(ref) for ref in sources if ref != target):
            reasons.append('SOURCE_DEPENDENCY_ARCHIVED')
        if not options:
            reasons.append('NO_ACTIVE_EXACT_PARENT')
        if reasons:
            options = []
        warnings: set[str] = set()
        ready = False
        if isinstance(value, dm.AssessmentBlueprint):
            if not complete or not concepts:
                warnings.add('CONCEPT_MAPPING_UNRESOLVED')
            else:
                readiness = assessment_recommendation_readiness(self.connection, self.workspace_id, target)
                self.qualifications.append((target, readiness))
                warnings.update(readiness.reason_codes)
                # Current independent suitability also requires current semantic sources.
                for question in questions:
                    facts = question_qualification_facts(self.connection, self.workspace_id, reference(question))
                    for concept in facts.concept_refs:
                        applicability = evidence_applicability(self.connection, self.workspace_id, reference(question), concept)
                        if applicability.status != 'usable':
                            warnings.update(applicability.reason_codes)
                ready = readiness.independent_ready and not warnings and not reasons
            warnings.update(reasons)
        return RecommendationCandidate(target_ref=target, title=value.title, navigation_options=options,
            concept_refs=concepts, concept_skills=skills, prerequisite_refs=prerequisites,
            course_refs=_unique(reference(course) for course in courses), lesson_refs=_unique(reference(lesson) for lesson in lessons),
            block_refs=_unique(reference(block) for block in blocks), mapping_state='complete' if complete else 'unresolved',
            material_review='unreviewed', available=not reasons, unavailable_reason_codes=sorted(reasons),
            test_ready=ready, test_warning_codes=sorted(warnings), estimated_minutes=None)


def recommendation_catalog(connection: sqlite3.Connection, workspace_id: str,
                           course_id: str | None = None) -> RecommendationCatalog:
    """Return a canonical checked public catalog without queueing or changing data."""
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '推荐内容读取需要同一事务的快照。')
    guard_subject_access(connection, workspace_id)
    ContentRepository(connection, workspace_id).require_workspace()
    source = _Catalog(connection, workspace_id)
    courses = [course for course in source.courses if course_id is None or course.id == course_id]
    if course_id is not None and not courses:
        raise missing()
    candidates = []
    for row in source.rows.values():
        if isinstance(row.value, (dm.Lesson, dm.ContentBlock, dm.PracticeSet, dm.AssessmentBlueprint)):
            candidate = source.candidate(row.value, course_id)
            if candidate is not None:
                candidates.append(candidate)
    concept_refs = (_unique(reference(row.value) for row in source.rows.values() if isinstance(row.value, dm.Concept))
        if course_id is None else source.concept_closure([ref for course in courses for ref in course.concept_refs]
            + [ref for candidate in candidates for ref in [*candidate.concept_refs, *candidate.prerequisite_refs]]))
    concepts = []
    for ref in concept_refs:
        value = source.exact(ref)
        if not isinstance(value, dm.Concept):
            raise damaged()
        closure = source.closure([ref])
        concepts.append(CandidateConcept(ref=ref, title=value.title, skill_dimensions=value.skill_dimensions,
            prerequisite_refs=source.mapped[key(ref)], mapping_state='complete' if all(source.complete[key(item)] for item in closure) else 'unresolved',
            available=all(source.active(item) for item in closure)))
    course_facts = [CandidateCourse(ref=reference(course), title=course.title, language=course.language,
        difficulty=course.difficulty, lifecycle=source.rows[key(course)].lifecycle) for course in courses]
    routes = route_values(connection, workspace_id)
    result = RecommendationCatalog(course_refs=[course.ref for course in course_facts], courses=course_facts,
        concepts=concepts, candidates=candidates, routes=routes, content_basis_sha256='0' * 64)
    result.content_basis_sha256 = sha256_bytes(canonical_bytes({'version': 'recommendation-content-catalog-v1',
        'workspace_id': workspace_id, 'course_id': course_id,
        'catalog': result.model_dump(mode='json', exclude={'content_basis_sha256'}),
        'qualifications': [{'assessment_ref': ref.model_dump(mode='json'), 'facts': facts.model_dump(mode='json')}
                           for ref, facts in source.qualifications]}))
    return result
