"""Practice-owned, receipt-validated help metadata; no private help text crosses this port."""

from datetime import datetime
import sqlite3
from typing import Literal

from pydantic import Field, TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json

from ..infrastructure.practice_repository import PracticeRepository, assignment_bytes
from .assessment_content import AssessmentContent
from .errors import ApiError
from .learning import read_learning_event


class HelpWitness(dm.StrictModel):
    exposure_id: dm.Id
    workspace_id: dm.Id
    session_id: dm.Id
    question_ref: dm.ContentRef
    exposure_group: dm.Id
    kind: Literal['hint', 'solution']
    level: int = Field(ge=0)
    occurred_at: dm.UTC
    event_id: dm.Id
    event_occurred_at: dm.UTC
    event_sha256: dm.Sha256
    exposure_sha256: dm.Sha256
    receipt_sha256: dm.Sha256
    assignment_sha256: dm.Sha256
    help_sha256: dm.Sha256


class HelpFacts(dm.StrictModel):
    witnesses: list[HelpWitness]
    pre_submission_state: Literal['none', 'present', 'unknown']
    in_attempt_state: Literal['none', 'present', 'unknown']


def instant(value: str) -> datetime:
    TypeAdapter(dm.UTC).validate_python(value)
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _witness(connection: sqlite3.Connection, workspace_id: str, exposure_id: str) -> HelpWitness:
    row = connection.execute('SELECT * FROM exposures WHERE workspace_id=? AND id=?', (workspace_id, exposure_id)).fetchone()
    if row is None:
        raise ValueError('missing help exposure')
    ref = dm.ContentRef.model_validate(strict_json(row['question_ref_json']))
    question = AssessmentContent(connection, workspace_id).exact(ref)
    if not isinstance(question, dm.QuestionPublic) or question.exposure_group != row['exposure_group'] or row['kind'] not in {'hint', 'solution'}:
        raise ValueError('help question mismatch')
    event = read_learning_event(connection, workspace_id, row['event_id'])
    if (event.actor != 'server' or event.origin != 'native' or event.ref != ref or event.attempt_id is None
            or event.kind != ('hint_revealed' if row['kind'] == 'hint' else 'solution_revealed')):
        raise ValueError('help event mismatch')
    repository = PracticeRepository(connection, workspace_id)
    record = repository.load(event.attempt_id)
    if ref not in record.question_refs:
        raise ValueError('help assignment mismatch')
    receipt = connection.execute('SELECT * FROM practice_exposures WHERE exposure_id=? AND session_id=? AND question_id=? AND kind=?',
        (exposure_id, record.id, ref.id, row['kind'])).fetchone()
    if receipt is None:
        from ..infrastructure.practice_model_help_repository import PracticeModelHelpRepository
        model_help = PracticeModelHelpRepository(connection, workspace_id).by_exposure(exposure_id)
        if (model_help is None or row['kind'] != 'hint' or model_help.event_id != event.event_id
                or model_help.answer.practice.session_id != record.id
                or model_help.answer.practice.question_ref != ref):
            raise ValueError('missing help receipt')
        # Zero means no rules hint level; the immutable receipt explicitly says model.
        level, receipt_hash, help_hash = 0, metadata_sha256(model_help), model_help.answer.text_sha256
    else:
        help_result = repository.help(record, ref.id, row['kind'], receipt['level'])
        if help_result is None or help_result[0] != event.event_id:
            raise ValueError('help receipt event mismatch')
        level = receipt['level']
        receipt_hash = sha256_bytes(canonical_bytes({key: receipt[key] for key in receipt.keys() if key != 'help_json'}))
        help_hash = metadata_sha256(help_result[1])
    instant(row['occurred_at'])
    return HelpWitness(exposure_id=exposure_id, workspace_id=workspace_id, session_id=record.id,
        question_ref=ref, exposure_group=question.exposure_group, kind=row['kind'], level=level,
        occurred_at=row['occurred_at'], event_id=event.event_id, event_occurred_at=event.occurred_at,
        event_sha256=metadata_sha256(event), exposure_sha256=sha256_bytes(canonical_bytes(dict(row))),
        receipt_sha256=receipt_hash,
        assignment_sha256=sha256_bytes(assignment_bytes(record.practice_ref, record.question_refs, record.solution_refs)),
        help_sha256=help_hash)


def help_witnesses(connection: sqlite3.Connection, workspace_id: str, question_ref: dm.ContentRef,
                   exposure_group: str, created_at: str, submitted_at: str) -> HelpFacts:
    """Freeze the transaction-visible set; invalid relevant sources stay unknown."""
    start, cutoff = instant(created_at), instant(submitted_at)
    if cutoff < start:
        raise ApiError(409, 'EVIDENCE_PREREQUISITES_INVALID', '证据依据的时间顺序无法验证。')
    witnesses = []
    unknown = False
    for row in connection.execute('SELECT * FROM exposures WHERE workspace_id=? AND kind IN (\'hint\',\'solution\',\'imported_claim\') ORDER BY id', (workspace_id,)):
        try:
            value = _witness(connection, workspace_id, row['id'])
            # Relevance also comes from a validated binding. A changed exposure
            # ref/group must not hide the original target's native help event.
            if value.question_ref != question_ref and value.exposure_group != exposure_group:
                continue
            # Check both independently recorded server clocks and the receipt
            # before excluding a later fact. A corrupt exposure timestamp must
            # not hide its actual pre-submit event and become 'no help'.
            clocks = (instant(value.occurred_at), instant(value.event_occurred_at))
            if min(clocks) > cutoff:
                continue
            if max(clocks) > cutoff:
                unknown = True
                continue
            witnesses.append(value)
        except (ApiError, ValueError, TypeError, KeyError):
            unknown = True
    in_attempt = [value for value in witnesses if min(instant(value.occurred_at), instant(value.event_occurred_at)) >= start]
    straddles = any(min(instant(value.occurred_at), instant(value.event_occurred_at)) < start <= max(instant(value.occurred_at), instant(value.event_occurred_at)) for value in witnesses)
    return HelpFacts(witnesses=witnesses,
        pre_submission_state='present' if witnesses else 'unknown' if unknown else 'none',
        in_attempt_state='present' if in_attempt else 'unknown' if unknown or straddles else 'none')


def validate_help_witnesses(connection: sqlite3.Connection, workspace_id: str, values: list[HelpWitness]) -> None:
    """Revalidate original immutable receipts without adding post-submit help."""
    try:
        for value in values:
            if value.workspace_id != workspace_id or _witness(connection, workspace_id, value.exposure_id) != value:
                raise ValueError('frozen help mismatch')
        if len({value.exposure_id for value in values}) != len(values):
            raise ValueError('duplicate frozen help')
    except (ApiError, ValueError, TypeError, KeyError):
        raise ApiError(409, 'EVIDENCE_PREREQUISITES_INVALID', '原提交关联的帮助依据完整性校验失败。') from None
