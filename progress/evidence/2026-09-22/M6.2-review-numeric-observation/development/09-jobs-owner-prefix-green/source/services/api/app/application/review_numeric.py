"""Owner-backed numeric observations and exact historical prefix verification.

Read methods never prepare a runtime or execute work. The future Review owner
must store the descriptor with its own authenticated history; this port does
not make caller-supplied self-consistent JSON an authentic past observation.
"""
import sqlite3
from typing import Literal, Protocol

from pydantic import ValidationError
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from ..authoring_dto import NumericCheckView
from ..authoring_group_dto import AuthoringGroupNumericCheckView
from ..infrastructure.authoring_job_repository import integrity
from ..infrastructure.authoring_numeric_repository import NumericRepository, NumericStart
from ..infrastructure.authoring_group_numeric_repository import GroupNumericRepository, GroupNumericRecord
from ..infrastructure.database import utc_now
from ..infrastructure.security import SessionIdentity, author_execution_identity
from .authoring import AuthoringService
from .authoring_group import AuthoringGroupService
from .authoring_context import AuthoringContext
from .draft_candidates import DraftCandidates
from .errors import ApiError
from .review_material_models import SingleReviewMaterial, GroupReviewMaterial
from .review_numeric_models import (
    NumericReviewCheck, NumericReviewCommand, NumericReviewEvent, ReviewNumericObservation, instant,
)

Repository = NumericRepository | GroupNumericRepository


def read_numeric_history(repo: Repository, identifier: str, observed_at: str,
                         original: NumericReviewCheck | None = None) -> NumericReviewCheck:
    """Called only by a real numeric repository after its complete ledger checks.

Commands use SQLite insertion order; Jobs use their durable seq. A caller may
already hold an older SQLite snapshot, so wall-clock timestamps cannot select
the prefix. Explicit frozen revision/prefix facts are rechecked instead.
    """
    record = repo.load(identifier)
    rows = repo.conn.execute('SELECT * FROM authoring_commands WHERE workspace_id=? AND owner_id=? ORDER BY rowid',
                             (repo.workspace_id, identifier)).fetchall()
    commands = [NumericReviewCommand.model_validate({key: row[key] for key in NumericReviewCommand.model_fields})
                for row in rows]
    if original is not None:
        count = len(original.commands)
        if commands[:count] != original.commands:
            raise integrity()
        commands = commands[:count]
    # Approval has just one durable decision. Its original preview ACK remains
    # independently checked even after this mutable record advances to r2.
    if not any(command.route.endswith('/decision') for command in commands):
        raw = record.model_dump(mode='json')
        raw['decision_actor_id'] = None
        raw['view'].update(revision=1, decision='pending', job=None, job_revision=None, result=None, expired=False)
        record = type(record).model_validate(raw)
    job = value = start = end = None
    events: list[NumericReviewEvent] = []
    raw_view = record.view.model_dump(mode='json')
    raw_view['expired'] = instant(record.view.expires_at) <= instant(observed_at)
    if record.view.job is not None:
        job_id = record.view.job.id
        value = repo.job_input(job_id)
        current = repo.jobs.snapshot(job_id)
        revision = original.job.revision if original is not None and original.job is not None else current.revision
        job = repo.jobs.snapshot(job_id, revision)
        events = [NumericReviewEvent(seq=event.seq, type=event.type, payload_json=event.payload_json,
                                    occurred_at=event.occurred_at) for event in repo.jobs.event_prefix(job_id, revision)]
        start, end = repo.execution_state(job_id)
        if original is not None:
            if original.start is None:
                start = None
            else:
                if start is None:
                    raise integrity()
                # mark_started fills the one allowed field without changing the
                # launch permission; the original absent process fact stays absent.
                raw_start = start.model_dump(mode='json')
                if original.start.actual_started_at is None:
                    raw_start['actual_started_at'] = None
                start = NumericStart.model_validate(raw_start)
            if original.end is None:
                end = None
        raw_view.update(job={'id': job.id, 'status': job.status}, job_revision=job.revision,
                        result=end.result.model_dump(mode='json') if end else None)
    view = (AuthoringGroupNumericCheckView.model_validate(raw_view) if isinstance(record, GroupNumericRecord)
            else NumericCheckView.model_validate(raw_view))
    result = NumericReviewCheck(record=record, view=view, commands=commands, job=job, input=value,
                               events=events, start=start, end=end)
    if original is not None and result != original:
        raise integrity()
    return result


def _checked_observation(value: ReviewNumericObservation) -> ReviewNumericObservation:
    try:
        return ReviewNumericObservation.model_validate(value.model_dump(mode='python'))
    except (ValidationError, ValueError, TypeError, AttributeError):
        raise integrity() from None


def _observation(raw: dict) -> ReviewNumericObservation:
    raw['descriptor_sha256'] = sha256_bytes(canonical_bytes(raw))
    return ReviewNumericObservation.model_validate(raw)


