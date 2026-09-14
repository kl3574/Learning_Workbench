"""Content-owned exact question concepts and material links; no inferred mastery."""

from collections.abc import Sequence
import sqlite3
from typing import Literal

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm

from ..infrastructure.content_repository import damaged, reference
from .assessment_content import AssessmentContent

Skill = Literal["recall", "explain", "compute", "derive", "transfer"]


class QuestionQualificationFacts(dm.StrictModel):
    question_ref: dm.ContentRef
    required_concept_ids: list[dm.Id]
    concept_refs: list[dm.ContentRef]
    skill: Skill
    exposure_group: dm.Id
    max_score: float = Field(gt=0, le=100)
    mapping_valid: bool


class ReviewMaterial(dm.StrictModel):
    course_ref: dm.ContentRef
    lesson_ref: dm.ContentRef
    block_ref: dm.ContentRef
    title: str
    concept_refs: list[dm.ContentRef]

    @model_validator(mode="after")
    def exact_types(self):
        if (self.course_ref.entity != "course" or self.lesson_ref.entity != "lesson" or self.block_ref.entity != "block"
                or not self.concept_refs or any(ref.entity != "concept" for ref in self.concept_refs)):
            raise ValueError("review material must retain a complete exact parent chain")
        return self


def question_qualification_facts(connection: sqlite3.Connection, workspace_id: str,
                                 question_ref: dm.ContentRef) -> QuestionQualificationFacts:
    """Caller checks policy; missing/ambiguous mapping stays explicitly unresolved."""
    content = AssessmentContent(connection, workspace_id)
    question = content.exact(question_ref)
    if not isinstance(question, dm.QuestionPublic):
        raise damaged()
    concepts = []
    valid = len(set(question.concept_ids)) == len(question.concept_ids)
    for identifier in dict.fromkeys(question.concept_ids):
        rows = connection.execute("SELECT d.target_revision,o.workspace_id,o.kind FROM object_dependencies d "
            "JOIN objects o ON o.id=d.target_id WHERE d.owner_id=? AND d.owner_revision=? AND d.target_id=? AND d.relation='concept'",
            (question.id, question.revision, identifier)).fetchall()
        if any(row["workspace_id"] != workspace_id or row["kind"] != "concept" for row in rows):
            raise damaged()
        if len(rows) != 1:
            valid = False
            continue
        concept = content.public.load("concept", identifier, rows[0]["target_revision"]).value
        if not isinstance(concept, dm.Concept):
            raise damaged()
        concepts.append(reference(concept))
    return QuestionQualificationFacts(question_ref=question_ref, required_concept_ids=question.concept_ids,
        concept_refs=concepts, skill=question.skill, exposure_group=question.exposure_group,
        max_score=question.max_score, mapping_valid=valid and len(concepts) == len(question.concept_ids))


def review_materials(connection: sqlite3.Connection, workspace_id: str, question_ref: dm.ContentRef,
                     course_refs: Sequence[dm.ContentRef]) -> list[ReviewMaterial]:
    """Find exact concept overlaps within each frozen course, without latest substitution."""
    facts = question_qualification_facts(connection, workspace_id, question_ref)
    if not facts.mapping_valid:
        return []
    required = {(ref.id, ref.revision, ref.sha256) for ref in facts.concept_refs}
    content = AssessmentContent(connection, workspace_id)
    output = []
    seen = set()
    for course_ref in course_refs:
        course = content.exact(course_ref)
        if not isinstance(course, dm.Course):
            raise damaged()
        for ref in course.concept_refs:
            if not isinstance(content.exact(ref), dm.Concept):
                raise damaged()
        for lesson_ref in course.lesson_refs:
            lesson = content.exact(lesson_ref)
            if not isinstance(lesson, dm.Lesson):
                raise damaged()
            for block_ref in lesson.block_refs:
                block = content.exact(block_ref)
                if not isinstance(block, dm.ContentBlock):
                    raise damaged()
                overlaps = [reference(content.public.concept_dependency(block, identifier)) for identifier in dict.fromkeys(block.concepts)]
                overlaps = [ref for ref in overlaps if (ref.id, ref.revision, ref.sha256) in required]
                key = (course_ref.id, course_ref.revision, lesson_ref.id, lesson_ref.revision, block_ref.id, block_ref.revision)
                if overlaps and key not in seen:
                    seen.add(key)
                    output.append(ReviewMaterial(course_ref=course_ref, lesson_ref=lesson_ref,
                        block_ref=block_ref, title=block.title, concept_refs=overlaps))
    return output
