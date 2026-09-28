"""Actual review commands and owner-authenticated reads, in one SQLite transaction."""
from collections.abc import Mapping
import re
import sqlite3
from typing import Literal
from uuid import uuid4

from packages.contracts.canonical import metadata_sha256, sha256_bytes
from ..import_dto import DownloadArtifact, JobCancelRequest, JobSnapshot
from ..review_dto import DraftReviewWrite, ReviewDecisionWrite
from ..infrastructure.artifact_repository import ArtifactRepository
from ..infrastructure.blobs import BlobStore
from ..infrastructure.content_repository import ContentRepository
from ..infrastructure.database import Database, utc_now
from ..infrastructure.review_repository import ReviewRepository, integrity, validated
from ..infrastructure.review_artifact_repository import ReviewArtifactRepository
from ..infrastructure.security import SessionIdentity, current_session_identity
from .artifacts import ArtifactReader, unavailable_owner
from .authoring_context import AuthoringContext
from .draft_candidates import DraftCandidates
from .errors import ApiError
from .jobs import artifact_job_kind
from .providers import validate_key
from .review_artifacts import PROFILE
from .review_history_models import (
    ReviewHistory, ReviewMachineRecord, ReviewDecisionRecord, ReviewArtifactBinding, StoredReviewReceipt,
    ReviewCreateCommand, ReviewDecisionCommand, ReviewCancelCommand, ReviewJobAck, ReviewCancelAck,
    ReviewCancelRequest,
)
from .review_material_models import CheckedReviewMaterial, EditReviewMaterial
from .review_models import ReviewJobInput
from .review_numeric import ReviewNumeric


