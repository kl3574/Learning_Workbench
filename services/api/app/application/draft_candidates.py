"""Explicit owner routing and same-transaction admission for M6.2 candidate identities."""

import sqlite3
from typing import Protocol

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from ..infrastructure.draft_candidate_repository import DraftCandidateRepository
from ..infrastructure.security import SessionIdentity, author_execution_identity
from .authoring_context import AuthoringContext
from .draft_candidate_models import DraftSourceKind, ResolvedDraftCandidate
from .errors import ApiError
from .review_material_models import CheckedReviewMaterial


class DraftCandidateOwner(Protocol):
    def resolve_candidate(self, connection: sqlite3.Connection, identity: SessionIdentity,
                          candidate: dm.DraftCandidate) -> ResolvedDraftCandidate: ...

    def read_review_material(self, connection: sqlite3.Connection, identity: SessionIdentity,
                             candidate: dm.DraftCandidate) -> CheckedReviewMaterial: ...


class DraftCandidates:
    def __init__(self, owners: dict[DraftSourceKind, DraftCandidateOwner]):
        self._owners = dict(owners)

    def lookup(self, connection: sqlite3.Connection, identity: SessionIdentity,
               draft_id: str, expected_revision: int) -> ResolvedDraftCandidate:
        """Read only: the catalog selects one owner, which rechecks complete history.

        Missing registration is never repaired here, including for an otherwise
        valid legacy candidate. No owner detection by ID prefix or fallback scan.
        """
        current, registered, owner = self._registered_owner(connection, identity, draft_id, expected_revision)
        resolved = owner.resolve_candidate(connection, current, registered.candidate)
        if resolved != registered:
            raise ApiError(503, 'DRAFT_OWNER_INTEGRITY', '草稿所属记录当前无法核验。')
        return resolved

    def _registered_owner(self, connection: sqlite3.Connection, identity: SessionIdentity,
                          draft_id: str, expected_revision: int) -> tuple[SessionIdentity, ResolvedDraftCandidate, DraftCandidateOwner]:
        AuthoringContext.check_access(connection, identity)
        current = author_execution_identity(connection, identity.workspace_id, identity.id)
        AuthoringContext.check_access(connection, current)
        registered = DraftCandidateRepository(connection).lookup(
            current.workspace_id, draft_id, expected_revision)
        owner = self._owners.get(registered.source_kind)
        if owner is None:
            raise ApiError(503, 'DRAFT_OWNER_UNAVAILABLE', '草稿所属服务当前无法核验。')
        return current, registered, owner

    def read_review_material(self, connection: sqlite3.Connection, identity: SessionIdentity,
                             draft_id: str, expected_revision: int) -> CheckedReviewMaterial:
        """Resolve exactly one registered owner; never register, repair or execute."""
        current, registered, owner = self._registered_owner(connection, identity, draft_id, expected_revision)
        result = owner.read_review_material(connection, current, registered.candidate)
        try:
            result = CheckedReviewMaterial.model_validate(result.model_dump(mode='python'))
        except (ValidationError, ValueError, TypeError, AttributeError):
            raise ApiError(503, 'DRAFT_OWNER_INTEGRITY', '审核材料当前无法完整核验。') from None
        if (result.workspace_id != registered.workspace_id or result.owner != registered.owner
                or result.source_kind != registered.source_kind or result.candidate != registered.candidate):
            raise ApiError(503, 'DRAFT_OWNER_INTEGRITY', '审核材料当前无法完整核验。')
        return result

    def admit(self, connection: sqlite3.Connection, identity: SessionIdentity,
              source_kind: DraftSourceKind, candidate: dm.DraftCandidate) -> ResolvedDraftCandidate:
        """No implicit owner detection, HTTP handler, review, content write or Provider call.

        The caller owns the writer transaction. Even exact catalog retries recheck
        current Policy and the owner's original complete history before registration.
        """
        AuthoringContext.check_access(connection, identity)
        # A prior HTTP/session snapshot cannot keep author rights after revocation.
        current = author_execution_identity(connection, identity.workspace_id, identity.id)
        AuthoringContext.check_access(connection, current)
        owner = self._owners.get(source_kind)
        if owner is None:
            raise ApiError(503, 'DRAFT_OWNER_UNAVAILABLE', '草稿所属服务当前无法核验。')
        try:
            # Revalidate model_copy/model_construct input, including unexpected subclasses.
            candidate = dm.DraftCandidate.model_validate(candidate.model_dump(mode='python'))
        except (ValidationError, ValueError, TypeError, AttributeError):
            raise ApiError(422, 'SCHEMA_INVALID', '草稿候选身份无效。') from None
        resolved = owner.resolve_candidate(connection, current, candidate)
        expected_owner = 'import' if source_kind == 'import' else 'authoring'
        if (resolved.workspace_id != identity.workspace_id or resolved.source_kind != source_kind
                or resolved.owner != expected_owner or resolved.candidate != candidate):
            raise ApiError(503, 'DRAFT_OWNER_INTEGRITY', '草稿所属记录当前无法核验。')
        DraftCandidateRepository(connection).register(resolved)
        return resolved
