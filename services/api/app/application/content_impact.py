"""Content-owned impact evidence from real publication events.

Only explicit ContentRefs can establish a revision-qualified dependency here.
Pure concept IDs remain conservative candidates. This read never reconciles
learning facts, indexes, reviews, notes or other owners' progress.
"""

from collections import deque
from dataclasses import dataclass
import sqlite3
from typing import Literal

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import CANONICAL_VERSION, canonical_bytes, sha256_bytes, strict_json
from packages.contracts.validation import PublishedModel, refs_in

from ..infrastructure.content_repository import ContentRepository, damaged, missing, reference
from .errors import ApiError


@dataclass(frozen=True)
class ContentImpactSnapshot:
    event_id: str
    old_ref: dm.ContentRef
    new_ref: dm.ContentRef
    reason: Literal["content_revision_published"]
    affected_ids: tuple[str, ...]
    exact_dependency_refs: tuple[dm.ContentRef, ...]
    conservative_only_ids: tuple[str, ...]
    evidence_version: Literal["owner_frozen_v1", "legacy_unverified"]
    applicability: Literal["pending_review"] = "pending_review"
    snapshot_sha256: str | None = None


def _key(ref: dm.ContentRef) -> str:
    return ref.model_dump_json()


def _event_revision(repository: ContentRepository, ref: dm.ContentRef) -> PublishedModel:
    """An event's missing or damaged revision is corrupt evidence, not a missing event."""
    try:
        value = repository.load(ref.entity, ref.id, ref.revision).value
    except ApiError:
        raise damaged() from None
    if reference(value) != ref:
        raise damaged()
    return value


def _explicit_dependents(repository: ContentRepository, old_ref: dm.ContentRef,
                         affected_ids: tuple[str, ...]) -> tuple[dm.ContentRef, ...]:
    """Traverse only owner metadata's explicit refs within this write transaction."""
    affected = set(affected_ids)
    visited = {_key(old_ref)}
    pending = deque([old_ref])
    exact: list[dm.ContentRef] = []
    while pending:
        target = pending.popleft()
        rows = repository.connection.execute(
            "SELECT d.owner_id,d.owner_revision,d.relation,o.kind FROM object_dependencies d "
            "JOIN objects o ON o.id=d.owner_id WHERE d.target_id=? AND d.target_revision=? "
            "AND d.relation IN ('reference','anchor') AND o.workspace_id=? "
            "ORDER BY d.owner_id,d.owner_revision,d.relation",
            (target.id, target.revision, repository.workspace_id),
        ).fetchall()
        for edge in rows:
            if edge["owner_id"] not in affected:
                raise damaged()
            try:
                owner = repository.load(edge["kind"], edge["owner_id"], edge["owner_revision"]).value
            except ApiError:
                raise damaged() from None
            owner_ref = reference(owner)
            if (target not in refs_in(owner)
                    or edge["relation"] == "anchor" and not isinstance(owner, dm.Note)):
                raise damaged()
            identity = _key(owner_ref)
            if identity not in visited:
                visited.add(identity)
                exact.append(owner_ref)
                pending.append(owner_ref)
    return tuple(exact)


def freeze_impact_event(repository: ContentRepository, event_id: str, event_raw: bytes,
                        old_ref: dm.ContentRef, new_ref: dm.ContentRef,
                        affected_ids: tuple[str, ...]) -> None:
    """Owner-transaction evidence, never a later read-side reconstruction."""
    if not repository.connection.in_transaction:
        raise damaged()
    source = repository.connection.execute(
        "SELECT payload_json FROM outbox WHERE id=? AND event_type='content.dependencies_invalidated'",
        (event_id,),
    ).fetchone()
    if source is None or source["payload_json"] != event_raw.decode():
        raise damaged()
    exact = _explicit_dependents(repository, old_ref, affected_ids)
    frozen = {
        "version": "content-impact-v1", "event_id": event_id,
        "workspace_id": repository.workspace_id,
        "event_payload_sha256": sha256_bytes(event_raw),
        "old_ref": old_ref.model_dump(mode="json"),
        "new_ref": new_ref.model_dump(mode="json"),
        "affected_ids": list(affected_ids),
        "exact_dependency_refs": [ref.model_dump(mode="json") for ref in exact],
    }
    data = canonical_bytes(frozen)
    repository.connection.execute(
        "INSERT INTO content_impact_snapshots(event_id,workspace_id,snapshot_json,snapshot_sha256) "
        "VALUES(?,?,?,?)",
        (event_id, repository.workspace_id, data.decode(), sha256_bytes(data)),
    )


