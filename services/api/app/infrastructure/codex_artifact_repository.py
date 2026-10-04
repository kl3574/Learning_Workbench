"""Immutable copied-output membership, independently bound by the Codex chain."""
from ..application.codex_artifact_models import ArtifactRecord
from ..application.codex_turn_context import damaged
from ..import_dto import DownloadArtifact
from ..serialization import canonical_json, content_sha256
from .artifact_repository import ArtifactRepository
from .codex_turn_repository import decode
from .codex_answer_materializer import SCAN_PROFILE


class CodexArtifactRepository:
    def __init__(self, connection, workspace):
        if not connection.in_transaction:
            raise damaged()
        self.conn, self.workspace = connection, workspace

    def checked(self, history) -> dict[str, ArtifactRecord]:
        expected = {turn.control.id: turn for state in history.values() for turn in state.turns.values()
                    if turn.manifest is not None}
        rows = self.conn.execute('SELECT * FROM codex_artifact_records WHERE workspace_id=?', (self.workspace,)).fetchall()
        members = self.conn.execute('SELECT * FROM codex_artifact_members WHERE workspace_id=?', (self.workspace,)).fetchall()
        registered = self.conn.execute("SELECT id FROM artifacts WHERE workspace_id=? AND profile='codex_turn_output_v1'", (self.workspace,)).fetchall()
        if {row['turn_id'] for row in rows} != set(expected):
            raise damaged()
        result, actual_members = {}, []
        artifacts = ArtifactRepository(self.conn, self.workspace)
        for row in rows:
            record = decode(ArtifactRecord, row['record_json'])
            turn = expected[row['turn_id']]
            source, view = record.receipt.collection.source, record.manifest
            witness = turn.manifest
            if (record.manifest != witness.manifest or witness.receipt_sha256 != content_sha256(record.receipt)
                    or content_sha256(record) != row['record_sha256'] or source.workspace_id != self.workspace
                    or source.turn_id != turn.control.id or source.session_id != turn.control.session_id
                    or source.job_id != turn.control.job.id or turn.control.manifest_id != view.manifest.id
                    or record.receipt.collection.scan_profile_sha256 != content_sha256(SCAN_PROFILE)
                    or turn.control.execution != 'terminal' or turn.control.outcome != record.receipt.source_outcome
                    or turn.control.error_code != record.receipt.error_code):
                raise damaged()
            for ordinal, entry in enumerate(view.manifest.entries):
                binding = artifacts.binding(entry.artifact_id)
                if binding.profile != 'codex_turn_output_v1' or binding.job_id != source.job_id:
                    raise damaged()
                artifacts.manifest_sha256(entry.artifact_id, DownloadArtifact(artifact_id=entry.artifact_id,
                    filename=entry.logical_path, media_type=entry.media_type, size=entry.size, sha256=entry.sha256,
                    download_path=f"/api/v1/artifacts/{entry.artifact_id}/download"))
                actual_members.append((self.workspace, source.turn_id, ordinal, entry.artifact_id, content_sha256(entry)))
            result[source.turn_id] = record
        if (sorted(tuple(row) for row in members) != sorted(actual_members)
                or {row[0] for row in registered} != {item[3] for item in actual_members}):
            raise damaged()
        return result

    def insert(self, record: ArtifactRecord) -> None:
        source = record.receipt.collection.source
        if source.workspace_id != self.workspace:
            raise damaged()
        self.conn.execute('INSERT INTO codex_artifact_records VALUES(?,?,?,?)',
            (self.workspace, source.turn_id, canonical_json(record), content_sha256(record)))
        for index, entry in enumerate(record.manifest.manifest.entries):
            self.conn.execute('INSERT INTO codex_artifact_members VALUES(?,?,?,?,?)',
                (self.workspace, source.turn_id, index, entry.artifact_id, content_sha256(entry)))
