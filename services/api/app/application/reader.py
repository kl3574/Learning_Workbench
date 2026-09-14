"""Guarded exact course directories and public, revision-bound Reader provenance."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import sqlite3

from pydantic import TypeAdapter, ValidationError

from packages.contracts import domain_models as dm

from ..infrastructure.content_repository import ContentRepository, damaged, reference
from ..infrastructure.database import Database
from ..infrastructure.provenance_repository import ProvenanceRepository
from ..infrastructure.security import SessionIdentity, guard_subject_access
from ..reader_dto import (
    BlockProvenanceResponse, DirectoryAncestor, DirectoryHit, DirectorySearchResponse,
    OutlineBlock, OutlineLesson, OutlineResponse, OutlineSection, RetainedOriginal,
)
from .errors import ApiError
from .learning import reading_states


def invalid() -> ApiError:
    return ApiError(422, 'SCHEMA_INVALID', '目录查询字段或引用无效。')


def exact_key(ref: dm.ContentRef) -> str:
    return f'{ref.entity}:{ref.id}:{ref.revision}:{ref.sha256}'


class ReaderService:
    def __init__(self, database: Database):
        self.database = database

    @contextmanager
    def _access(self, identity: SessionIdentity, id: str, revision: int) -> Iterator[ContentRepository]:
        try:
            TypeAdapter(dm.Id).validate_python(id, strict=True)
            if type(revision) is not int or revision < 1:
                raise invalid()
        except ValidationError:
            raise invalid() from None
        try:
            with self.database.transaction() as connection:
                repository = ContentRepository(connection, identity.workspace_id)
                repository.require_workspace()
                guard_subject_access(connection, identity.workspace_id)
                yield repository
        except sqlite3.Error:
            raise ApiError(503, 'CONTENT_STORAGE_UNAVAILABLE', '内容存储暂不可用。', True) from None

    @staticmethod
    def _course(repository: ContentRepository, id: str, revision: int) -> tuple[dm.Course, dict[str, dm.Lesson], dict[str, list[dm.ContentBlock]]]:
        course = repository.load('course', id, revision).value
        if not isinstance(course, dm.Course):
            raise damaged()
        lessons: dict[str, dm.Lesson] = {}
        blocks: dict[str, list[dm.ContentBlock]] = {}
        for lesson_ref in course.lesson_refs:
            lesson = repository.load(lesson_ref.entity, lesson_ref.id, lesson_ref.revision).value
            if not isinstance(lesson, dm.Lesson) or reference(lesson) != lesson_ref:
                raise damaged()
            lessons[lesson.id] = lesson
            blocks[lesson.id] = []
            for block_ref in lesson.block_refs:
                block = repository.load(block_ref.entity, block_ref.id, block_ref.revision).value
                if not isinstance(block, dm.ContentBlock) or reference(block) != block_ref:
                    raise damaged()
                blocks[lesson.id].append(block)
        return course, lessons, blocks

    @staticmethod
    def _sections(course: dm.Course) -> list[dm.CourseSection]:
        return course.sections or [dm.CourseSection(id=course.id, title=course.title,
                                                     lesson_ids=[ref.id for ref in course.lesson_refs])]

    def outline(self, identity: SessionIdentity, id: str, revision: int) -> OutlineResponse:
        with self._access(identity, id, revision) as repository:
            course, lessons, blocks = self._course(repository, id, revision)
            states = reading_states(repository.connection, identity.workspace_id, course.lesson_refs,
                                    {exact_key(reference(lesson)): lesson.block_refs for lesson in lessons.values()})
            return OutlineResponse(course_ref=reference(course), sections=[OutlineSection(
                id=section.id, title=section.title, lessons=[OutlineLesson(
                    ref=reference(lessons[lesson_id]), title=lessons[lesson_id].title,
                    blocks=[OutlineBlock(ref=reference(block), kind=block.kind, title=block.title) for block in blocks[lesson_id]],
                    reading_state=states[exact_key(reference(lessons[lesson_id]))],
                ) for lesson_id in section.lesson_ids],
            ) for section in self._sections(course)])

    def directory_search(self, identity: SessionIdentity, id: str, revision: int, *, q: str, limit: int = 20) -> DirectorySearchResponse:
        if not isinstance(q, str) or not q.strip() or len(q) > 2000 or type(limit) is not int or not 1 <= limit <= 50:
            raise invalid()
        with self._access(identity, id, revision) as repository:
            course, lessons, blocks = self._course(repository, id, revision)
            query = q.strip().casefold()
            hits: list[DirectoryHit] = []

            def include(ref: dm.ContentRef, title: str, ancestors: list[DirectoryAncestor]) -> None:
                if len(hits) < limit and any(query in text.casefold() for text in [title, *(item.title for item in ancestors)]):
                    hits.append(DirectoryHit(ref=ref, title=title, ancestors=ancestors))

            include(reference(course), course.title, [])
            for section in self._sections(course):
                ancestors = [DirectoryAncestor(id=course.id, title=course.title)]
                if section.id != course.id or section.title != course.title:
                    ancestors.append(DirectoryAncestor(id=section.id, title=section.title))
                for lesson_id in section.lesson_ids:
                    lesson = lessons[lesson_id]
                    include(reference(lesson), lesson.title, ancestors)
                    block_ancestors = [*ancestors, DirectoryAncestor(id=lesson.id, title=lesson.title)]
                    for block in blocks[lesson_id]:
                        include(reference(block), block.title, block_ancestors)
            return DirectorySearchResponse(hits=hits)

    def block(self, identity: SessionIdentity, id: str, revision: int) -> BlockProvenanceResponse:
        with self._access(identity, id, revision) as repository:
            block = repository.load('block', id, revision).value
            if not isinstance(block, dm.ContentBlock):
                raise damaged()
            provenance = ProvenanceRepository(repository.connection, identity.workspace_id)
            snapshot = provenance.frozen(block)
            if snapshot is None:
                return BlockProvenanceResponse(block=block, block_ref=reference(block), original_source=None, citations=[],
                    unresolved_citation_ids=list(block.citations), warnings=[dm.Warning(code='PROVENANCE_UNRESOLVED',
                        message='此修订尚无可核验的冻结来源记录；原始引用保留，未按相同 ID 猜测来源。', severity='warning')])
            return BlockProvenanceResponse(block=block, block_ref=reference(block),
                original_source=RetainedOriginal(source=snapshot.source,
                    original_access=provenance.original_access(identity, snapshot.source)),
                citations=provenance.resolved(identity, snapshot), unresolved_citation_ids=[], warnings=snapshot.warnings)


# Startup migration work is explicit and separate from guarded, read-only Reader GETs.


@dataclass(frozen=True)
class ProvenanceBackfillResult:
    scanned_imports: int
    frozen_blocks: int
    unresolved_blocks: int
    warnings: tuple[dm.Warning, ...]


def backfill_provenance(database: Database) -> ProvenanceBackfillResult:
    from collections import Counter

    from packages.contracts.canonical import sha256_bytes
    from ..infrastructure.import_repository import ImportRepository, json_object
    from ..infrastructure.provenance_repository import FrozenProvenance
    from .import_parsing import ImportParsingError, parse_import
    from .imports import ImportService

    service = ImportService(database)
    plans: list[tuple[str, str, str, list[FrozenProvenance]]] = []
    scanned = frozen = unresolved = 0
    failed = False
    with database.connect() as connection:
        rows = connection.execute(
            "SELECT i.id,i.workspace_id,i.preview_json,COUNT(p.block_id) AS frozen_count FROM ingestion_imports i "
            "LEFT JOIN block_provenance p ON p.import_id=i.id AND p.workspace_id=i.workspace_id "
            "WHERE i.status='committed' GROUP BY i.id,i.workspace_id,i.preview_json",
        ).fetchall()
    for candidate in rows:
        expected_count = 0
        try:
            initial_preview = json_object(candidate['preview_json'])
            expected_count = sum(item['entity'] == 'block' for item in initial_preview['objects'])
            if candidate['frozen_count'] == expected_count:
                continue
            scanned += 1
            with database.transaction() as connection:
                guard_subject_access(connection, candidate['workspace_id'])
                row = ImportRepository(connection, candidate['workspace_id']).load(candidate['id'])
                if row['status'] != 'committed' or row['job_status'] != 'completed':
                    raise damaged()
                options = json_object(row['input_json'])
                budgets = service.frozen_budgets(row)
                store = service.frozen_store(row)
                info = ImportRepository(connection, candidate['workspace_id']).blob(row['blob_sha256'])
                input_sha = row['input_sha256']
                source_id = row['source_id']
            original = store.read(info.sha256, expected_size=info.size)
            if sha256_bytes(original) != input_sha:
                raise damaged()
            # The same parser port enforces all frozen input budgets and mandatory
            # PDF/DOCX namespace isolation. No database lock is held while extracting.
            parsed = parse_import(original, kind=options['kind'], filename=options['filename'],
                                  source_id=source_id, budgets=budgets)
            warnings = [*parsed.warnings, dm.Warning(code='IMPORT_REVIEW_UNVERIFIED',
                message='确认解析结果不会认证材料的数学正确性或来源权利。', severity='warning')]
            with database.transaction() as connection:
                guard_subject_access(connection, candidate['workspace_id'])
                repository = ProvenanceRepository(connection, candidate['workspace_id'])
                snapshots = repository.recovery_snapshots(
                    candidate['id'], objects=parsed.objects, citations=parsed.citations, warnings=warnings,
                    input_sha256=input_sha, parser_version=parsed.parser_version,
                    read_blob=lambda digest,size:store.read(digest,expected_size=size))
                stamp = repository.recovery_stamp(candidate['id'])
            plans.append((candidate['id'], candidate['workspace_id'], stamp, snapshots))
        except (ApiError, ImportParsingError, OSError, ValueError, KeyError, TypeError, sqlite3.Error):
            unresolved += max(0, expected_count - candidate['frozen_count'])
            failed = True
    # No first-match backfill: two historic imports claiming one exact block are ambiguous.
    owners = Counter((workspace, exact_key(snapshot.block_ref)) for _,workspace,_,items in plans for snapshot in items)
    for import_id, workspace, stamp, items in plans:
        safe = [item for item in items if owners[(workspace,exact_key(item.block_ref))] == 1]
        unresolved += len(items) - len(safe)
        failed = failed or len(safe) != len(items)
        try:
            with database.transaction() as connection:
                guard_subject_access(connection, workspace)
                repository = ProvenanceRepository(connection, workspace)
                if repository.recovery_stamp(import_id) != stamp:
                    raise damaged()
                count = sum(repository.insert_recovered(import_id, item) for item in safe)
            frozen += count
        except (ApiError, ValueError, KeyError, TypeError, sqlite3.Error):
            unresolved += len(safe)
            failed = True
    diagnostics = (dm.Warning(code='PROVENANCE_BACKFILL_UNRESOLVED',
        message='部分旧修订的原件、确认映射或精确哈希无法核验，保留为来源未解析。',severity='warning'),) if failed else ()
    return ProvenanceBackfillResult(scanned, frozen, unresolved, diagnostics)
