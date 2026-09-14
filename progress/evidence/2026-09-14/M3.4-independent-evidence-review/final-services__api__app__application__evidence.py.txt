"""Frozen prerequisites, atomic grade events and read-only current evidence."""

import base64
from collections.abc import Callable
import hashlib
import hmac
import re
import secrets
import sqlite3
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json

from ..infrastructure.database import Database, utc_now
from ..infrastructure.evidence_repository import EvidenceRepository, invalid_evidence
from ..infrastructure.learning_repository import LearningRepository
from ..infrastructure.security import guard_subject_access
from ..learning_dto import LearningProgress, PageEvidence
from .assessment_evidence_access import SubmissionWitness, completed_grade_keys, completed_grade_witness, submission_witness
from .eligibility import evidence_reason, finalize_eligibility, validate_prerequisites
from .eligibility_models import ItemPrerequisites, Skill
from .errors import ApiError
from .evidence_models import BoundItem, FrozenItem, FrozenPrerequisites, GradeBinding, SubmissionBasis
from .practice_help_access import HelpFacts, help_witnesses, instant, validate_help_witnesses
from .question_qualification import question_qualification_facts


def _transaction(connection: sqlite3.Connection) -> None:
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '提交资格与评分证据必须和原操作在同一事务中保存。')


def _items(connection: sqlite3.Connection, witness: SubmissionWitness, *, historical: bool) -> list[FrozenItem]:
    if ([pin.question_ref for pin in witness.private_pins] != witness.question_refs
            or [seen.question_ref for seen in witness.prior_seen.questions] != witness.question_refs):
        raise invalid_evidence()
    output = []
    for ref, pin, seen in zip(witness.question_refs, witness.private_pins, witness.prior_seen.questions, strict=True):
        facts = question_qualification_facts(connection, witness.workspace_id, ref)
        help = HelpFacts(witnesses=[], pre_submission_state='unknown', in_attempt_state='unknown') if historical else help_witnesses(
            connection, witness.workspace_id, ref, facts.exposure_group, witness.created_at, witness.submitted_at)
        prerequisites = ItemPrerequisites(question_ref=ref, required_concept_ids=facts.required_concept_ids,
            concept_refs=facts.concept_refs, skill=facts.skill, exposure_group=facts.exposure_group, max_score=facts.max_score,
            solution_revision=pin.solution_revision, solution_sha256=pin.sha256, answer_review_status=pin.review_status,
            prior_seen=seen.state, pre_submission_help_state=help.pre_submission_state,
            in_attempt_help_state=help.in_attempt_state, source_trusted=True)
        if prerequisites.mapping_complete != facts.mapping_valid:
            raise invalid_evidence()
        output.append(FrozenItem(prerequisites=validate_prerequisites(prerequisites), help=help))
    return output


def freeze_submission_prerequisites(connection: sqlite3.Connection, workspace_id: str, attempt_id: str) -> FrozenPrerequisites:
    _transaction(connection)
    witness = submission_witness(connection, workspace_id, attempt_id)
    value = FrozenPrerequisites(submission=witness, recorded_at=utc_now(), items=_items(connection, witness, historical=False))
    EvidenceRepository(connection, workspace_id).freeze(value)
    checked = checked_submission_basis(connection, workspace_id, attempt_id)
    if checked.prerequisites != value:
        raise invalid_evidence()
    return value


def checked_submission_basis(connection: sqlite3.Connection, workspace_id: str, attempt_id: str) -> SubmissionBasis:
    witness = submission_witness(connection, workspace_id, attempt_id)
    basis = EvidenceRepository(connection, workspace_id).basis(attempt_id)
    value = basis.prerequisites
    if value is None:
        return basis
    try:
        if value.submission != witness or instant(value.recorded_at) < instant(witness.submitted_at):
            raise ValueError('original submission mismatch')
        for frozen, pin, seen in zip(value.items, witness.private_pins, witness.prior_seen.questions, strict=True):
            item = validate_prerequisites(frozen.prerequisites)
            facts = question_qualification_facts(connection, workspace_id, item.question_ref)
            if (item.required_concept_ids != facts.required_concept_ids or item.concept_refs != facts.concept_refs
                    or item.skill != facts.skill or item.exposure_group != facts.exposure_group or item.max_score != facts.max_score
                    or item.mapping_complete != facts.mapping_valid or item.solution_revision != pin.solution_revision
                    or item.solution_sha256 != pin.sha256 or item.answer_review_status != pin.review_status
                    or item.prior_seen != seen.state or not item.source_trusted
                    or item.pre_submission_help_state != frozen.help.pre_submission_state
                    or item.in_attempt_help_state != frozen.help.in_attempt_state):
                raise ValueError('frozen metadata mismatch')
            validate_help_witnesses(connection, workspace_id, frozen.help.witnesses)
            for help in frozen.help.witnesses:
                if ((help.question_ref != item.question_ref and help.exposure_group != item.exposure_group)
                        or max(instant(help.occurred_at), instant(help.event_occurred_at)) > instant(witness.submitted_at)):
                    raise ValueError('help cutoff mismatch')
            if frozen.help.witnesses and item.pre_submission_help_state != 'present':
                raise ValueError('help existence mismatch')
        return basis
    except (ValueError, TypeError, KeyError):
        raise ApiError(409, 'EVIDENCE_PREREQUISITES_INVALID', '原提交的资格依据无法通过完整性校验。') from None


