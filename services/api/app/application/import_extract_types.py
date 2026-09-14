"""Small standard-library values shared by isolated extractors and the host builder."""

from dataclasses import dataclass
import re
import os
from pathlib import Path
from typing import Literal, NoReturn


@dataclass(frozen=True)
class ExtractionWarning:
    code: str
    message: str
    locator: str | None
    severity: Literal["info", "warning", "error"]


@dataclass(frozen=True)
class ExtractedChunk:
    kind: Literal["page", "heading", "paragraph", "table"]
    body_markdown: str
    locator: str
    heading_level: int | None = None


@dataclass(frozen=True)
class ExtractedDocument:
    chunks: tuple[ExtractedChunk, ...]
    warnings: tuple[ExtractionWarning, ...]
    extractor_version: str
    original_visibility: Literal["learner", "author_private"]


class ExtractionFailure(ValueError):
    def __init__(self, code: str, warnings: tuple[ExtractionWarning, ...] = ()):
        self.code = code
        self.warnings = warnings
        super().__init__(code)


class Diagnostics:
    def __init__(self) -> None:
        self.values: list[ExtractionWarning] = []
        self.seen: set[tuple[str, str | None]] = set()

    def add(self, code: str, message: str, locator: str | None,
            severity: Literal["info", "warning", "error"] = "warning") -> None:
        key = code, locator
        if key in self.seen:
            return
        if len(self.values) < 500:
            self.seen.add(key)
            self.values.append(ExtractionWarning(code, message, locator, severity))
        elif len(self.values) == 500:
            self.values.append(ExtractionWarning("EXTRACTION_DIAGNOSTICS_AGGREGATED", "诊断超过 500 项，其余位置请核对原件。", None, "warning"))

    def fail(self, code: str, message: str, locator: str | None = None) -> NoReturn:
        self.add(code, message, locator, "error")
        raise ExtractionFailure(code, tuple(self.values))


def passive_text(text: str) -> str:
    """Present extracted characters literally; do not infer Markdown or TeX semantics."""
    return re.sub(r"([\\`*_{}\[\]()#+.!|><&$-])", r"\\\1", text)


def checked_budgets(budgets: dict[str, int]) -> dict[str, int]:
    expected = {"max_source_bytes", "max_block_characters", "max_package_bytes", "max_package_files", "max_compression_ratio"}
    if set(budgets) != expected or any(type(value) is not int or value < 1 for value in budgets.values()):
        raise ExtractionFailure("EXTRACTION_BUDGET_INVALID")
    return budgets


def check_chunks(chunks: list[ExtractedChunk], budgets: dict[str, int], diagnostics: Diagnostics) -> None:
    if len(chunks) > budgets["max_package_files"]:
        diagnostics.fail("EXTRACTION_BUDGET_EXCEEDED", "候选文本块数量超过配置预算。")
    if sum(len(chunk.body_markdown.encode("utf-8")) for chunk in chunks) > budgets["max_package_bytes"]:
        diagnostics.fail("EXTRACTION_BUDGET_EXCEEDED", "候选正文总字节数超过配置预算。")
    for chunk in chunks:
        if len(chunk.body_markdown) > budgets["max_block_characters"]:
            diagnostics.fail("EXTRACTION_BUDGET_EXCEEDED", "候选正文块超过配置字符预算。", chunk.locator)


def require_sandbox() -> None:
    """Accidental host use fails closed; real isolation is established by the port."""
    try:
        ready = os.environ.get("LEARNING_DOCUMENT_SANDBOX") == "1" and "NoNewPrivs:\t1" in Path("/proc/self/status").read_text()
    except OSError:
        ready = False
    if not ready:
        raise ExtractionFailure("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
