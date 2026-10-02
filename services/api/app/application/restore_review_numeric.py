"""Restore-specific complete ledger observations; no Provider/generation fiction."""
from typing import Annotated, Literal, Self
from pydantic import Field, model_validator
from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256, canonical_bytes, sha256_bytes
from ..authoring_dto import AuthoringModel
from ..restore_numeric_dto import RestoreNumericMaterialView, RestoreNumericCheckView
from ..import_dto import JobSnapshot
from ..infrastructure.restore_numeric_repository import RestoreNumericRepository, RestoreNumericHistory, integrity, model
from ..infrastructure.content_restore_repository import RestoreRepository
from ..infrastructure.authoring_numeric_repository import NumericStart, NumericEnd
from ..infrastructure.database import utc_now
from .restore_numeric_models import RestoreNumericRecord, RestoreNumericJobInput, RestoreNumericCommand, RestoreNumericEvent, event_payload


class RestoreNumericJobEvent(AuthoringModel):
    seq: dm.Revision
    type: str
    payload_json: str
    occurred_at: dm.UTC


class RestoreNumericCheckObservation(AuthoringModel):
    record: RestoreNumericRecord
    view: RestoreNumericCheckView
    commands: Annotated[list[RestoreNumericCommand], Field(min_length=1)]
    job: JobSnapshot | None
    input: RestoreNumericJobInput | None
    events: list[RestoreNumericJobEvent]
    start: NumericStart | None
    end: NumericEnd | None

    @model_validator(mode='after')
    def identities(self) -> Self:
        excluded = {'expired', 'job', 'job_revision', 'result'}
        if self.record.view.model_dump(exclude=excluded) != self.view.model_dump(exclude=excluded):
            raise ValueError('numeric observation must preserve the entire original operation')
        if self.job is None:
            if any(x is not None for x in (self.view.job, self.input, self.start, self.end)) or self.events:
                raise ValueError('unapproved observation cannot claim execution')
        elif (self.input is None or self.view.job is None or self.view.job.id != self.job.id
                or self.view.job.status != self.job.status or self.view.job_revision != self.job.revision
                or len(self.events) != self.job.revision or self.input.job_id != self.job.id
                or self.input.check_id != self.view.id or self.input.operation_sha256 != self.view.operation_sha256
                or self.input.candidate.model_dump() != self.view.candidate.model_dump() or self.input.plan != self.view.plan
                or self.input.runtime != self.view.runtime or self.input.numeric_material_sha256 != self.view.numeric_material_sha256):
            raise ValueError('observation must preserve exact job/input/events')
        if self.view.result != (self.end.result if self.end else None):
            raise ValueError('result must retain complete original output bytes')
        return self


class RestoreReviewNumericObservation(AuthoringModel):
    version: Literal['restore-review-numeric-observation-v1']
    workspace_id: dm.Id
    source_kind: Literal['authoring_restore']
    candidate: dm.DraftCandidate
    restore_record_sha256: dm.Sha256
    numeric_material: RestoreNumericMaterialView | None
    observed_at: dm.UTC
    ledger_events: list[RestoreNumericEvent]
    checks: Annotated[list[RestoreNumericCheckObservation], Field(max_length=100)]
    descriptor_sha256: dm.Sha256

    @model_validator(mode='after')
    def complete(self) -> Self:
        if self.descriptor_sha256 != sha256_bytes(canonical_bytes(self.model_dump(mode='json', exclude={'descriptor_sha256'}))):
            raise ValueError('descriptor must bind all original Restore facts')
        if self.numeric_material is None:
            if self.ledger_events or self.checks:
                raise ValueError('unbound observation cannot claim numeric facts')
        elif (self.numeric_material.candidate.model_dump() != self.candidate.model_dump()
              or self.numeric_material.restore_record_sha256 != self.restore_record_sha256):
            raise ValueError('material must belong to the exact Restore record')
        if len({check.view.id for check in self.checks}) != len(self.checks):
            raise ValueError('each check must be distinct in original ledger order')
        for check in self.checks:
            if (check.record.workspace_id != self.workspace_id or check.view.candidate.model_dump() != self.candidate.model_dump()
                    or self.numeric_material is None or check.view.numeric_material_sha256 != self.numeric_material.numeric_material_sha256
                    or check.view.expired != (check.view.expires_at <= self.observed_at)
                    or check.view.created_at > self.observed_at):
                raise ValueError('Restore check observation identity/time mismatch')
        if any(event.workspace_id != self.workspace_id or event.draft_id != self.candidate.draft_id
               or event.recorded_at > self.observed_at for event in self.ledger_events):
            raise ValueError('observation cannot claim foreign or future ledger facts')
        return self