def _checked_binding(connection: sqlite3.Connection, workspace_id: str, attempt_id: str, revision: int) -> GradeBinding:
    source = completed_grade_witness(connection, workspace_id, attempt_id, revision)
    basis = checked_submission_basis(connection, workspace_id, attempt_id)
    value = EvidenceRepository(connection, workspace_id).binding(attempt_id, revision)
    if value is None:
        failed = connection.execute('SELECT 1 FROM learning_evidence_recovery_failures WHERE workspace_id=? AND attempt_id=? AND grading_revision=?', (workspace_id, attempt_id, revision)).fetchone()
        if failed:
            raise invalid_evidence()
        raise ApiError(503, 'EVIDENCE_RECOVERY_PENDING', '原成绩保留完整，学习证据历史正在恢复，请稍后重试。', True)
    try:
        if (value.result_sha256 != source.result_sha256 or value.finalized_at != source.result.finalized_at
                or value.qualification_basis != basis.basis or value.prerequisites_sha256 != basis.prerequisites_sha256
                or value.event.ref != source.assessment_ref or metadata_sha256(value.event) != value.event_sha256
                or len(value.items) != len(source.result.items)):
            raise ValueError('grade source mismatch')
        if LearningRepository(connection, workspace_id).read_learning_event(value.event.event_id) != value.event:
            raise ValueError('grade event mismatch')
        outbox = connection.execute('SELECT * FROM outbox WHERE id=?', (value.outbox_id,)).fetchone()
        payload = {'workspace_id': workspace_id, 'event_id': value.event.event_id, 'progress_revision': value.progress_revision}
        if outbox is None or outbox['event_type'] != 'learning.action_recorded' or outbox['payload_json'] != canonical_bytes(payload).decode():
            raise ValueError('grade learning outbox mismatch')
        witness = submission_witness(connection, workspace_id, attempt_id)
        originals = basis.prerequisites.items if basis.prerequisites is not None else _items(connection, witness, historical=True)
        for item, original, grade in zip(value.items, originals, source.result.items, strict=True):
            if item.prerequisites != original.prerequisites:
                raise ValueError('qualification facts changed')
            decision = finalize_eligibility(prerequisites=item.prerequisites, grade=grade,
                mode=witness.mode, basis=basis.basis)
            if decision != item.decision:
                raise ValueError('qualification decision mismatch')
            for concept, evidence in zip(decision.concept_refs, item.evidence, strict=True):
                expected = dm.Evidence(id=evidence.id, event_id=value.event.event_id, concept_id=concept.id, skill=decision.skill,
                    eligible=decision.eligible, reason=evidence_reason(decision), score=decision.normalized_score,
                    independence=decision.independence, freshness=decision.freshness)
                if evidence != expected:
                    raise ValueError('evidence projection mismatch')
        return value
    except (ValueError, TypeError, KeyError):
        raise invalid_evidence() from None