class ReviewService:
    def __init__(self, database: Database, candidates: DraftCandidates, numeric: ReviewNumeric,
                 artifact_readers: Mapping[tuple[str, str], ArtifactReader]):
        self.database, self.candidates, self.numeric = database, candidates, numeric
        self.external_artifact_readers = dict(artifact_readers)
        self.artifacts = ReviewArtifactRepository(BlobStore(database.settings.data_dir))

    def readers(self) -> dict[tuple[str, str], ArtifactReader]:
        return {**self.external_artifact_readers, (PROFILE, 'draft_review'): self}

    def read_publication_basis(self, connection: sqlite3.Connection, identity: SessionIdentity,
                               identifier: str) -> tuple[ReviewHistory, CheckedReviewMaterial]:
        """Current checked Quality facts; never a cached or reusable permission.

        The caller must own the transaction and still perform publication's
        remaining prerequisites. No state/history repair occurs on this read.
        """
        if not connection.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '发布准入核验需要当前事务。')
        return self._history(connection, identity, identifier)

    @staticmethod
    def _identity(conn: sqlite3.Connection, identity: SessionIdentity, *, subject: bool = True) -> SessionIdentity:
        current = current_session_identity(conn, identity)
        ContentRepository(conn, current.workspace_id).require_workspace()
        if subject:
            AuthoringContext.check_access(conn, current)
        return current

    def _history(self, conn: sqlite3.Connection, identity: SessionIdentity, identifier: str,
                 ancestors: frozenset[str] = frozenset(),
                 verified: dict[str, tuple[ReviewHistory, CheckedReviewMaterial]] | None = None,
                 ) -> tuple[ReviewHistory, CheckedReviewMaterial]:
        current = self._identity(conn, identity)
        if identifier in ancestors:
            raise ApiError(409, 'REVIEW_EVIDENCE_CYCLE', '审核附件引用形成循环，无法完整核验。')
        verified = {} if verified is None else verified
        if identifier in verified:
            return verified[identifier]
        if len(ancestors) >= 32:
            raise ApiError(413, 'REVIEW_EVIDENCE_DEPTH', '审核附件引用超过核验深度。')
        ancestors = ancestors | {identifier}
        history = ReviewRepository(conn, current.workspace_id).load(identifier)
        value = history.binding.input
        material = self.candidates.read_review_material(conn, current, value.candidate.draft_id,
                                                        value.candidate.draft_revision)
        if material.candidate != value.candidate or material.source_kind != value.source_kind:
            raise integrity()
        if history.records:
            machine = history.records[0]
            if not isinstance(machine, ReviewMachineRecord) or machine.material != material:
                raise integrity()
            self.numeric.verify_review_numeric(conn, current, machine.numeric)
            self.artifacts.read(conn, value, machine)
            for record in history.records[1:]:
                if not isinstance(record, ReviewDecisionRecord):
                    raise integrity()
                self._decision_applicability(material, record.request)
                for binding in record.evidence:
                    actual = self._evidence(conn, current, material, binding.artifact.artifact_id,
                                            binding.bound_at, ancestors, verified)
                    if actual != binding:
                        raise integrity()
        verified[identifier] = history, material
        return history, material

    def _evidence(self, conn: sqlite3.Connection, identity: SessionIdentity, material: CheckedReviewMaterial,
                  identifier: str, bound_at: str, ancestors: frozenset[str],
                  verified: dict[str, tuple[ReviewHistory, CheckedReviewMaterial]] | None = None,
                  ) -> ReviewArtifactBinding:
        routing = ArtifactRepository(conn, identity.workspace_id).binding(identifier)
        kind = artifact_job_kind(conn, identity.workspace_id, routing.job_id)
        if (routing.profile, kind) == (PROFILE, 'draft_review'):
            history, _ = self._history(conn, identity, routing.job_id, ancestors, verified)
            if not history.records or not isinstance(history.records[0], ReviewMachineRecord):
                raise integrity()
            machine = history.records[0]
            if machine.report.artifact.artifact_id != identifier:
                raise integrity()
            raw, artifact = self.artifacts.read(conn, history.binding.input, machine)
            owner: Literal['import', 'quality'] = 'quality'
        else:
            reader = self.external_artifact_readers.get((routing.profile, kind))
            if reader is None or kind != 'import':
                raise unavailable_owner()
            raw, artifact = reader.read_artifact(conn, identity, identifier)
            owner = 'import'
        if artifact.artifact_id != identifier or artifact.sha256 != sha256_bytes(raw) or artifact.size != len(raw):
            raise integrity()
        manifest_sha = ArtifactRepository(conn, identity.workspace_id).manifest_sha256(identifier, artifact)
        return ReviewArtifactBinding(version='review-artifact-binding-v1', workspace_id=identity.workspace_id,
            candidate=material.candidate, artifact=artifact, artifact_owner=owner, source_job_id=routing.job_id,
            profile=routing.profile, manifest_sha256=manifest_sha,
            purpose='human_decision_evidence', bound_at=bound_at)

    @staticmethod
    def _decision_applicability(material: CheckedReviewMaterial, request: ReviewDecisionWrite) -> None:
        if request.mathematical == 'NOT_APPLICABLE':
            def declares_math(value: object, *, include_title: bool = False) -> bool:
                if isinstance(value, dict):
                    if (value.get('kind') in {'worked_example', 'theorem', 'proof', 'formula', 'numeric', 'expression', 'calculation'}
                            or value.get('numeric_plan') is not None or bool(value.get('symbols'))):
                        return True
                    for key, item in value.items():
                        if isinstance(item, str) and ('markdown' in key or key in {'formula', 'proof'}
                                or (include_title and key == 'title')):
                            if re.search(r'\\(?:\(|\[|begin\{(?:equation|align|math|gather)\*?\})|\$[^$]+\$', item):
                                return True
                    return any(declares_math(item, include_title=include_title) for item in value.values())
                return isinstance(value, list) and any(declares_math(item, include_title=include_title) for item in value)
            # An edit's frozen base is provenance, not its current candidate.
            # Owner/history reads still authenticate that complete original base.
            payload = material.payload.record.payload if isinstance(material.payload, EditReviewMaterial) else material.payload
            if declares_math(payload.model_dump(mode='python', warnings='error'),
                    include_title=isinstance(material.payload, EditReviewMaterial)):
                raise ApiError(409, 'MATHEMATICAL_REVIEW_REQUIRED', '原材料包含数学结构或数值计划，不能标为数学审校不适用。')
            # Absence of these explicit signals is not automatic classification.
            # The current author's explicit N/A and original nonblank reason are
            # retained as a human judgment on this exact material, never machine PASS.

    def create(self, identity: SessionIdentity, draft_id: str, body: DraftReviewWrite, key: str) -> ReviewJobAck:
        key, body = validate_key(key), validated(DraftReviewWrite, body)
        with self.database.transaction() as conn:
            current = self._identity(conn, identity)
            repo = ReviewRepository(conn, current.workspace_id)
            route = f'POST /drafts/{draft_id}/review'
            replay = repo.replay(current.id, route, key, body)
            if replay is not None:
                self._history(conn, current, replay.review_id)
                if not isinstance(replay, ReviewCreateCommand):
                    raise integrity()
                return replay.ack
            material = self.candidates.read_current_review_material(conn, current, draft_id, body.expected_revision)
            self.numeric.read_review_numeric(conn, current, draft_id, body.expected_revision)
            identifier, now = 'review_' + uuid4().hex, utc_now()
            value = ReviewJobInput(version='draft-review-job-v1', workspace_id=current.workspace_id,
                review_id=identifier, source_kind=material.source_kind, candidate=material.candidate,
                request=body, creator_session_id=current.id, rules_version='draft-review-rules-v1', created_at=now)
            repo.jobs.create(identifier, 'draft_review', value)
            ack = ReviewJobAck(id=identifier, status='queued')
            repo.bind(value, ReviewCreateCommand(workspace_id=current.workspace_id, actor_id=current.id,
                route=route, command_key=key, review_id=identifier, basis_revision=body.expected_revision,
                resulting_revision=1, recorded_at=utc_now(), command_kind='create', request=body, ack=ack))
            self._history(conn, current, identifier)
            return ack

    def read(self, identity: SessionIdentity, identifier: str) -> StoredReviewReceipt:
        with self.database.transaction(immediate=False) as conn:
            history, _ = self._history(conn, identity, identifier)
            if history.receipt is None:
                raise ApiError(409, 'REVIEW_NOT_READY', '审核尚无机器回执，请读取任务状态。')
            return history.receipt

    def decide(self, identity: SessionIdentity, identifier: str, body: ReviewDecisionWrite, key: str) -> StoredReviewReceipt:
        key, body = validate_key(key), validated(ReviewDecisionWrite, body)
        with self.database.transaction() as conn:
            current = self._identity(conn, identity)
            history, material = self._history(conn, current, identifier)
            repo, route = ReviewRepository(conn, current.workspace_id), f'POST /reviews/{identifier}/decision'
            replay = repo.replay(current.id, route, key, body)
            if replay is not None:
                if not isinstance(replay, ReviewDecisionCommand):
                    raise integrity()
                return replay.ack
            if history.receipt is None or not history.records or not isinstance(history.records[0], ReviewMachineRecord):
                raise ApiError(409, 'REVIEW_NOT_READY', '审核尚无机器回执。')
            if history.receipt.revision != body.expected_revision:
                raise ApiError(412, 'REVIEW_REVISION_MISMATCH', '审核回执已更新，请重新读取。')
            if body.candidate_sha256 != material.candidate.candidate_sha256:
                raise ApiError(412, 'DRAFT_REVISION_MISMATCH', '审核内容已变化，请重新读取。')
            self._decision_applicability(material, body)
            now, machine = utc_now(), history.records[0]
            evidence = [self._evidence(conn, current, material, item, now, frozenset({identifier}))
                        for item in body.evidence_artifact_ids]
            receipt = StoredReviewReceipt(**{**history.receipt.model_dump(), 'revision':body.expected_revision + 1,
                'mathematical':body.mathematical, 'sources':body.sources, 'reviewer':current.id,
                'decision_reason':body.reason, 'evidence_paths':[machine.report.artifact.download_path,
                    *[item.artifact.download_path for item in evidence]]})
            record = ReviewDecisionRecord(version='review-decision-record-v1', workspace_id=current.workspace_id,
                review_id=identifier, candidate=material.candidate, previous_receipt_sha256=metadata_sha256(history.receipt),
                machine_record_sha256=metadata_sha256(machine), material_descriptor_sha256=material.descriptor_sha256,
                request=body, request_sha256=metadata_sha256(body), actor_session_id=current.id,
                actor_role_at_decision='author', evidence=evidence, receipt=receipt, decided_at=now)
            command = ReviewDecisionCommand(workspace_id=current.workspace_id, actor_id=current.id, route=route,
                command_key=key, review_id=identifier, basis_revision=body.expected_revision,
                resulting_revision=receipt.revision, recorded_at=now, command_kind='decision', request=body, ack=receipt)
            repo.append_decision(record, command)
            self._history(conn, current, identifier)
            return receipt

    def read_job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        with self.database.transaction(immediate=False) as conn:
            current = self._identity(conn, identity, subject=False)
            return ReviewRepository(conn, current.workspace_id).load(identifier).binding.job

    def cancel(self, identity: SessionIdentity, identifier: str, body: JobCancelRequest, key: str) -> JobSnapshot:
        key, request = validate_key(key), validated(ReviewCancelRequest, body)
        with self.database.transaction() as conn:
            current = self._identity(conn, identity, subject=False)
            repo, route = ReviewRepository(conn, current.workspace_id), f'POST /jobs/{identifier}/cancel'
            history = repo.load(identifier)
            replay = repo.replay(current.id, route, key, request)
            if replay is not None:
                if not isinstance(replay, ReviewCancelCommand):
                    raise integrity()
                return replay.ack
            basis = history.binding.job.revision
            ack = validated(ReviewCancelAck, repo.jobs.cancel(identifier, request.expected_revision))
            repo.record_cancel(ReviewCancelCommand(workspace_id=current.workspace_id, actor_id=current.id,
                route=route, command_key=key, review_id=identifier, basis_revision=basis,
                resulting_revision=ack.revision, recorded_at=utc_now(), command_kind='cancel', request=request, ack=ack))
            return ack

    def read_artifact(self, conn: sqlite3.Connection, identity: SessionIdentity,
                      identifier: str) -> tuple[bytes, DownloadArtifact]:
        current = self._identity(conn, identity)
        routing = ArtifactRepository(conn, current.workspace_id).binding(identifier)
        if (routing.profile, artifact_job_kind(conn, current.workspace_id, routing.job_id)) != (PROFILE, 'draft_review'):
            raise unavailable_owner()
        history, _ = self._history(conn, current, routing.job_id)
        if not history.records or not isinstance(history.records[0], ReviewMachineRecord):
            raise integrity()
        machine = history.records[0]
        if machine.report.artifact.artifact_id != identifier:
            raise integrity()
        return self.artifacts.read(conn, history.binding.input, machine)