def read_observation(repo: RestoreNumericRepository, candidate, original: RestoreReviewNumericObservation | None = None):
    record = RestoreRepository(repo.conn, repo.workspace_id).load(candidate.draft_id)
    if record.candidate != candidate:
        raise integrity()
    current = repo.history(candidate.draft_id)
    history = current
    if original is not None:
        if current.events[:len(original.ledger_events)] != original.ledger_events:
            raise integrity()
        if original.numeric_material is not None and current.material != original.numeric_material:
            raise integrity()
        history = RestoreNumericHistory(original.numeric_material)
        for event in original.ledger_events:
            identifier, value = event.check_id, event_payload(event)
            if event.kind in {'preview', 'decision'}:
                history.records[identifier] = model(RestoreNumericRecord, value)
                history.commands.setdefault(identifier, [])
            elif event.kind in {'admission', 'start'}:
                history.starts[identifier] = model(NumericStart, value)
            elif event.kind == 'terminal':
                history.ends[identifier] = model(NumericEnd, value)
            else:
                history.commands[identifier].append(model(RestoreNumericCommand, value))
            history.events.append(event)
    observed_at = original.observed_at if original else utc_now()
    checks = []
    for index, (identifier, value) in enumerate(history.records.items()):
        job = job_input = None
        events = []
        revision = None
        if value.view.job is not None:
            if original is not None:
                if index >= len(original.checks) or original.checks[index].job is None:
                    raise integrity()
                previous_job = original.checks[index].job
                assert previous_job is not None
                revision = previous_job.revision
            job = repo.jobs.snapshot(value.view.job.id, revision)
            job_input = repo.job_input(job.id)
            events = [RestoreNumericJobEvent(seq=e.seq, type=e.type, payload_json=e.payload_json, occurred_at=e.occurred_at)
                      for e in repo.jobs.event_prefix(job.id, job.revision)]
        checks.append(RestoreNumericCheckObservation(record=value,
            view=repo.project(history, identifier, observed_at, revision), commands=history.commands[identifier],
            job=job, input=job_input, events=events, start=history.starts.get(identifier), end=history.ends.get(identifier)))
    raw = dict(version='restore-review-numeric-observation-v1', workspace_id=repo.workspace_id,
        source_kind='authoring_restore', candidate=candidate.model_dump(mode='json'), restore_record_sha256=metadata_sha256(record),
        numeric_material=history.material.model_dump(mode='json') if history.material else None, observed_at=observed_at,
        ledger_events=[event.model_dump(mode='json') for event in history.events], checks=[check.model_dump(mode='json') for check in checks])
    result = RestoreReviewNumericObservation(**raw, descriptor_sha256=sha256_bytes(canonical_bytes(raw)))
    if original is not None and result != original:
        raise integrity()
    return result


def same_endpoint(left: RestoreReviewNumericObservation, right: RestoreReviewNumericObservation) -> bool:
    def facts(value):
        raw = value.model_dump(mode='json', exclude={'observed_at', 'descriptor_sha256'})
        for check in raw['checks']:
            check['view'].pop('expired')
        return raw
    return facts(left) == facts(right)
