"""Real isolated extraction of original synthetic PDFs and OOXML containers."""

from dataclasses import replace
import html
import struct
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from markdown_it import MarkdownIt
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets
from packages.contracts.canonical import sha256_bytes
from packages.contracts.validation import validate_objects
from services.api.app.application.import_extract_docx import extract_docx
from services.api.app.application.import_extract_pdf import extract_pdf
from services.api.app.application.import_extract_types import ExtractionFailure
from services.api.app.application.import_parsing import ImportParsingError, parse_import
from tests.document_fixtures import (
    DOCX_DOCUMENT, _pdf, docx_dtd_fixture, docx_fixture, docx_from_payloads,
    docx_malformed_fixture, docx_payloads, formula_pixels, formula_png,
    pdf_encrypted_fixture, pdf_malformed_fixture, pdf_mixed_fixture, pdf_scan_fixture, pdf_text_fixture,
)


SOURCE = "source_document_test"


def parse(data: bytes, kind: str, *, budgets: ImportBudgets = ImportBudgets()):
    return parse_import(data, kind=kind, filename="synthetic." + kind, source_id=SOURCE, budgets=budgets)


def codes(result):
    return {warning.code for warning in result.warnings}


def test_pdf_two_pages_are_exact_source_citations_and_distinct_derived_bodies():
    original = pdf_text_fixture()
    result = parse(original, "pdf")
    validate_objects(result.objects, result.bodies)
    assert len(result.bodies) == 2
    assert [citation.locator for citation in result.citations] == [f"source:{SOURCE};pdf:page:1", f"source:{SOURCE};pdf:page:2"]
    assert all(citation.source_sha256 == sha256_bytes(original) and citation.verification == "user_supplied" for citation in result.citations)
    for block in result.objects:
        if isinstance(block, dm.ContentBlock):
            assert block.body_sha256 == sha256_bytes(result.bodies[block.body_path]) != sha256_bytes(original)
    text = b"\n".join(result.bodies.values()).decode()
    for marker in ("PDF page one alpha", "PDF page two beta", "Left column line one", "Right column line two", "Cell A", "Cell B"):
        assert marker in text
    assert {"PDF_TEXT_LAYOUT_UNVERIFIED", "PDF_IMAGE_NOT_TEX", "PDF_VECTOR_LAYOUT_UNVERIFIED"} <= codes(result)
    assert next(w.locator for w in result.warnings if w.code == "PDF_IMAGE_NOT_TEX").endswith("pdf:page:2")
    assert "x²" not in text and "x^2" not in text and "\\frac" not in text


def test_image_formula_fixture_contains_real_original_pixels_not_a_text_formula():
    width, height, rgb = formula_pixels()
    assert (width, height) == (72, 48)
    assert len(rgb) == width * height * 3 and rgb.count(b"\x00\x00\x00") > 100
    assert formula_png().startswith(b"\x89PNG\r\n\x1a\n")
    assert rgb in pdf_text_fixture() and formula_png() in docx_fixture()


def test_mixed_pdf_preserves_readable_page_and_marks_exact_unreadable_page():
    result = parse(pdf_mixed_fixture(), "pdf")
    assert len(result.bodies) == 1
    warning = next(w for w in result.warnings if w.code == "PDF_PAGE_NO_TEXT")
    assert warning.locator == f"source:{SOURCE};pdf:page:2"
    assert all("pdf:page:2" not in c.locator for c in result.citations)


@pytest.mark.parametrize("factory,kind,code", [
    (pdf_scan_fixture, "pdf", "PDF_NO_EXTRACTABLE_TEXT"),
    (pdf_encrypted_fixture, "pdf", "PDF_ENCRYPTED_UNSUPPORTED"),
    (pdf_malformed_fixture, "pdf", "PDF_MALFORMED"),
    (docx_malformed_fixture, "docx", "DOCX_XML_INVALID"),
    (docx_dtd_fixture, "docx", "DOCX_XML_UNSAFE"),
])
def test_failed_documents_return_safe_diagnostics_without_candidate_or_raw_exception(factory, kind, code):
    with pytest.raises(ImportParsingError) as error:
        parse(factory(), kind)
    assert error.value.code == code
    assert error.value.warnings
    assert all(w.locator.startswith(f"source:{SOURCE}") for w in error.value.warnings)
    assert "synthetic-private" not in str(error.value) + str(error.value.warnings)
    if code == "PDF_NO_EXTRACTABLE_TEXT":
        assert {"PDF_PAGE_NO_TEXT", "PDF_IMAGE_NOT_TEX"} <= codes(error.value)


