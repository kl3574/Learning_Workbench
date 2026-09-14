"""M2.2 parser entry point; original-file persistence belongs to ingestion."""

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
        raise ImportParsingError(
            "EXTRACTION_NOT_IMPLEMENTED", "PDF/DOCX 隔离提取属于 M2.3，当前未实现；原件可保留，未生成虚假正文。"
        )
    if actual_kind == "learnpack":
        return parse_package(data, budgets=budgets)
    return parse_textual(data, actual_kind, filename, source_id, budgets=budgets)
