"""Pure linkage/structure checks shared by local question-content consumers.

Inputs have already passed their respective shape validation; published question
linkage is checked separately from reference-free grading fields. Success does not
grade an answer, approve a solution, or prove
question wording, distractors, units, mathematical correctness or pedagogy.
There is no database, permission decision, content lookup or model invocation.
"""

from collections.abc import Sequence
import math
from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256


QuestionKind = Literal['single_choice', 'text_blank', 'numeric', 'expression', 'calculation']
GradingKind = Literal['choice_exact', 'text_normalized', 'numeric_tolerance', 'symbolic_review', 'rubric_review']

_GRADING_COMPATIBILITY: dict[QuestionKind, set[GradingKind]] = {
    'single_choice': {'choice_exact'},
    'text_blank': {'text_normalized'},
    'numeric': {'numeric_tolerance'},
    'expression': {'symbolic_review'},
    'calculation': {'numeric_tolerance', 'symbolic_review', 'rubric_review'},
}


def validate_grading_structure(*, question_kind: QuestionKind, grading_kind: GradingKind,
                              choice_ids: Sequence[str], accepted_answers: Sequence[str]) -> None:
    """Check already shape-validated fields without any reference or owner lookup.

    Choice answers must name supplied options; numerical answers must parse as
    finite numbers. Other graders get only the compatibility check, not semantic
    answer validation. Strings, ordering, duplicates and caller objects remain
    untouched. The caller owns schema, identity and membership validation.
    """
    if grading_kind not in _GRADING_COMPATIBILITY.get(question_kind, set()):
        raise ValueError('Duplicate or mismatched private solution')
    if grading_kind == 'choice_exact' and not set(accepted_answers).issubset(choice_ids):
        raise ValueError('Solution selects an absent option')
    if grading_kind == 'numeric_tolerance' and any(
        not math.isfinite(float(value)) for value in accepted_answers
    ):
        raise ValueError('Non-finite numeric answer')


def validate_question_solutions(questions: Sequence[dm.QuestionPublic],
                                solutions: Sequence[dm.SolutionPrivate]) -> None:
    """Check the exact supplied question versions and existing grader rules.

    This combines Import's existing package-level exact reference precondition
    with its private-solution compatibility checks. It neither resolves a newer
    question nor mutates the supplied models or their review status.
    """
    by_identity: dict[tuple[str, int], dm.QuestionPublic] = {}
    for supplied_question in questions:
        key = (supplied_question.id, supplied_question.revision)
        if key in by_identity:
            raise ValueError('Duplicate question identity')
        by_identity[key] = supplied_question
    identities: set[tuple[str, int]] = set()
    targets: set[tuple[str, int, int]] = set()
    for solution in solutions:
        ref = solution.question_ref
        question = by_identity.get((ref.id, ref.revision))
        if ref.entity != 'question' or question is None or ref.sha256 != metadata_sha256(question):
            raise ValueError('Solution question reference mismatch')
        identity = (solution.id, solution.revision)
        target = (question.id, question.revision, solution.revision)
        if identity in identities or target in targets:
            raise ValueError('Duplicate or mismatched private solution')
        identities.add(identity)
        targets.add(target)
        validate_grading_structure(question_kind=question.kind, grading_kind=solution.grading_kind,
                                   choice_ids=[choice.id for choice in question.choices],
                                   accepted_answers=solution.accepted_answers)