def record_grade_finalized(connection: sqlite3.Connection, workspace_id: str, attempt_id: str, grading_revision: int) -> GradeBinding:
    _transaction(connection)
    repository = EvidenceRepository(connection, workspace_id)
    if repository.binding(attempt_id, grading_revision) is not None:
        return _checked_binding(connection, workspace_id, attempt_id, grading_revision)
    source = completed_grade_witness(connection, workspace_id, attempt_id, grading_revision)
    witness = submission_witness(connection, workspace_id, attempt_id)
    basis = checked_submission_basis(connection, workspace_id, attempt_id)
    frozen = basis.prerequisites.items if basis.prerequisites is not None else _items(connection, witness, historical=True)
    now = utc_now()
    event = dm.LearningEvent(event_id=f'event_{uuid4().hex}', workspace_id=workspace_id, actor='server', origin='native',
        kind='grade_finalized', ref=source.assessment_ref, occurred_at=now, attempt_id=attempt_id)
    items = []
    for original, grade in zip(frozen, source.result.items, strict=True):
        decision = finalize_eligibility(prerequisites=original.prerequisites, grade=grade, mode=witness.mode, basis=basis.basis)
        evidence = [dm.Evidence(id=f'evidence_{uuid4().hex}', event_id=event.event_id, concept_id=concept.id,
            skill=decision.skill, eligible=decision.eligible, reason=evidence_reason(decision), score=decision.normalized_score,
            independence=decision.independence, freshness=decision.freshness) for concept in decision.concept_refs]
        items.append(BoundItem(prerequisites=original.prerequisites, decision=decision, evidence=evidence))
    learning = LearningRepository(connection, workspace_id)
    previous = learning.progress()
    updated = LearningProgress(revision=previous.revision + 1, readings=previous.readings, bookmarks=previous.bookmarks, route_steps=previous.route_steps)
    learning.append(event)
    learning.save(previous, updated, event.event_id)
    outbox = connection.execute("SELECT id FROM outbox WHERE event_type='learning.action_recorded' AND json_extract(payload_json,'$.event_id')=?", (event.event_id,)).fetchall()
    if len(outbox) != 1:
        raise invalid_evidence()
    value = GradeBinding(workspace_id=workspace_id, attempt_id=attempt_id, grading_revision=grading_revision,
        result_sha256=source.result_sha256, qualification_basis=basis.basis, prerequisites_sha256=basis.prerequisites_sha256,
        finalized_at=source.result.finalized_at, recorded_at=now, event=event, event_sha256=metadata_sha256(event),
        progress_revision=updated.revision, outbox_id=outbox[0]['id'], items=items)
    repository.insert(value)
    return _checked_binding(connection, workspace_id, attempt_id, grading_revision)


def history(connection: sqlite3.Connection, workspace_id: str, attempt_id: str):
    from ..assessment_dto import GradeHistoryEntry, GradeHistoryItem
    output = []
    for key in completed_grade_keys(connection, workspace_id, attempt_id):
        value = _checked_binding(connection, workspace_id, attempt_id, key.grading_revision)
        grade = completed_grade_witness(connection, workspace_id, attempt_id, key.grading_revision).result
        output.append(GradeHistoryEntry(grading_revision=key.grading_revision, grading_rules_version=grade.grading_rules_version,
            status=grade.status, finalized_at=grade.finalized_at, qualification_basis=value.qualification_basis,
            qualification_recorded_at=value.recorded_at, items=[GradeHistoryItem(question_ref=item.question_ref,
                score=item.score, max_score=item.max_score, status=item.status, concept_refs=bound.decision.concept_refs,
                eligible=bound.decision.eligible, reason_codes=bound.decision.reason_codes,
                evidence_ids=[evidence.id for evidence in bound.evidence], independence=bound.decision.independence,
                freshness=bound.decision.freshness) for item, bound in zip(grade.items, value.items, strict=True)]))
    return output