def read_owner_numeric(connection: sqlite3.Connection, identity: SessionIdentity, candidate: dm.DraftCandidate,
                       repo: Repository, authoring: AuthoringService | AuthoringGroupService | None,
                       original: ReviewNumericObservation | None = None) -> ReviewNumericObservation:
    AuthoringContext.check_access(connection, identity)
    current = author_execution_identity(connection, identity.workspace_id, identity.id)
    AuthoringContext.check_access(connection, current)
    if authoring is None:
        raise ApiError(503, 'AUTHORING_OUTPUT_UNAVAILABLE', '原生成结果当前无法核验。')
    material = authoring.read_review_material(connection, current, candidate)
    if not isinstance(material.payload, (SingleReviewMaterial, GroupReviewMaterial)):
        raise integrity()
    source_kind = 'authoring_single' if isinstance(repo, NumericRepository) else 'authoring_group'
    if material.source_kind != source_kind:
        raise integrity()
    observed_at = utc_now() if original is None else original.observed_at
    identifiers = repo.candidate_checks(candidate.draft_id)
    if original is not None:
        previous = [item.view.id for item in original.checks]
        if identifiers[:len(previous)] != previous:
            raise integrity()
        identifiers = previous
    checks = [repo.review_check(identifier, observed_at, original.checks[index] if original else None)
              for index, identifier in enumerate(identifiers)]
    record = material.payload.record
    result = _observation(dict(version='review-numeric-observation-v1', workspace_id=current.workspace_id,
        source_kind=source_kind, candidate=material.candidate.model_dump(mode='json'),
        candidate_record_sha256=metadata_sha256(record), source_job_id=record.source_job_id,
        provider_receipt_id=record.provider_receipt_id, coverage='authoring_numeric_ledger', observed_at=observed_at,
        checks=[item.model_dump(mode='json') for item in checks]))
    if original is not None and result != original:
        raise integrity()
    return result


def verify_owner_numeric(connection: sqlite3.Connection, identity: SessionIdentity, original: ReviewNumericObservation,
                         repo: Repository, authoring: AuthoringService | AuthoringGroupService | None) -> None:
    original = _checked_observation(original)
    if original.workspace_id != identity.workspace_id:
        raise ApiError(404, 'NUMERIC_CHECK_MISSING', '数值观察不存在或不可访问。')
    read_owner_numeric(connection, identity, original.candidate, repo, authoring, original)


class ReviewNumericOwner(Protocol):
    def read_review_numeric(self, connection: sqlite3.Connection, identity: SessionIdentity,
                            candidate: dm.DraftCandidate) -> ReviewNumericObservation: ...

    def verify_review_numeric(self, connection: sqlite3.Connection, identity: SessionIdentity,
                              observation: ReviewNumericObservation) -> None: ...


class ReviewNumeric:
    """Catalog-routed read facade. Import absence is a pipeline fact, not N/A."""
    def __init__(self, candidates: DraftCandidates,
                 owners: dict[Literal['authoring_single', 'authoring_group'], ReviewNumericOwner]):
        self.candidates, self.owners = candidates, dict(owners)

    def read_review_numeric(self, connection: sqlite3.Connection, identity: SessionIdentity,
                            draft_id: str, expected_revision: int) -> ReviewNumericObservation:
        resolved = self.candidates.lookup(connection, identity, draft_id, expected_revision)
        if resolved.source_kind == 'import':
            return _observation(dict(version='review-numeric-observation-v1', workspace_id=resolved.workspace_id,
                source_kind='import', candidate=resolved.candidate.model_dump(mode='json'), candidate_record_sha256=None,
                source_job_id=None, provider_receipt_id=None, coverage='no_numeric_owner_pipeline', observed_at=utc_now(), checks=[]))
        owner = self.owners.get(resolved.source_kind)
        if owner is None:
            raise ApiError(503, 'NUMERIC_OWNER_UNAVAILABLE', '数值观察所属服务当前不可用。')
        result = _checked_observation(owner.read_review_numeric(connection, identity, resolved.candidate))
        if (result.workspace_id != resolved.workspace_id or result.source_kind != resolved.source_kind
                or result.candidate != resolved.candidate):
            raise integrity()
        return result

    def verify_review_numeric(self, connection: sqlite3.Connection, identity: SessionIdentity,
                              observation: ReviewNumericObservation) -> None:
        original = _checked_observation(observation)
        resolved = self.candidates.lookup(connection, identity, original.candidate.draft_id, original.candidate.draft_revision)
        if (original.workspace_id != resolved.workspace_id or original.source_kind != resolved.source_kind
                or original.candidate != resolved.candidate):
            raise integrity()
        if resolved.source_kind != 'import':
            owner = self.owners.get(resolved.source_kind)
            if owner is None:
                raise ApiError(503, 'NUMERIC_OWNER_UNAVAILABLE', '数值观察所属服务当前不可用。')
            owner.verify_review_numeric(connection, identity, original)
