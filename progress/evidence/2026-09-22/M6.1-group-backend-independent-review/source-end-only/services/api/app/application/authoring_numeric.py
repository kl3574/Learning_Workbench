"""finite-arithmetic-v1: bounded syntax trees, interpreted without Python execution.

Only decimal literals, declared ASCII names and arithmetic exist in this language.
AST depth counts literal/name and unary/binary expression nodes (not parentheses).
This module is also the fixed stdlib-only sandbox entry: no product/site imports.
"""
from dataclasses import dataclass
import math
import re
from typing import Literal


class NumericError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, repr=False)
class _Node:
    kind: Literal['number', 'name', 'unary', 'binary']
    value: str
    children: tuple['_Node', ...] = ()
    depth: int = 1


_TOKEN = re.compile(r'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[A-Za-z][A-Za-z0-9_]*|\*\*|[()+*/-]')
_NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,31}\Z')
_RESERVED = {'True', 'False', 'None', 'and', 'or', 'not', 'if', 'else', 'lambda', 'import'}


class _Parser:
    def __init__(self, text: str, names: set[str]):
        if type(text) is not str or not text.strip() or len(text) > 512:
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
        self.tokens: list[str] = []
        offset = 0
        while offset < len(text):
            if text[offset] in ' \t\r\n':
                offset += 1
                continue
            match = _TOKEN.match(text, offset)
            if match is None:
                raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
            self.tokens.append(match[0])
            offset = match.end()
        self.index = 0
        self.nodes = 0
        self.names = names

    def peek(self) -> str:
        return self.tokens[self.index] if self.index < len(self.tokens) else ''

    def node(self, kind: Literal['number', 'name', 'unary', 'binary'], value: str,
             children: tuple[_Node, ...] = ()) -> _Node:
        self.nodes += 1
        depth = 1 + max((child.depth for child in children), default=0)
        if self.nodes > 128 or depth > 16:
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
        return _Node(kind, value, children, depth)

    def expression(self, minimum: int = 0) -> _Node:
        token = self.peek()
        self.index += 1
        if token in {'+', '-'}:
            left = self.node('unary', token, (self.expression(30),))
        elif token == '(':
            left = self.expression()
            if self.peek() != ')':
                raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
            self.index += 1
        elif token and (token[0].isdigit() or token[0] == '.'):
            left = self.node('number', token)
        elif token in self.names and token not in _RESERVED:
            left = self.node('name', token)
        else:
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
        precedence = {'+': 10, '-': 10, '*': 20, '/': 20, '**': 40}
        while self.peek() in precedence and precedence[self.peek()] >= minimum:
            operator = self.peek()
            self.index += 1
            right = self.expression(precedence[operator] + (0 if operator == '**' else 1))
            left = self.node('binary', operator, (left, right))
        return left

    def parse(self) -> _Node:
        try:
            result = self.expression()
        except RecursionError:
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED') from None
        if self.index != len(self.tokens):
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
        return result


def _finite(value: object) -> float:
    if type(value) not in {int, float}:
        raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
    try:
        result = float(value)  # type: ignore[arg-type]
    except OverflowError:
        raise NumericError('NUMERIC_NONFINITE') from None
    if not math.isfinite(result):
        raise NumericError('NUMERIC_NONFINITE')
    return result


def _variables(variables: dict[str, float]) -> dict[str, float]:
    if len(variables) > 32 or any(not _NAME.fullmatch(name) or name in _RESERVED for name in variables):
        raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
    return {name: _finite(value) for name, value in variables.items()}


def validate_expression(text: str, names: set[str]) -> None:
    """Syntax admission only; a parsed arithmetic instance can still evaluate in error."""
    _Parser(text, names).parse()


