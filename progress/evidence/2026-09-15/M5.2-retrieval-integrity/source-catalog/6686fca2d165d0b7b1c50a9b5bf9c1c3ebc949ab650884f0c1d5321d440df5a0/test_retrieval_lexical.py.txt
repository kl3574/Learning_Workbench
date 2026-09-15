"""Lexical contracts and frozen fixture generation, not retrieval/Recall acceptance."""

import hashlib
import json
from pathlib import Path

import pytest

from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.application.errors import ApiError

ROOT = Path(__file__).resolve().parents[2]


def encoded(prefix: str, text: str) -> str:
    return prefix + text.encode('utf-8').hex()


def test_han_unigrams_bigrams_repeat_dedup_and_no_cross_punctuation():
    from services.api.app.application.retrieval_lexical import tokenize

    assert tokenize('概率概率') == tuple(sorted({
        encoded('h', '概'), encoded('h', '率'), encoded('g', '概率'), encoded('g', '率概'),
    }))
    assert tokenize('概，率') == tuple(sorted((encoded('h', '概'), encoded('h', '率'))))


@pytest.mark.parametrize('point', [0x3400, 0x4DBF, 0x4E00, 0x9FFF, 0x20000, 0x2FA1F, 0x30000, 0x323AF])
def test_fixed_han_ranges_include_the_declared_endpoints_even_if_unassigned(point):
    from services.api.app.application.retrieval_lexical import tokenize

    assert tokenize(chr(point)) == (encoded('h', chr(point)),)


def test_nfc_is_derived_only_and_latin_casefold_is_not_greek_casefold():
    from services.api.app.application.retrieval_lexical import tokenize

    source = 'Cafe\u0301 STRAẞE Δt δt'
    assert tokenize(source) == tuple(sorted({encoded('w', 'café'), encoded('w', 'strasse'),
        encoded('u', 'Δ'), encoded('u', 'δ'), encoded('w', 't')}))
    assert source == 'Cafe\u0301 STRAẞE Δt δt'
    assert tokenize('\uf900') == (encoded('h', '豈'),)


def test_tex_consumes_ascii_control_word_and_preserves_case_without_aliases():
    from services.api.app.application.retrieval_lexical import tokenize

    assert tokenize(r'\Gamma \gamma \alpha α alpha') == tuple(sorted({
        encoded('t', r'\Gamma'), encoded('t', r'\gamma'), encoded('t', r'\alpha'),
        encoded('u', 'α'), encoded('w', 'alpha'),
    }))
    assert tokenize(r'\Gamma2') == tuple(sorted((encoded('t', r'\Gamma'), encoded('w', '2'))))
    assert tokenize('\\，') == ()


def test_latin_digits_and_marks_follow_declared_word_boundaries():
    from services.api.app.application.retrieval_lexical import tokenize

    assert tokenize('FTS5') == tokenize('fts 5') == tuple(sorted((encoded('w', 'fts'), encoded('w', '5'))))
    assert tokenize('a\u0301b') == (encoded('w', 'áb'),)
    assert tokenize('\u0301abc') == (encoded('w', 'abc'),)
    assert tokenize('１２') == tuple(sorted((encoded('u', '１'), encoded('u', '２'))))


def test_math_symbols_are_exact_terms_and_match_syntax_is_only_text():
    from services.api.app.application.retrieval_lexical import tokenize

    symbols = '+-*/=<>≤≥≠≈±×÷∑∏√∞∂∇∈∉⊂⊆∪∩∀∃¬∧∨→↔^_%|!'
    assert tokenize(symbols) == tuple(sorted(encoded('m', character) for character in symbols))
    assert tokenize('"MATCH" OR NOT NEAR(match*)') == tuple(sorted({
        encoded('w', 'match'), encoded('w', 'or'), encoded('w', 'not'), encoded('w', 'near'), encoded('m', '*'),
    }))
    assert tokenize('“”（），；：\\') == ()


@pytest.mark.parametrize('text', ['', ' \n\t', '（）“”'])
def test_empty_lexical_body_is_valid_but_zero_term_query_is_rejected(text):
    from services.api.app.application.retrieval_lexical import tokenize, tokenize_query

    assert tokenize(text) == ()
    with pytest.raises(ApiError) as failure:
        tokenize_query(text)
    assert failure.value.status == 422
    assert failure.value.code == ('QUERY_NO_TERMS' if text.strip() else 'SCHEMA_INVALID')


@pytest.mark.parametrize('text', ['\ud800', '\udfff', 1, True, b'abc', None])
def test_invalid_unicode_or_non_text_is_rejected_without_echo(text):
    from services.api.app.application.retrieval_lexical import tokenize

    with pytest.raises(ApiError) as failure:
        tokenize(text)
    assert failure.value.code == 'SCHEMA_INVALID'
    assert failure.value.message == '检索文字必须是有效 Unicode 文本。'


