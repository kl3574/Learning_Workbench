"""Policy-guarded public content reads and an internal atomic publication port."""

import base64
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
import hashlib
import hmac
import re
import secrets
import sqlite3
import time

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json
from packages.contracts.validation import (
    ENTITY_MODELS, PublishedModel,
    canonical_path, refs_in, validate_dag, validate_route,
)

from ..content_dto import CourseSummary, PageCourse, PageRevision, RevisionSummary
from ..infrastructure.blobs import BlobInfo, BlobStore
from ..infrastructure.content_repository import ContentRepository, damaged, reference
from ..infrastructure.database import Database
from ..infrastructure.notes_repository import mark_stale_notes
from ..infrastructure.security import guard_subject_access
from .errors import ApiError


def invalid() -> ApiError:
    return ApiError(422, "SCHEMA_INVALID", "内容结构、引用或查询参数无效。")


def key(value: PublishedModel | dm.ContentRef) -> str:
    return f"{value.entity}:{value.id}:{value.revision}"


def concept_ids(value: PublishedModel) -> list[str]:
    if isinstance(value, (dm.Concept, dm.Lesson)):
        return value.prerequisite_ids
    if isinstance(value, dm.ContentBlock):
        return value.concepts
    if isinstance(value, dm.QuestionPublic):
        return value.concept_ids
    return []


