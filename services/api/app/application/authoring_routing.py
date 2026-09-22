"""Explicit dispatch across immutable Authoring input versions, never identifier prefixes."""
import sqlite3

from packages.contracts import domain_models as dm
from ..infrastructure.authoring_job_repository import AuthoringJobRepository, integrity
from ..infrastructure.security import SessionIdentity
from ..provider_dto import ReferenceSummary
from .authoring_source import AuthoringOutboundSource
from .authoring_group_source import AuthoringGroupOutboundSource
from .provider_models import DispatchLease, PreparedOutboundMaterial


class AuthoringSourceRouter:
    def __init__(self, single: AuthoringOutboundSource, group: AuthoringGroupOutboundSource):
        self.single, self.group = single, group

    def _source(self, conn: sqlite3.Connection, identity: SessionIdentity,
                identifier: str) -> AuthoringOutboundSource | AuthoringGroupOutboundSource:
        version = AuthoringJobRepository(conn, identity.workspace_id).input_version(identifier)
        if version == 'authoring-job-v1':
            return self.single
        if version == 'authoring-group-job-v1':
            return self.group
        raise integrity()

    def read_prepared(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                      job_id: str, expected_job_revision: int) -> PreparedOutboundMaterial:
        return self._source(transaction, identity, job_id).read_prepared(
            transaction, identity, job_id, expected_job_revision)

    def verify_prepared(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        material: PreparedOutboundMaterial) -> None:
        self._source(transaction, identity, material.job_id).verify_prepared(transaction, identity, material)

    def reference_summaries(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                            material: PreparedOutboundMaterial) -> list[ReferenceSummary]:
        return self._source(transaction, identity, material.job_id).reference_summaries(transaction, identity, material)

    def record_proposal(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        job_id: str, prepared_input_sha256: str, proposal_id: str) -> None:
        self._source(transaction, identity, job_id).record_proposal(
            transaction, identity, job_id, prepared_input_sha256, proposal_id)

    def bind_authorization(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                           job_id: str, prepared_input_sha256: str, consent_id: str) -> None:
        self._source(transaction, identity, job_id).bind_authorization(
            transaction, identity, job_id, prepared_input_sha256, consent_id)

    def verify_dispatch(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        material: PreparedOutboundMaterial, lease: DispatchLease, consent_id: str) -> dm.JobRef:
        return self._source(transaction, identity, material.job_id).verify_dispatch(
            transaction, identity, material, lease, consent_id)

    def read_job(self, transaction: sqlite3.Connection, identity: SessionIdentity, job_id: str) -> dm.JobRef:
        return self._source(transaction, identity, job_id).read_job(transaction, identity, job_id)

    def verify_output(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                      job_id: str, dispatch_id: str) -> None:
        self._source(transaction, identity, job_id).verify_output(transaction, identity, job_id, dispatch_id)
