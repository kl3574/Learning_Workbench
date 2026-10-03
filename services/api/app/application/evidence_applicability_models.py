"""Private owner records; no pins, commands, or source bindings are HTTP payloads."""

from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes

from ..authoring_dto import AuthoringModel
from ..evidence_applicability_dto import EvidenceImpactDecisionReceipt, EvidenceImpactDecisionWrite
from .assessment_evidence_access import SubmissionWitness
from .content_learning_access import EvidenceSemanticBasis


class RelevantImpactEvent(AuthoringModel):
    event_id: dm.Id
    old_ref: dm.ContentRef
    new_ref: dm.ContentRef
    affected_ids: list[dm.Id]
    exact_dependency_refs: list[dm.ContentRef]
    conservative_only_ids: list[dm.Id]
    evidence_version: Literal['owner_frozen_v1', 'legacy_unverified']
    event_snapshot_sha256: dm.Sha256 | None
    relevance: Literal['exact_ref', 'id_only_candidate']


class EvidenceCurrentBasis(AuthoringModel):
    version: Literal['evidence-applicability-basis-v1']
    workspace_id: dm.Id
    original_evidence: dm.Evidence
    question_ref: dm.ContentRef
    concept_ref: dm.ContentRef
    attempt_id: dm.Id
    grading_revision: dm.Revision
    original_binding_sha256: dm.Sha256
    submission: SubmissionWitness
    semantics: EvidenceSemanticBasis
    events: list[RelevantImpactEvent]


class EvidenceDecisionRecord(AuthoringModel):
    version: Literal['evidence-applicability-decision-v1']
    workspace_id: dm.Id
    route: str
    key: str
    request: EvidenceImpactDecisionWrite
    basis: EvidenceCurrentBasis
    receipt: EvidenceImpactDecisionReceipt


def decision_route(evidence_id: str) -> str:
    return f'POST /learning/evidence/{evidence_id}/applicability-decisions'


def request_digest(workspace_id: str, actor: str, evidence_id: str,
                   key: str, body: EvidenceImpactDecisionWrite) -> str:
    return sha256_bytes(canonical_bytes({'version': 'evidence-applicability-command-v1', 'workspace_id': workspace_id,
        'actor_session_id': actor, 'route': decision_route(evidence_id), 'key': key, 'body': body.model_dump(mode='json')}))


def receipt_digest(receipt: EvidenceImpactDecisionReceipt) -> str:
    return sha256_bytes(canonical_bytes({'version': 'evidence-applicability-receipt-v1',
                           **receipt.model_dump(mode='json', exclude={'receipt_sha256'})}))
