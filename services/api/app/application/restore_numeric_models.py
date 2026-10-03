"""Restore-owned numeric identities. No generation or historical approval alias."""
import math
import re
from typing import Literal, Self
from pydantic import model_validator
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from ..authoring_dto import AuthoringModel, NumericPlan, NumericRuntimeProfile
from ..restore_numeric_dto import RestoreNumericMaterialWrite, RestoreNumericMaterialView, RestoreNumericCheckView
from ..infrastructure.authoring_job_repository import checked
from .content_restore_models import RestoreRecord
from .authoring_numeric import NumericError, validate_plan
from .errors import ApiError


def material_binding(workspace: str, value: RestoreNumericMaterialView) -> str:
    return sha256_bytes(canonical_bytes({'version': 'restore-numeric-binding-v1', 'workspace_id': workspace,
                           **value.model_dump(mode='json', exclude={'numeric_material_sha256'})}))


def bind_material(record: RestoreRecord, material: RestoreNumericMaterialWrite) -> RestoreNumericMaterialView:
    """Literal Unicode codepoints only; no semantic formula/units approval."""
    validate_plan(material.plan.model_dump(mode='json'))
    body = record.payload.source.body_markdown
    def span(value):
        if value.end_codepoint > len(body):
            raise ApiError(422, 'SCHEMA_INVALID', '数值原文定位超过原正文范围。')
        if body[value.start_codepoint:value.end_codepoint] != value.quote:
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
    def number(value, expected):
        span(value)
        if re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', value.quote) is None:
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
        actual = float(value.quote)
        if not math.isfinite(actual) or actual != float(expected):
            raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
    variables = {item.name: item.value for item in material.plan.variables}
    assertions = {item.id: item for item in material.plan.assertions}
    if ({item.variable_name for item in material.variable_bindings} != set(variables)
            or len(material.variable_bindings) != len(variables)
            or {item.assertion_id for item in material.assertion_bindings} != set(assertions)
            or len(material.assertion_bindings) != len(assertions)):
        raise NumericError('NUMERIC_PLAN_UNSUPPORTED')
    for binding in material.variable_bindings:
        number(binding.value_source, variables[binding.variable_name])
    for assertion_binding in material.assertion_bindings:
        span(assertion_binding.expression_source)
        number(assertion_binding.expected_source, assertions[assertion_binding.assertion_id].expected)
    raw = dict(owner='authoring_restore', candidate=record.candidate.model_dump(mode='json'),
        restore_record_sha256=metadata_sha256(record), source_ref=record.payload.request.source_ref.model_dump(mode='json'),
        source_material_sha256=metadata_sha256(record.payload.source.material),
        body_sha256=sha256_bytes(body.encode('utf-8')), material=material.model_dump(mode='json'))
    raw['numeric_material_sha256'] = sha256_bytes(canonical_bytes({'version': 'restore-numeric-binding-v1',
                                                     'workspace_id': record.workspace_id, **raw}))
    return RestoreNumericMaterialView.model_validate(raw)


def operation_sha256(workspace: str, check: str, candidate: dm.DraftCandidate, material_sha: str,
                     plan: NumericPlan, runtime: NumericRuntimeProfile) -> str:
    return sha256_bytes(canonical_bytes(dict(version='restore-numeric-operation-v1', workspace_id=workspace, check_id=check,
        candidate=candidate.model_dump(mode='json'), numeric_material_sha256=material_sha,
        plan=plan.model_dump(mode='json'), runtime=runtime.model_dump(mode='json'))))


class RestoreNumericJobInput(AuthoringModel):
    version: Literal['restore-numeric-job-v1']
    workspace_id: dm.Id
    job_id: dm.Id
    check_id: dm.Id
    candidate: dm.DraftCandidate
    restore_record_sha256: dm.Sha256
    numeric_material_sha256: dm.Sha256
    plan: NumericPlan
    runtime: NumericRuntimeProfile
    operation_sha256: dm.Sha256

    @model_validator(mode='after')
    def operation(self) -> Self:
        if self.operation_sha256 != operation_sha256(self.workspace_id, self.check_id, self.candidate,
                self.numeric_material_sha256, self.plan, self.runtime):
            raise ValueError('Restore Job must retain its exact approved operation')
        return self


class RestoreNumericRecord(AuthoringModel):
    version: Literal['restore-numeric-check-record-v1']
    workspace_id: dm.Id
    actor_id: dm.Id
    decision_actor_id: dm.Id | None
    runtime_manifest_json: str
    view: RestoreNumericCheckView

    @model_validator(mode='after')
    def original(self) -> Self:
        checked(self.runtime_manifest_json, self.view.runtime.runtime_manifest_sha256)
        if ((self.decision_actor_id is None) != (self.view.decision == 'pending') or self.view.expired
                or self.view.result is not None or self.view.job is not None and (
                    self.view.job.status != 'queued' or self.view.job_revision != 1)):
            raise ValueError('record must preserve the original command projection')
        if self.view.operation_sha256 != operation_sha256(self.workspace_id, self.view.id, self.view.candidate,
                self.view.numeric_material_sha256, self.view.plan, self.view.runtime):
            raise ValueError('record must preserve its exact original operation')
        return self


class RestoreNumericCommand(AuthoringModel):
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
    def exact_bytes(self) -> Self:
        checked(self.request_json, self.request_sha256)
        checked(self.ack_json, self.ack_sha256)
        return self


class RestoreNumericEvent(AuthoringModel):
    version: Literal['restore-numeric-event-v1']
    workspace_id: dm.Id
    draft_id: dm.Id
    sequence: dm.Revision
    previous_sha256: dm.Sha256
    check_id: dm.Id
    kind: Literal['preview', 'decision', 'admission', 'start', 'terminal', 'command']
    payload_json: str
    payload_sha256: dm.Sha256
    recorded_at: dm.UTC

    @model_validator(mode='after')
    def exact_bytes(self) -> Self:
        checked(self.payload_json, self.payload_sha256)
        return self


def event_payload(event: RestoreNumericEvent):
    return checked(event.payload_json, event.payload_sha256)
