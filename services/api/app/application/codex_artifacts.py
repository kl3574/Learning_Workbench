"""Checked Broker answer materialization and immutable Artifact-owned reads."""
from uuid import uuid4

from packages.contracts.canonical import sha256_bytes
from ..codex_turn_dto import CodexArtifactEntry, CodexArtifactManifest, CodexArtifactManifestView
from ..import_dto import DownloadArtifact
from ..infrastructure.artifact_repository import ArtifactRepository
from ..infrastructure.blobs import BlobInfo, BlobStore
from ..infrastructure.codex_answer_materializer import CheckedAnswerMaterializer, LIMIT
from ..infrastructure.codex_artifact_repository import CodexArtifactRepository
from ..infrastructure.database import utc_now
from ..serialization import content_sha256
from .codex_artifact_models import AnswerSource, ArtifactRecord, ArtifactTerminalReceipt, TurnManifestReady
from .codex_bootstrap_access import current_control_access
from .codex_turn_context import damaged
from .errors import ApiError
from .import_codex_models import CheckedCodexArtifactSource


class CodexArtifactsService:
    def __init__(self, turns, producer: CheckedAnswerMaterializer | None = None):
        self.turns, self.database, self.producer = turns, turns.database, producer
        self.blobs = BlobStore(self.database.settings.data_dir, max_bytes=LIMIT)

    def _source(self, conn, workspace, history, turn_id, provider, result) -> AnswerSource:
        state, turn = self.turns._find(history, turn_id)
        if provider.started is None or result is None or result.first_response is None:
            raise damaged()
        operations = self.turns.approvals.verify_history(conn, workspace, history) if self.turns.approvals else {}
        hashes = []
        for identifier in turn.control.approval_ids:
            operation = operations[identifier]
            if operation.started is not None:
                if operation.finished is None or operation.finished.outcome == 'unknown':
                    raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '不能证明全部原操作已可靠结束。')
                hashes.append(content_sha256({'operation': operation.operation.model_dump(mode='json'),
                    'started': operation.started.model_dump(mode='json'), 'finished': operation.finished.model_dump(mode='json')}))
        raw = result.answer.encode('utf-8')
        return AnswerSource(version='codex-checked-answer-source-v1', workspace_id=workspace,
            session_id=state.anchor.session_id, turn_id=turn_id, job_id=turn.control.job.id,
            execution_owner_id=provider.started.execution_owner_id, start_sha256=content_sha256(provider.started),
            model_result_sha256=content_sha256(result), runtime_profile_sha256=turn.prepared.command.ack.summary.runtime.profile_sha256,
            operation_result_sha256=hashes, answer_sha256=sha256_bytes(raw), answer_bytes=len(raw))

    def collect_stopped_answer(self, workspace, turn_id, owner, result):
        """Only called after the explicitly registered synchronous adapter returns.

        This read gathers original owner facts. File I/O then happens with no
        SQLite transaction held; registration rechecks the facts in the finish TX.
        """
        if self.producer is None:
            return None
        if type(self.producer) is not CheckedAnswerMaterializer or self.producer.data_dir != self.database.settings.data_dir:
            raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '原产物生成器当前不可用。')
        if result is None or result.first_response is None:
            return None
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            _, _, history = self.turns._owned_state(conn, workspace)
            providers, _ = self.turns.outbound_owner.owned_states(conn, workspace)
            provider = providers[turn_id]
            source = self._source(conn, workspace, history, turn_id, provider, result)
            if provider.finished is not None or source.execution_owner_id != owner:
                raise damaged()
        return self.producer.collect(source, result.answer)

    def record_manifest(self, conn, workspace, history, state, turn, provider, result, collection, outcome, code):
        if collection.source != self._source(conn, workspace, history, turn.control.id, provider, result):
            raise damaged()
        receipt = ArtifactTerminalReceipt(version='codex-artifact-terminal-receipt-v1', collection=collection,
            source_outcome=outcome, error_code=code)
        entries = []
        artifacts = ArtifactRepository(conn, workspace)
        for file in collection.files:
            raw = self.blobs.read(file.sha256, file.size)
            if sha256_bytes(raw) != file.sha256:
                raise damaged()
            entry = CodexArtifactEntry(artifact_id='artifact_'+uuid4().hex, scan='PASS', **file.model_dump())
            artifacts.register(identifier=entry.artifact_id, job_id=turn.control.job.id, profile='codex_turn_output_v1',
                info=BlobInfo(file.sha256, f'blobs/{file.sha256[:2]}/{file.sha256}', file.size),
                filename=file.logical_path, media_type=file.media_type)
            entries.append(entry)
        now = utc_now()
        manifest = CodexArtifactManifest(version='codex-artifact-manifest-v1', id='codexmanifest_'+uuid4().hex,
            revision=1, session_id=state.anchor.session_id, turn_id=turn.control.id, run_id=turn.control.job.id,
            source_job_id=turn.control.job.id, source_outcome=outcome, runtime_profile_sha256=collection.source.runtime_profile_sha256,
            terminal_receipt_sha256=content_sha256(receipt), scan_profile_sha256=collection.scan_profile_sha256,
            created_at=now, entries=entries, excluded=[], total_bytes=sum(item.size for item in entries),
            mathematical='NOT_RUN', sources='NOT_RUN', independent_pedagogy='NOT_RUN')
        view = CodexArtifactManifestView(manifest=manifest, manifest_sha256=content_sha256(manifest))
        record = ArtifactRecord(version='codex-artifact-record-v1', receipt=receipt, manifest=view)
        CodexArtifactRepository(conn, workspace).insert(record)
        return TurnManifestReady(kind='manifest_ready', turn_id=turn.control.id,
            receipt_sha256=content_sha256(receipt), manifest=view), now

    def verify_sources(self, conn, workspace, history):
        records = CodexArtifactRepository(conn, workspace).checked(history)
        if not records:
            return records
        providers, _ = self.turns.outbound_owner.owned_states(conn, workspace)
        for identifier, record in records.items():
            provider = providers.get(identifier)
            if provider is None or provider.finished is None:
                raise damaged()
            source = self._source(conn, workspace, history, identifier, provider, provider.finished.execution_result)
            if source != record.receipt.collection.source:
                raise damaged()
        return records

    def read_manifest(self, identity, session_id, turn_id):
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current, _, _, history = self.turns._state(conn, identity, subject=True)
            _, turn = self.turns._find(history, turn_id)
            if turn.control.session_id != session_id:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '原任务不属于此会话。')
            records = self.verify_sources(conn, current.workspace_id, history)
            record = records.get(turn_id)
            if record is None:
                raise ApiError(404, 'CODEX_ARTIFACT_MISSING', '原任务没有登记受检产物清单。')
            for item in record.manifest.manifest.entries:
                self.blobs.read(item.sha256, item.size)
            value = record.manifest
        return self.turns._deliver(identity, value, subject=True)

    def read_artifact(self, conn, identity, identifier):
        current = current_control_access(conn, identity, write=True)
        _, _, history = self.turns._owned_state(conn, current.workspace_id)
        records = self.verify_sources(conn, current.workspace_id, history)
        for record in records.values():
            for item in record.manifest.manifest.entries:
                if item.artifact_id == identifier:
                    raw = self.blobs.read(item.sha256, item.size)
                    return raw, DownloadArtifact(artifact_id=identifier, filename=item.logical_path,
                        media_type=item.media_type, size=item.size, sha256=item.sha256,
                        download_path=f'/api/v1/artifacts/{identifier}/download')
        raise ApiError(404, 'CODEX_ARTIFACT_MISSING', '此附件不属于原受检清单。')

    def read_selected_artifacts(self, conn, identity, session_id, body):
        """Import calls this real owner port inside its caller's transaction."""
        current, _, _, history = self.turns._state(conn, identity, subject=True)
        _, turn = self.turns._find(history, body.turn_id)
        if turn.control.session_id != session_id:
            raise ApiError(409, 'CODEX_BINDING_INVALID', '原任务不属于此会话。')
        records = self.verify_sources(conn, current.workspace_id, history)
        record = records.get(body.turn_id)
        if record is None:
            raise ApiError(404, 'CODEX_ARTIFACT_MISSING', '原任务没有登记受检清单。')
        view = record.manifest
        if body.expected_manifest_sha256 != view.manifest_sha256:
            raise ApiError(412, 'REVISION_MISMATCH', '原清单摘要与明确选择不一致。')
        if (view.manifest.source_outcome == 'unknown' or len(body.artifact_ids) != len(set(body.artifact_ids))):
            raise ApiError(409, 'CODEX_ARTIFACT_REJECTED', '原产物终态或选择不允许回导。')
        by_id = {item.artifact_id:item for item in view.manifest.entries}
        result = []
        for identifier in body.artifact_ids:
            entry = by_id.get(identifier)
            if entry is None or entry.import_kind is None or entry.size == 0:
                raise ApiError(409, 'CODEX_ARTIFACT_REJECTED', '选择不是此清单的可导入原件。')
            raw, descriptor = self.read_artifact(conn, current, identifier)
            if descriptor.sha256 != entry.sha256 or descriptor.size != entry.size:
                raise damaged()
            result.append(CheckedCodexArtifactSource(workspace_id=current.workspace_id, actor_session_id=current.id,
                session_id=session_id, turn_id=body.turn_id, source_job_id=turn.control.job.id,
                terminal_receipt_sha256=view.manifest.terminal_receipt_sha256, manifest_id=view.manifest.id,
                manifest_sha256=view.manifest_sha256, artifact_id=entry.artifact_id, artifact_sha256=entry.sha256,
                artifact_size=entry.size, import_kind=entry.import_kind, filename=entry.logical_path,
                media_type=entry.media_type, data=raw))
        return tuple(result)
