"""Content-owned, read-only interpretation of one persisted invalidation intent.

An affected object ID is only a conservative candidate. An exact dependency
ref names a persisted revision-qualified edge to the old revision, not semantic staleness.
Neither result is a reconciliation decision or a replacement for old evidence.
"""

from collections import deque
from dataclasses import dataclass
import sqlite3
from typing import Literal

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import CANONICAL_VERSION, canonical_bytes, strict_json
from packages.contracts.validation import PublishedModel, refs_in

from ..infrastructure.content_repository import ContentRepository, damaged, missing, reference


@dataclass(frozen=True)
class ContentImpactSnapshot:
    event_id: str
    old_ref: dm.ContentRef
    new_ref: dm.ContentRef
    reason: Literal["content_revision_published"]
    affected_ids: tuple[str, ...]
    exact_dependency_refs: tuple[dm.ContentRef, ...]
    conservative_only_ids: tuple[str, ...]
    applicability: Literal["pending_review"] = "pending_review"


def _concept_ids(value: PublishedModel) -> list[str]:
    if isinstance(value, (dm.Concept, dm.Lesson)):
        return value.prerequisite_ids
    if isinstance(value, dm.ContentBlock):
        return value.concepts
    if isinstance(value, dm.QuestionPublic):
        return value.concept_ids
    return []


def _course_concepts(repository: ContentRepository, course: dm.Course) -> list[dm.ContentRef]:
    """Check the exact prerequisite chain, including derived course edges."""
    found = {ref.model_dump_json(): ref for ref in course.concept_refs}
    queue = list(course.concept_refs)
    while queue:
        current = queue.pop()
        value = repository.load("concept", current.id, current.revision).value
        if not isinstance(value, dm.Concept) or reference(value) != current:
            raise damaged()
        for identifier in value.prerequisite_ids:
            dependency = reference(repository.concept_dependency(value, identifier))
            identity = dependency.model_dump_json()
            if identity not in found:
                found[identity] = dependency
                queue.append(dependency)
    return list(found.values())


def _edge_matches(repository: ContentRepository, owner: PublishedModel,
                  target: dm.ContentRef, relation: str) -> bool:
    if relation == "reference":
        return target in refs_in(owner)
    if relation == "anchor":
        return isinstance(owner, dm.Note) and owner.anchor.ref == target
    if relation == "concept" and target.entity == "concept":
        if isinstance(owner, dm.Course):
            return target in _course_concepts(repository, owner)
        return target.id in _concept_ids(owner)
    return False


def _affected_at_publication(connection: sqlite3.Connection, workspace_id: str,
                             changed_id: str, published_at: str) -> tuple[str, ...]:
    # The writer walks IDs across every then-persisted historical revision.
    # Immutable revision creation times exclude later dependencies from this
    # historical reconstruction; exact refs below use a separate traversal.
    rows = connection.execute(
        "WITH RECURSIVE affected(id) AS (SELECT ? UNION SELECT d.owner_id "
        "FROM object_dependencies d JOIN affected a ON d.target_id=a.id "
        "JOIN revisions r ON r.object_id=d.owner_id AND r.revision=d.owner_revision "
        "JOIN objects o ON o.id=d.owner_id "
        "WHERE o.workspace_id=? AND r.created_at<=?) SELECT id FROM affected ORDER BY id",
        (changed_id, workspace_id, published_at),
    ).fetchall()
    return tuple(row["id"] for row in rows)


def _verify_frozen_edges(repository: ContentRepository, ids: tuple[str, ...], published_at: str) -> None:
    """Validate each candidate revision's stored edges against its immutable metadata.

    This prevents a changed edge from silently turning an exact dependency into
    a merely conservative ID candidate. It does not certify semantic staleness.
    """
    for identifier in ids:
        rows = repository.connection.execute(
            "SELECT r.revision,o.kind FROM revisions r JOIN objects o ON o.id=r.object_id "
            "WHERE o.id=? AND o.workspace_id=? AND r.created_at<=? ORDER BY r.revision",
            (identifier, repository.workspace_id, published_at),
        ).fetchall()
        for row in rows:
            owner = repository.load(row["kind"], identifier, row["revision"]).value
            edges = repository.connection.execute(
                "SELECT d.target_id,d.target_revision,d.relation,o.kind,o.workspace_id FROM object_dependencies d "
                "JOIN objects o ON o.id=d.target_id "
                "WHERE d.owner_id=? AND d.owner_revision=? ORDER BY d.target_id,d.target_revision,d.relation",
                (identifier, row["revision"]),
            ).fetchall()
            actual: set[tuple[str, int, str]] = set()
            for edge in edges:
                if edge["workspace_id"] != repository.workspace_id:
                    raise damaged()
                target = repository.load(edge["kind"], edge["target_id"], edge["target_revision"]).value
                target_ref = reference(target)
                if not _edge_matches(repository, owner, target_ref, edge["relation"]):
                    raise damaged()
                actual.add((target_ref.id, target_ref.revision, edge["relation"]))
            for explicit_ref in refs_in(owner):
                if not any((explicit_ref.id, explicit_ref.revision, relation) in actual
                           for relation in ("reference", "anchor")):
                    raise damaged()
            for concept_id in _concept_ids(owner):
                if not any(edge[0] == concept_id and edge[2] == "concept" for edge in actual):
                    raise damaged()