def test_docx_headings_paragraph_cells_and_omitted_fidelity_have_real_node_locators():
    original = docx_fixture()
    result = parse(original, "docx")
    text = b"\n".join(result.bodies.values()).decode()
    assert result.original_visibility == "author_private"
    course = next(value for value in result.objects if isinstance(value, dm.Course))
    assert course.title == "Synthetic DOCX"
    assert "DOCX paragraph alpha" in text and "Cell A" in text and "Cell B" in text
    assert "External reference" in text and "https://" not in text
    assert "x²" not in text and "x/2" not in text and "\\frac" not in text
    assert {"DOCX_ORIGINAL_RESTRICTED", "DOCX_OMML_NOT_TEX", "DOCX_FLOATING_IMAGE", "DOCX_EXTERNAL_RESOURCE_NOT_FETCHED", "DOCX_TABLE_LAYOUT_UNVERIFIED", "DOCX_PART_OMITTED"} <= codes(result)
    assert all(c.source_sha256 == sha256_bytes(original) for c in result.citations)
    locators = {c.locator for c in result.citations}
    prefix = f"source:{SOURCE};docx:part:word/document.xml;node:/w:document/w:body"
    assert prefix + "/w:p[2]" in locators
    assert prefix + "/w:tbl[1]/w:tr[1]/w:tc[1]" in locators
    assert next(w.locator for w in result.warnings if w.code == "DOCX_OMML_NOT_TEX") == prefix + "/w:p[3]"
    assert next(w.locator for w in result.warnings if w.code == "DOCX_FLOATING_IMAGE") == prefix + "/w:p[4]"


@pytest.mark.parametrize("kind", ["pdf", "docx"])
def test_plain_characters_stay_literal_through_markdown_rendering(kind):
    literal = r"<b> &lt; $x$ \alpha [label](javascript:bad)"
    if kind == "pdf":
        escaped = literal.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        data = _pdf([f"BT /F1 12 Tf 50 700 Td ({escaped}) Tj ET".encode()], image=False)
    else:
        payloads = docx_payloads()
        payloads["word/document.xml"] = DOCX_DOCUMENT.replace("DOCX paragraph alpha", html.escape(literal)).encode()
        data = docx_from_payloads(payloads)
    result = parse(data, kind)
    markdown = next(body.decode() for body in result.bodies.values() if "alpha" in body.decode())
    parser = MarkdownIt("commonmark", {"html": True})
    tokens = parser.parse(markdown)
    children = [child for token in tokens for child in token.children or []]
    assert not any(child.type in {"html_inline", "link_open", "image"} for child in children)
    assert literal in "".join(child.content for child in children)
    rendered = parser.render(markdown)
    assert "<b>" not in rendered and "&lt;b&gt;" in rendered and "&amp;lt;" in rendered


@pytest.mark.parametrize("data,kind", [(pdf_text_fixture(), "pdf"), (docx_fixture(), "docx")])
def test_explicit_source_and_text_budgets_can_be_lowered_then_raised(data, kind):
    budget = replace(ImportBudgets(), max_source_bytes=len(data) - 1)
    with pytest.raises(ImportParsingError) as error:
        parse(data, kind, budgets=budget)
    assert error.value.code == "SOURCE_BUDGET_EXCEEDED"
    with pytest.raises(ImportParsingError) as error:
        parse(data, kind, budgets=replace(budget, max_source_bytes=len(data), max_block_characters=5))
    assert error.value.code == "EXTRACTION_BUDGET_EXCEEDED"
    assert parse(data, kind, budgets=replace(budget, max_source_bytes=len(data), max_block_characters=1000)).bodies


