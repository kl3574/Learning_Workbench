"""Frozen numeric ledger observations, never numerical or publication approval.

Hashes bind bytes. A later Review owner must durably authenticate this complete
observation; reconstructing a self-consistent model does not prove it occurred.
"""
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from ..authoring_dto import AuthoringModel, NumericCheckView
from ..authoring_group_dto import AuthoringGroupNumericCheckView
from ..import_dto import JobSnapshot
from ..infrastructure.authoring_job_repository import checked
from ..infrastructure.authoring_numeric_repository import NumericRecord, NumericStart, NumericEnd
from ..infrastructure.authoring_group_numeric_repository import GroupNumericRecord
from .authoring_models import NumericJobInput
from .authoring_group_models import AuthoringGroupNumericJobInput
from .draft_candidate_models import DraftSourceKind


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


class NumericReviewCommand(AuthoringModel):
    actor_id: dm.Id
    route: str
    key: str
    request_json: str
    request_sha256: dm.Sha256
    ack_json: str
    ack_sha256: dm.Sha256
    job_revision: dm.Revision | None
    basis_revision: dm.Revision | None
    created_at: dm.UTC

    @model_validator(mode='after')
    def complete_bytes(self) -> Self:
        checked(self.request_json, self.request_sha256)
        checked(self.ack_json, self.ack_sha256)
        return self


class NumericReviewEvent(AuthoringModel):
    seq: dm.Revision
    type: str
    payload_json: str
    occurred_at: dm.UTC


NumericReviewRecord = Annotated[NumericRecord | GroupNumericRecord, Field(discriminator='version')]
NumericReviewInput = Annotated[NumericJobInput | AuthoringGroupNumericJobInput, Field(discriminator='version')]


class NumericReviewCheck(AuthoringModel):
    record: NumericReviewRecord
    view: NumericCheckView | AuthoringGroupNumericCheckView
    commands: Annotated[list[NumericReviewCommand], Field(min_length=1)]
    job: JobSnapshot | None
    input: NumericReviewInput | None
    events: list[NumericReviewEvent]
    start: NumericStart | None
    end: NumericEnd | None

    @model_validator(mode='after')
    def same_operation(self) -> Self:
        excluded = {'expired', 'job', 'job_revision', 'result'}
        if self.record.view.model_dump(exclude=excluded) != self.view.model_dump(exclude=excluded):
            raise ValueError('observation must preserve the complete original numeric operation')
        if self.job is None:
            if any(value is not None for value in [self.view.job, self.input, self.start, self.end]) or self.events:
                raise ValueError('unapproved observation cannot claim execution history')
        else:
            if (self.view.job is None or self.input is None or self.view.job.id != self.job.id
                    or self.view.job.status != self.job.status or self.view.job_revision != self.job.revision
                    or self.input.job_id != self.job.id or self.input.check_id != self.view.id
                    or self.input.operation_sha256 != self.view.operation_sha256
                    or self.input.candidate != self.view.candidate or self.input.plan != self.view.plan
                    or self.input.runtime != self.view.runtime or len(self.events) != self.job.revision):
                raise ValueError('observation must preserve the exact Job/input/event revision')
        if self.view.result != (self.end.result if self.end else None):
            raise ValueError('result must retain its complete original output bytes')
        return self


class ReviewNumericObservation(AuthoringModel):
    version: Literal['review-numeric-observation-v1']
    workspace_id: dm.Id
    source_kind: DraftSourceKind
    candidate: dm.DraftCandidate
    candidate_record_sha256: dm.Sha256 | None
    source_job_id: dm.Id | None
    provider_receipt_id: dm.Id | None
    coverage: Literal['authoring_numeric_ledger', 'no_numeric_owner_pipeline']
    observed_at: dm.UTC
    checks: Annotated[list[NumericReviewCheck], Field(max_length=100)]
    descriptor_sha256: dm.Sha256

    @model_validator(mode='after')
    def complete_observation(self) -> Self:
        import_owner = self.source_kind == 'import'
        identities = [self.candidate_record_sha256, self.source_job_id, self.provider_receipt_id]
        if import_owner:
            if self.coverage != 'no_numeric_owner_pipeline' or self.checks or any(x is not None for x in identities):
                raise ValueError('Import has no execution ledger; this does not establish absence of mathematics')
        elif self.coverage != 'authoring_numeric_ledger' or any(x is None for x in identities):
            raise ValueError('generated observation requires the actual original owner history')
        if len({check.view.id for check in self.checks}) != len(self.checks):
            raise ValueError('all original checks must be distinct in ledger order')
        for check in self.checks:
            group = isinstance(check.record, GroupNumericRecord)
            if (check.record.workspace_id != self.workspace_id
                    or check.view.candidate.model_dump() != self.candidate.model_dump()
                    or group != (self.source_kind == 'authoring_group')
                    or check.view.expired != (instant(check.view.expires_at) <= instant(self.observed_at))
                    or instant(check.view.created_at) > instant(self.observed_at)):
                raise ValueError('each observation must retain its exact owner/candidate and observation time')
            times = [command.created_at for command in check.commands] + [event.occurred_at for event in check.events]
            if check.start:
                times += [value for value in [check.start.admitted_at, check.start.actual_started_at] if value is not None]
            if check.end:
                times.append(check.end.result.finished_at)
            if any(instant(value) > instant(self.observed_at) for value in times):
                raise ValueError('observations cannot claim facts from their future')
        raw = self.model_dump(mode='json', exclude={'descriptor_sha256'})
        if sha256_bytes(canonical_bytes(raw)) != self.descriptor_sha256:
            raise ValueError('descriptor must cover all original ledger facts without selecting a preferred result')
        return self
