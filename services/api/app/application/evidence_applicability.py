"""Learning-owned human applicability decisions; original learning facts never change."""

import base64
import hashlib
import hmac
import re
import secrets
import sqlite3
from dataclasses import dataclass
from collections.abc import Sequence
from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json

from ..evidence_applicability_dto import (
    EvidenceApplicabilityDecisionView, EvidenceImpactArtifact, EvidenceImpactDecisionReceipt, EvidenceImpactDecisionWrite,
)
from ..infrastructure.database import Database, utc_now
from ..infrastructure.evidence_applicability_repository import EvidenceApplicabilityRepository, invalid_decision
from ..infrastructure.security import SessionIdentity, current_session_identity, require_role
from .artifacts import ArtifactsService
from .content_impact import ContentImpactSnapshot, impact_snapshot, list_impact_snapshots
from .content_learning_access import evidence_semantic_basis, verify_evidence_semantic_history
from .errors import ApiError
from .evidence import checked_evidence_origin
from .evidence_applicability_models import (
    EvidenceCurrentBasis, EvidenceDecisionRecord, RelevantImpactEvent, decision_route, receipt_digest, request_digest,
)
from .learning_state_models import EvidenceApplicability
from .policy import Policy


def _event(snapshot: ContentImpactSnapshot, basis_refs: Sequence[dm.ContentRef],
           direct_refs: Sequence[dm.ContentRef]) -> RelevantImpactEvent | None:
    relevance: Literal['exact_ref', 'id_only_candidate'] | None = ('exact_ref' if snapshot.old_ref in basis_refs else
                 'id_only_candidate' if {ref.id for ref in direct_refs}.intersection(snapshot.affected_ids) else None)
    if relevance is None:
        return None
    return RelevantImpactEvent(event_id=snapshot.event_id, old_ref=snapshot.old_ref, new_ref=snapshot.new_ref,
        affected_ids=list(snapshot.affected_ids), exact_dependency_refs=list(snapshot.exact_dependency_refs),
        conservative_only_ids=list(snapshot.conservative_only_ids), evidence_version=snapshot.evidence_version,
        event_snapshot_sha256=snapshot.snapshot_sha256, relevance=relevance)


def _basis(connection: sqlite3.Connection, workspace_id: str, evidence_id: str) -> EvidenceCurrentBasis:
    origin = checked_evidence_origin(connection, workspace_id, evidence_id)
    observed = origin.observation
    try:
        semantics = evidence_semantic_basis(connection, workspace_id, observed.question_ref, observed.concept_ref)
    except ApiError as error:
        if error.status == 404:
            raise invalid_decision() from None
        raise
    events = [event for snapshot in list_impact_snapshots(connection, workspace_id)
              if (event := _event(snapshot, semantics.original_refs, [observed.question_ref, observed.concept_ref])) is not None]
    return EvidenceCurrentBasis(version='evidence-applicability-basis-v1', workspace_id=workspace_id,
        original_evidence=observed.evidence, question_ref=observed.question_ref, concept_ref=observed.concept_ref,
        attempt_id=observed.attempt_id, grading_revision=observed.grading_revision,
        original_binding_sha256=origin.binding_sha256, submission=origin.submission, semantics=semantics,
        events=sorted(events, key=lambda event: event.event_id))


