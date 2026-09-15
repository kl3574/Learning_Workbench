"""Pure lexical-han-gram-v1 terms; never normalize stored Markdown or infer aliases.

The caller owns Content/Policy, body/hash checks, resource limits, FTS and ranking
ties. These functions neither query storage nor prove relevance or permission.
"""

import hashlib
import re
import unicodedata

from .errors import ApiError

UNICODE_VERSION = '15.0.0'
TOKENIZER_VERSION = 'lexical-han-gram-v1'
NORMALIZATION_VERSION = 'nfc-v1'
RANKING_VERSION = 'scope-coverage-v1'
MAX_QUERY_CODEPOINTS = 512
MAX_QUERY_TERMS = 64
_HAN_RANGES = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF),
               (0x20000, 0x2FA1F), (0x30000, 0x323AF))
_MATH_SYMBOLS = frozenset('+-*/=<>≤≥≠≈±×÷∑∏√∞∂∇∈∉⊂⊆∪∩∀∃¬∧∨→↔^_%|!')
_TERM = re.compile(r'[tghwmu](?:[0-9a-f]{2})+')


def _text(text: str) -> None:
    if not isinstance(text, str) or any(0xD800 <= ord(character) <= 0xDFFF for character in text):
        raise ApiError(422, 'SCHEMA_INVALID', '检索文字必须是有效 Unicode 文本。')


def _unicode_version() -> None:
    # The project pins Python 3.12; its NFC, categories and str.casefold share UCD15.
    if unicodedata.unidata_version != UNICODE_VERSION:
        raise ApiError(503, 'TOKENIZER_VERSION_UNAVAILABLE', '所需的 Unicode 词法版本不可用。')


def _ascii_letter(character: str) -> bool:
    return 'A' <= character <= 'Z' or 'a' <= character <= 'z'


def _han(character: str) -> bool:
    point = ord(character)
    return any(low <= point <= high for low, high in _HAN_RANGES)


def _latin(character: str) -> bool:
    return unicodedata.category(character).startswith('L') and 'LATIN' in unicodedata.name(character, '')


def _encoded(prefix: str, value: str) -> str:
    return prefix + value.encode('utf-8').hex()


def tokenize(text: str) -> tuple[str, ...]:
    """Return unique ASCII-sorted typed hex terms; a termless body is valid."""
    _unicode_version()
    _text(text)
    normalized = unicodedata.normalize('NFC', text)
    terms: set[str] = set()
    position = 0
    while position < len(normalized):
        character = normalized[position]
        if character == '\\' and position + 1 < len(normalized) and _ascii_letter(normalized[position + 1]):
            end = position + 2
            while end < len(normalized) and _ascii_letter(normalized[end]):
                end += 1
            terms.add(_encoded('t', normalized[position:end]))
            position = end
        elif _han(character):
            terms.add(_encoded('h', character))
            if position + 1 < len(normalized) and _han(normalized[position + 1]):
                terms.add(_encoded('g', normalized[position:position + 2]))
            position += 1
        elif _latin(character):
            end = position + 1
            while end < len(normalized) and (_latin(normalized[end]) or unicodedata.category(normalized[end]).startswith('M')):
                end += 1
            terms.add(_encoded('w', unicodedata.normalize('NFC', normalized[position:end].casefold())))
            position = end
        elif '0' <= character <= '9':
            end = position + 1
            while end < len(normalized) and '0' <= normalized[end] <= '9':
                end += 1
            terms.add(_encoded('w', normalized[position:end]))
            position = end
        else:
            if character in _MATH_SYMBOLS:
                terms.add(_encoded('m', character))
            elif unicodedata.category(character)[0] in {'L', 'N'}:
                terms.add(_encoded('u', character))
            position += 1
    return tuple(sorted(terms))


def tokenize_query(text: str) -> tuple[str, ...]:
    """Enforce the query's original-codepoint and unique-derived-term budgets."""
    _unicode_version()
    _text(text)
    if not 1 <= len(text) <= MAX_QUERY_CODEPOINTS or not text.strip():
        raise ApiError(422, 'SCHEMA_INVALID', '检索文字长度或空白约束不满足。')
    terms = tokenize(text)
    if not terms:
        raise ApiError(422, 'QUERY_NO_TERMS', '检索文字没有可匹配的词项。')
    if len(terms) > MAX_QUERY_TERMS:
        raise ApiError(422, 'QUERY_TERM_BUDGET_EXCEEDED', '检索文字的不同词项超过预算。')
    return terms


def _canonical_terms(terms: tuple[str, ...]) -> None:
    """Check the stored representation, not the terms' correspondence to a body."""
    if not isinstance(terms, tuple):
        raise ValueError('Expected canonical lexical terms.')
    previous = ''
    for term in terms:
        if not isinstance(term, str) or _TERM.fullmatch(term) is None or term <= previous:
            raise ValueError('Expected canonical lexical terms.')
        try:
            bytes.fromhex(term[1:]).decode('utf-8')
        except UnicodeError:
            raise ValueError('Expected canonical lexical terms.') from None
        previous = term


def terms_sha256(terms: tuple[str, ...]) -> str:
    """Hash exact canonical ASCII terms joined by one space, with no trailing byte."""
    _canonical_terms(terms)
    return hashlib.sha256(' '.join(terms).encode('ascii')).hexdigest()


def coverage_score(query_terms: tuple[str, ...], block_terms: tuple[str, ...]) -> float:
    """Return |Q intersection T|/|Q|; zero is a non-hit, never an HTTP hit score."""
    _canonical_terms(query_terms)
    _canonical_terms(block_terms)
    if not query_terms:
        raise ApiError(422, 'QUERY_NO_TERMS', '检索文字没有可匹配的词项。')
    query = frozenset(query_terms)
    return sum(term in query for term in block_terms) / len(query)