class ContentService:
    def __init__(self, database: Database):
        self.database = database
        self.blobs = BlobStore(database.settings.data_dir, max_bytes=max(database.settings.import_budgets.max_package_bytes, database.settings.import_budgets.max_source_bytes))
        # Short-lived server-issued pagination; restart requires a fresh first page.
        self._cursor_key = secrets.token_bytes(32)

    @contextmanager
    def _access(self, workspace_id: str, *, allow_notes: bool = False) -> Iterator[ContentRepository]:
        try:
            # Shared workspace guard and the result are read under the same writer lock
            # used by attempt transitions, so a second connection cannot start an attempt mid-read.
            with self.database.transaction() as connection:
                repository = ContentRepository(connection, workspace_id, allow_notes=allow_notes)
                repository.require_workspace()
                guard_subject_access(connection, workspace_id)
                yield repository
        except sqlite3.Error:
            raise ApiError(503, "CONTENT_STORAGE_UNAVAILABLE", "内容存储暂不可用。", True) from None

    @staticmethod
    def _identity(object_id: str, revision: int | None = None) -> None:
        if (not isinstance(object_id, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", object_id) is None
                or revision is not None and (type(revision) is not int or revision < 1)):
            raise invalid()

    def read(self, workspace_id: str, entity: str, id: str, revision: int) -> PublishedModel:
        self._identity(id, revision)
        with self._access(workspace_id) as repository:
            return repository.load(entity, id, revision).value

    def body(self, workspace_id: str, id: str, revision: int) -> tuple[bytes, str]:
        self._identity(id, revision)
        with self._access(workspace_id) as repository:
            value = repository.load("block", id, revision).value
            if not isinstance(value, dm.ContentBlock):
                raise damaged()
            info = repository.body_info(value)
            return BlobStore(self.database.settings.data_dir, max_bytes=max(self.blobs.max_bytes, info.size)).read(info.sha256, expected_size=info.size), info.sha256

    def current(self, workspace_id: str, id: str) -> dm.ContentRef:
        self._identity(id)
        with self._access(workspace_id, allow_notes=True) as repository:
            return reference(repository.current(id).value)

    def _context(self, workspace_id: str, scope: str, query: str, limit: int) -> str:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise invalid()
        return sha256_bytes(canonical_bytes([workspace_id, scope, query, limit]))

    def _cursor(self, context: str, position: str | int) -> str:
        data = canonical_bytes({"v": 1, "context": context, "position": position, "expires": int(time.time()) + 3600})
        signature = hmac.new(self._cursor_key, data, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(data + signature).decode().rstrip("=")

    def _position(self, cursor: str | None, context: str, position_type: type[str] | type[int]) -> str | int | None:
        if cursor is None:
            return None
        try:
            if not isinstance(cursor, str) or not 1 <= len(cursor) <= 1024 or re.fullmatch(r"[A-Za-z0-9_-]+", cursor) is None:
                raise invalid()
            decoded = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
            data, signature = decoded[:-32], decoded[-32:]
            if not hmac.compare_digest(signature, hmac.new(self._cursor_key, data, hashlib.sha256).digest()):
                raise invalid()
            value = strict_json(data)
            if (not isinstance(value, dict) or set(value) != {"v", "context", "position", "expires"}
                    or value["v"] != 1 or value["context"] != context or type(value["expires"]) is not int
                    or value["expires"] < time.time() or type(value["position"]) is not position_type):
                raise invalid()
            return value["position"]
        except (ValueError, TypeError, KeyError):
            raise invalid() from None

    def courses(self, workspace_id: str, q: str | None = None, limit: int = 20, cursor: str | None = None) -> PageCourse:
        if q is not None and (not isinstance(q, str) or len(q) > 2000):
            raise invalid()
        context = self._context(workspace_id, "courses", q or "", limit)
        position = self._position(cursor, context, str)
        with self._access(workspace_id) as repository:
            rows = repository.connection.execute(
                "SELECT r.*,o.kind,o.lifecycle FROM objects o JOIN revisions r "
                "ON r.object_id=o.id AND r.revision=o.current_revision "
                "WHERE o.workspace_id=? AND o.kind='course' AND o.lifecycle='active' AND o.id>? "
                "AND (?='' OR instr(json_extract(r.metadata_json,'$.title'),?)>0) ORDER BY o.id LIMIT ?",
                (workspace_id, position or "", q or "", q or "", limit + 1),
            ).fetchall()
            items = []
            for row in rows[:limit]:
                value = repository.decode(row).value
                if not isinstance(value, dm.Course):
                    raise damaged()
                items.append(CourseSummary(ref=reference(value), title=value.title, language=value.language,
                                           lesson_count=len(value.lesson_refs)))
            return PageCourse(items=items, next_cursor=self._cursor(context, items[-1].ref.id) if len(rows) > limit else None)

    def revisions(self, workspace_id: str, id: str, limit: int = 20, cursor: str | None = None) -> PageRevision:
        self._identity(id)
        context = self._context(workspace_id, "revisions", id, limit)
        position = self._position(cursor, context, int)
        with self._access(workspace_id, allow_notes=True) as repository:
            repository.object_row(id)
            rows = repository.connection.execute(
                "SELECT r.*,o.kind,o.lifecycle FROM revisions r JOIN objects o ON o.id=r.object_id "
                "WHERE o.workspace_id=? AND o.id=? AND (? IS NULL OR r.revision<?) ORDER BY r.revision DESC LIMIT ?",
                (workspace_id, id, position, position, limit + 1),
            ).fetchall()
            items = []
            for row in rows[:limit]:
                stored = repository.decode(row)
                items.append(RevisionSummary(ref=reference(stored.value), created_at=stored.created_at,
                                             lifecycle=stored.lifecycle))
            return PageRevision(items=items, next_cursor=self._cursor(context, items[-1].ref.revision) if len(rows) > limit else None)

    @staticmethod
    def _candidates(objects: Iterable[PublishedModel], *, import_history: bool = False, budgets: ImportBudgets = ImportBudgets()) -> list[PublishedModel]:
        values: list[PublishedModel] = []
        identities: set[str] = set()
        revisions: set[str] = set()
        entities: dict[str, str] = {}
        try:
            for candidate in objects:
                if len(values) >= budgets.max_package_files or not isinstance(candidate, tuple(ENTITY_MODELS.values())):
                    raise invalid()
                if ((candidate.entity == "note" or candidate.id in identities) and not import_history
                        or key(candidate) in revisions
                        or candidate.id in entities and entities[candidate.id] != candidate.entity):
                    raise invalid()
                # Revalidate even model_construct/model_copy input; never serialize a secret-bearing subclass.
                value = ENTITY_MODELS[candidate.entity].model_validate(candidate.model_dump(mode="python"))
                identities.add(value.id)
                revisions.add(key(value))
                entities[value.id] = value.entity
                values.append(value)
            if not values:
                raise invalid()
            if sum(len(canonical_bytes(value)) for value in values) > budgets.max_package_bytes:
                raise invalid()
            return values
        except (ValueError, TypeError, AttributeError, KeyError, ValidationError):
            raise invalid() from None

    @staticmethod
    def _body_bytes(value: dm.ContentBlock, body: bytes, budgets: ImportBudgets = ImportBudgets()) -> None:
        try:
            if (type(body) is not bytes or sha256_bytes(body) != value.body_sha256
                    or len(body) > budgets.max_package_bytes):
                raise invalid()
            text = body.decode("utf-8")
            if "\r" in text or len(text) > budgets.max_block_characters:
                raise invalid()
        except (ValueError, TypeError, UnicodeError):
            raise invalid() from None

    def _stage(self, repository: ContentRepository, values: list[PublishedModel], bodies: Mapping[str, bytes], budgets: ImportBudgets) -> dict[str, BlobInfo]:
        blob_store = self.blobs if budgets == self.database.settings.import_budgets else BlobStore(self.database.settings.data_dir, max_bytes=max(budgets.max_package_bytes, budgets.max_source_bytes))
        required: dict[str, str] = {}
        try:
            for value in values:
                if isinstance(value, dm.ContentBlock):
                    path = canonical_path(value.body_path)
                    if path.startswith("private/") or path in required and required[path] != value.body_sha256:
                        raise invalid()
                    required[path] = value.body_sha256
            if (set(bodies) - set(required) or sum(len(body) for body in bodies.values())
                    + sum(len(canonical_bytes(value)) for value in values) > budgets.max_package_bytes):
                raise invalid()
            output = {}
            for value in values:
                if not isinstance(value, dm.ContentBlock):
                    continue
                body = bodies.get(value.body_path)
                if body is None:
                    info = repository.public_body(value.body_sha256)
                    body = blob_store.read(info.sha256, expected_size=info.size)
                self._body_bytes(value, body, budgets)
                output[value.body_sha256] = blob_store.write(body, expected_sha256=value.body_sha256)
            return output
        except (ValueError, TypeError):
            raise invalid() from None

    def _closure(self, repository: ContentRepository, values: list[PublishedModel], budgets: ImportBudgets) -> tuple[
        dict[str, PublishedModel], dict[str, list[tuple[dm.ContentRef, str]]], dict[str, dict[str, dm.Concept]],
    ]:
        registry = {key(value): value for value in values}
        candidate_concepts: dict[str, list[dm.Concept]] = {}
        for value in values:
            if isinstance(value, dm.Concept):
                candidate_concepts.setdefault(value.id, []).append(value)
        # A course's exact concept_refs disambiguate historical pure-ID edges.
        bindings: dict[str, dict[str, dm.ContentRef]] = {}
        for course in (value for value in values if isinstance(value, dm.Course)):
            selections = {ref.id: ref for ref in course.concept_refs}
            ref_queue = list(refs_in(course))
            seen: set[str] = set()
            while ref_queue:
                ref = ref_queue.pop()
                if key(ref) in seen:
                    continue
                seen.add(key(ref))
                target = registry.get(key(ref))
                if target is None:
                    continue
                owned = bindings.setdefault(key(target), {})
                for identifier, selection in selections.items():
                    if identifier not in concept_ids(target):
                        continue
                    if identifier in owned and owned[identifier] != selection:
                        raise invalid()
                    owned[identifier] = selection
                ref_queue.extend(refs_in(target))
        candidate_keys = set(registry)
        pending = list(values)
        dependencies: dict[str, list[tuple[dm.ContentRef, str]]] = {}

        def include(value: PublishedModel) -> None:
            if key(value) not in registry:
                if len(registry) >= max(10000, budgets.max_package_files * 5):
                    raise invalid()
                registry[key(value)] = value
                pending.append(value)

        def resolve(ref: dm.ContentRef) -> PublishedModel:
            value = registry.get(key(ref))
            if value is None:
                value = repository.load(ref.entity, ref.id, ref.revision).value
            if metadata_sha256(value) != ref.sha256:
                raise damaged()
            include(value)
            return value

        def concept(identifier: str, owner: PublishedModel) -> dm.Concept:
            if key(owner) not in candidate_keys:
                frozen = repository.concept_dependency(owner, identifier)
                include(frozen)
                return frozen
            choices = candidate_concepts.get(identifier, [])
            selection = bindings.get(key(owner), {}).get(identifier)
            if selection is not None:
                chosen = resolve(selection)
                if not isinstance(chosen, dm.Concept):
                    raise invalid()
                return chosen
            if len(choices) > 1:
                raise ApiError(422, "IMPORT_CONCEPT_AMBIGUOUS", "历史概念的纯 ID 依赖缺少可验证的精确版本。")
            value = choices[0] if choices else None
            if value is None:
                stored = repository.current(identifier).value
                if not isinstance(stored, dm.Concept):
                    raise invalid()
                value = stored
            include(value)
            return value

        while pending:
            value = pending.pop()
            targets = [(ref, "reference") for ref in refs_in(value)]
            for ref, _ in targets:
                if ref.entity == "note" and not isinstance(value, dm.Note):
                    raise invalid()
                resolve(ref)
            for identifier in concept_ids(value):
                targets.append((reference(concept(identifier, value)), "concept"))
            dependencies[key(value)] = targets
            if isinstance(value, dm.Course) and (any(ref.entity != "lesson" for ref in value.lesson_refs)
                                                 or any(ref.entity != "concept" for ref in value.concept_refs)):
                raise invalid()
            if isinstance(value, dm.Lesson) and any(ref.entity != "block" for ref in value.block_refs):
                raise invalid()
            if isinstance(value, dm.PracticeSet) and (value.lesson_ref.entity != "lesson"
                    or any(ref.entity != "question" for ref in value.question_refs)):
                raise invalid()
            if isinstance(value, dm.AssessmentBlueprint) and any(ref.entity != "question" for ref in value.question_refs):
                raise invalid()
            if isinstance(value, dm.Route):
                validate_route(value)
        validate_dag({identifier: [key(ref) for ref, _ in refs] for identifier, refs in dependencies.items()})

        course_concepts: dict[str, dict[str, dm.Concept]] = {}
        for course in (value for value in values if isinstance(value, dm.Course)):
            selected = {ref.id: registry[key(ref)] for ref in course.concept_refs}
            if len(selected) != len(course.concept_refs):
                raise invalid()
            if not all(isinstance(value, dm.Concept) for value in selected.values()):
                raise invalid()
            concepts = {identifier: value for identifier, value in selected.items() if isinstance(value, dm.Concept)}
            queue = list(concepts.values())
            while queue:
                value = queue.pop()
                for identifier in value.prerequisite_ids:
                    if identifier not in concepts:
                        target = concept(identifier, value)
                        concepts[identifier] = target
                        queue.append(target)
                    elif reference(concepts[identifier]) != reference(concept(identifier, value)):
                        # A course cannot silently merge two revisions of the same concept.
                        raise invalid()
            validate_dag({identifier: value.prerequisite_ids for identifier, value in concepts.items()})
            course_concepts[key(course)] = concepts
            dependencies[key(course)].extend((reference(value), "concept") for value in concepts.values())
        return registry, dependencies, course_concepts

    def publish(self, workspace_id: str, objects: Iterable[PublishedModel], bodies: Mapping[str, bytes]) -> list[dm.ContentRef]:
        """Internal trusted port; callers still own import/review approval workflows.

        All file durability precedes SQL references. Any failed validation or SQL
        commit can leave only unreferenced, content-addressed blobs for future GC.
        No approvals, learning evidence or private solutions are created here.
        """
        with self._access(workspace_id) as repository:
            return self.publish_in_transaction(repository.connection, workspace_id, objects, bodies)

    def publish_in_transaction(self, connection: sqlite3.Connection, workspace_id: str,
                               objects: Iterable[PublishedModel], bodies: Mapping[str, bytes], *,
                               import_history: bool = False, budgets: ImportBudgets | None = None) -> list[dm.ContentRef]:
        """Caller must own an active transaction, including import receipts and state."""
        if not connection.in_transaction:
            raise ApiError(409, "TRANSACTION_REQUIRED", "发布需要有效事务。")
        guard_subject_access(connection, workspace_id)
        repository = ContentRepository(connection, workspace_id, allow_notes=import_history)
        repository.require_workspace()
        budgets = budgets or self.database.settings.import_budgets
        values = self._candidates(objects, import_history=import_history, budgets=budgets)
        if any(isinstance(value, dm.Note) and value.workspace_id != workspace_id for value in values):
            raise invalid()
        repository.ensure_new(values)
        # Capture the actual current revisions once, before publishing a batch
        # that may itself contain multiple historical revisions of one object.
        previous_refs = []
        for identifier in sorted({value.id for value in values}):
            row = connection.execute(
                "SELECT current_revision FROM objects WHERE workspace_id=? AND id=?",
                (workspace_id, identifier),
            ).fetchone()
            if row is not None and row["current_revision"] is not None:
                previous_refs.append(reference(repository.current(identifier).value))
        try:
            _, dependencies, courses = self._closure(repository, values, budgets)
            staged = self._stage(repository, values, bodies, budgets)
        except (ValueError, TypeError, ValidationError):
            raise invalid() from None
        repository.insert_revisions(values, staged)
        for value in values:
            repository.insert_dependencies(value, dependencies[key(value)])
            if isinstance(value, dm.Course):
                repository.insert_concept_edges(value, courses[key(value)])
            if isinstance(value, dm.Note):
                connection.execute(
                    "INSERT INTO notes_index(note_id,note_revision,workspace_id,anchor_id,anchor_revision,anchor_state) "
                    "VALUES(?,?,?,?,?,?)", (value.id, value.revision, workspace_id, value.anchor.ref.id,
                                           value.anchor.ref.revision, value.anchor_state),
                )
        for value in sorted(values, key=lambda item: (item.id, item.revision)):
            repository.advance(value)
        mark_stale_notes(connection, workspace_id, previous_refs)
        from .recommendations import inputs_changed
        inputs_changed(connection, workspace_id, 'content.published')
        return [reference(value) for value in values]
