"""Versioned group history, immutable plan/candidate membership and original command ACKs."""
import sqlite3
from typing import Literal, TypeVar

from pydantic import BaseModel, TypeAdapter
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from ..application.authoring_group_models import AuthoringGroupCandidateRecord, AuthoringGroupJobInput, AuthoringContentPlanRecord
from ..application.errors import ApiError
from ..authoring_dto import AuthoringModel
from ..authoring_group_dto import (
    AuthoringGroupDraftView, AuthoringGroupJobSummary, AuthoringGroupJobView,
    AuthoringGroupPreparationSummary, AuthoringGroupPrepareWrite, AuthoringGroupValidation,
)
from ..application.authoring_group_validation import (
    build_group_candidate_payload, group_draft_view, parse_group_generated, parse_group_plan, plan_sha256,
)
from ..application.provider_models import UsageSnapshot
from ..import_dto import JobCancelRequest, JobSnapshot
from .authoring_job_repository import AuthoringJobRepository, checked, integrity
from .database import utc_now
from .security import SessionIdentity

M = TypeVar('M', bound=BaseModel)


def group_not_run() -> AuthoringGroupValidation:
    return AuthoringGroupValidation.model_validate({'schema': 'NOT_RUN', 'references': 'NOT_RUN',
        'symbol_declarations': 'NOT_RUN', 'issues': [], 'mathematical': 'NOT_RUN',
        'sources': 'NOT_RUN', 'independent_pedagogy': 'NOT_RUN',
        'plan_membership': 'NOT_RUN', 'private_bindings': 'NOT_RUN', 'question_checks': []})


class AuthoringGroupRecord(AuthoringModel):
    version: Literal['authoring-group-record-envelope-v1']
    input: AuthoringGroupJobInput
    view: AuthoringGroupJobView
    execution_actor_id: dm.Id | None
    consent_history: list[dm.Id]


class AuthoringGroupAuthorization(AuthoringModel):
    version: Literal['authoring-group-authorization-v1']
    workspace_id: dm.Id
    job_id: dm.Id
    consent_id: dm.Id
    proposal_id: dm.Id
    actor_id: dm.Id
    prepared_input_sha256: dm.Sha256
    job_revision: dm.Revision


class AuthoringGroupRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.conn, self.workspace_id = connection, workspace_id
        self.jobs = AuthoringJobRepository(connection, workspace_id)

    def create(self, identity: SessionIdentity, value: AuthoringGroupJobInput,
               preparation: AuthoringGroupPreparationSummary) -> None:
        row = self.jobs.load(value.job_id)
        view = AuthoringGroupJobView(variant='group', plan_ref=None, content_plan=None, summary=AuthoringGroupJobSummary(id=value.job_id, kind='authoring',
            job_revision=row['revision'], status=row['status'], title=value.request.topic, candidate=None,
            created_at=row['created_at'], updated_at=row['updated_at']), request=value.request,
            preparation=preparation, proposal_id=None, consent_id=None, provider_receipt_id=None,
            provider_outcome=None, usage=UsageSnapshot(input_tokens=None, output_tokens=None),
            raw_answer=None, raw_refusal=None, validation=group_not_run(), error_code=None)
        record = AuthoringGroupRecord(version='authoring-group-record-envelope-v1', input=value, view=view,
                                 execution_actor_id=None, consent_history=[])
        raw = canonical_bytes(record).decode()
        self.conn.execute('INSERT INTO authoring_records(job_id,workspace_id,actor_id,record_json,record_sha256) VALUES(?,?,?,?,?)',
                          (value.job_id, self.workspace_id, identity.id, raw, sha256_bytes(raw.encode())))

    def load(self, identifier: str, *, commands: bool = True) -> AuthoringGroupRecord:
        row = self.jobs.load(identifier)
        owner = self.conn.execute('SELECT * FROM authoring_records WHERE job_id=? AND workspace_id=?',
                                  (identifier, self.workspace_id)).fetchone()
        if owner is None or row['kind'] != 'authoring':
            raise integrity()
        try:
            record = AuthoringGroupRecord.model_validate(checked(owner['record_json'], owner['record_sha256']))
            view = record.view
            if (record.version != 'authoring-group-record-envelope-v1' or record.input.job_id != identifier
                    or record.input.workspace_id != self.workspace_id
                    or canonical_bytes(record.input).decode() != row['input_json']
                    or view.request != record.input.request or view.summary.id != identifier
                    or view.summary.title != record.input.request.topic
                    or view.summary.job_revision != row['revision'] or view.summary.status != row['status']
                    or view.summary.created_at != row['created_at'] or view.summary.updated_at != row['updated_at']
                    or view.preparation.job_input_sha256 != row['input_sha256']):
                raise integrity()
            if (record.execution_actor_id is not None) != (view.consent_id is not None):
                raise integrity()
            if (len(set(record.consent_history)) != len(record.consent_history)
                    or view.consent_id is not None and (not record.consent_history or record.consent_history[-1] != view.consent_id)):
                raise integrity()
            authorizations = self.conn.execute('SELECT * FROM authoring_authorizations WHERE workspace_id=? AND job_id=? ORDER BY rowid',
                                                (self.workspace_id, identifier)).fetchall()
            if [item['consent_id'] for item in authorizations] != record.consent_history:
                raise integrity()
            for item in authorizations:
                auth = AuthoringGroupAuthorization.model_validate(checked(item['record_json'], item['record_sha256']))
                if (auth.workspace_id != self.workspace_id or auth.job_id != identifier or auth.consent_id != item['consent_id']
                        or auth.prepared_input_sha256 != view.preparation.prepared_input_sha256
                        or self.jobs.snapshot(identifier, auth.job_revision).status != 'queued'):
                    raise integrity()
                if view.consent_id == auth.consent_id and (record.execution_actor_id != auth.actor_id or view.proposal_id != auth.proposal_id):
                    raise integrity()
            TypeAdapter(dm.Id).validate_python(owner['actor_id'])
            if view.summary.candidate is not None:
                candidate = self.candidate(view.summary.candidate.draft_id)
                if (candidate.candidate != view.summary.candidate or candidate.source_job_id != identifier
                        or candidate.provider_receipt_id != view.provider_receipt_id
                        or candidate.validation != view.validation
                        or candidate.plan_ref != view.plan_ref
                        or (candidate.payload, candidate.validation) != build_group_candidate_payload(
                            parse_group_generated(view.raw_answer or '', record.input.request,
                                view.preparation.targets, view.preparation.materials), record.input.request,
                            view.preparation.targets, view.preparation.materials)):
                    raise integrity()
            elif self.conn.execute('SELECT 1 FROM authoring_group_candidates WHERE source_job_id=?', (identifier,)).fetchone():
                raise integrity()
            self.validate_plan(record)
            if row['status'] in {'completed', 'failed', 'cancelled'}:
                terminal_result = {'result_sha256': sha256_bytes(canonical_bytes(view.model_dump(mode='json', exclude={'summary'}))),
                    'candidate': view.summary.candidate.model_dump() if view.summary.candidate else None}
                if row['result_json'] == canonical_bytes({'cancelled_before_execution': True}).decode():
                    if row['status'] != 'cancelled' or view.provider_receipt_id is not None or view.summary.candidate is not None:
                        raise integrity()
                elif row['result_json'] != canonical_bytes(terminal_result).decode():
                    raise integrity()
            if commands:
                self.validate_commands(identifier, record)
            return record
        except (ValueError, TypeError, KeyError):
            raise integrity() from None

    def save(self, record: AuthoringGroupRecord) -> None:
        record = AuthoringGroupRecord.model_validate(record.model_dump(mode='json'))
        raw = canonical_bytes(record).decode()
        changed = self.conn.execute('UPDATE authoring_records SET record_json=?,record_sha256=? WHERE job_id=? AND workspace_id=?',
            (raw, sha256_bytes(raw.encode()), record.input.job_id, self.workspace_id))
        if changed.rowcount != 1:
            raise integrity()

    def record_authorization(self, identity: SessionIdentity, record: AuthoringGroupRecord, job_revision: int) -> None:
        if record.view.consent_id is None or record.view.proposal_id is None:
            raise integrity()
        value = AuthoringGroupAuthorization(version='authoring-group-authorization-v1', workspace_id=self.workspace_id,
            job_id=record.input.job_id, consent_id=record.view.consent_id, proposal_id=record.view.proposal_id,
            actor_id=identity.id, prepared_input_sha256=record.view.preparation.prepared_input_sha256,
            job_revision=job_revision)
        raw = canonical_bytes(value).decode()
        self.conn.execute('INSERT INTO authoring_authorizations VALUES(?,?,?,?,?)',
            (value.consent_id, self.workspace_id, value.job_id, raw, sha256_bytes(raw.encode())))

    def sync(self, record: AuthoringGroupRecord) -> AuthoringGroupRecord:
        row = self.jobs.load(record.input.job_id)
        record.view.summary = record.view.summary.model_copy(update={'job_revision': row['revision'],
            'status': row['status'], 'updated_at': row['updated_at']})
        self.save(record)
        return record

    def candidate(self, identifier: str) -> AuthoringGroupCandidateRecord:
        row = self.conn.execute('SELECT * FROM authoring_group_candidates WHERE draft_id=? AND workspace_id=?',
                                (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, 'AUTHORING_DRAFT_MISSING', '创作草稿不存在或不可访问。')
        try:
            result = AuthoringGroupCandidateRecord.model_validate(checked(row['record_json'], row['record_sha256']))
            if (result.candidate.draft_id != identifier or result.candidate.draft_revision != 1
                    or result.workspace_id != self.workspace_id or result.source_job_id != row['source_job_id']):
                raise integrity()
            return result
        except (ValueError, TypeError, KeyError):
            raise integrity() from None

    def draft(self, identifier: str) -> AuthoringGroupDraftView:
        candidate = self.candidate(identifier)
        self.load(candidate.source_job_id)
        checks = self.conn.execute('SELECT check_id FROM authoring_group_numeric_checks WHERE draft_id=? AND workspace_id=? ORDER BY rowid',
                                   (identifier, self.workspace_id)).fetchall()
        return group_draft_view(candidate, [row[0] for row in checks],
            [dm.Warning(code='AUTHORING_REVIEW_NOT_RUN', severity='warning',
                message='当前为草稿；数学、来源、教学审核与发布均未完成。')])

    def validate_plan(self, record: AuthoringGroupRecord) -> AuthoringContentPlanRecord | None:
        row = self.conn.execute('SELECT * FROM authoring_content_plans WHERE source_job_id=? AND workspace_id=?',
                                (record.input.job_id, self.workspace_id)).fetchone()
        view = record.view
        if view.plan_ref is None:
            if row is not None or view.content_plan is not None:
                raise integrity()
            return None
        if row is None or view.content_plan is None or view.provider_receipt_id is None:
            raise integrity()
        try:
            plan = AuthoringContentPlanRecord.model_validate(checked(row['record_json'], row['record_sha256']))
            if (plan.workspace_id != self.workspace_id or plan.source_job_id != record.input.job_id
                    or plan.provider_receipt_id != view.provider_receipt_id
                    or plan.job_input_sha256 != view.preparation.job_input_sha256
                    or plan.plan_ref != view.plan_ref or plan.plan != view.content_plan
                    or plan.plan_ref.source_job_id != record.input.job_id
                    or plan.plan_ref.plan_sha256 != plan_sha256(plan.plan)
                    or plan.plan != parse_group_plan(view.raw_answer or '', record.input.request)):
                raise integrity()
            return plan
        except (ValueError, TypeError, KeyError):
            raise integrity() from None

    def store_plan(self, value: AuthoringContentPlanRecord) -> None:
        if value.workspace_id != self.workspace_id:
            raise integrity()
        raw = canonical_bytes(value).decode()
        self.conn.execute('INSERT INTO authoring_content_plans VALUES(?,?,?,?)',
            (value.source_job_id, self.workspace_id, raw, sha256_bytes(raw.encode())))

    def store_candidate(self, value: AuthoringGroupCandidateRecord) -> None:
        if value.workspace_id != self.workspace_id:
            raise integrity()
        raw = canonical_bytes(value).decode()
        self.conn.execute('INSERT INTO authoring_group_candidates VALUES(?,?,?,?,?)',
            (value.candidate.draft_id, self.workspace_id, value.source_job_id, raw, sha256_bytes(raw.encode())))

    def validate_commands(self, identifier: str, record: AuthoringGroupRecord) -> None:
        rows = self.conn.execute('SELECT * FROM authoring_commands WHERE workspace_id=? AND owner_id=? ORDER BY created_at',
                                 (self.workspace_id, identifier)).fetchall()
        creates = 0
        for row in rows:
            request = checked(row['request_json'], row['request_sha256'])
            ack = checked(row['ack_json'], row['ack_sha256'])
            try:
                TypeAdapter(dm.UTC).validate_python(row['created_at'])
                TypeAdapter(dm.Id).validate_python(row['actor_id'])
                if row['route'] == 'POST /authoring/group-jobs':
                    creates += 1
                    if (AuthoringGroupPrepareWrite.model_validate(request) != record.input.request
                            or dm.JobRef.model_validate(ack) != dm.JobRef(id=identifier, status='awaiting_approval')
                            or row['job_revision'] != 1):
                        raise integrity()
                elif row['route'] == f'POST /jobs/{identifier}/cancel':
                    command = JobCancelRequest.model_validate(request)
                    result = JobSnapshot.model_validate(ack)
                    if result.revision != row['job_revision']:
                        raise integrity()
                    self.jobs.verify_cancel_ack(identifier, command.expected_revision, result,
                                                row['basis_revision'], row['created_at'])
                else:
                    raise integrity()
            except (ValueError, TypeError, KeyError):
                raise integrity() from None
        if creates != 1:
            raise integrity()

    def replay(self, identity: SessionIdentity, route: str, key: str, body: BaseModel, model: type[M]) -> M | None:
        row = self.conn.execute('SELECT * FROM authoring_commands WHERE workspace_id=? AND actor_id=? AND route=? AND key=?',
                                (self.workspace_id, identity.id, route, key)).fetchone()
        if row is None:
            return None
        self.load(row['owner_id'])
        request = checked(row['request_json'], row['request_sha256'])
        if canonical_bytes(body) != canonical_bytes(request):
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原命令键已用于不同的完整命令。')
        try:
            return model.model_validate(checked(row['ack_json'], row['ack_sha256']))
        except (ValueError, TypeError):
            raise integrity() from None

    def record_command(self, identity: SessionIdentity, route: str, key: str, body: BaseModel,
                       ack: BaseModel, owner_id: str, job_revision: int, basis_revision: int | None = None) -> None:
        raw, result = canonical_bytes(body).decode(), canonical_bytes(ack).decode()
        self.conn.execute('INSERT INTO authoring_commands(workspace_id,actor_id,route,key,owner_id,request_json,request_sha256,ack_json,ack_sha256,job_revision,created_at,basis_revision) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (self.workspace_id, identity.id, route, key, owner_id, raw, sha256_bytes(raw.encode()), result,
             sha256_bytes(result.encode()), job_revision, utc_now(), basis_revision))