def _frozen_refs(repository: ContentRepository, event_id: str, event_raw: str,
                 old_ref: dm.ContentRef, new_ref: dm.ContentRef,
                 affected_ids: tuple[str, ...]) -> tuple[dm.ContentRef, ...] | None:
    row = repository.connection.execute(
        "SELECT workspace_id,snapshot_json,snapshot_sha256 FROM content_impact_snapshots WHERE event_id=?",
        (event_id,),
    ).fetchone()
    legacy = repository.connection.execute(
        "SELECT payload_json FROM content_impact_legacy_events WHERE event_id=?",
        (event_id,),
    ).fetchone()
    if row is None:
        # Only byte-frozen pre-migration IDs may receive the legacy label.
        if legacy is None or legacy["payload_json"] != event_raw:
            raise damaged()
        return None
    if legacy is not None:
        raise damaged()
    try:
        data = row["snapshot_json"].encode()
        value = strict_json(data)
        if (row["workspace_id"] != repository.workspace_id or sha256_bytes(data) != row["snapshot_sha256"]
                or not isinstance(value, dict) or canonical_bytes(value) != data
                or set(value) != {"version", "event_id", "workspace_id", "event_payload_sha256",
                                  "old_ref", "new_ref", "affected_ids", "exact_dependency_refs"}
                or value["version"] != "content-impact-v1" or value["event_id"] != event_id
                or value["workspace_id"] != repository.workspace_id
                or value["event_payload_sha256"] != sha256_bytes(event_raw.encode())
                or value["old_ref"] != old_ref.model_dump(mode="json")
                or value["new_ref"] != new_ref.model_dump(mode="json")
                or value["affected_ids"] != list(affected_ids)
                or not isinstance(value["exact_dependency_refs"], list)):
            raise damaged()
        refs = tuple(dm.ContentRef.model_validate(item) for item in value["exact_dependency_refs"])
    except (ValueError, TypeError, KeyError, AttributeError, ValidationError):
        raise damaged() from None
    reachable = {_key(old_ref)}
    affected = set(affected_ids)
    for ref in refs:
        if ref.id not in affected or _key(ref) in reachable:
            raise damaged()
        owner = _event_revision(repository, ref)
        if not any(_key(target) in reachable for target in refs_in(owner)):
            raise damaged()
        reachable.add(_key(ref))
    return refs


def impact_snapshot(connection: sqlite3.Connection, workspace_id: str, event_id: str) -> ContentImpactSnapshot:
    """Read one policy-checked event in the caller's locked SQLite transaction."""
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

    _event_revision(repository, old_ref)
    _event_revision(repository, new_ref)
    paired = connection.execute(
        "SELECT COUNT(*) FROM outbox WHERE event_type='content.published' AND payload_json=?",
        (raw,),
    ).fetchone()[0]
    if paired != 1:
        raise damaged()

    exact = _frozen_refs(repository, event_id, raw, old_ref, new_ref, tuple(ids))
    evidence_version: Literal["owner_frozen_v1", "legacy_unverified"] = (
        "owner_frozen_v1" if exact is not None else "legacy_unverified")
    exact = exact or ()
    exact_ids = {item.id for item in exact}
    return ContentImpactSnapshot(event_id, old_ref, new_ref, "content_revision_published", tuple(ids), exact,
                                 tuple(item for item in ids if item != old_ref.id and item not in exact_ids),
                                 evidence_version, snapshot_sha256=(connection.execute(
                                     "SELECT snapshot_sha256 FROM content_impact_snapshots WHERE event_id=?",
                                     (event_id,),
                                 ).fetchone()[0] if evidence_version == "owner_frozen_v1" else None))


def list_impact_snapshots(connection: sqlite3.Connection, workspace_id: str) -> tuple[ContentImpactSnapshot, ...]:
    """Enumerate validated owner events, irrespective of delivery/consumer status."""
    if not connection.in_transaction:
        raise damaged()
    rows = connection.execute(
        "SELECT id FROM outbox WHERE event_type='content.dependencies_invalidated' "
        "AND json_extract(payload_json,'$.workspace_id')=? ORDER BY id", (workspace_id,),
    ).fetchall()
    return tuple(impact_snapshot(connection, workspace_id, row['id']) for row in rows)
