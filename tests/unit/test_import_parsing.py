"""Actual import candidates, hostile inputs and preservation boundaries."""

import base64
from dataclasses import replace
import hashlib
from io import BytesIO
import json
from pathlib import Path
import stat
import struct
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

import pytest
from markdown_it import MarkdownIt

from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets
from packages.contracts.canonical import metadata_sha256
from packages.contracts.validation import validate_objects
from services.api.app.application.import_parsing import detect_import_visibility, parse_import
from services.api.app.application.import_parse_types import ImportParsingError
from services.api.app.infrastructure.import_archive import has_complete_archive_envelope

ROOT = Path(__file__).resolve().parents[2]


def parse(data, kind="markdown", filename="original.md", *, budgets=ImportBudgets()):
    return parse_import(data, kind=kind, filename=filename, source_id="source_original", budgets=budgets)


def public_text(result):
    return "\n".join(data.decode() for data in result.bodies.values())


def package_payloads(profile="author"):
    path = ROOT / f"fixtures/synthetic/course-{profile}.learnpack.zip"
    with ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def repack(payloads, *, additions=(), compression=ZIP_STORED):
    """Independently update raw payload hashes after modifying a test archive."""
    manifest = json.loads(payloads["manifest.json"])
    entries = {entry["path"]: entry for entry in manifest["files"]}
    for entry in additions:
        entries[entry["path"]] = entry
    manifest["files"] = [
        {**entries[name], "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in payloads.items()
        if name != "manifest.json"
    ]
    stream = BytesIO()
    with ZipFile(stream, "w", compression=compression) as archive:
        for name, data in payloads.items():
            archive.writestr(name, json.dumps(manifest).encode() if name == "manifest.json" else data)
    return stream.getvalue()


def test_markdown_uses_syntax_boundaries_preserves_tex_code_and_exact_source_references(tmp_path):
    target = tmp_path / "must-not-exist"
    data = (
        f"# 估计理论\n\n## 条件\n\n显式公式 $x_1$ 与来源 [材料](https://example.invalid/source)。\n\n"
        "$$\n\\sum_i x_i\n\n= \\theta\n$$\n\n"
        f"```python\nfrom pathlib import Path\nPath({str(target)!r}).write_text('executed')\n```\n"
    ).encode()
    result = parse(data)
    assert not target.exists()
    assert any(isinstance(value, dm.ContentBlock) and value.kind == "code" for value in result.objects)
    assert any(b"$$\n\\sum_i x_i\n\n= \\theta\n$$" in body for body in result.bodies.values())
    assert "估计理论" in public_text(result) and "$x_1$" in public_text(result)
    assert result.citations and all(
        citation.source_sha256 == hashlib.sha256(data).hexdigest() for citation in result.citations
    )
    assert all("source_original" in citation.locator for citation in result.citations)
    assert any(
        citation.url == "https://example.invalid/source" and citation.verification == "unverified"
        for citation in result.citations
    )
    validate_objects(result.objects, result.bodies)
    assert [metadata_sha256(value) for value in result.objects] == [
        metadata_sha256(value) for value in parse(data).objects
    ]
    assert all(len(value.id) <= 80 for value in result.objects)


def test_plain_text_is_one_unstructured_literal_block_and_lf_conversion_is_explicit():
    data = b"# not a structured lesson\r\n<script>literal text</script>\r\n"
    result = parse(data, "text", "original.txt")
    blocks = [value for value in result.objects if isinstance(value, dm.ContentBlock)]
    assert len(blocks) == 1 and blocks[0].kind == "text"
    assert len(result.bodies) == 1 and next(iter(result.bodies.values())).startswith(b"```text\n")
    assert "LINE_ENDINGS_NORMALIZED" in {item.code for item in result.warnings}
    assert all(b"\r" not in body for body in result.bodies.values())
    assert result.citations[0].source_sha256 == hashlib.sha256(data).hexdigest()
    assert result.citations[0].source_sha256 != hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def test_html_removes_active_content_keeps_source_tex_and_marks_image_formula_loss():
    data = b"""<!doctype html><html><body><h1>Original</h1><p onclick="evil()">Safe $x_1$ text
<script>window.secret='never execute'</script><iframe src="https://evil.invalid/embed"></iframe>
<a href="javascript:evil()">unsafe link text</a><a href="https://example.invalid/source">source</a>
<img src="https://evil.invalid/image" onerror="evil()"><svg onload="evil()"><text>not reconstructed</text></svg>
</p><script type="math/tex; mode=display">\\frac{a}{b}</script>
<math><semantics><annotation encoding="application/x-tex">\\theta_1</annotation></semantics></math>
<table><tr><td>A</td><td>B</td></tr></table></body></html>"""
    result = parse(data, "html", "original.html")
    text = public_text(result)
    assert "Safe $x_1$ text" in text and "unsafe link text" in text
    assert "\\frac{a}{b}" in text and "\\theta_1" in text
    assert all(
        forbidden not in text
        for forbidden in [
            "<script",
            "<iframe",
            "onerror",
            "onclick",
            "javascript:",
            "evil.invalid",
            "window.secret",
            "not reconstructed",
        ]
    )
    assert {
        "HTML_ACTIVE_ELEMENT_REMOVED",
        "HTML_ACTIVE_ATTRIBUTES_REMOVED",
        "HTML_LINK_REMOVED",
        "HTML_FIGURE_NOT_TEX",
        "HTML_TABLE_LINEARIZED",
    } <= {item.code for item in result.warnings}
    assert all(item.severity == "warning" for item in result.warnings)
    validate_objects(result.objects, result.bodies)


def test_markdown_embedded_html_is_sanitized_but_fenced_examples_are_not_executed():
    data = b'# Text\n\n<div onclick="evil()">safe text<script>evil()</script></div>\n\n```html\n<script>literal example</script>\n```\n'
    result = parse(data)
    assert "safe text" in public_text(result) and 'onclick="evil()"' not in public_text(result)
    assert "```html\n<script>literal example</script>\n```" in public_text(result)
    assert "MARKDOWN_HTML_NORMALIZED" in {item.code for item in result.warnings}


@pytest.mark.parametrize(
    "definition",
    [
        '[s]: https://example.test/paper "Source title"',
        '> [s]: https://example.test/paper "Source title"',
        '- a\n  - b\n    - [s]: https://example.test/paper "Source title"',
    ],
)
def test_reference_style_links_resolve_in_each_independent_body(definition):
    data = f"# Synthetic\n\nRead [paper][s].\n\n> - Read [nested paper][s].\n\n{definition}\n".encode()
    result = parse(data)
    renderer = MarkdownIt("commonmark")
    linked_bodies = [body.decode() for body in result.bodies.values() if "Read " in body.decode()]
    assert len(linked_bodies) == 2
    for body in linked_bodies:
        rendered = renderer.render(body)
        assert 'href="https://example.test/paper" title="Source title"' in rendered
    assert sum(citation.url == "https://example.test/paper" for citation in result.citations) == 2
    assert all(citation.source_sha256 == hashlib.sha256(data).hexdigest() for citation in result.citations)
    assert "MARKDOWN_REFERENCE_CONTEXT" in {item.code for item in result.warnings}
    validate_objects(result.objects, result.bodies)


def test_nested_markdown_html_and_images_get_same_security_diagnostics():
    result = parse(
        b'> - Read <span onclick="evil()">safe text</span> and <script>evil()</script>.\n\n- ![image](https://example.test/pixel.png)\n'
    )
    assert 'onclick="evil()"' not in public_text(result) and "<script>" not in public_text(result)
    assert {"MARKDOWN_HTML_NORMALIZED", "MARKDOWN_IMAGE_NOT_FETCHED"} <= {item.code for item in result.warnings}


@pytest.mark.parametrize("profile,solutions", [("author", 3), ("learner", 0)])
def test_both_specification_packages_return_complete_objects_and_separate_private_solutions(profile, solutions):
    data = (ROOT / f"fixtures/synthetic/course-{profile}.learnpack.zip").read_bytes()
    result = parse(data, "learnpack", f"course-{profile}.learnpack.zip")
    assert len(result.objects) == 9 and len(result.bodies) == 1
    assert len(result.solutions) == solutions and len(result.symbols) == 1
    assert result.quality_receipt == package_payloads(profile)["checks/quality-receipt.json"]
    assert result.package_profile == profile
    assert not any(isinstance(value, dm.SolutionPrivate) for value in result.objects)
    validate_objects(result.objects, result.bodies)


def test_package_preserves_passive_assets_and_downgrades_untrusted_quality_claims():
    payloads = package_payloads()
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
    )
    payloads["assets/pixel.png"] = png
    payloads["sources/citations.json"] = json.dumps(
        [
            {
                "id": "citation_import",
                "title": "untrusted claim",
                "url": "javascript:evil()",
                "locator": "original",
                "verification": "verified",
            }
        ]
    ).encode()
    original = json.loads(payloads["private/solutions.jsonl"].splitlines()[0])
    original["review_status"] = "approved"
    payloads["private/solutions.jsonl"] = (
        json.dumps(original).encode() + b"\n" + b"\n".join(payloads["private/solutions.jsonl"].splitlines()[1:]) + b"\n"
    )
    result = parse(
        repack(payloads, additions=[{"path": "assets/pixel.png", "media_type": "image/png", "visibility": "learner"}]),
        "learnpack",
    )
    assert result.assets[0].data == png and result.assets[0].path == "assets/pixel.png"
    assert result.citations[0].verification == "user_supplied" and result.citations[0].url is None
    assert result.solutions[0].review_status == "needs_review"
    assert "IMPORTED_QUALITY_UNVERIFIED" in {item.code for item in result.warnings}


