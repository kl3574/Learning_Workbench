"""Actual group source; one original frozen request and one explicit Provider consent."""
import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from ..infrastructure.authoring_job_repository import integrity
from ..infrastructure.authoring_job_repository import AuthoringLease
from ..infrastructure.authoring_group_repository import AuthoringGroupRecord, AuthoringGroupRepository
from ..infrastructure.consent_repository import ConsentRepository, prepared_digest
from ..infrastructure.security import SessionIdentity
from ..provider_dto import ReferenceSummary
from .authoring_group_context import AuthoringGroupContext
from .authoring_group_models import AuthoringGroupJobInput, PreparedAuthoringGroupContext
from .errors import ApiError
from .provider_models import DispatchLease, PreparedOutboundMaterial
from .provider_ports import SourcePreparationChanged


def build_group_outbound(value: AuthoringGroupJobInput, context: PreparedAuthoringGroupContext, revision: int) -> PreparedOutboundMaterial:
    if value.job_id != context.job_id or context.snapshot.request_sha256 != sha256_bytes(canonical_bytes(value.request)):
        raise integrity()
    result = PreparedOutboundMaterial(job_id=value.job_id, job_revision=revision,
        job_input_sha256=sha256_bytes(canonical_bytes(value)), purpose='authoring',
        context_snapshot=context.snapshot, messages=context.messages, evidence=context.evidence,
        preparation_version=context.template_version, prepared_input_sha256='0' * 64)
    result.prepared_input_sha256 = prepared_digest(value.workspace_id, result)
    return result