class EvidenceService:
    def __init__(self, database: Database):
        self.database = database
        self._cursor_key = secrets.token_bytes(32)

    def _cursor(self, context: str, watermark: int, position: str) -> str:
        data = canonical_bytes({'context': context, 'watermark': watermark, 'position': position})
        return base64.urlsafe_b64encode(hmac.new(self._cursor_key, data, hashlib.sha256).digest() + data).decode().rstrip('=')

    def _position(self, cursor: str | None, context: str, watermark: int) -> str | None:
        if cursor is None:
            return None
        try:
            if not 1 <= len(cursor) <= 1024 or re.fullmatch('[A-Za-z0-9_-]+', cursor) is None:
                raise ValueError('invalid cursor')
            decoded = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
            signature, data = decoded[:32], decoded[32:]
            if not hmac.compare_digest(signature, hmac.new(self._cursor_key, data, hashlib.sha256).digest()):
                raise ValueError('invalid cursor signature')
            value = strict_json(data)
            if (not isinstance(value, dict) or set(value) != {'context', 'watermark', 'position'}
                    or value['context'] != context or type(value['watermark']) is not int or not isinstance(value['position'], str)):
                raise ValueError('invalid cursor context')
            if value['watermark'] != watermark:
                raise ApiError(409, 'CURSOR_EXPIRED', '学习证据已更新，请从第一页重新读取。')
            return value['position']
        except (ValueError, TypeError, KeyError):
            raise ApiError(422, 'CURSOR_INVALID', '分页游标无效或不属于本次查询。') from None

    def page(self, workspace_id: str, concept_id: str | None = None, skill: Skill | None = None,
             cursor: str | None = None, limit: int = 20) -> PageEvidence:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ApiError(422, 'SCHEMA_INVALID', '分页数量必须为 1 到 100。')
        context = sha256_bytes(canonical_bytes({'workspace_id': workspace_id, 'concept_id': concept_id, 'skill': skill, 'limit': limit}))
        try:
            with self.database.transaction() as connection:
                guard_subject_access(connection, workspace_id)
                keys = completed_grade_keys(connection, workspace_id)
                # Validate every real persisted version, including a legacy version
                # without a binding. Reads do not hide incomplete history or repair it.
                latest = {}
                for key in keys:
                    latest[key.attempt_id] = _checked_binding(connection, workspace_id, key.attempt_id, key.grading_revision)
                watermark = connection.execute('SELECT COALESCE(MAX(sequence),0) FROM learning_grade_bindings WHERE workspace_id=?', (workspace_id,)).fetchone()[0]
                position = self._position(cursor, context, watermark)
                items = sorted((evidence for value in latest.values() for item in value.items for evidence in item.evidence
                    if (concept_id is None or evidence.concept_id == concept_id) and (skill is None or evidence.skill == skill)
                    and (position is None or evidence.id > position)), key=lambda item: item.id)
                page = items[:limit]
                return PageEvidence(items=page, next_cursor=self._cursor(context, watermark, page[-1].id) if len(items) > limit else None)
        except sqlite3.Error:
            raise ApiError(503, 'LEARNING_STORAGE_UNAVAILABLE', '学习证据存储暂不可用。', True) from None


class EvidenceRecovery:
    """One legacy grade per tick; diagnostics never starve grading or importing."""

    def __init__(self, database: Database, stopping: Callable[[], bool] = lambda: False):
        self.database = database
        self.stopping = stopping

    def run_once(self) -> bool:
        if self.stopping():
            return False
        with self.database.transaction() as connection:
            workspaces = [row[0] for row in connection.execute('SELECT DISTINCT workspace_id FROM learning_submission_bases ORDER BY workspace_id')]
            for workspace_id in workspaces:
                try:
                    keys = completed_grade_keys(connection, workspace_id)
                except ApiError as error:
                    if error.code == 'ASSESSMENT_ACTIVE':
                        continue
                    raise
                for key in keys:
                    if connection.execute('SELECT 1 FROM learning_grade_bindings WHERE workspace_id=? AND attempt_id=? AND grading_revision=?', (workspace_id, key.attempt_id, key.grading_revision)).fetchone():
                        continue
                    if connection.execute('SELECT 1 FROM learning_evidence_recovery_failures WHERE workspace_id=? AND attempt_id=? AND grading_revision=?', (workspace_id, key.attempt_id, key.grading_revision)).fetchone():
                        continue
                    if self.stopping():
                        return False
                    connection.execute('SAVEPOINT evidence_recovery_item')
                    try:
                        basis = checked_submission_basis(connection, workspace_id, key.attempt_id)
                        if basis.basis != 'history_not_frozen':
                            raise invalid_evidence()
                        record_grade_finalized(connection, workspace_id, key.attempt_id, key.grading_revision)
                        if self.stopping():
                            connection.execute('ROLLBACK TO evidence_recovery_item')
                            connection.execute('RELEASE evidence_recovery_item')
                            return False
                        connection.execute('RELEASE evidence_recovery_item')
                    except (ApiError, ValueError, TypeError, KeyError, sqlite3.IntegrityError):
                        connection.execute('ROLLBACK TO evidence_recovery_item')
                        connection.execute('RELEASE evidence_recovery_item')
                        connection.execute('INSERT INTO learning_evidence_recovery_failures(workspace_id,attempt_id,grading_revision,code,source_fingerprint,detected_at) VALUES(?,?,?,?,?,?)',
                            (workspace_id, key.attempt_id, key.grading_revision, 'EVIDENCE_HISTORY_INVALID', metadata_sha256(key), utc_now()))
                    return True
            return False