@pytest.mark.parametrize(
    "mutation",
    [
        "raw_hash",
        "reference_hash",
        "symbol_scope",
        "duplicate_symbol",
        "duplicate_solution",
        "bad_answer",
        "learner_private",
        "unknown_payload",
        "active_asset",
    ],
)
def test_invalid_packages_never_return_partial_candidates(mutation):
    payloads = package_payloads()
    additions = []
    if mutation == "raw_hash":
        data = repack(payloads)
        stream = BytesIO()
        with ZipFile(BytesIO(data)) as source, ZipFile(stream, "w") as target:
            for name in source.namelist():
                target.writestr(name, b"corruption" if name.endswith(".md") else source.read(name))
        data = stream.getvalue()
    else:
        if mutation == "reference_hash":
            value = json.loads(payloads["course.json"])
            value["lesson_refs"][0]["sha256"] = "a" * 64
            payloads["course.json"] = json.dumps(value).encode()
        elif mutation in {"symbol_scope", "duplicate_symbol"}:
            values = json.loads(payloads["symbols.json"])
            if mutation == "symbol_scope":
                values[0]["scope"] = "missing_object"
            else:
                values.append(values[0])
            payloads["symbols.json"] = json.dumps(values).encode()
        elif mutation == "duplicate_solution":
            payloads["private/solutions.jsonl"] += payloads["private/solutions.jsonl"].splitlines()[0] + b"\n"
        elif mutation == "bad_answer":
            values = [json.loads(line) for line in payloads["private/solutions.jsonl"].splitlines()]
            values[0]["accepted_answers"] = ["absent_choice"]
            payloads["private/solutions.jsonl"] = b"".join(json.dumps(value).encode() + b"\n" for value in values)
        elif mutation == "learner_private":
            value = json.loads(payloads["manifest.json"])
            value["profile"] = "learner"
            payloads["manifest.json"] = json.dumps(value).encode()
        else:
            path = "assets/active.svg" if mutation == "active_asset" else "unrecognized.bin"
            payloads[path] = b'<svg onload="evil()"></svg>'
            additions.append({"path": path, "media_type": "image/svg+xml", "visibility": "learner"})
        data = repack(payloads, additions=additions)
    with pytest.raises(ImportParsingError):
        parse(data, "learnpack")


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a\\b", "a/../b"])
def test_zip_paths_are_rejected_before_any_extraction(name):
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr(name, b"data")
    with pytest.raises(ImportParsingError):
        parse(stream.getvalue(), "learnpack")