def test_docx_file_expansion_and_compression_budgets_are_real_and_configurable():
    payloads = docx_payloads()
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        for name, value in payloads.items():
            archive.writestr(name, value)
    data = stream.getvalue()
    for change in ({"max_package_files": 2}, {"max_package_bytes": 100}, {"max_compression_ratio": 1}):
        with pytest.raises(ImportParsingError) as error:
            parse(data, "docx", budgets=replace(ImportBudgets(), **change))
        assert error.value.code == "EXTRACTION_BUDGET_EXCEEDED"
    assert parse(data, "docx", budgets=replace(ImportBudgets(), max_compression_ratio=1000)).bodies


@pytest.mark.parametrize("name", ["../secret", "/absolute", "word/../secret", "word\\secret"])
def test_docx_rejects_unsafe_archive_members(name):
    payloads = docx_payloads()
    payloads[name] = b"synthetic private bytes"
    with pytest.raises(ImportParsingError):
        parse(docx_from_payloads(payloads), "docx")


@pytest.mark.parametrize("alteration", ["prefix", "tail", "concat", "duplicate"])
def test_docx_rejects_ambiguous_archive_envelopes(alteration):
    data = docx_fixture()
    if alteration == "prefix":
        data = b"hidden bytes" + data
    elif alteration == "tail":
        data += b"hidden bytes"
    elif alteration == "concat":
        data += docx_fixture()
    else:
        stream = BytesIO(data)
        with ZipFile(stream, "a") as archive:
            with pytest.warns(UserWarning, match="Duplicate"):
                archive.writestr("word/document.xml", DOCX_DOCUMENT)
        data = stream.getvalue()
    with pytest.raises(ImportParsingError):
        parse(data, "docx")


def test_docx_unsafe_xml_in_an_omitted_part_still_fails_closed():
    payloads = docx_payloads()
    payloads["customXml/hidden.xml"] = b'<!DOCTYPE doc [<!ENTITY e SYSTEM "file:///synthetic-private">]><doc>&e;</doc>'
    with pytest.raises(ImportParsingError) as error:
        parse(docx_from_payloads(payloads), "docx")
    assert error.value.code == "DOCX_XML_UNSAFE"


def test_docx_hidden_deleted_and_field_instruction_text_does_not_become_public_body():
    payloads = docx_payloads()
    marker = '<w:p><w:r><w:rPr><w:vanish/></w:rPr><w:t>HIDDEN_SECRET</w:t></w:r><w:del><w:r><w:delText>DELETED_SECRET</w:delText></w:r></w:del><w:r><w:instrText>INCLUDETEXT SECRET_FILE</w:instrText></w:r></w:p>'
    payloads["word/document.xml"] = DOCX_DOCUMENT.replace("<w:sectPr/>", marker + "<w:sectPr/>").encode()
    result = parse(docx_from_payloads(payloads), "docx")
    assert b"SECRET" not in b"".join(result.bodies.values())
    assert {"DOCX_HIDDEN_CONTENT_OMITTED", "DOCX_ACTIVE_CONTENT_OMITTED"} <= codes(result)


@pytest.mark.parametrize("extractor", [extract_pdf, extract_docx])
def test_extractor_cannot_be_accidentally_called_in_the_host_process(extractor):
    with pytest.raises(ExtractionFailure) as error:
        extractor(b"untrusted", budgets={})
    assert error.value.code == "EXTRACTION_ENVIRONMENT_UNAVAILABLE"


@pytest.mark.parametrize("style", [
    '<w:style w:type="character" w:styleId="Secret"><w:rPr><w:vanish/></w:rPr></w:style>',
    '<w:style w:type="paragraph" w:styleId="Base"><w:rPr><w:vanish/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Derived"><w:basedOn w:val="Base"/></w:style>',
    '<w:docDefaults><w:rPrDefault><w:rPr><w:vanish/></w:rPr></w:rPrDefault></w:docDefaults>',
])
def test_hidden_style_cascade_cannot_expose_text_to_public_preview(style):
    payloads = docx_payloads()
    payloads["word/styles.xml"] = f'<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{style}</w:styles>'.encode()
    payloads["word/document.xml"] = DOCX_DOCUMENT.replace("DOCX paragraph alpha", "STYLE_HIDDEN_SECRET").encode()
    with pytest.raises(ImportParsingError) as error:
        parse(docx_from_payloads(payloads), "docx")
    assert error.value.code == "DOCX_HIDDEN_STYLE_UNSUPPORTED"
    assert "STYLE_HIDDEN_SECRET" not in str(error.value.warnings)


