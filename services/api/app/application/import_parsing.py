"""Parser entry point; PDF/DOCX parsing requires the restricted process port."""

from typing import Literal

from pydantic import TypeAdapter, ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets

from .import_parse_markdown import parse_textual
from .import_parse_package import parse_package
from .import_parse_types import (
    ImportParsingError,
    ParsedAsset as ParsedAsset,
    ParsedImport as ParsedImport,
)

KINDS = {"auto", "markdown", "text", "html", "pdf", "docx", "learnpack"}


def detected_kind(data: bytes, kind: str, filename: str) -> str:
    if kind not in KINDS:
        raise ImportParsingError("IMPORT_KIND_UNSUPPORTED", "导入类型不受支持。")
    if kind != "auto":
        return kind
    name = filename.lower()
    for suffixes, detected in [
        ((".pdf",), "pdf"),
        ((".docx",), "docx"),
        ((".learnpack.zip", ".zip"), "learnpack"),
        ((".md", ".markdown"), "markdown"),
        ((".html", ".htm"), "html"),
        ((".txt",), "text"),
    ]:
        if name.endswith(suffixes):
            return detected
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "learnpack"
    if data.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        return "html"
    return "text"


def detect_import_visibility(data: bytes, kind: str, filename: str) -> Literal["learner", "author_private"]:
    """Every unvalidated archive is private, regardless of its manifest claims."""
    if (
        kind == "learnpack"
        or filename.lower().endswith((".zip", ".docx"))
        or data.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"))
    ):
        return "author_private"
    return "learner"


def parse_import(
    data: bytes, *, kind: str, filename: str, source_id: str, budgets: ImportBudgets = ImportBudgets()
) -> ParsedImport:
    if type(data) is not bytes or len(data) > budgets.max_source_bytes:
        raise ImportParsingError(
            "SOURCE_BUDGET_EXCEEDED", f"单原件必须是字节流且不超过配置预算 {budgets.max_source_bytes} 字节。"
        )
    try:
        TypeAdapter(dm.Id).validate_python(source_id)
        if not isinstance(filename, str):
            raise ValueError("Invalid filename")
    except (ValidationError, ValueError):
        raise ImportParsingError("IMPORT_INPUT_INVALID", "来源标识或文件名无效。") from None
    actual_kind = detected_kind(data, kind, filename)
    if actual_kind in {"pdf", "docx"}:
        from ..infrastructure.document_sandbox import DocumentSandboxError, extract_document
        from .import_extract_build import build_document, source_warnings

        try:
            document = extract_document(data, kind=actual_kind, filename=filename, source_id=source_id, budgets=budgets)
        except DocumentSandboxError as error:
            raise ImportParsingError(error.code, "文档隔离提取未完成；原件已保留，请查看定位诊断或修正提取环境。",
                                     warnings=source_warnings(error.warnings, source_id)) from None
        return build_document(data, document, filename=filename, source_id=source_id, budgets=budgets)
    if actual_kind == "learnpack":
        return parse_package(data, budgets=budgets)
    return parse_textual(data, actual_kind, filename, source_id, budgets=budgets)