@pytest.mark.parametrize("mutation", ["prefix", "concat", "tail", "comment"])
def test_hidden_archive_bytes_cannot_be_treated_as_a_complete_learner_package(mutation):
    learner = (ROOT / "fixtures/synthetic/course-learner.learnpack.zip").read_bytes()
    if mutation == "prefix":
        data = b"unclaimed original bytes" + learner
    elif mutation == "concat":
        data = (ROOT / "fixtures/synthetic/course-author.learnpack.zip").read_bytes() + learner
    elif mutation == "tail":
        data = learner + b"unclaimed original bytes"
    else:
        stream = BytesIO(learner)
        with ZipFile(stream, "a") as archive:
            archive.comment = b"unclaimed original bytes"
        data = stream.getvalue()
    with pytest.raises(ImportParsingError) as error:
        parse(data, "learnpack")
    assert error.value.code == "PACKAGE_ENVELOPE_UNCLAIMED"


def test_valid_deflate_stream_cannot_hide_an_extra_author_archive():
    """Before the fix this parsed as learner/zero solutions and exposed the raw author ZIP."""
    learner = (ROOT / "fixtures/synthetic/course-learner.learnpack.zip").read_bytes()
    author = (ROOT / "fixtures/synthetic/course-author.learnpack.zip").read_bytes()
    with ZipFile(BytesIO(learner)) as archive:
        entry = next(entry for entry in archive.infolist() if entry.compress_type == ZIP_DEFLATED)
        name_size, extra_size = struct.unpack_from("<HH", learner, entry.header_offset + 26)
        insertion = entry.header_offset + 30 + name_size + extra_size + entry.compress_size
        data = bytearray(learner[:insertion] + author + learner[insertion:])
        struct.pack_into("<L", data, entry.header_offset + 18, entry.compress_size + len(author))
        position = archive.start_dir + len(author)
        for _ in archive.infolist():
            name_size, extra_size, comment_size = struct.unpack_from("<HHH", data, position + 28)
            offset = struct.unpack_from("<L", data, position + 42)[0]
            if offset == entry.header_offset:
                struct.pack_into("<L", data, position + 20, entry.compress_size + len(author))
            elif offset >= insertion:
                struct.pack_into("<L", data, position + 42, offset + len(author))
            position += 46 + name_size + extra_size + comment_size
        struct.pack_into("<L", data, position + 16, archive.start_dir + len(author))
    raw = bytes(data)
    assert has_complete_archive_envelope(raw)  # Layout accounting alone is insufficient.
    with ZipFile(BytesIO(raw)) as standard_reader:
        assert standard_reader.read(entry.filename) == package_payloads("learner")[entry.filename]
    with ZipFile(BytesIO(raw[insertion : insertion + len(author)])) as hidden:
        assert b"accepted_answers" in hidden.read("private/solutions.jsonl")
    with pytest.raises(ImportParsingError) as error:
        parse(raw, "learnpack")
    assert error.value.code == "PACKAGE_COMPRESSED_TRAILING_DATA"


