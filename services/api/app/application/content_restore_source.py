"""Content-owned exact historical block, dependency and retained original-byte reads."""
import sqlite3
from typing import Literal
from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from packages.contracts.validation import PublishedModel, refs_in, validate_dag
from ..content_restore_dto import RestoreSourceMaterial
from ..infrastructure.content_repository import ContentRepository, reference
from ..infrastructure.provenance_repository import ProvenanceRepository
from ..infrastructure.security import SessionIdentity, current_session_identity
from .authoring_context import AuthoringContext
from .content import ContentService, concept_ids, key
from .content_restore_models import RestoreSource, RestoreDependency, integrity
from .draft_edit_models import unresolved_warning
from .errors import ApiError


class ContentRestoreSource:
    def __init__(self, database):
        self.content = ContentService(database)

    def read(self, conn: sqlite3.Connection, identity: SessionIdentity, ref: dm.ContentRef) -> RestoreSource:
        current = current_session_identity(conn, identity)
        AuthoringContext.check_access(conn, current)
        if ref.entity != 'block':
            raise ApiError(422, 'RESTORE_SCOPE_INVALID', '恢复只接受公开内容块。')
        if ref.revision > 2**63 - 1:
            raise ApiError(404, 'RESTORE_SOURCE_MISSING', '历史来源不存在或不可访问。')
        block, raw = self.content.verify_publication_in_transaction(conn, current.workspace_id, ref)
        try:
            return self._retained(conn, current, ref, block, raw)
        except ApiError as error:
            if error.status == 404:
                raise integrity() from None
            raise

    def _retained(self, conn: sqlite3.Connection, current: SessionIdentity, ref: dm.ContentRef,
                  block: dm.ContentBlock, raw: bytes) -> RestoreSource:
        repo = ContentRepository(conn, current.workspace_id)
        dependencies: list[RestoreDependency] = []
        graph: dict[str, list[str]] = {}
        pending: list[PublishedModel] = [block]
        seen: set[str] = set()
        while pending:
            value = pending.pop()
            owner = reference(value)
            if key(owner) in seen:
                continue
            seen.add(key(owner))
            if len(seen) > 10000 or repo.load(owner.entity, owner.id, owner.revision).lifecycle != 'active':
                raise ApiError(409, 'RESTORE_DEPENDENCY_UNAVAILABLE', '恢复来源或依赖已归档或超过核验预算。')
            if isinstance(value, dm.ContentBlock):
                if value.body_path.startswith('private/'):
                    raise ApiError(403, 'RESTORE_SOURCE_PROTECTED', '恢复来源包含受保护材料。')
                self.content.verify_publication_in_transaction(conn, current.workspace_id, owner)
            targets: list[tuple[dm.ContentRef, Literal['reference', 'concept']]] = [(r, 'reference') for r in refs_in(value)]
            targets.extend((reference(repo.concept_dependency(value, identifier)), 'concept') for identifier in concept_ids(value))
            if isinstance(value, dm.Course):
                concepts = list(value.concept_refs)
                course_seen = set()
                while concepts:
                    concept_ref = concepts.pop()
                    if concept_ref.id in course_seen:
                        continue
                    course_seen.add(concept_ref.id)
                    concept = repo.load('concept', concept_ref.id, concept_ref.revision).value
                    if not isinstance(concept, dm.Concept) or reference(concept) != concept_ref:
                        raise integrity()
                    targets.append((concept_ref, 'concept'))
                    concepts.extend(reference(repo.concept_dependency(concept, dep)) for dep in concept.prerequisite_ids)
            actual = {(r['target_id'], r['target_revision'], r['relation']) for r in conn.execute(
                'SELECT target_id,target_revision,relation FROM object_dependencies WHERE owner_id=? AND owner_revision=?', (owner.id, owner.revision))}
            if actual != {(r.id, r.revision, relation) for r, relation in targets}:
                raise integrity()
            graph[key(owner)] = [key(r) for r, _ in targets]
            for target, relation in targets:
                if target.entity == 'note':
                    raise ApiError(409, 'RESTORE_DEPENDENCY_UNSUPPORTED', '恢复块包含当前切片不支持的依赖。')
                stored = repo.load(target.entity, target.id, target.revision)
                if reference(stored.value) != target:
                    raise integrity()
                dependencies.append(RestoreDependency(owner_ref=owner, target_ref=target, relation=relation))
                pending.append(stored.value)
        try:
            validate_dag(graph)
        except ValueError:
            raise integrity() from None
        provenance = ProvenanceRepository(conn, current.workspace_id).verified_original(block, self.content.blobs.read)
        material = RestoreSourceMaterial(version='restore-source-v1', source_ref=ref, metadata=block,
            body_sha256=block.body_sha256, source_descriptor_sha256=metadata_sha256(provenance) if provenance else None,
            warnings=provenance.warnings if provenance else [unresolved_warning()])
        return RestoreSource(material=material, body_markdown=raw.decode('utf-8'), provenance=provenance,
            dependencies=sorted(dependencies, key=lambda d: (key(d.owner_ref), d.relation, key(d.target_ref))))

    def require_current(self, conn: sqlite3.Connection, identity: SessionIdentity, expected: dm.ContentRef) -> None:
        current = ContentRepository(conn, identity.workspace_id).current(expected.id)
        if current.lifecycle != 'active' or reference(current.value) != expected:
            raise ApiError(412, 'RESTORE_BASE_CHANGED', '当前块已变化或归档；请明确重新创建恢复稿。')
        block, _ = self.content.verify_publication_in_transaction(conn, identity.workspace_id, expected)
        if block.body_path.startswith('private/'):
            raise ApiError(403, 'RESTORE_SOURCE_PROTECTED', '恢复当前基准包含受保护材料。')
