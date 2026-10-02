"""Content-owned exact public base and retained provenance, in the caller transaction."""
import sqlite3
from pydantic import TypeAdapter

from packages.contracts import domain_models as dm
from ..infrastructure.database import Database
from ..infrastructure.provenance_repository import ProvenanceRepository
from ..infrastructure.security import SessionIdentity, current_session_identity
from .authoring_context import AuthoringContext
from .content import ContentService
from .draft_edit_models import DraftBaseMaterial, DependencyDraftBaseMaterial, StoredDraftBase, checked, integrity, unsupported, unresolved_warning


class ContentDraftSource:
    def __init__(self, database: Database):
        self.content = ContentService(database)

    def read_exact(self, conn: sqlite3.Connection, identity: SessionIdentity, ref: dm.ContentRef) -> StoredDraftBase:
        current = current_session_identity(conn, identity)
        AuthoringContext.check_access(conn, current)
        ref = checked(dm.ContentRef, ref, request=True)
        if ref.entity != 'block':
            raise unsupported()
        block, raw = self.content.verify_publication_in_transaction(conn, current.workspace_id, ref)
        if block.kind != 'text' or block.concepts or block.body_path.startswith('private/'):
            raise unsupported()
        dependencies = self.content.verify_retained_dependencies_in_transaction(conn, current.workspace_id, ref) if block.depends_on else None
        provenance = ProvenanceRepository(conn, current.workspace_id).bounded_frozen(block, max_bytes=2_000_000)
        try:
            if dependencies is not None:
                return DependencyDraftBaseMaterial(version='draft-base-material-dependencies-v2', ref=ref, metadata=block,
                    body_markdown=raw.decode('utf-8'), provenance=provenance,
                    warnings=provenance.warnings if provenance else [unresolved_warning()], dependency_witness=dependencies)
            return DraftBaseMaterial(ref=ref, metadata=block, body_markdown=raw.decode('utf-8'), provenance=provenance,
                warnings=provenance.warnings if provenance else [unresolved_warning()])
        except (ValueError, TypeError, UnicodeError):
            raise integrity() from None

    def verify_exact(self, conn: sqlite3.Connection, identity: SessionIdentity, expected: StoredDraftBase) -> None:
        try:
            expected = TypeAdapter(StoredDraftBase).validate_python(expected.model_dump(mode='python', warnings='error'))
        except (ValueError, TypeError, AttributeError):
            raise integrity() from None
        if self.read_exact(conn, identity, expected.ref) != expected:
            raise integrity()