def _evaluate(node: _Node, variables: dict[str, float]) -> float:
    if node.kind == 'number':
        return _finite(float(node.value))
    if node.kind == 'name':
        return variables[node.value]
    left = _evaluate(node.children[0], variables)
    if node.kind == 'unary':
        return _finite(-left if node.value == '-' else left)
    right = _evaluate(node.children[1], variables)
    try:
        if node.value == '+':
            value = left + right
        elif node.value == '-':
            value = left - right
        elif node.value == '*':
            value = left * right
        elif node.value == '/':
            value = left / right
        else:
            if not right.is_integer() or not -16 <= right <= 16:
                raise NumericError('NUMERIC_DOMAIN_ERROR')
            value = left ** int(right)
    except (ZeroDivisionError, ValueError):
        raise NumericError('NUMERIC_DOMAIN_ERROR') from None
    except OverflowError:
        raise NumericError('NUMERIC_NONFINITE') from None
    return _finite(value)


def evaluate_expression(text: str, variables: dict[str, float]) -> float:
    values = _variables(variables)
    return _evaluate(_Parser(text, set(values)).parse(), values)


@dataclass(frozen=True, repr=False)
class AssertionEvaluation:
    id: str
    actual: float | None
    passed: bool
    error_code: Literal['NUMERIC_DOMAIN_ERROR', 'NUMERIC_NONFINITE'] | None


@dataclass(frozen=True, repr=False)
class _Assertion:
    id: str
    expression: str
    expected: float
    atol: float
    rtol: float


def _object(value: object, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys or any(type(key) is not str for key in value):
        raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
    return value


def _text(value: object, limit: int) -> str:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
    return value


def _plan(plan: object) -> tuple[dict[str, float], tuple[_Assertion, ...]]:
    raw = _object(plan, {'version', 'variables', 'assertions', 'seed'})
    if raw['version'] != 'finite-arithmetic-v1' or raw['seed'] is not None:
        raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
    items, checks = raw['variables'], raw['assertions']
    if not isinstance(items, list) or len(items) > 32 or not isinstance(checks, list) or not 1 <= len(checks) <= 32:
        raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
    variables: dict[str, float] = {}
    for item in items:
        value = _object(item, {'name', 'value', 'unit'})
        name = _text(value['name'], 32)
        _text(value['unit'], 64)
        if name in variables:
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
        variables[name] = _finite(value['value'])
    variables = _variables(variables)
    assertions: list[_Assertion] = []
    names: set[str] = set()
    for check in checks:
        value = _object(check, {'id', 'expression', 'expected', 'atol', 'rtol', 'unit'})
        identity = _text(value['id'], 80)
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,79}', identity) or identity in names:
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
        names.add(identity)
        _text(value['unit'], 64)
        expression = _text(value['expression'], 512)
        validate_expression(expression, set(variables))
        expected, atol, rtol = (_finite(value[key]) for key in ('expected', 'atol', 'rtol'))
        if atol < 0 or rtol < 0:
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
        assertions.append(_Assertion(identity, expression, expected, atol, rtol))
    return variables, tuple(assertions)


def validate_plan(plan: object) -> None:
    """Reject unsupported input before approval; no expression is executed here."""
    _plan(plan)


def evaluate_plan(plan: object) -> tuple[AssertionEvaluation, ...]:
    variables, assertions = _plan(plan)
    results: list[AssertionEvaluation] = []
    for item in assertions:
        try:
            actual = evaluate_expression(item.expression, variables)
            difference = _finite(abs(_finite(actual - item.expected)))
            product = _finite(item.rtol * abs(item.expected))
            tolerance = _finite(item.atol + product)
            results.append(AssertionEvaluation(item.id, actual, difference <= tolerance, None))
        except NumericError as error:
            if error.code not in {'NUMERIC_DOMAIN_ERROR', 'NUMERIC_NONFINITE'}:
                raise
            code: Literal['NUMERIC_DOMAIN_ERROR', 'NUMERIC_NONFINITE'] = (
                'NUMERIC_DOMAIN_ERROR' if error.code == 'NUMERIC_DOMAIN_ERROR' else 'NUMERIC_NONFINITE')
            results.append(AssertionEvaluation(item.id, None, False, code))
    return tuple(results)
