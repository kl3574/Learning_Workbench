"""Learning-owned append-only evidence persistence and verified raw projections."""

import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, strict_json

from ..application.errors import ApiError
from ..application.evidence_models import FrozenPrerequisites, GradeBinding, SubmissionBasis


def invalid_evidence() -> ApiError:
    return ApiError(409, 'EVIDENCE_HISTORY_INVALID', '学习证据历史完整性校验失败，未返回不完整成绩或资格。')


class EvidenceRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def basis(self, attempt_id: str) -> SubmissionBasis:
        row = self.connection.execute('SELECT * FROM learning_submission_bases WHERE workspace_id=? AND attempt_id=?', (self.workspace_id, attempt_id)).fetchone()
        try:
            if row is None or row['rule_version'] != 'eligibility-v1':
                raise ValueError('missing submission basis')
            prerequisites = None if row['prerequisites_json'] is None else FrozenPrerequisites.model_validate(strict_json(row['prerequisites_json']))
            if prerequisites is not None and (canonical_bytes(prerequisites).decode() != row['prerequisites_json']
                    or metadata_sha256(prerequisites) != row['prerequisites_sha256']):
                raise ValueError('prerequisite hash mismatch')
            if row['legacy_migration'] != ('0007_learning_evidence' if row['basis'] == 'history_not_frozen' else None):
                raise ValueError('unclassified history')
            return SubmissionBasis(workspace_id=self.workspace_id, attempt_id=attempt_id, basis=row['basis'],
                recorded_at=row['recorded_at'], prerequisites=prerequisites, prerequisites_sha256=row['prerequisites_sha256'])
        except (ValueError, TypeError, KeyError):
            raise ApiError(409, 'EVIDENCE_PREREQUISITES_INVALID', '原提交缺少有效资格依据，未将新提交冒充历史记录。') from None

    def freeze(self, value: FrozenPrerequisites) -> None:
        self.connection.execute('INSERT INTO learning_submission_bases(attempt_id,workspace_id,basis,rule_version,prerequisites_json,prerequisites_sha256,recorded_at) VALUES(?,?,?,?,?,?,?)',
            (value.submission.attempt_id, self.workspace_id, 'submission_frozen', value.version,
             canonical_bytes(value).decode(), metadata_sha256(value), value.recorded_at))

    def binding(self, attempt_id: str, revision: int) -> GradeBinding | None:
        row = self.connection.execute('SELECT * FROM learning_grade_bindings WHERE workspace_id=? AND attempt_id=? AND grading_revision=?', (self.workspace_id, attempt_id, revision)).fetchone()
        if row is None:
            return None
        try:
            value = GradeBinding.model_validate(strict_json(row['binding_json']))
            if (value.workspace_id != self.workspace_id or value.attempt_id != attempt_id or value.grading_revision != revision
                    or value.result_sha256 != row['result_sha256'] or value.qualification_basis != row['basis']
                    or value.prerequisites_sha256 != row['prerequisites_sha256'] or value.version != row['qualification_version']
                    or value.event.event_id != row['event_id'] or value.recorded_at != row['recorded_at']
                    or metadata_sha256(value) != row['binding_sha256'] or canonical_bytes(value).decode() != row['binding_json']):
                raise ValueError('binding hash mismatch')
            expected_ids = {evidence.id for item in value.items for evidence in item.evidence}
            refs = self.connection.execute('SELECT r.*,e.event_id,e.evidence_json,e.freshness,e.workspace_id AS stored_workspace,e.attempt_id AS stored_attempt,e.grading_revision AS stored_revision FROM learning_evidence_refs r JOIN evidence e ON e.id=r.evidence_id WHERE r.workspace_id=? AND r.attempt_id=? AND r.grading_revision=?', (self.workspace_id, attempt_id, revision)).fetchall()
            if {item['evidence_id'] for item in refs} != expected_ids:
                raise ValueError('incomplete evidence binding')
            rows = {item['evidence_id']: item for item in refs}
            for item in value.items:
                if len(item.evidence) != len(item.decision.concept_refs):
                    raise ValueError('incomplete concept evidence')
                for concept, evidence in zip(item.decision.concept_refs, item.evidence, strict=True):
                    source = rows[evidence.id]
                    actual = dm.Evidence.model_validate(strict_json(source['evidence_json']))
                    if (actual != evidence or canonical_bytes(actual).decode() != source['evidence_json']
                            or source['evidence_sha256'] != metadata_sha256(actual)
                            or source['stored_workspace'] != self.workspace_id or source['stored_attempt'] != attempt_id
                            or source['stored_revision'] != revision or source['event_id'] != value.event.event_id
                            or source['freshness'] != evidence.freshness or source['skill'] != evidence.skill
                            or (source['question_id'], source['question_revision'], source['question_sha256']) != (item.decision.question_ref.id, item.decision.question_ref.revision, item.decision.question_ref.sha256)
                            or (source['concept_id'], source['concept_revision'], source['concept_sha256']) != (concept.id, concept.revision, concept.sha256)):
                        raise ValueError('evidence exact reference mismatch')
            # A row added directly to the original table cannot hide from the association.
            actual_ids = {entry[0] for entry in self.connection.execute('SELECT id FROM evidence WHERE workspace_id=? AND attempt_id=? AND grading_revision=?', (self.workspace_id, attempt_id, revision))}
            if actual_ids != expected_ids:
                raise ValueError('unbound evidence row')
            return value
        except (ValueError, TypeError, KeyError):
            raise invalid_evidence() from None

    def insert(self, value: GradeBinding) -> None:
        self.connection.execute('INSERT INTO learning_grade_bindings(workspace_id,attempt_id,grading_revision,event_id,result_sha256,basis,prerequisites_sha256,qualification_version,binding_json,binding_sha256,recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (self.workspace_id, value.attempt_id, value.grading_revision, value.event.event_id, value.result_sha256,
             value.qualification_basis, value.prerequisites_sha256, value.version, canonical_bytes(value).decode(), metadata_sha256(value), value.recorded_at))
        for item in value.items:
            for concept, evidence in zip(item.decision.concept_refs, item.evidence, strict=True):
                self.connection.execute('INSERT INTO evidence(id,workspace_id,event_id,attempt_id,grading_revision,evidence_json,freshness) VALUES(?,?,?,?,?,?,?)',
                    (evidence.id, self.workspace_id, value.event.event_id, value.attempt_id, value.grading_revision, canonical_bytes(evidence).decode(), evidence.freshness))
                self.connection.execute('INSERT INTO learning_evidence_refs(evidence_id,workspace_id,attempt_id,grading_revision,question_id,question_revision,question_sha256,concept_id,concept_revision,concept_sha256,skill,evidence_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                    (evidence.id, self.workspace_id, value.attempt_id, value.grading_revision, item.decision.question_ref.id,
                     item.decision.question_ref.revision, item.decision.question_ref.sha256, concept.id, concept.revision,
                     concept.sha256, evidence.skill, metadata_sha256(evidence)))