@pytest.mark.parametrize("content", [
    b'<bogus/>',
    b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
    b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/xml"/></Types>',
    b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.ms-word.document.macroEnabled.main+xml"/></Types>',
])
def test_required_content_type_is_real_docx_and_never_a_macro_document(content):
    payloads = docx_payloads()
    payloads["[Content_Types].xml"] = content
    with pytest.raises(ImportParsingError) as error:
        parse(docx_from_payloads(payloads), "docx")
    assert error.value.code in {"DOCX_CONTENT_TYPE_INVALID", "DOCX_MACRO_UNSUPPORTED"}


def test_omitted_private_member_names_are_not_public_diagnostic_text():
    payloads = docx_payloads()
    payloads["private/SECRET_ANSWER_42.xml"] = b"<private>SECRET_ANSWER_42</private>"
    result = parse(docx_from_payloads(payloads), "docx")
    assert "SECRET_ANSWER_42" not in str(result.warnings) + str(result.citations) + str(result.bodies)
    assert any(w.code == "DOCX_PART_OMITTED" and "omitted-member:" in w.locator for w in result.warnings)


def test_shared_non_encrypted_document_fixtures_are_byte_deterministic():
    assert docx_fixture() == docx_fixture()
    assert pdf_text_fixture() == pdf_text_fixture()



def test_docx_deflate_member_cannot_hide_unconsumed_private_payload():
    payloads = docx_payloads()
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        for name, value in payloads.items():
            archive.writestr(name, value)
    clean = stream.getvalue()
    hidden = b"HIDDEN_PRIVATE_PAYLOAD"
    with ZipFile(BytesIO(clean)) as archive:
        entry = archive.infolist()[0]
        name_size, extra_size = struct.unpack_from("<HH", clean, entry.header_offset + 26)
        insertion = entry.header_offset + 30 + name_size + extra_size + entry.compress_size
        dirty = bytearray(clean[:insertion] + hidden + clean[insertion:])
        struct.pack_into("<L", dirty, entry.header_offset + 18, entry.compress_size + len(hidden))
        position = archive.start_dir + len(hidden)
        for _ in archive.infolist():
            name_size, extra_size, comment_size = struct.unpack_from("<HHH", dirty, position + 28)
            offset = struct.unpack_from("<L", dirty, position + 42)[0]
            if offset == entry.header_offset:
                struct.pack_into("<L", dirty, position + 20, entry.compress_size + len(hidden))
            elif offset >= insertion:
                struct.pack_into("<L", dirty, position + 42, offset + len(hidden))
            position += 46 + name_size + extra_size + comment_size
        struct.pack_into("<L", dirty, position + 16, archive.start_dir + len(hidden))
    with ZipFile(BytesIO(dirty)) as standard_reader:
        assert standard_reader.read(entry.filename) == payloads[entry.filename]
    with pytest.raises(ImportParsingError) as error:
        parse(bytes(dirty), "docx")
    assert error.value.code == "DOCX_COMPRESSED_TRAILING_DATA"


@pytest.mark.parametrize("target", ["../../outside", "file:///synthetic-private", "media/missing.png"])
def test_internal_docx_relationship_cannot_escape_or_silently_point_to_absent_part(target):
    payloads = docx_payloads()
    payloads["word/_rels/document.xml.rels"] = payloads["word/_rels/document.xml.rels"].replace(b"media/synthetic.png", target.encode())
    with pytest.raises(ImportParsingError) as error:
        parse(docx_from_payloads(payloads), "docx")
    assert error.value.code == "DOCX_RELATIONSHIP_INVALID"


