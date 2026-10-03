"""Provenance application port for guarded, exact publication source snapshots."""
import sqlite3

from packages.contracts import domain_models as dm
from ..infrastructure.provenance_repository import FrozenProvenance, ProvenanceRepository
from ..infrastructure.security import SessionIdentity, current_session_identity
from .authoring_context import AuthoringContext


class PublicationProvenance:
    @staticmethod
    def read(conn: sqlite3.Connection, identity: SessionIdentity, import_id: str,
             block: dm.ContentBlock) -> FrozenProvenance:
        current = current_session_identity(conn, identity)
        AuthoringContext.check_access(conn, current)
        return ProvenanceRepository(conn, current.workspace_id).frozen_for_import(import_id, block)

    @staticmethod
    def freeze(conn: sqlite3.Connection, identity: SessionIdentity, import_id: str,
               block: dm.ContentBlock) -> FrozenProvenance:
        current = current_session_identity(conn, identity)
        AuthoringContext.check_access(conn, current)
        ProvenanceRepository(conn, current.workspace_id).freeze_import(import_id, [block])
        return PublicationProvenance.read(conn, current, import_id, block)