def test_zip_duplicate_symlink_and_compression_bomb_are_rejected():
    for scenario in ["duplicate", "symlink", "ratio"]:
        stream = BytesIO()
        with ZipFile(stream, "w", compression=ZIP_DEFLATED if scenario == "ratio" else ZIP_STORED) as archive:
            archive.writestr("one", b"x" * 5000 if scenario == "ratio" else b"data")
            if scenario == "duplicate":
                with pytest.warns(UserWarning):
                    archive.writestr("one", b"duplicate")
            if scenario == "symlink":
                entry = ZipInfo("link")
                entry.create_system = 3
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(entry, "../escape")
        with pytest.raises(ImportParsingError):
            parse(stream.getvalue(), "learnpack")


@pytest.mark.parametrize(
    "data,kind,code",
    [
        (b"\xffbad", "text", "ENCODING_CHOICE_REQUIRED"),
        (b"a\x00b", "text", "TEXT_BINARY_CONTENT"),
        (b"", "text", "EMPTY_CONTENT"),
        (b"%PDF-1.7", "pdf", "PDF_MALFORMED"),
        (b"PK", "docx", "DOCX_CONTAINER_UNSUPPORTED"),
    ],
)
def test_invalid_encoding_empty_and_malformed_extraction_are_visible_failures(data, kind, code):
    with pytest.raises(ImportParsingError) as error:
        parse(data, kind)
    assert error.value.code == code