def test_docx_explicit_false_hidden_property_keeps_visible_text():
    payloads = docx_payloads()
    payloads["word/document.xml"] = DOCX_DOCUMENT.replace('<w:r><w:t>DOCX paragraph alpha', '<w:r><w:rPr><w:vanish w:val="0"/></w:rPr><w:t>DOCX paragraph alpha').encode()
    result = parse(docx_from_payloads(payloads), "docx")
    assert b"DOCX paragraph alpha" in b"".join(result.bodies.values())



def test_hidden_styles_at_relationship_selected_nonstandard_part_are_still_rejected():
    payloads = docx_payloads()
    payloads["word/styles2.xml"] = b'<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="character" w:styleId="Secret"><w:rPr><w:vanish/></w:rPr></w:style></w:styles>'
    relation = '<Relationship Id="rStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles2.xml"/>'
    payloads["word/_rels/document.xml.rels"] = payloads["word/_rels/document.xml.rels"].replace(b"</Relationships>", relation.encode() + b"</Relationships>")
    payloads["word/document.xml"] = DOCX_DOCUMENT.replace('<w:r><w:t>DOCX paragraph alpha', '<w:r><w:rPr><w:rStyle w:val="Secret"/></w:rPr><w:t>STYLE_SECRET').encode()
    with pytest.raises(ImportParsingError) as error:
        parse(docx_from_payloads(payloads), "docx")
    assert error.value.code == "DOCX_HIDDEN_STYLE_UNSUPPORTED"
    assert "STYLE_SECRET" not in str(error.value.warnings)


@pytest.mark.parametrize("declaration", ["relationship", "override", "default", "all"])
def test_non_xml_extension_hidden_style_part_cannot_bypass_preview_rejection(declaration):
    """Regression: before part discovery used declarations, .bin styles leaked this text."""
    payloads = docx_payloads()
    payloads["word/styles-hidden.bin"] = b'<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="character" w:styleId="Secret"><w:rPr><w:vanish/></w:rPr></w:style></w:styles>'
    if declaration in {"relationship", "all"}:
        relation = '<Relationship Id="rStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles-hidden.bin"/>'
        payloads["word/_rels/document.xml.rels"] = payloads["word/_rels/document.xml.rels"].replace(b"</Relationships>", relation.encode() + b"</Relationships>")
    if declaration in {"override", "default", "all"}:
        identity = 'Extension="bin"' if declaration == "default" else 'PartName="/word/styles-hidden.bin"'
        element = "Default" if declaration == "default" else "Override"
        content_type = f'<{element} {identity} ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        payloads["[Content_Types].xml"] = payloads["[Content_Types].xml"].replace(b"</Types>", content_type.encode() + b"</Types>")
    payloads["word/document.xml"] = DOCX_DOCUMENT.replace('<w:r><w:t>DOCX paragraph alpha', '<w:r><w:rPr><w:rStyle w:val="Secret"/></w:rPr><w:t>HiddenStyleSecret42').encode()
    with pytest.raises(ImportParsingError) as error:
        parse(docx_from_payloads(payloads), "docx")
    assert error.value.code == "DOCX_HIDDEN_STYLE_UNSUPPORTED"
    assert "HiddenStyleSecret42" not in str(error.value.warnings)


@pytest.mark.parametrize("role", ["styles", "settings", "numbering", "theme"])
def test_non_xml_extension_key_relationship_target_is_still_parsed_safely(role):
    payloads = docx_payloads()
    payloads["word/synthetic.bin"] = b'<!DOCTYPE doc [<!ENTITY e SYSTEM "file:///synthetic-private">]><doc>&e;</doc>'
    relation = f'<Relationship Id="rSynthetic" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{role}" Target="synthetic.bin"/>'
    payloads["word/_rels/document.xml.rels"] = payloads["word/_rels/document.xml.rels"].replace(b"</Relationships>", relation.encode() + b"</Relationships>")
    with pytest.raises(ImportParsingError) as error:
        parse(docx_from_payloads(payloads), "docx")
    assert error.value.code == "DOCX_XML_UNSAFE"