def test_query_budget_counts_codepoints_and_unique_derived_terms():
    from services.api.app.application.retrieval_lexical import tokenize_query

    assert len(tokenize_query('𠀀' * 512)) == 2
    with pytest.raises(ApiError, match='SCHEMA_INVALID'):
        tokenize_query('𠀀' * 513)
    words = [chr(97 + i // 26) + chr(97 + i % 26) for i in range(65)]
    assert len(tokenize_query(' '.join(words[:64]))) == 64
    with pytest.raises(ApiError) as failure:
        tokenize_query(' '.join(words))
    assert failure.value.code == 'QUERY_TERM_BUDGET_EXCEEDED'
    assert len(tokenize_query('a ' * 100)) == 1


def test_wrong_unicode_version_fails_closed_before_any_tokenization(monkeypatch):
    from services.api.app.application import retrieval_lexical as lexical

    monkeypatch.setattr(lexical.unicodedata, 'unidata_version', '16.0.0')
    for operation in (lexical.tokenize, lexical.tokenize_query):
        with pytest.raises(ApiError) as failure:
            operation('abc')
        assert failure.value.code == 'TOKENIZER_VERSION_UNAVAILABLE'


def test_terms_hash_and_scope_coverage_have_no_global_statistics():
    from services.api.app.application.retrieval_lexical import coverage_score, terms_sha256

    assert terms_sha256(()) == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    assert terms_sha256(('w61', 'w62')) == hashlib.sha256(b'w61 w62').hexdigest()
    assert coverage_score(('w61', 'w62'), ('w62', 'w63')) == 0.5
    assert coverage_score(('w61', 'w62'), ('w61', 'w62', 'w63')) == 1.0
    assert coverage_score(('w61',), ()) == 0.0
    with pytest.raises(ApiError, match='QUERY_NO_TERMS'):
        coverage_score((), ('w61',))


@pytest.mark.parametrize('terms', [('w62', 'w61'), ('w61', 'w61'), ('OR',), ('wzz',), ('w6',), ('wff',)])
def test_noncanonical_persisted_terms_do_not_get_a_plausible_hash(terms):
    from services.api.app.application.retrieval_lexical import terms_sha256

    with pytest.raises(ValueError, match='canonical lexical terms'):
        terms_sha256(terms)


def test_fixture_is_exact_hashed_material_and_gold_before_any_retrieval(tmp_path):
    from scripts.generate_retrieval_fixture import build_fixture, generate

    fixture = build_fixture(ROOT / 'PRODUCT_DESIGN.md')
    assert len(fixture.objects) == 32 and len(fixture.bodies) == 30
    blocks, lesson, course = fixture.objects[:30], fixture.objects[30], fixture.objects[31]
    assert [reference.id for reference in lesson.block_refs] == [block.id for block in blocks]
    assert course.lesson_refs[0].sha256 == metadata_sha256(lesson)
    gold = json.loads(fixture.payloads['gold.json'])
    assert len(gold['cases']) == 42
    by_id = {block.id: block for block in blocks}
    for case in gold['cases']:
        assert [ref['id'] for ref in case['expected_refs']] == case['expected_block_ids']
        assert all(ref['sha256'] == metadata_sha256(by_id[ref['id']]) for ref in case['expected_refs'])
    for block in blocks:
        body = fixture.bodies[block.body_path]
        assert not body.endswith(b'\n') and hashlib.sha256(body).hexdigest() == block.body_sha256
        assert fixture.payloads[f'blocks/{block.id}.r1.json'] == canonical_bytes(block)
    assert json.loads(fixture.payloads['passport.json'])['execution'] == {
        'content_published': False, 'retrieval_executed': False, 'recall_measured': False,
    }
    first = generate(ROOT / 'PRODUCT_DESIGN.md', tmp_path)
    assert generate(ROOT / 'PRODUCT_DESIGN.md', tmp_path, check=True) == first
    assert generate(ROOT / 'PRODUCT_DESIGN.md', tmp_path) == first


@pytest.mark.parametrize('damage', ['heading', 'fence', 'hash', 'duplicate_key', 'gold_reference'])
def test_fixture_rejects_ambiguous_or_damaged_sole_source_before_writing(tmp_path, damage):
    from scripts.generate_retrieval_fixture import generate

    source = (ROOT / 'PRODUCT_DESIGN.md').read_text()
    if damage == 'heading':
        source += '\n## F.1 M5.2 原创冻结词法基准 lexical-gold-v1\n'
    elif damage == 'fence':
        source = source.replace('# 附录 G：', '```json\n{}\n```\n# 附录 G：', 1)
    elif damage == 'hash':
        source = source.replace('d178039d0e51b963c0dfac383d8ba42dadccc5cbcd370161ba8547bbfc31bae1', '0' * 64, 1)
    elif damage == 'duplicate_key':
        source = source.replace('"index_field": "body_markdown",', '"index_field": "body_markdown", "index_field": "body_markdown",', 1)
    else:
        source = source.replace('"expected_block_ids": [\n        "m52_block_01"', '"expected_block_ids": [\n        "missing_block"', 1)
    spec = tmp_path / 'SPEC.md'
    spec.write_text(source)
    destination = tmp_path / 'output'
    with pytest.raises(ValueError):
        generate(spec, destination)
    assert not destination.exists()


def test_fixture_refuses_all_writes_when_any_existing_file_differs(tmp_path):
    from scripts.generate_retrieval_fixture import generate

    destination = tmp_path / 'output'
    destination.mkdir()
    (destination / 'gold.json').write_text('user work')
    with pytest.raises(ValueError, match='edited destination'):
        generate(ROOT / 'PRODUCT_DESIGN.md', destination)
    assert list(destination.iterdir()) == [destination / 'gold.json']
    assert (destination / 'gold.json').read_text() == 'user work'


def test_fixture_check_is_read_only_and_symlinks_are_rejected(tmp_path):
    from scripts.generate_retrieval_fixture import generate

    missing = tmp_path / 'missing'
    with pytest.raises(ValueError):
        generate(ROOT / 'PRODUCT_DESIGN.md', missing, check=True)
    assert not missing.exists()
    outside = tmp_path / 'outside'
    outside.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        generate(ROOT / 'PRODUCT_DESIGN.md', link)
    assert not list(outside.iterdir())
