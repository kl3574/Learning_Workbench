"""Content-owned exact public base and retained provenance, in the caller transaction."""
import sqlite3

from packages.contracts import domain_models as dm
from ..infrastructure.database import Database
from ..infrastructure.provenance_repository import ProvenanceRepository
from ..infrastructure.security import SessionIdentity, current_session_identity
from .authoring_context import AuthoringContext
from .content import ContentService
from .draft_edit_models import DraftBaseMaterial, checked, integrity, unsupported, unresolved_warning


class ContentDraftSource:
    def __init__(self, database: Database):
        self.content = ContentService(database)

    def read_exact(self, conn: sqlite3.Connection, identity: SessionIdentity, ref: dm.ContentRef) -> DraftBaseMaterial:
        current = current_session_identity(conn, identity)
        AuthoringContext.check_access(conn, current)
        ref = checked(dm.ContentRef, ref, request=True)
        if ref.entity != 'block':
            raise unsupported()
        block, raw = self.content.verify_publication_in_transaction(conn, current.workspace_id, ref)
        if block.kind != 'text' or block.concepts or block.depends_on or block.body_path.startswith('private/'):
            raise unsupported()
        provenance = ProvenanceRepository(conn, current.workspace_id).bounded_frozen(block, max_bytes=2_000_000)
        try:
            return DraftBaseMaterial(ref=ref, metadata=block, body_markdown=raw.decode('utf-8'), provenance=provenance,
                warnings=provenance.warnings if provenance else [unresolved_warning()])
        except (ValueError, TypeError, UnicodeError):
            raise integrity() from None

    def verify_exact(self, conn: sqlite3.Connection, identity: SessionIdentity, expected: DraftBaseMaterial) -> None:
        expected = checked(DraftBaseMaterial, expected)
        if self.read_exact(conn, identity, expected.ref) != expected:
            raise integrity()