class AuthoringGroupOutboundSource:
    def __init__(self, context: AuthoringGroupContext):
        self.context = context

    def _state(self, conn: sqlite3.Connection, identity: SessionIdentity, identifier: str) -> AuthoringGroupRecord:
        self.context.check_access(conn, identity)
        record = AuthoringGroupRepository(conn, identity.workspace_id).load(identifier)
        for consent_id in record.consent_history:
            summary, material, _ = ConsentRepository(conn, identity.workspace_id).dispatch_material(consent_id)
            if (summary.job_id != identifier or material.job_input_sha256 != record.view.preparation.job_input_sha256
                    or material.prepared_input_sha256 != record.view.preparation.prepared_input_sha256):
                raise integrity()
        return record

    def _prepared(self, conn: sqlite3.Connection, identity: SessionIdentity,
                  record: AuthoringGroupRecord) -> tuple[PreparedAuthoringGroupContext, PreparedOutboundMaterial]:
        context = self.context.read_group(conn, identity, record.view.preparation.context_snapshot_id)
        actual = build_group_outbound(record.input, context, record.view.summary.job_revision)
        if (actual.prepared_input_sha256 != record.view.preparation.prepared_input_sha256
                or context.snapshot.snapshot_sha256 != record.view.preparation.snapshot_sha256
                or context.materials != record.view.preparation.materials
                or context.targets != record.view.preparation.targets):
            raise integrity()
        return context, actual

    def read_prepared(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                      job_id: str, expected_job_revision: int) -> PreparedOutboundMaterial:
        record = self._state(transaction, identity, job_id)
        if record.view.summary.job_revision != expected_job_revision:
            raise ApiError(412, 'REVISION_MISMATCH', '任务已更新，请读取当前版本后预览。')
        if record.view.summary.status != 'awaiting_approval' or record.view.consent_id is not None:
            raise ApiError(409, 'OUTBOUND_SOURCE_UNAVAILABLE', '任务当前不处于首次待批准阶段。')
        context, actual = self._prepared(transaction, identity, record)
        self.context.verify_group(transaction, identity, context)
        return actual

    def verify_prepared(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        material: PreparedOutboundMaterial) -> None:
        record = self._state(transaction, identity, material.job_id)
        row = AuthoringGroupRepository(transaction, identity.workspace_id).jobs.load(material.job_id)
        if row['status'] not in {'queued', 'running', 'awaiting_approval'} or row['cancel_requested']:
            raise ApiError(409, 'OUTBOUND_SOURCE_UNAVAILABLE', '任务已停止，不能继续批准或派发。')
        context, actual = self._prepared(transaction, identity, record)
        if actual.model_dump(exclude={'job_revision'}) != material.model_dump(exclude={'job_revision'}):
            raise integrity()
        try:
            self.context.verify_group(transaction, identity, context)
        except ApiError as error:
            if error.code == 'AUTHORING_CONTEXT_CHANGED':
                raise SourcePreparationChanged() from None
            raise

    def reference_summaries(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                            material: PreparedOutboundMaterial) -> list[ReferenceSummary]:
        self.verify_prepared(transaction, identity, material)
        context = self.context.read_group(transaction, identity, material.context_snapshot.id)
        return [ReferenceSummary(ref=item.ref, title=meta.title, locator=item.locator,
            character_count=len(item.text), excerpt_sha256=meta.body_sha256)
            for item, meta in zip(context.evidence, context.materials, strict=True)]

    def record_proposal(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        job_id: str, prepared_input_sha256: str, proposal_id: str) -> None:
        record = self._state(transaction, identity, job_id)
        _, actual = self._prepared(transaction, identity, record)
        proposal, material, _ = ConsentRepository(transaction, identity.workspace_id).proposal_material(proposal_id)
        if (actual.prepared_input_sha256 != prepared_input_sha256
                or material.prepared_input_sha256 != prepared_input_sha256 or proposal.summary.job_id != job_id
                or proposal.summary.provider_id != record.input.request.provider_id):
            raise integrity()
        record.view.proposal_id = proposal_id
        AuthoringGroupRepository(transaction, identity.workspace_id).save(record)

    def bind_authorization(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                           job_id: str, prepared_input_sha256: str, consent_id: str) -> None:
        repo = AuthoringGroupRepository(transaction, identity.workspace_id)
        record = self._state(transaction, identity, job_id)
        context, actual = self._prepared(transaction, identity, record)
        self.context.verify_group(transaction, identity, context)
        summary, material, _ = ConsentRepository(transaction, identity.workspace_id).dispatch_material(consent_id)
        if (record.view.summary.status != 'awaiting_approval' or record.view.consent_id is not None
                or actual.prepared_input_sha256 != prepared_input_sha256
                or material.prepared_input_sha256 != prepared_input_sha256 or summary.job_id != job_id
                or summary.provider_id != record.input.request.provider_id):
            raise integrity()
        consent = ConsentRepository(transaction, identity.workspace_id).consent(consent_id)
        record.view.proposal_id = consent['proposal_id']
        record.view.consent_id = consent_id
        record.execution_actor_id = identity.id
        record.consent_history.append(consent_id)
        repo.jobs.transition(repo.jobs.load(job_id), 'queued')
        repo.record_authorization(identity, record, repo.jobs.load(job_id)['revision'])
        repo.sync(record)

    def resume_before_dispatch(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                               lease: AuthoringLease) -> bool:
        """Only proven unused revoked/expired consent can return to approval.

        This is an explicit owner worker transition, never a GET repair and
        never a new grant. Original Provider history remains immutable.
        """
        repo = AuthoringGroupRepository(transaction, identity.workspace_id)
        record = self._state(transaction, identity, lease.job_id)
        row = repo.jobs.load(lease.job_id)
        if not repo.jobs.owned(row, lease) or record.view.consent_id is None:
            return False
        provider = ConsentRepository(transaction, identity.workspace_id)
        consent = provider.consent(record.view.consent_id)
        summary, _, _ = provider.dispatch_material(record.view.consent_id)
        from ..infrastructure.database import utc_now
        if (provider.dispatch_for_consent(record.view.consent_id) is not None
                or consent['status'] == 'active' and summary.expires_at > utc_now()):
            return False
        record.view.consent_id = None
        record.view.proposal_id = None
        record.execution_actor_id = None
        repo.jobs.transition(row, 'awaiting_approval')
        repo.sync(record)
        return True

    def verify_dispatch(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        material: PreparedOutboundMaterial, lease: DispatchLease, consent_id: str) -> dm.JobRef:
        self.verify_prepared(transaction, identity, material)
        repo = AuthoringGroupRepository(transaction, identity.workspace_id)
        record, row = repo.load(material.job_id), repo.jobs.load(material.job_id)
        from ..infrastructure.database import utc_now
        if (row['status'] != 'running' or row['cancel_requested'] or record.view.consent_id != consent_id
                or row['revision'] != lease.job_revision or row['lease_owner'] != lease.owner_id
                or row['lease_until'] < lease.expires_at or lease.expires_at <= utc_now()):
            raise ApiError(409, 'AUTHORING_LEASE_LOST', '任务执行许可已失效。')
        return dm.JobRef(id=material.job_id, status='running')

    def read_job(self, transaction: sqlite3.Connection, identity: SessionIdentity, job_id: str) -> dm.JobRef:
        record = self._state(transaction, identity, job_id)
        return dm.JobRef(id=job_id, status=record.view.summary.status)

    def verify_output(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                      job_id: str, dispatch_id: str) -> None:
        record = self._state(transaction, identity, job_id)
        self._prepared(transaction, identity, record)
        dispatch = ConsentRepository(transaction, identity.workspace_id).read_dispatch(dispatch_id)
        if dispatch.job_id != job_id or dispatch.consent_id != record.view.consent_id:
            raise integrity()


def group_preparation(value: AuthoringGroupJobInput, context: PreparedAuthoringGroupContext):
    from ..authoring_group_dto import AuthoringGroupPreparationSummary
    material = build_group_outbound(value, context, 1)
    return AuthoringGroupPreparationSummary(context_snapshot_id=context.snapshot.id,
        snapshot_sha256=context.snapshot.snapshot_sha256, job_input_sha256=material.job_input_sha256,
        prepared_input_sha256=material.prepared_input_sha256, character_count=context.snapshot.character_count,
        materials=context.materials, targets=context.targets, warnings=context.warnings)
