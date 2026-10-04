"""Explicit ordinary Import previews, with permanent aggregate command ACKs."""
from uuid import uuid4

from packages.contracts import domain_models as dm
from ..codex_turn_dto import CodexArtifactImportView, CodexArtifactImportItem, CodexArtifactImportWrite
from ..infrastructure.codex_artifact_import_repository import CodexArtifactImportRepository
from ..infrastructure.codex_turn_repository import decode
from ..serialization import canonical_json, content_sha256
from .codex_artifact_import_models import (
    ArtifactImportCreated, ArtifactImportCancelled, ArtifactImportInput, ArtifactImportResult,
)
from .codex_bootstrap_access import current_control_access
from .codex_turn_context import damaged
from .errors import ApiError
from .providers import validate_key


def cancel_digest(job_id, actor, key, body, basis):
    return content_sha256({'job_id':job_id, 'actor_session_id':actor, 'key':key,
        'body':body.model_dump(mode='json'), 'basis_revision':basis})


class CodexArtifactImports:
    def __init__(self, artifacts, imports):
        self.artifacts, self.imports = artifacts, imports
        self.turns, self.database = artifacts.turns, artifacts.database

    def _checked(self, conn, workspace):
        _, _, history = self.turns._owned_state(conn, workspace)
        manifests = self.artifacts.verify_sources(conn, workspace, history)
        repo = CodexArtifactImportRepository(conn, workspace)
        records = repo.checked()
        if self.imports.codex_aggregate_members(conn, workspace) != set(records):
            raise damaged()
        stages = {}
        for identifier, state in records.items():
            original = state.created
            record = manifests.get(original.input.request.turn_id)
            if record is None or record.manifest.manifest.source_outcome == 'unknown':
                raise damaged()
            view = record.manifest
            manifest = view.manifest
            entries = {item.artifact_id:item for item in manifest.entries}
            if (manifest.session_id != original.input.session_id
                    or view.manifest_sha256 != original.input.request.expected_manifest_sha256):
                raise damaged()
            for item in original.bindings:
                entry = entries.get(item.artifact_id)
                if (entry is None or item.manifest_id != manifest.id or item.source_job_id != manifest.source_job_id
                        or item.terminal_receipt_sha256 != manifest.terminal_receipt_sha256
                        or item.artifact_sha256 != entry.sha256 or item.artifact_size != entry.size
                        or entry.import_kind is None):
                    raise damaged()
            actual = self.imports.check_codex_bindings(conn, workspace, tuple(original.bindings))
            stages[identifier] = actual
            job = repo.jobs.load(identifier)
            if job['status'] in {'completed', 'failed', 'cancelled'}:
                result = decode(ArtifactImportResult, job['result_json'])
                if result.outcome != job['status']:
                    raise damaged()
                if result.outcome == 'completed':
                    if result.preview_receipts != [item.preview_receipt_sha256 for item in actual] or not all(item.preview_reached for item in actual):
                        raise damaged()
                elif result.outcome == 'failed':
                    failed = {item.binding.import_id for item in actual if item.status in {'failed', 'cancelled'}}
                    if len(set(result.failed_import_ids)) != len(result.failed_import_ids) or not set(result.failed_import_ids) <= failed:
                        raise damaged()
                elif not any(isinstance(event.event, ArtifactImportCancelled) and result.cancel_request_sha256 == cancel_digest(
                        identifier, event.event.actor_session_id, event.event.key, event.event.body, event.event.basis_revision)
                        for event in state.events):
                    raise damaged()
        return repo, records, stages

    @staticmethod
    def _replay(records, actor, session, body, key):
        for state in records.values():
            event = state.created
            if (event.input.actor_session_id, event.input.session_id, event.key) == (actor, session, key):
                if canonical_json(event.input.request) != canonical_json(body):
                    raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原回导命令与本次完整选择不同。')
                return event.ack
        return None

    def create(self, identity, session_id, body, key):
        key = validate_key(key)
        body = CodexArtifactImportWrite.model_validate(body.model_dump(mode='json'))
        with self.database.transaction() as conn:
            current = current_control_access(conn, identity, write=True)
            repo, records, _ = self._checked(conn, current.workspace_id)
            ack = self._replay(records, current.id, session_id, body, key)
            if ack is None:
                # Real selected bytes and all current admission precede the new
                # aggregate. Import rechecks via this same owned source port.
                self.artifacts.read_selected_artifacts(conn, current, session_id, body)
                identifier = 'job_'+uuid4().hex
                value = ArtifactImportInput(version='codex-artifact-import-input-v1', workspace_id=current.workspace_id,
                    actor_session_id=current.id, session_id=session_id, request=body)
                repo.create_job(identifier, value)
                bindings = self.imports.stage_codex_artifacts(conn, current, session_id=session_id, body=body,
                    aggregate_job_id=identifier, source=self.artifacts)
                ack = dm.JobRef(id=identifier, status='queued')
                event = ArtifactImportCreated(kind='created', input=value, key=key, ack=ack, bindings=list(bindings))
                repo.append(identifier, event)
                self._checked(conn, current.workspace_id)
            current_control_access(conn, current, write=True)
        return self.turns._deliver(identity, ack, subject=True)

    def read(self, identity, identifier):
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current = current_control_access(conn, identity, write=True)
            repo, records, stages = self._checked(conn, current.workspace_id)
            state = records.get(identifier)
            if state is None:
                raise ApiError(404, 'REFERENCE_MISSING', '本工作区没有此回导任务。')
            original = state.created
            value = CodexArtifactImportView(job=dm.JobRef(id=identifier, status=repo.jobs.load(identifier)['status']),
                session_id=original.input.session_id, turn_id=original.input.request.turn_id,
                manifest_sha256=original.input.request.expected_manifest_sha256,
                actor_session_id=original.input.actor_session_id,
                items=[CodexArtifactImportItem(artifact_id=item.binding.artifact_id,
                    source_sha256=item.binding.artifact_sha256, import_id=item.binding.import_id, job=item.job)
                    for item in stages[identifier]])
        return self.turns._deliver(identity, value, subject=True)

    def job(self, identity, identifier):
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current = current_control_access(conn, identity, write=False)
            repo, _, _ = self._checked(conn, current.workspace_id)
            result = repo.jobs.snapshot(identifier)
        return self.turns._deliver(identity, result, subject=False)

    def cancel_job(self, identity, identifier, body, key):
        key = validate_key(key)
        with self.database.transaction() as conn:
            current = current_control_access(conn, identity, write=False)
            repo, states, _ = self._checked(conn, current.workspace_id)
            state = states.get(identifier)
            if state is None:
                raise ApiError(404, 'JOB_MISSING', '本工作区没有此回导任务。')
            for envelope in state.events:
                event = envelope.event
                if isinstance(event, ArtifactImportCancelled) and (event.actor_session_id, event.key) == (current.id, key):
                    if canonical_json(event.body) != canonical_json(body):
                        raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原取消命令与本次请求不同。')
                    ack = event.ack
                    break
            else:
                row = repo.jobs.load(identifier)
                basis = row['revision']
                if row['status'] == 'queued':
                    if body.expected_revision != basis:
                        raise ApiError(412, 'REVISION_MISMATCH', '回导任务已更新。')
                    self.imports.cancel_codex_imports(conn, current.workspace_id, tuple(state.created.bindings))
                    result = ArtifactImportResult(version='codex-artifact-import-result-v1', outcome='cancelled',
                        preview_receipts=[], failed_import_ids=[], cancel_request_sha256=cancel_digest(
                            identifier, current.id, key, body, basis))
                    repo.jobs.transition(row, 'cancelled', cancel=True, result=result.model_dump(mode='json'))
                ack = repo.jobs.snapshot(identifier)
                repo.append(identifier, ArtifactImportCancelled(kind='cancelled', actor_session_id=current.id,
                    key=key, body=body, basis_revision=basis, ack=ack), state)
                self._checked(conn, current.workspace_id)
            current_control_access(conn, current, write=False)
        return self.turns._deliver(identity, ack, subject=False)

    def run_once(self) -> bool:
        """Local convergence only; no parser, file scan, model or CLI is invoked."""
        workspace = self.database.workspace_id()
        with self.database.transaction() as conn:
            repo, records, stages = self._checked(conn, workspace)
            for identifier in sorted(records):
                row = repo.jobs.load(identifier)
                if row['status'] != 'queued':
                    continue
                children = stages[identifier]
                failed = [item.binding.import_id for item in children if item.status in {'failed', 'cancelled'}]
                receipts = [item.preview_receipt_sha256 for item in children]
                if failed:
                    result = ArtifactImportResult(version='codex-artifact-import-result-v1', outcome='failed',
                        preview_receipts=[], failed_import_ids=failed, cancel_request_sha256=None)
                elif all(item.preview_reached for item in children) and all(receipts):
                    result = ArtifactImportResult(version='codex-artifact-import-result-v1', outcome='completed',
                        preview_receipts=receipts, failed_import_ids=[], cancel_request_sha256=None)
                else:
                    continue
                repo.jobs.transition(row, result.outcome, result=result.model_dump(mode='json'))
                self._checked(conn, workspace)
                return True
        return False