def test_source_block_budgets_can_be_explicitly_lowered_and_raised():
    with pytest.raises(ImportParsingError, match="10"):
        parse(b"x" * 11, budgets=ImportBudgets(max_source_bytes=10))
    assert public_text(parse(b"x" * 11, budgets=ImportBudgets(max_source_bytes=11))) == "x" * 11
    with pytest.raises(ImportParsingError, match="400000"):
        parse(b"x" * 400001)
    result = parse(b"x" * 400001, budgets=ImportBudgets(max_block_characters=400001))
    assert public_text(result) == "x" * 400001
    assert next(value for value in result.objects if isinstance(value, dm.ContentBlock)).title == "original"
    with pytest.raises(ImportParsingError, match="10"):
        parse(b"x" * 11, budgets=ImportBudgets(max_block_characters=10))


@pytest.mark.parametrize(
    "field", ["max_source_bytes", "max_package_bytes", "max_package_files", "max_compression_ratio"]
)
def test_all_archive_budgets_are_enforced_using_explicit_configuration(field):
    payloads = package_payloads("learner")
    data = repack(payloads, compression=ZIP_DEFLATED)
    with ZipFile(BytesIO(data)) as archive:
        required = {
            "max_source_bytes": len(data),
            "max_package_bytes": sum(entry.file_size for entry in archive.infolist()),
            "max_package_files": len(archive.infolist()),
            "max_compression_ratio": max(
                (entry.file_size + entry.compress_size - 1) // max(1, entry.compress_size)
                for entry in archive.infolist()
            ),
        }[field]
    with pytest.raises(ImportParsingError) as error:
        parse(data, "learnpack", budgets=replace(ImportBudgets(), **{field: required - 1}))
    assert error.value.code in {"SOURCE_BUDGET_EXCEEDED", "PACKAGE_BUDGET_EXCEEDED"}
    result = parse(data, "learnpack", budgets=replace(ImportBudgets(), **{field: required}))
    assert len(result.objects) == 9 and len(result.bodies) == 1


def test_archive_block_budget_is_passed_through_shared_semantic_validation():
    data = (ROOT / "fixtures/synthetic/course-learner.learnpack.zip").read_bytes()
    body = next(value for path, value in package_payloads("learner").items() if path.endswith(".md"))
    required = len(body.decode("utf-8"))
    with pytest.raises(ImportParsingError):
        parse(data, "learnpack", budgets=ImportBudgets(max_block_characters=required - 1))
    assert parse(data, "learnpack", budgets=ImportBudgets(max_block_characters=required)).bodies


def test_archive_files_and_compression_can_exceed_default_budgets_after_configuration():
    payloads = package_payloads("learner")
    additions = []
    for index in range(2002 - len(payloads)):
        name = f"assets/passive_{index}.txt"
        payloads[name] = b"passive source attachment"
        additions.append({"path": name, "media_type": "text/plain", "visibility": "learner"})
    data = repack(payloads, additions=additions)
    with pytest.raises(ImportParsingError):
        parse(data, "learnpack")
    result = parse(data, "learnpack", budgets=ImportBudgets(max_package_files=2002))
    assert len(result.assets) == len(additions)
    payloads = package_payloads("learner")
    payloads["assets/compressible.txt"] = b"x" * 100000
    data = repack(
        payloads,
        compression=ZIP_DEFLATED,
        additions=[
            {
                "path": "assets/compressible.txt",
                "media_type": "text/plain",
                "visibility": "learner",
            }
        ],
    )
    with pytest.raises(ImportParsingError, match="压缩比"):
        parse(data, "learnpack")
    assert parse(data, "learnpack", budgets=ImportBudgets(max_compression_ratio=1000)).assets[0].data == b"x" * 100000


def test_html_complexity_still_fails_closed_independently_of_configured_file_budget():
    with pytest.raises(ImportParsingError, match="HTML"):
        parse(b"<div>" * 130 + b"text", "html")


def test_unvalidated_archives_are_private_even_when_claimed_to_be_text():
    assert detect_import_visibility(b"PK\x03\x04", "text", "fake.txt") == "author_private"
    assert detect_import_visibility(b"bad zip", "learnpack", "fake.txt") == "author_private"
    assert detect_import_visibility(b"ordinary text", "auto", "book.txt") == "learner"
