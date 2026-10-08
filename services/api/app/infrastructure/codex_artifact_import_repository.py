"""Aggregate Jobs and complete immutable command membership, no Import SQL."""
from dataclasses import dataclass

from ..application.codex_artifact_import_models import (
    ArtifactImportCreated, ArtifactImportCancelled, ArtifactImportEnvelope, ArtifactImportInput,
)
from ..application.codex_turn_context import damaged
from ..serialization import canonical_json, content_sha256
from .authoring_job_repository import AuthoringJobRepository
from .codex_turn_repository import decode
from .security import historical_session_belongs_to


class CodexArtifactImportJobs(AuthoringJobRepository):
    kinds = frozenset({'codex_artifact_import'})
    transitions = {'queued': {'completed', 'failed', 'cancelled'}}


@dataclass
class CheckedArtifactImport:
    created: ArtifactImportCreated
    events: list[ArtifactImportEnvelope]


class CodexArtifactImportRepository:
    def __init__(self, conn, workspace):
        if not conn.in_transaction:
            raise damaged()
        self.conn, self.workspace = conn, workspace
        self.jobs = CodexArtifactImportJobs(conn, workspace)

    def checked(self):
        heads = self.conn.execute('SELECT * FROM codex_artifact_import_heads WHERE workspace_id=?', (self.workspace,)).fetchall()
        rows = self.conn.execute('SELECT * FROM codex_artifact_import_events WHERE workspace_id=?', (self.workspace,)).fetchall()
        witnesses = self.conn.execute('SELECT * FROM codex_artifact_import_members WHERE workspace_id=?', (self.workspace,)).fetchall()
        commands = self.conn.execute('SELECT * FROM codex_artifact_import_commands WHERE workspace_id=?', (self.workspace,)).fetchall()
        jobs = self.jobs.member_ids()
        if (jobs != {row['job_id'] for row in heads} or jobs != {row['job_id'] for row in rows}
                or {(row['job_id'], row['seq'], row['record_sha256']) for row in rows}
                    != {(row['job_id'], row['seq'], row['record_sha256']) for row in witnesses}):
            raise damaged()
        result, expected_commands = {}, []
        for head in heads:
            selected = sorted((row for row in rows if row['job_id'] == head['job_id']), key=lambda row: row['seq'])
            if len(selected) != head['event_count']:
                raise damaged()
            chain, previous, original = [], None, None
            for seq, row in enumerate(selected, 1):
                value = decode(ArtifactImportEnvelope, row['record_json'])
                if (value.workspace_id != self.workspace or value.job_id != head['job_id'] or value.seq != seq
                        or row['seq'] != seq or value.previous_sha256 != previous
                        or content_sha256(value) != row['record_sha256']):
                    raise damaged()
                event = value.event
                if isinstance(event, ArtifactImportCreated):
                    if seq != 1 or event.ack.id != value.job_id or event.input.workspace_id != self.workspace:
                        raise damaged()
                    original = event
                    job = self.jobs.load(value.job_id)
                    if job['input_json'] != canonical_json(event.input):
                        raise damaged()
                    actor, route, target = event.input.actor_session_id, 'import', event.input.session_id
                else:
                    if seq == 1 or event.ack.id != value.job_id:
                        raise damaged()
                    self.jobs.verify_cancel_ack(value.job_id, event.body.expected_revision,
                        event.ack, event.basis_revision, event.ack.updated_at)
                    actor, route, target = event.actor_session_id, 'cancel', value.job_id
                if not historical_session_belongs_to(self.conn, self.workspace, actor):
                    raise damaged()
                expected_commands.append((self.workspace, actor, route, target, event.key,
                    value.job_id, seq, content_sha256(event)))
                chain.append(value)
                previous = row['record_sha256']
            if original is None or previous != head['head_sha256']:
                raise damaged()
            result[head['job_id']] = CheckedArtifactImport(original, chain)
        if sorted(expected_commands) != sorted(tuple(row) for row in commands):
            raise damaged()
        return result

    def append(self, job_id, event: ArtifactImportCreated | ArtifactImportCancelled, previous=None):
        seq = len(previous.events) + 1 if previous else 1
        digest = content_sha256(previous.events[-1]) if previous else None
        envelope = ArtifactImportEnvelope(version='codex-artifact-import-event-v1', workspace_id=self.workspace,
            job_id=job_id, seq=seq, previous_sha256=digest, event=event)
        hashed = content_sha256(envelope)
        if previous is None:
            self.conn.execute('INSERT INTO codex_artifact_import_heads VALUES(?,?,?,?)', (self.workspace, job_id, 1, hashed))
        else:
            changed = self.conn.execute('UPDATE codex_artifact_import_heads SET event_count=?,head_sha256=? WHERE job_id=? AND event_count=? AND head_sha256=?',
                (seq, hashed, job_id, seq-1, digest))
            if changed.rowcount != 1:
                raise damaged()
        self.conn.execute('INSERT INTO codex_artifact_import_events VALUES(?,?,?,?,?)',
            (self.workspace, job_id, seq, canonical_json(envelope), hashed))
        self.conn.execute('INSERT INTO codex_artifact_import_members VALUES(?,?,?,?)', (self.workspace, job_id, seq, hashed))
        actor = event.input.actor_session_id if isinstance(event, ArtifactImportCreated) else event.actor_session_id
        route = 'import' if isinstance(event, ArtifactImportCreated) else 'cancel'
        target = event.input.session_id if isinstance(event, ArtifactImportCreated) else job_id
        self.conn.execute('INSERT INTO codex_artifact_import_commands VALUES(?,?,?,?,?,?,?,?)',
            (self.workspace, actor, route, target, event.key, job_id, seq, content_sha256(event)))

    def create_job(self, identifier, value: ArtifactImportInput):
        self.jobs.create(identifier, 'codex_artifact_import', value)
