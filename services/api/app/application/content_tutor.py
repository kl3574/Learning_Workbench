"""Content-owned exact public material for Tutor; never reads private answers."""
import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from ..infrastructure.content_repository import ContentRepository, reference
from ..infrastructure.database import Database
from ..infrastructure.security import SessionIdentity
from .content_retrieval import ContentRetrievalSource
from .errors import ApiError
from .retrieval_models import MAX_BLOCKS, SCOPE_BYTE_BUDGET


class ContentTutorSource:
    def __init__(self, database: Database):
        self.materials = ContentRetrievalSource(database)

    @staticmethod
    def exact(conn: sqlite3.Connection, identity: SessionIdentity, ref: dm.ContentRef):
        repository = ContentRepository(conn, identity.workspace_id)
        repository.require_workspace()
        value = repository.load(ref.entity, ref.id, ref.revision).value
        if reference(value) != ref:
            raise ApiError(409, 'TUTOR_CONTEXT_INVALID', '上下文引用与实际修订不一致。')
        return value

    def blocks(self, conn: sqlite3.Connection, identity: SessionIdentity,
               roots: list[dm.ContentRef]) -> list[dm.ContentBlock]:
        """Preserve explicit root order and each owner's exact child order."""
        result: list[dm.ContentBlock] = []
        seen: set[tuple[str, int, str]] = set()
        metadata_bytes = 0
        for root in roots:
            if root.entity not in {'course', 'lesson', 'block'}:
                raise ApiError(422, 'TUTOR_CONTEXT_INVALID', '附加材料须为明确的课程、小节或教材块。')
            self.materials.resolve_scope(conn, identity, [root])
            # Recreate child order from immutable Content metadata. No depends_on,
            # current pointer, concept expansion, or query-driven index rebuild.
            def visit(ref: dm.ContentRef) -> None:
                nonlocal metadata_bytes
                value = self.exact(conn, identity, ref)
                if isinstance(value, dm.Course):
                    for child in value.lesson_refs:
                        visit(child)
                elif isinstance(value, dm.Lesson):
                    for child in value.block_refs:
                        visit(child)
                elif isinstance(value, dm.ContentBlock):
                    key = (ref.id, ref.revision, ref.sha256)
                    if key not in seen:
                        seen.add(key)
                        metadata_bytes += len(canonical_bytes(value))
                        if len(seen) > MAX_BLOCKS or metadata_bytes > SCOPE_BYTE_BUDGET:
                            raise ApiError(413, 'TUTOR_CONTEXT_BUDGET_EXCEEDED', '明确材料范围超过本机解析预算。')
                        result.append(value)
                else:
                    raise ApiError(422, 'TUTOR_CONTEXT_INVALID', '教材范围包含不支持的对象。')
            visit(root)
        return result

    @staticmethod
    def body_size(conn: sqlite3.Connection, identity: SessionIdentity, block: dm.ContentBlock) -> int:
        return ContentRepository(conn, identity.workspace_id).body_info(block).size

    def body(self, conn: sqlite3.Connection, identity: SessionIdentity, block: dm.ContentBlock) -> bytes:
        ref = reference(block)
        scope = self.materials.resolve_scope(conn, identity, [ref])
        result = self.materials.read_material(conn, identity, scope, ref).body
        result.decode('utf-8')
        return result

    def route(self, conn: sqlite3.Connection, identity: SessionIdentity, ref: dm.ContentRef) -> tuple[str, str]:
        value = self.exact(conn, identity, ref)
        if not isinstance(value, dm.Route):
            raise ApiError(422, 'TUTOR_CONTEXT_INVALID', '学习路线必须绑定实际路线修订。')
        # The route itself is the explicit unit; its targets are references, not
        # permission to silently insert every target's teaching text.
        return value.title, canonical_bytes(value).decode('utf-8')
