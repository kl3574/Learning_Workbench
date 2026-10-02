"""Learning's immutable decision history and complete original command replay."""

import sqlite3

from packages.contracts.canonical import canonical_bytes, metadata_sha256, strict_json

from .security import historical_session_belongs_to
from ..application.errors import ApiError
from ..application.evidence_applicability_models import (
    EvidenceDecisionRecord, decision_route, receipt_digest, request_digest,
)


def invalid_decision() -> ApiError:
    return ApiError(409, 'EVIDENCE_APPLICABILITY_INVALID', '学习证据适用性决定无法通过完整性校验。')


class EvidenceApplicabilityRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection, self.workspace_id = connection, workspace_id

    def history(self, evidence_id: str) -> list[EvidenceDecisionRecord]:
        rows = self.connection.execute('SELECT * FROM learning_applicability_decisions '
            'WHERE workspace_id=? AND evidence_id=? ORDER BY event_id,decision_revision',
            (self.workspace_id, evidence_id)).fetchall()
        heads: dict[str, tuple[int, str]] = {}
        output = []
        try:
            for row in rows:
                value = EvidenceDecisionRecord.model_validate(strict_json(row['record_json']))
                receipt, basis, request = value.receipt, value.basis, value.request
                matching = [event for event in basis.events if event.event_id == receipt.event_id]
                if (canonical_bytes(value).decode() != row['record_json'] or metadata_sha256(value) != row['record_sha256']
                        or not historical_session_belongs_to(self.connection, self.workspace_id, receipt.actor_session_id)
                        or value.workspace_id != self.workspace_id or basis.workspace_id != self.workspace_id
                        or receipt.evidence_id != evidence_id or basis.original_evidence.id != evidence_id
                        or receipt.event_id != row['event_id'] or request.event_id != receipt.event_id
                        or value.route != decision_route(evidence_id) or value.route != row['route']
                        or value.key != row['command_key'] or receipt.actor_session_id != row['actor_session_id']
                        or receipt.decided_at != row['created_at'] or receipt.decision_revision != row['decision_revision']
                        or receipt.decision_revision != heads.get(receipt.event_id, (0, ''))[0] + 1
                        or request.expected_decision_revision != receipt.decision_revision - 1
                        or request.decision != receipt.decision or request.reason != receipt.reason
                        or request.evidence_artifact_ids != [artifact.id for artifact in receipt.evidence_artifacts]
                        or len(matching) != 1 or matching[0].relevance != receipt.relevance
                        or matching[0].evidence_version != 'owner_frozen_v1' or matching[0].event_snapshot_sha256 is None
                        or receipt.original_evidence_sha256 != metadata_sha256(basis.original_evidence)
                        or receipt.current_basis_sha256 != metadata_sha256(basis)
                        or request.expected_current_basis_sha256 != receipt.current_basis_sha256
                        or receipt.question_ref != basis.question_ref or receipt.concept_ref != basis.concept_ref
                        or receipt.attempt_id != basis.attempt_id or receipt.grading_revision != basis.grading_revision
                        or receipt.request_sha256 != row['request_sha256']
                        or receipt.request_sha256 != request_digest(self.workspace_id, receipt.actor_session_id,
                                                                   evidence_id, value.key, request)
                        or receipt.receipt_sha256 != receipt_digest(receipt)):
                    raise invalid_decision()
                heads[receipt.event_id] = (receipt.decision_revision, receipt.receipt_sha256)
                output.append(value)
            stored = self.connection.execute('SELECT event_id,decision_revision,receipt_sha256 '
                'FROM learning_applicability_heads WHERE workspace_id=? AND evidence_id=?',
                (self.workspace_id, evidence_id)).fetchall()
            if heads != {row['event_id']: (row['decision_revision'], row['receipt_sha256']) for row in stored}:
                raise invalid_decision()
            return output
        except (ValueError, TypeError, KeyError, AttributeError):
            raise invalid_decision() from None

    def command(self, actor: str, evidence_id: str, key: str,
                history: list[EvidenceDecisionRecord]) -> EvidenceDecisionRecord | None:
        matches = [record for record in history if record.receipt.actor_session_id == actor and record.key == key]
        if len(matches) > 1:
            raise invalid_decision()
        return matches[0] if matches else None

    def append(self, value: EvidenceDecisionRecord) -> None:
        receipt = value.receipt
        self.connection.execute('INSERT INTO learning_applicability_decisions '
            '(workspace_id,evidence_id,event_id,decision_revision,actor_session_id,route,command_key,'
            'request_sha256,record_json,record_sha256,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (self.workspace_id, receipt.evidence_id, receipt.event_id, receipt.decision_revision,
             receipt.actor_session_id, value.route, value.key, receipt.request_sha256,
             canonical_bytes(value).decode(), metadata_sha256(value), receipt.decided_at))

        if receipt.decision_revision == 1:
            self.connection.execute('INSERT INTO learning_applicability_heads '
                '(workspace_id,evidence_id,event_id,decision_revision,receipt_sha256) VALUES(?,?,?,?,?)',
                (self.workspace_id, receipt.evidence_id, receipt.event_id, 1, receipt.receipt_sha256))
        else:
            changed = self.connection.execute('UPDATE learning_applicability_heads SET decision_revision=?,receipt_sha256=? '
                'WHERE workspace_id=? AND evidence_id=? AND event_id=? AND decision_revision=?',
                (receipt.decision_revision, receipt.receipt_sha256, self.workspace_id, receipt.evidence_id,
                 receipt.event_id, receipt.decision_revision - 1))
            if changed.rowcount != 1:
                raise invalid_decision()