def impact_snapshot(connection: sqlite3.Connection, workspace_id: str, event_id: str) -> ContentImpactSnapshot:
    """Read one real event in the caller's consistent, policy-checked transaction."""
    if not connection.in_transaction:
        raise damaged()
    repository = ContentRepository(connection, workspace_id, allow_notes=True)
    row = connection.execute(
        "SELECT payload_json FROM outbox WHERE id=? AND event_type='content.dependencies_invalidated'",
        (event_id,),
    ).fetchone()
    if row is None:
        raise missing()
    raw = row["payload_json"]
    try:
        value = strict_json(raw)
        if (not isinstance(value, dict)
                or set(value) != {"workspace_id", "canonical_version", "old_ref", "new_ref", "affected_ids", "reason"}
                or canonical_bytes(value).decode() != raw or value["canonical_version"] != CANONICAL_VERSION
                or value["reason"] != "content_revision_published"):
            raise damaged()
        if value["workspace_id"] != workspace_id:
            raise missing()
        old_ref = dm.ContentRef.model_validate(value["old_ref"])
        new_ref = dm.ContentRef.model_validate(value["new_ref"])
        ids = value["affected_ids"]
        if (not isinstance(ids, list) or not ids or any(not isinstance(item, str) or not item for item in ids)
                or ids != sorted(set(ids)) or old_ref.entity != new_ref.entity or old_ref.id != new_ref.id
                or old_ref.revision >= new_ref.revision or old_ref.id not in ids):
            raise damaged()
    except (ValueError, TypeError, KeyError, ValidationError):
        raise damaged() from None

    old = repository.load(old_ref.entity, old_ref.id, old_ref.revision)
    new = repository.load(new_ref.entity, new_ref.id, new_ref.revision)
    if reference(old.value) != old_ref or reference(new.value) != new_ref:
        raise damaged()
    # Content.advance writes a paired publication intent in its owner transaction.
    # A matching persisted pair is checked, not claimed as cryptographic provenance.
    paired = connection.execute(
        "SELECT COUNT(*) FROM outbox WHERE event_type='content.published' AND payload_json=?",
        (raw,),
    ).fetchone()[0]
    if paired != 1 or tuple(ids) != _affected_at_publication(connection, workspace_id, old_ref.id, new.created_at):
        raise damaged()

    _verify_frozen_edges(repository, tuple(ids), new.created_at)

    affected = set(ids)
    visited = {old_ref.model_dump_json()}
    queue = deque([old_ref])
    exact: list[dm.ContentRef] = []
    while queue:
        target = queue.popleft()
        rows = connection.execute(
            "SELECT d.owner_id,d.owner_revision,d.relation,r.created_at FROM object_dependencies d "
            "JOIN revisions r ON r.object_id=d.owner_id AND r.revision=d.owner_revision "
            "JOIN objects o ON o.id=d.owner_id WHERE d.target_id=? AND d.target_revision=? "
            "AND o.workspace_id=? AND r.created_at<=? ORDER BY d.owner_id,d.owner_revision,d.relation",
            (target.id, target.revision, workspace_id, new.created_at),
        ).fetchall()
        for edge in rows:
            if edge["owner_id"] not in affected:
                raise damaged()
            owner_row = repository.object_row(edge["owner_id"])
            owner = repository.load(owner_row["kind"], edge["owner_id"], edge["owner_revision"]).value
            if not _edge_matches(repository, owner, target, edge["relation"]):
                raise damaged()
            owner_ref = reference(owner)
            identity = owner_ref.model_dump_json()
            if identity not in visited:
                visited.add(identity)
                exact.append(owner_ref)
                queue.append(owner_ref)
    exact_ids = {item.id for item in exact}
    return ContentImpactSnapshot(event_id, old_ref, new_ref, "content_revision_published", tuple(ids),
                                 tuple(exact), tuple(item for item in ids if item != old_ref.id and item not in exact_ids))
