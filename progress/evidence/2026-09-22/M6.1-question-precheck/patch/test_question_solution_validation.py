"""Synthetic structure/linkage cases; no grading, approval or generation claim."""

from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json
from services.api.app.application.import_parse_package import parse_package
from services.api.app.application.import_parse_types import ImportParsingError
from services.api.app.application.question_solution_validation import validate_question_solutions


def question(kind: str = 'single_choice', *, identifier: str = 'question_synthetic', revision: int = 1):
    return dm.QuestionPublic.model_validate({
        'id': identifier, 'revision': revision, 'kind': kind,
        'stem_markdown': '合成结构用例；未审核题意。',
        'choices': [{'id': 'choice_a', 'text_markdown': '合成选项 A'},
                    {'id': 'choice_b', 'text_markdown': '合成选项 B'}] if kind == 'single_choice' else [],
        'concept_ids': ['concept_synthetic'], 'skill': 'compute',
        'exposure_group': 'exposure_synthetic', 'input_instructions': '只用于结构校验。',
    })


def solution(q: dm.QuestionPublic, grading_kind: str = 'choice_exact', *,
             answers: Sequence[str] = ('choice_a',), identifier: str = 'solution_synthetic', revision: int = 1):
    return dm.SolutionPrivate.model_validate({
        'id': identifier, 'revision': revision,
        'question_ref': {'entity': 'question', 'id': q.id, 'revision': q.revision, 'sha256': metadata_sha256(q)},
        'grading_kind': grading_kind, 'accepted_answers': list(answers),
        'absolute_tolerance': 0.01, 'relative_tolerance': 0.001, 'unit': 'm',
        'solution_markdown': '合成私解；纯结构校验不核验推导。', 'review_status': 'needs_review',
    })


@pytest.mark.parametrize(('kind', 'grader', 'answers'), [
    ('single_choice', 'choice_exact', ('choice_a', 'choice_b')),
    ('text_blank', 'text_normalized', ('alpha', 'Alpha')),
    ('numeric', 'numeric_tolerance', ('1.5', '+2e0')),
    ('expression', 'symbolic_review', ('x + 1',)),
    ('calculation', 'numeric_tolerance', ('42',)),
    ('calculation', 'symbolic_review', ('x ** 2',)),
    ('calculation', 'rubric_review', ('需人工检查步骤',)),
])
def test_existing_kind_grader_pairs_preserve_full_accepted_answers_without_approval(kind, grader, answers):
    q = question(kind)
    s = solution(q, grader, answers=answers)
    before = canonical_bytes([q.model_dump(mode='json'), s.model_dump(mode='json')])
    assert validate_question_solutions([q], [s]) is None
    assert tuple(s.accepted_answers) == answers and s.review_status == 'needs_review'
    assert canonical_bytes([q.model_dump(mode='json'), s.model_dump(mode='json')]) == before


@pytest.mark.parametrize(('kind', 'grader'), [
    ('single_choice', 'numeric_tolerance'), ('text_blank', 'choice_exact'),
    ('numeric', 'text_normalized'), ('expression', 'rubric_review'),
    ('calculation', 'choice_exact'),
])
def test_incompatible_question_kind_and_grader_are_rejected(kind, grader):
    q = question(kind)
    with pytest.raises(ValueError, match='mismatched private solution'):
        validate_question_solutions([q], [solution(q, grader, answers=('1',))])


def test_choice_answers_must_identify_options_in_that_exact_question():
    q = question()
    with pytest.raises(ValueError, match='absent option'):
        validate_question_solutions([q], [solution(q, answers=('choice_a', 'absent_choice'))])


@pytest.mark.parametrize('answer', ['NaN', 'Infinity', '-inf', '1e10000', 'not-a-number'])
def test_numeric_expected_answers_must_parse_as_finite_values(answer):
    q = question('numeric')
    with pytest.raises(ValueError):
        validate_question_solutions([q], [solution(q, 'numeric_tolerance', answers=('1.0', answer))])


@pytest.mark.parametrize('field,value', [('entity', 'lesson'), ('id', 'question_other'), ('revision', 2), ('sha256', '0' * 64)])
def test_solution_must_bind_the_full_exact_public_question_reference(field, value):
    q = question()
    body = solution(q).model_dump(mode='json')
    body['question_ref'][field] = value
    s = dm.SolutionPrivate.model_validate(body)
    with pytest.raises(ValueError, match='reference mismatch'):
        validate_question_solutions([q], [s])


def test_same_id_revision_different_question_bytes_do_not_satisfy_original_reference():
    q = question()
    s = solution(q)
    replaced = q.model_copy(update={'stem_markdown': '同ID同修订的另一份题面。'})
    with pytest.raises(ValueError, match='reference mismatch'):
        validate_question_solutions([replaced], [s])


