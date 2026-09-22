"""Pure linkage/structure checks shared by local question-content consumers.

Inputs are already validated core models, kept as separate public questions and
private solutions. Success does not grade an answer, approve a solution, or prove
question wording, distractors, units, mathematical correctness or pedagogy.
There is no database, permission decision, content lookup or model invocation.
"""

from collections.abc import Sequence
import math

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256


def validate_question_solutions(questions: Sequence[dm.QuestionPublic],
                                solutions: Sequence[dm.SolutionPrivate]) -> None:
    """Check the exact supplied question versions and existing grader rules.

    This combines Import's existing package-level exact reference precondition
    with its private-solution compatibility checks. It neither resolves a newer
    question nor mutates the supplied models or their review status.
    """
    by_identity: dict[tuple[str, int], dm.QuestionPublic] = {}
    for question in questions:
        key = (question.id, question.revision)
        if key in by_identity:
            raise ValueError('Duplicate question identity')
        by_identity[key] = question
    identities: set[tuple[str, int]] = set()
    targets: set[tuple[str, int, int]] = set()
    grading = {
        'single_choice': {'choice_exact'},
        'text_blank': {'text_normalized'},
        'numeric': {'numeric_tolerance'},
        'expression': {'symbolic_review'},
        'calculation': {'numeric_tolerance', 'symbolic_review', 'rubric_review'},
    }
    for solution in solutions:
        ref = solution.question_ref
        question = by_identity.get((ref.id, ref.revision))
        if ref.entity != 'question' or question is None or ref.sha256 != metadata_sha256(question):
            raise ValueError('Solution question reference mismatch')
        identity = (solution.id, solution.revision)
        target = (question.id, question.revision, solution.revision)
        if identity in identities or target in targets or solution.grading_kind not in grading[question.kind]:
            raise ValueError('Duplicate or mismatched private solution')
        identities.add(identity)
        targets.add(target)
        if solution.grading_kind == 'choice_exact' and not set(solution.accepted_answers).issubset(
            {choice.id for choice in question.choices}
        ):
            raise ValueError('Solution selects an absent option')
        if solution.grading_kind == 'numeric_tolerance' and any(
            not math.isfinite(float(value)) for value in solution.accepted_answers
        ):
            raise ValueError('Non-finite numeric answer')