def _history(connection: sqlite3.Connection, basis: EvidenceCurrentBasis) -> list[EvidenceDecisionRecord]:
    """Verify receipts and original sources independently of current basis equality.

    Artifact IDs/hashes here are frozen decision facts. This internal metadata
    projection grants no private artifact access. The protected API rechecks
    actual bytes through their registered owners before returning history.
    """
    records = EvidenceApplicabilityRepository(connection, basis.workspace_id).history(basis.original_evidence.id)
    for record in records:
        old = record.basis
        if (old.original_evidence != basis.original_evidence or old.question_ref != basis.question_ref
                or old.concept_ref != basis.concept_ref or old.attempt_id != basis.attempt_id
                or old.grading_revision != basis.grading_revision or old.original_binding_sha256 != basis.original_binding_sha256
                or old.submission != basis.submission or old.semantics.original_refs != basis.semantics.original_refs
                or [event.event_id for event in old.events] != sorted({event.event_id for event in old.events})):
            raise invalid_decision()
        verify_evidence_semantic_history(connection, basis.workspace_id, old.semantics)
        for event in old.events:
            try:
                actual = _event(impact_snapshot(connection, basis.workspace_id, event.event_id),
                                old.semantics.original_refs, [old.question_ref, old.concept_ref])
            except ApiError as error:
                if error.status == 404:
                    raise invalid_decision() from None
                raise
            if actual != event:
                raise invalid_decision()
    return records


def _projection(basis: EvidenceCurrentBasis, records: list[EvidenceDecisionRecord]) -> EvidenceApplicability:
    digest = metadata_sha256(basis)
    heads = {record.receipt.event_id: record.receipt for record in records}
    valid = {event.event_id: heads[event.event_id] for event in basis.events
             if event.event_id in heads and heads[event.event_id].current_basis_sha256 == digest}
    reasons: set[str] = set()
    if any(item.lifecycle != 'active' for item in basis.semantics.dependencies):
        reasons.add('SEMANTIC_DEPENDENCY_NOT_ACTIVE')
    if any(receipt.decision == 'confirmed_stale' for receipt in valid.values()):
        return EvidenceApplicability(status='confirmed_stale',
            reason_codes=sorted(reasons | {'CONTENT_APPLICABILITY_CONFIRMED_STALE'}), checked_refs=basis.semantics.original_refs)
    unresolved = [event for event in basis.events if event.event_id not in valid]
    for event in unresolved:
        reasons.add('EXACT_CONTENT_CHANGE_PENDING' if event.relevance == 'exact_ref' else 'ID_ONLY_CONTENT_CHANGE_PENDING')
        if event.evidence_version == 'legacy_unverified':
            reasons.add('CONTENT_CHANGE_LEGACY_UNVERIFIED')
    # Human decisions can clear revision-change review, never archived materials.
    if (not basis.events or unresolved) and any(item.ref != item.current_ref for item in basis.semantics.dependencies):
        reasons.add('SEMANTIC_DEPENDENCY_REVISION_CHANGED')
    return EvidenceApplicability(status='pending_review' if reasons else 'usable',
        reason_codes=sorted(reasons), checked_refs=basis.semantics.original_refs)


def current_evidence_applicability(connection: sqlite3.Connection, workspace_id: str,
                                   evidence_id: str) -> EvidenceApplicability:
    """Read-only Learning port for Recommendation and concept-state consumers."""
    basis = _basis(connection, workspace_id, evidence_id)
    return _projection(basis, _history(connection, basis))


@dataclass(frozen=True)
class PagePosition:
    watermark: tuple[tuple[str, int], ...]
    after: tuple[str, int]


