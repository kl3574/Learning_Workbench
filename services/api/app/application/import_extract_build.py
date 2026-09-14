"""Build strict candidate objects from the validated, passive sandbox document."""

from pathlib import PurePosixPath
import re

from pydantic import TypeAdapter, ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets
from packages.contracts.canonical import sha256_bytes
from packages.contracts.validation import PublishedModel, validate_objects

from .import_extract_types import ExtractedDocument, ExtractionWarning
from .import_parse_markdown import reference, stable_id
from .import_parse_types import ImportParsingError, ParsedImport


def source_warnings(warnings: tuple[ExtractionWarning, ...], source_id: str) -> tuple[dm.Warning, ...]:
    return tuple(dm.Warning(code=item.code, message=item.message,
                            locator=f"source:{source_id};{item.locator}" if item.locator else f"source:{source_id}",
                            severity=item.severity) for item in warnings)


def build_document(data: bytes, document: ExtractedDocument, *, filename: str, source_id: str, budgets: ImportBudgets) -> ParsedImport:
    filename_title = PurePosixPath(filename.replace("\\", "/")).stem.strip() or "导入资料"
    title = next((re.sub(r"\\([\\`*_{}\[\]()#+.!|><&$-])", r"\1", chunk.body_markdown).strip()
                  for chunk in document.chunks if chunk.kind == "heading"), filename_title)
    warnings = source_warnings(document.warnings, source_id)
    try:
        TypeAdapter(dm.Text).validate_python(title)
        TypeAdapter(dm.Text).validate_python(filename_title)
        objects: list[PublishedModel] = []
        bodies: dict[str, bytes] = {}
        citations: list[dm.Citation] = []
        lessons: list[dm.Lesson] = []
        block_refs: list[dm.ContentRef] = []
        current_title = title

        def finish_lesson() -> None:
            nonlocal block_refs
            if block_refs:
                lesson = dm.Lesson(id=stable_id("lesson", source_id, len(lessons)), revision=1,
                                   title=current_title, objectives=[], block_refs=block_refs)
                lessons.append(lesson)
                objects.append(lesson)
                block_refs = []

        for index, chunk in enumerate(document.chunks):
            if chunk.kind == "heading" and chunk.heading_level in {1, 2}:
                finish_lesson()
                current_title = re.sub(r"\\([\\`*_{}\[\]()#+.!|><&$-])", r"\1", chunk.body_markdown).strip()
            body = chunk.body_markdown.encode("utf-8")
            block_id = stable_id("block", source_id, index)
            path = f"content/{block_id}.r1.md"
            citation = dm.Citation(id=stable_id("citation", source_id, index), title=filename_title,
                                   source_sha256=sha256_bytes(data), verification="user_supplied",
                                   locator=f"source:{source_id};{chunk.locator}")
            citations.append(citation)
            block = dm.ContentBlock(id=block_id, revision=1, kind="text", title=current_title,
                                    body_path=path, body_sha256=sha256_bytes(body), citations=[citation.id])
            objects.append(block)
            bodies[path] = body
            block_refs.append(reference(block))
        finish_lesson()
        if not lessons:
            raise ImportParsingError("EMPTY_CONTENT", "未得到有效的提取正文，未生成空教材。", warnings=warnings)
        course = dm.Course(id=stable_id("course", source_id), revision=1, title=title,
                           audience="用户导入的参考材料", lesson_refs=[reference(lesson) for lesson in lessons],
                           sections=[dm.CourseSection(id=stable_id("section", source_id), title=title,
                                                      lesson_ids=[lesson.id for lesson in lessons])])
        objects.append(course)
        validate_objects(objects, bodies, budgets=budgets)
        return ParsedImport(tuple(objects), bodies, (), warnings, document.extractor_version,
                            citations=tuple(citations), original_visibility=document.original_visibility)
    except (ValidationError, ValueError) as error:
        if isinstance(error, ImportParsingError):
            raise
        raise ImportParsingError("EXTRACTION_CANDIDATE_INVALID", "提取结果未满足严格候选结构或元数据约束，未部分导入。", warnings=warnings) from None
