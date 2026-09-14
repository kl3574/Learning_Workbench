"""Text-only PDF extraction, called exclusively inside the document sandbox."""

from io import BytesIO
import logging

from pypdf import PdfReader, apply_configuration
from pypdf.errors import PdfReadError, PdfStreamError
from pypdf.generic import DictionaryObject

from .import_extract_types import (
    Diagnostics, ExtractedChunk, ExtractedDocument, ExtractionFailure,
    check_chunks, checked_budgets, passive_text, require_sandbox,
)


class _SafeLog(logging.Handler):
    def __init__(self, diagnostics: Diagnostics):
        super().__init__(logging.WARNING)
        self.diagnostics = diagnostics
        self.locator: str | None = None

    def emit(self, record: logging.LogRecord) -> None:
        self.diagnostics.add("PDF_STRUCTURE_WARNING", "PDF 库报告结构或编码异常；候选文字需核对原件。", self.locator)


def extract_pdf(data: bytes, *, budgets: dict[str, int]) -> ExtractedDocument:
    require_sandbox()
    checked_budgets(budgets)
    diagnostics = Diagnostics()
    if len(data) > budgets["max_source_bytes"]:
        diagnostics.fail("SOURCE_BUDGET_EXCEEDED", "PDF 原件超过配置字节预算。")
    logger = logging.getLogger("pypdf")
    handler = _SafeLog(diagnostics)
    logger.addHandler(handler)
    logger.propagate = False
    expanded = budgets["max_package_bytes"]
    try:
        with apply_configuration(
            maximum_declared_stream_length=expanded, array_based_stream_maximum_output_length=expanded,
            lzw_maximum_output_length=expanded, run_length_maximum_output_length=expanded,
            zlib_maximum_output_length=expanded, zlib_maximum_recovery_input_length=budgets["max_source_bytes"],
            flate_maximum_columns=expanded, flate_maximum_row_length=expanded,
            page_tree_maximum_entries=budgets["max_package_files"],
            jbig2dec_binary=None,
        ):
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted:
                diagnostics.fail("PDF_ENCRYPTED_UNSUPPORTED", "加密 PDF 未提取；当前导入不接收密码，原件已保留。")
            if len(reader.pages) > budgets["max_package_files"]:
                diagnostics.fail("EXTRACTION_BUDGET_EXCEEDED", "PDF 页数超过配置数量预算。")
            root = reader.root_object
            restricted = any(key in root for key in ("/Names", "/AF", "/OpenAction", "/AA", "/AcroForm"))
            if restricted:
                diagnostics.add("PDF_CONTAINER_CONTENT_OMITTED", "PDF 含附件、表单或主动内容容器；仅提取页面文字，原件受作者权限保护。", "pdf:catalog")
            chunks: list[ExtractedChunk] = []
            decoded_bytes = 0
            for number, page in enumerate(reader.pages, 1):
                locator = f"pdf:page:{number}"
                handler.locator = locator
                diagnostics.add("PDF_TEXT_LAYOUT_UNVERIFIED", "仅按 PDF 文字流提取；公式、双栏阅读顺序及表格结构未经核实，请对照原件。", locator)
                if "/Annots" in page or "/AA" in page:
                    restricted = True
                    diagnostics.add("PDF_ANNOTATIONS_OMITTED", "页面批注、表单及动作未作为正文提取；原件受作者权限保护。", locator)
                content = page.get_contents()
                if content is not None:
                    decoded_bytes += len(content.get_data())
                    if decoded_bytes > expanded:
                        diagnostics.fail("EXTRACTION_BUDGET_EXCEEDED", "PDF 解码文字流累计超过配置展开预算。", locator)
                    for operands, operator in content.operations:
                        if operator == b"INLINE IMAGE":
                            diagnostics.add("PDF_IMAGE_NOT_TEX", "页面含位图；图片公式未 OCR，也未猜测恢复 TeX。", locator)
                        elif operator == b"Do":
                            resources = page.get("/Resources", DictionaryObject()).get_object()
                            xobjects = resources.get("/XObject", DictionaryObject()).get_object()
                            target = xobjects.get(operands[0]) if isinstance(operands, list) and operands else None
                            subtype = target.get_object().get("/Subtype") if target else None
                            code = "PDF_IMAGE_NOT_TEX" if subtype == "/Image" else "PDF_FORM_LAYOUT_UNVERIFIED"
                            diagnostics.add(code, "页面含图片或嵌套图形；其公式与版式未转换为准确 TeX。", locator)
                        elif operator in {b"re", b"m", b"l", b"c", b"v", b"y"}:
                            diagnostics.add("PDF_VECTOR_LAYOUT_UNVERIFIED", "页面含矢量线条或图形；表格、图形和公式的结构未恢复。", locator)
                # Plain extraction preserves rotated text; layout mode can silently omit it.
                text = page.extract_text(extraction_mode="plain")
                if "\x00" in text:
                    diagnostics.fail("PDF_TEXT_ENCODING_INVALID", "PDF 文字含无法安全表示的 NUL 字符，未部分导入。", locator)
                if "\r" in text:
                    text = text.replace("\r\n", "\n").replace("\r", "\n")
                    diagnostics.add("LINE_ENDINGS_NORMALIZED", "候选正文换行转换为 LF；原件字节和哈希不变。", locator)
                if text.strip():
                    chunks.append(ExtractedChunk("page", passive_text(text).rstrip("\n") + "\n", locator))
                    check_chunks(chunks, budgets, diagnostics)
                else:
                    diagnostics.add("PDF_PAGE_NO_TEXT", "此页无可提取文字；未运行 OCR，页面只保留在原件中。", locator)
            if not chunks:
                diagnostics.fail("PDF_NO_EXTRACTABLE_TEXT", "PDF 未找到可提取文字；扫描或图片内容没有被伪造为正文，原件已保留。")
            return ExtractedDocument(tuple(chunks), tuple(diagnostics.values), "pypdf-6.18.1/text-1", "author_private" if restricted else "learner")
    except ExtractionFailure:
        raise
    except (PdfReadError, PdfStreamError, ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError, OverflowError):
        diagnostics.fail("PDF_MALFORMED", "PDF 结构或文字编码无法可靠解析，未部分导入；请核对原件。", handler.locator)
    finally:
        logger.removeHandler(handler)
    raise AssertionError("unreachable")