class EvidenceApplicabilityService:
    def __init__(self, database: Database, artifacts: ArtifactsService):
        self.database, self.artifacts = database, artifacts
        self._cursor_key = secrets.token_bytes(32)

    @staticmethod
    def _access(connection: sqlite3.Connection, identity: SessionIdentity) -> SessionIdentity:
        current = current_session_identity(connection, identity)
        require_role(current, 'author')
        Policy(connection, current.workspace_id).check('private_artifact')
        return current

    def _artifacts(self, connection: sqlite3.Connection, identity: SessionIdentity,
                   identifiers: list[str]) -> list[EvidenceImpactArtifact]:
        output = []
        for identifier in identifiers:
            _, artifact = self.artifacts.read_in_transaction(connection, identity, identifier)
            output.append(EvidenceImpactArtifact(id=identifier, sha256=artifact.sha256))
        return output

    def _checked_history(self, connection: sqlite3.Connection, identity: SessionIdentity,
                         basis: EvidenceCurrentBasis) -> list[EvidenceDecisionRecord]:
        records = _history(connection, basis)
        artifacts: dict[str, EvidenceImpactArtifact] = {}
        for record in records:
            for expected in record.receipt.evidence_artifacts:
                if expected.id not in artifacts:
                    try:
                        artifacts[expected.id] = self._artifacts(connection, identity, [expected.id])[0]
                    except ApiError as error:
                        if error.status == 404:
                            raise invalid_decision() from None
                        raise
                if artifacts[expected.id] != expected:
                    raise invalid_decision()
        return records

    def _cursor(self, context: str, position: PagePosition) -> str:
        raw = canonical_bytes({'context': context, 'watermark': position.watermark, 'after': position.after})
        return base64.urlsafe_b64encode(hmac.new(self._cursor_key, raw, hashlib.sha256).digest() + raw).decode().rstrip('=')

    def _position(self, token: str | None, context: str, heads: dict[str, int]) -> PagePosition:
        if token is None:
            return PagePosition(tuple(sorted(heads.items())), ('', 0))
        try:
            if len(token) > 65536 or re.fullmatch('[A-Za-z0-9_-]+', token) is None:
                raise ValueError('invalid cursor')
            raw = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
            if not hmac.compare_digest(raw[:32], hmac.new(self._cursor_key, raw[32:], hashlib.sha256).digest()):
                raise ValueError('bad signature')
            value = strict_json(raw[32:])
            if not isinstance(value, dict) or set(value) != {'context', 'watermark', 'after'} or value['context'] != context:
                raise ValueError('wrong context')
            watermark = tuple((item[0], item[1]) for item in value['watermark'])
            after = tuple(value['after'])
            if (len(after) != 2 or not isinstance(after[0], str) or type(after[1]) is not int or after[1] < 1
                    or any(not isinstance(event, str) or type(revision) is not int or revision < 1
                           or heads.get(event, 0) < revision for event, revision in watermark)
                    or watermark != tuple(sorted(dict(watermark).items())) or after[1] > dict(watermark).get(after[0], 0)):
                raise ValueError('invalid position')
            return PagePosition(watermark, (after[0], after[1]))
        except (ValueError, TypeError, KeyError, IndexError):
            raise ApiError(422, 'CURSOR_INVALID', '决定历史游标无效，请重新读取第一页。') from None

    def read(self, identity: SessionIdentity, evidence_id: str, event_id: str | None = None,
             cursor: str | None = None, limit: int = 20) -> EvidenceApplicabilityDecisionView:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ApiError(422, 'SCHEMA_INVALID', '分页数量必须为 1 到 100。')
        try:
            with self.database.transaction(immediate=False) as connection:
                current = self._access(connection, identity)
                basis = _basis(connection, current.workspace_id, evidence_id)
                records = self._checked_history(connection, current, basis)
                if event_id is not None and event_id not in {event.event_id for event in basis.events}:
                    raise ApiError(422, 'SCHEMA_INVALID', '筛选事件必须属于此证据的真实相关事件。')
                projection = _projection(basis, records)
                heads = {record.receipt.event_id: record.receipt.decision_revision for record in records
                         if event_id is None or record.receipt.event_id == event_id}
                context = sha256_bytes(canonical_bytes({'workspace_id': current.workspace_id, 'actor': current.id,
                    'evidence_id': evidence_id, 'event_id': event_id, 'limit': limit}))
                position = self._position(cursor, context, heads)
                frozen = dict(position.watermark)
                eligible = [record.receipt for record in records
                    if (record.receipt.event_id, record.receipt.decision_revision) > position.after
                    and record.receipt.decision_revision <= frozen.get(record.receipt.event_id, 0)]
                page = eligible[:limit]
                next_cursor = self._cursor(context, PagePosition(position.watermark,
                    (page[-1].event_id, page[-1].decision_revision))) if len(eligible) > limit else None
                return EvidenceApplicabilityDecisionView(evidence_id=evidence_id, original_evidence=basis.original_evidence,
                    question_ref=basis.question_ref, concept_ref=basis.concept_ref, attempt_id=basis.attempt_id,
                    grading_revision=basis.grading_revision, original_evidence_sha256=metadata_sha256(basis.original_evidence),
                    current_basis_sha256=metadata_sha256(basis), applicability=projection.status,
                    reason_codes=projection.reason_codes, relevant_event_ids=[event.event_id for event in basis.events],
                    event_decision_head=heads.get(event_id, 0) if event_id is not None else None,
                    decisions=page, next_cursor=next_cursor)
        except sqlite3.Error:
            raise ApiError(503, 'LEARNING_STORAGE_UNAVAILABLE', '学习证据存储暂不可用。', True) from None

    def decide(self, identity: SessionIdentity, evidence_id: str, body: EvidenceImpactDecisionWrite,
               key: str) -> EvidenceImpactDecisionReceipt:
        if re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key) is None:
            raise ApiError(400, 'IDEMPOTENCY_KEY_REQUIRED', '需要有效的 Idempotency-Key。')
        try:
            with self.database.transaction() as connection:
                current = self._access(connection, identity)
                basis = _basis(connection, current.workspace_id, evidence_id)
                records = self._checked_history(connection, current, basis)
                repository = EvidenceApplicabilityRepository(connection, current.workspace_id)
                digest = request_digest(current.workspace_id, current.id, evidence_id, key, body)
                previous = repository.command(current.id, evidence_id, key, records)
                if previous is not None:
                    if previous.receipt.request_sha256 != digest:
                        raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '相同幂等键不能用于不同决定命令。')
                    return previous.receipt
                relevant = [event for event in basis.events if event.event_id == body.event_id]
                if not relevant:
                    # Owner resolves unknown/cross-workspace before a real unrelated event conflict.
                    impact_snapshot(connection, current.workspace_id, body.event_id)
                    raise ApiError(409, 'EVIDENCE_EVENT_UNRELATED', '事件与此原证据的语义范围没有已核验关联。')
                event = relevant[0]
                if event.evidence_version != 'owner_frozen_v1':
                    raise ApiError(409, 'IMPACT_LEGACY_UNVERIFIED', '迁移前事件只有保守范围，不能提交适用性决定。')
                head = max((record.receipt.decision_revision for record in records
                            if record.receipt.event_id == body.event_id), default=0)
                if head != body.expected_decision_revision or metadata_sha256(basis) != body.expected_current_basis_sha256:
                    raise ApiError(412, 'REVISION_MISMATCH', '决定版本或证据依据已变化，请重新读取后复核。')
                artifacts = self._artifacts(connection, current, body.evidence_artifact_ids)
                receipt = EvidenceImpactDecisionReceipt(evidence_id=evidence_id, event_id=body.event_id,
                    decision_revision=head + 1, relevance=event.relevance, question_ref=basis.question_ref,
                    concept_ref=basis.concept_ref, attempt_id=basis.attempt_id, grading_revision=basis.grading_revision,
                    original_evidence_sha256=metadata_sha256(basis.original_evidence), current_basis_sha256=metadata_sha256(basis),
                    decision=body.decision, reason=body.reason, evidence_artifacts=artifacts,
                    actor_session_id=current.id, decided_at=utc_now(), request_sha256=digest, receipt_sha256='0' * 64)
                receipt = receipt.model_copy(update={'receipt_sha256': receipt_digest(receipt)})
                repository.append(EvidenceDecisionRecord(version='evidence-applicability-decision-v1',
                    workspace_id=current.workspace_id, route=decision_route(evidence_id), key=key, request=body,
                    basis=basis, receipt=receipt))
                from .recommendations import inputs_changed
                inputs_changed(connection, current.workspace_id, 'learning.evidence_applicability_decided')
                return receipt
        except sqlite3.Error:
            raise ApiError(503, 'LEARNING_STORAGE_UNAVAILABLE', '学习证据存储暂不可用。', True) from None