@pytest.mark.parametrize('duplicate', ['identity', 'target_revision'])
def test_existing_duplicate_solution_identity_or_target_revision_is_rejected(duplicate):
    first = question()
    second = question(identifier='question_second')
    one = solution(first)
    two = solution(second) if duplicate == 'identity' else solution(first, identifier='solution_second')
    with pytest.raises(ValueError, match='Duplicate'):
        validate_question_solutions([first, second], [one, two])


def test_distinct_historical_question_and_solution_revisions_remain_usable():
    first = question()
    second = question(revision=2)
    values = [solution(first), solution(first, revision=2), solution(second, revision=3)]
    assert validate_question_solutions([first, second], values) is None


def test_duplicate_public_question_identity_is_not_silently_overwritten():
    q = question()
    with pytest.raises(ValueError, match='Duplicate question'):
        validate_question_solutions([q, q], [solution(q)])


@pytest.fixture
def author_package():
    path = Path(__file__).resolve().parents[2] / 'fixtures/synthetic/course-author.learnpack.zip'
    with ZipFile(path) as archive:
        payloads = {name: archive.read(name) for name in archive.namelist()}
    questions = [dm.QuestionPublic.model_validate(strict_json(line))
                 for line in payloads['questions/public.jsonl'].splitlines()]
    solutions = [dm.SolutionPrivate.model_validate(strict_json(line))
                 for line in payloads['private/solutions.jsonl'].splitlines()]
    return payloads, questions, solutions


def rebuilt_author_package(payloads, questions, solutions):
    """Keep real file hashes valid so parsing reaches the semantic checks."""
    payloads = dict(payloads)
    payloads['questions/public.jsonl'] = b''.join(canonical_bytes(q) + b'\n' for q in questions)
    payloads['private/solutions.jsonl'] = b''.join(canonical_bytes(s) + b'\n' for s in solutions)
    manifest = strict_json(payloads['manifest.json'])
    for entry in manifest['files']:
        data = payloads[entry['path']]
        entry.update(size=len(data), sha256=sha256_bytes(data))
    payloads['manifest.json'] = canonical_bytes(manifest)
    stream = BytesIO()
    with ZipFile(stream, 'w') as archive:
        for name, data in payloads.items():
            archive.writestr(name, data)
    return stream.getvalue()


def test_import_preserves_accepted_answer_sets_and_historical_revisions(author_package):
    payloads, questions, solutions = author_package
    solutions[0] = solutions[0].model_copy(update={'accepted_answers': ['opt_a', 'opt_b']})
    solutions.append(solutions[0].model_copy(update={'revision': 2}))
    historical = questions[0].model_copy(update={'revision': 2})
    questions.append(historical)
    solutions.append(solutions[0].model_copy(update={
        'revision': 3,
        'question_ref': dm.ContentRef(entity='question', id=historical.id, revision=historical.revision,
                                     sha256=metadata_sha256(historical)),
    }))
    parsed = parse_package(rebuilt_author_package(payloads, questions, solutions))
    assert [value for value in parsed.objects if isinstance(value, dm.QuestionPublic)] == questions
    assert list(parsed.solutions) == solutions
    assert all(value.review_status == 'needs_review' for value in parsed.solutions)


@pytest.mark.parametrize('mutation', [
    'entity', 'id', 'revision', 'sha256', 'grader', 'absent_option', 'nonfinite',
    'duplicate_identity', 'duplicate_target', 'duplicate_question',
])
def test_import_still_reports_package_invalid_for_question_solution_failures(author_package, mutation):
    payloads, questions, solutions = author_package
    if mutation in {'entity', 'id', 'revision', 'sha256'}:
        values = {'entity': 'lesson', 'id': 'question_absent', 'revision': 2, 'sha256': '0' * 64}
        body = solutions[0].model_dump(mode='json')
        body['question_ref'][mutation] = values[mutation]
        solutions[0] = dm.SolutionPrivate.model_validate(body)
    elif mutation == 'grader':
        solutions[0] = solutions[0].model_copy(update={'grading_kind': 'text_normalized'})
    elif mutation == 'absent_option':
        solutions[0] = solutions[0].model_copy(update={'accepted_answers': ['absent_choice']})
    elif mutation == 'nonfinite':
        solutions[1] = solutions[1].model_copy(update={'accepted_answers': ['Infinity']})
    elif mutation == 'duplicate_identity':
        solutions[1] = solutions[1].model_copy(update={'id': solutions[0].id})
    elif mutation == 'duplicate_target':
        solutions.append(solutions[0].model_copy(update={'id': 'solution_second'}))
    else:
        questions.append(questions[0])
    with pytest.raises(ImportParsingError) as error:
        parse_package(rebuilt_author_package(payloads, questions, solutions))
    assert error.value.code == 'PACKAGE_INVALID'
