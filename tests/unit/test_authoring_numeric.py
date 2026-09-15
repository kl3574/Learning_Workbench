"""Finite arithmetic through the public evaluator, independent known answers."""
import pytest
from services.api.app.application.authoring_numeric import (
    NumericError, evaluate_expression, evaluate_plan, validate_expression, validate_plan,
)


def test_worked_example_arithmetic_preserves_precedence_and_declared_variables():
    assert evaluate_expression('(mass * speed ** 2) / 2', {'mass': 2.0, 'speed': 3.0}) == 9.0
    assert evaluate_expression('-2 ** 2 + 2 ** -2', {}) == -3.75


def test_tolerance_overflow_is_an_error_instead_of_an_infinite_passing_threshold():
    from services.api.app.application.authoring_numeric import evaluate_plan
    plan = {'version': 'finite-arithmetic-v1', 'seed': None, 'variables': [], 'assertions': [
        {'id': 'check_overflow', 'expression': '0', 'expected': 1e308, 'atol': 0.0, 'rtol': 2.0, 'unit': '1'}]}
    result = evaluate_plan(plan)
    assert len(result) == 1
    assert result[0].actual is None
    assert result[0].passed is False
    assert result[0].error_code == 'NUMERIC_NONFINITE'



@pytest.mark.parametrize('expression', [
    '__import__("os")', 'a[0]', 'a.real', '1 // 2', '1 % 2', 'True', 'False', '1j',
    '"1"', 'a = 1', '1 if a else 2', '0x10', '1_000', 'sum(1)', '1; 2', 'missing + 1',
])
def test_rejects_language_outside_explicit_arithmetic(expression):
    with pytest.raises(NumericError, match='NUMERIC_PLAN_UNSUPPORTED'):
        validate_expression(expression, {'a'})


@pytest.mark.parametrize(('expression', 'code'), [
    ('1 / 0', 'NUMERIC_DOMAIN_ERROR'), ('0 ** -1', 'NUMERIC_DOMAIN_ERROR'),
    ('2 ** 17', 'NUMERIC_DOMAIN_ERROR'), ('2 ** -17', 'NUMERIC_DOMAIN_ERROR'),
    ('2 ** (3 / 2)', 'NUMERIC_DOMAIN_ERROR'), ('1e999', 'NUMERIC_NONFINITE'),
    ('1e308 * 2', 'NUMERIC_NONFINITE'), ('1e308 - -1e308', 'NUMERIC_NONFINITE'),
])
def test_arithmetic_domain_and_every_nonfinite_intermediate_fail(expression, code):
    with pytest.raises(NumericError, match=code):
        evaluate_expression(expression, {})


def test_fixed_exponent_bound_and_decimal_scientific_literals():
    assert evaluate_expression('2 ** 16', {}) == 65536.0
    assert evaluate_expression('2 ** -16', {}) == 0.0000152587890625
    assert evaluate_expression('.25 + 2.5e-1', {}) == 0.5
    assert evaluate_expression('(' * 100 + '1' + ')' * 100, {}) == 1.0


def test_depth_node_and_text_bounds_are_separate():
    assert evaluate_expression('-' * 15 + '1', {}) == -1.0
    with pytest.raises(NumericError, match='NUMERIC_PLAN_UNSUPPORTED'):
        validate_expression('-' * 16 + '1', set())
    expression = '1'
    for _ in range(6):
        expression = f'({expression}+{expression})'
    assert evaluate_expression(expression, {}) == 64.0  # 127 expression nodes, depth 7.
    with pytest.raises(NumericError, match='NUMERIC_PLAN_UNSUPPORTED'):
        validate_expression(f'{expression}+1', set())  # 129 expression nodes.
    with pytest.raises(NumericError, match='NUMERIC_PLAN_UNSUPPORTED'):
        validate_expression(' ' * 512 + '1', set())


def test_results_keep_input_order_and_unit_labels_do_not_claim_dimensions():
    plan = {'version': 'finite-arithmetic-v1', 'seed': None, 'variables': [
        {'name': 'x', 'value': 2.0, 'unit': 'user-declared metres'}], 'assertions': [
        {'id': 'first', 'expression': 'x+1', 'expected': 3.0, 'atol': 0.0, 'rtol': 0.0, 'unit': 'seconds'},
        {'id': 'second', 'expression': 'x', 'expected': 7.0, 'atol': 0.0, 'rtol': 0.0, 'unit': '1'},
        {'id': 'third', 'expression': '1/0', 'expected': 0.0, 'atol': 0.0, 'rtol': 0.0, 'unit': '1'}]}
    result = evaluate_plan(plan)
    assert [(item.id, item.actual, item.passed, item.error_code) for item in result] == [
        ('first', 3.0, True, None), ('second', 2.0, False, None), ('third', None, False, 'NUMERIC_DOMAIN_ERROR')]


@pytest.mark.parametrize(('actual', 'expected', 'atol', 'rtol'), [
    ('0', 1e308, 1e308, 1.0), ('1e308', -1e308, 0.0, 0.0),
])
def test_tolerance_sum_and_difference_overflow_are_not_mismatch_or_pass(actual, expected, atol, rtol):
    result = evaluate_plan({'version': 'finite-arithmetic-v1', 'variables': [], 'seed': None, 'assertions': [
        {'id': 'overflow', 'expression': actual, 'expected': expected, 'atol': atol, 'rtol': rtol, 'unit': '1'}]})
    assert result[0].error_code == 'NUMERIC_NONFINITE'
    assert result[0].actual is None


def test_plan_admission_never_evaluates_or_hides_undeclared_names():
    plan = {'version': 'finite-arithmetic-v1', 'variables': [], 'seed': None, 'assertions': [
        {'id': 'domain', 'expression': '1/0', 'expected': 0.0, 'atol': 0.0, 'rtol': 0.0, 'unit': '1'}]}
    validate_plan(plan)  # Syntax is valid; the actual error belongs to approved execution.
    plan['assertions'][0]['expression'] = 'undeclared'
    with pytest.raises(NumericError, match='NUMERIC_PLAN_UNSUPPORTED'):
        validate_plan(plan)


def test_bool_variables_cannot_be_numbers():
    with pytest.raises(NumericError, match='NUMERIC_PLAN_UNSUPPORTED'):
        evaluate_expression('x', {'x': True})
