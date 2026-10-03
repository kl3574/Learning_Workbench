"""Explicit production Tutor source: existing owned job, frozen context and lease."""
import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from ..infrastructure.consent_repository import ConsentRepository, prepared_digest
from ..infrastructure.security import SessionIdentity
from ..infrastructure.tutor_repository import TutorRepository, TutorSourceState
from ..provider_dto import ReferenceSummary
from .errors import ApiError
from .provider_models import DispatchLease, PreparedOutboundMaterial
from .provider_ports import SourcePreparationChanged
from .tutor_context import ContextService, integrity
from .tutor_models import PreparedTutorContext, TutorJobInput


def build_outbound(value: TutorJobInput, context: PreparedTutorContext, job_revision: int) -> PreparedOutboundMaterial:
    if value.run_id != context.run_id or context.snapshot.request_sha256 != sha256_bytes(canonical_bytes(value.request)):
        raise integrity()
    result = PreparedOutboundMaterial(job_id=value.run_id, job_revision=job_revision,
        job_input_sha256=sha256_bytes(canonical_bytes(value)), purpose='tutor',
        context_snapshot=context.snapshot, messages=context.messages, evidence=context.evidence,
        preparation_version=context.template_version, prepared_input_sha256='0' * 64)
    result.prepared_input_sha256 = prepared_digest(value.workspace_id, result)
    return result


class TutorOutboundSource:
    def __init__(self, context: ContextService):
        self.context = context

    def _state(self, conn: sqlite3.Connection, identity: SessionIdentity, job_id: str) -> TutorSourceState:
        self.context.check_access(conn, identity)
        value = TutorRepository(conn, identity.workspace_id).source_state(job_id)
        self.context.check_scope(conn, identity, value.input.request.request.context, value.input.request.binding)
        return value

    def _prepared(self, conn: sqlite3.Connection, identity: SessionIdentity,
                  state: TutorSourceState) -> tuple[PreparedTutorContext, PreparedOutboundMaterial]:
        if state.context_id is None or state.prepared_input_sha256 is None:
            raise ApiError(409, 'OUTBOUND_SOURCE_UNAVAILABLE', '任务尚未冻结真实上下文。')
        context = self.context.read(conn, identity, state.context_id)
        material = build_outbound(state.input, context, state.job_revision)
        if (context.snapshot.snapshot_sha256 != state.context_sha256
                or material.prepared_input_sha256 != state.prepared_input_sha256):
            raise integrity()
        return context, material

    @staticmethod
    def _available(state: TutorSourceState) -> None:
        if state.status not in {'queued', 'running', 'awaiting_approval'} or state.cancel_requested:
            raise ApiError(409, 'OUTBOUND_SOURCE_UNAVAILABLE', '任务已停止，不能继续批准或派发。')

    def read_prepared(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                      job_id: str, expected_job_revision: int) -> PreparedOutboundMaterial:
        state = self._state(transaction, identity, job_id)
        if state.job_revision != expected_job_revision:
            raise ApiError(412, 'REVISION_MISMATCH', '任务已更新，请读取当前版本后预览。')
        if state.status != 'awaiting_approval' or state.consent_id is not None:
            raise ApiError(409, 'OUTBOUND_SOURCE_UNAVAILABLE', '此任务当前不处于首次待授权阶段。')
        self._available(state)
        context, material = self._prepared(transaction, identity, state)
        self.context.verify(transaction, identity, context)
        return material

    def verify_prepared(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        material: PreparedOutboundMaterial) -> None:
        state = self._state(transaction, identity, material.job_id)
        self._available(state)
        context, actual = self._prepared(transaction, identity, state)
        if actual.model_dump(exclude={'job_revision'}) != material.model_dump(exclude={'job_revision'}):
            raise integrity()
        try:
            self.context.verify(transaction, identity, context)
        except ApiError as error:
            if error.code == 'TUTOR_CONTEXT_CHANGED':
                raise SourcePreparationChanged() from None
            raise

    def reference_summaries(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                            material: PreparedOutboundMaterial) -> list[ReferenceSummary]:
        self.verify_prepared(transaction, identity, material)
        context = self.context.read(transaction, identity, material.context_snapshot.id)
        return [item.reference for item in context.included]

    def record_proposal(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        job_id: str, prepared_input_sha256: str, proposal_id: str) -> None:
        state = self._state(transaction, identity, job_id)
        _, material = self._prepared(transaction, identity, state)
        if material.prepared_input_sha256 != prepared_input_sha256:
            raise integrity()
        view, original, _ = ConsentRepository(transaction, identity.workspace_id).proposal_material(proposal_id)
        if original.prepared_input_sha256 != prepared_input_sha256 or view.summary.job_id != job_id:
            raise integrity()
        TutorRepository(transaction, identity.workspace_id).record_proposal(job_id, prepared_input_sha256, proposal_id)

    def bind_authorization(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                           job_id: str, prepared_input_sha256: str, consent_id: str) -> None:
        state = self._state(transaction, identity, job_id)
        context, material = self._prepared(transaction, identity, state)
        if material.prepared_input_sha256 != prepared_input_sha256:
            raise integrity()
        self.context.verify(transaction, identity, context)
        TutorRepository(transaction, identity.workspace_id).bind_authorization(job_id, prepared_input_sha256, consent_id)

    def verify_dispatch(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        material: PreparedOutboundMaterial, lease: DispatchLease, consent_id: str) -> dm.JobRef:
        self.verify_prepared(transaction, identity, material)
        return TutorRepository(transaction, identity.workspace_id).verify_lease(material.job_id, lease, consent_id)

    def read_job(self, transaction: sqlite3.Connection, identity: SessionIdentity, job_id: str) -> dm.JobRef:
        state = self._state(transaction, identity, job_id)
        return dm.JobRef.model_validate({'id': job_id, 'status': state.status})

    def verify_output(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                      job_id: str, dispatch_id: str) -> None:
        state = self._state(transaction, identity, job_id)
        self._prepared(transaction, identity, state)
        record = ConsentRepository(transaction, identity.workspace_id).read_dispatch(dispatch_id)
        if record.job_id != job_id or record.consent_id != state.consent_id:
            raise integrity()
        # No live-lease, active-consent or current-provider requirement for old
        # verified output. Current source Policy still governs its delivery.
