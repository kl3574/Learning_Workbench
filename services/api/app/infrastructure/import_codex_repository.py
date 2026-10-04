"""Immutable Import-owned batch/membership checks, within a caller transaction."""
import sqlite3

from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..application.errors import ApiError
from ..application.import_codex_models import CodexImportBatch, CodexImportRecord, CodexImportPreviewReceipt
from .import_repository import json_object


def codex_import_damaged() -> ApiError:
    return ApiError(409, 'CODEX_IMPORT_HISTORY_DAMAGED', '回导来源关联不完整或已改变。')


class CodexImportRepository:
    def __init__(self, conn: sqlite3.Connection, workspace_id: str):
        if not conn.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '回导关联需要调用方事务。')
        self.conn, self.workspace_id = conn, workspace_id

    def register(self, aggregate_job_id: str, records: list[CodexImportRecord]) -> None:
        batch = CodexImportBatch(version='codex-import-batch-v1', workspace_id=self.workspace_id,
            aggregate_job_id=aggregate_job_id, records=records)
        raw = canonical_bytes(batch)
        self.conn.execute('INSERT INTO codex_import_batches VALUES(?,?,?,?)',
            (aggregate_job_id, self.workspace_id, raw.decode(), sha256_bytes(raw)))
        for ordinal, record in enumerate(records):
            value, binding = canonical_bytes(record), record.binding
            self.conn.execute('INSERT INTO codex_import_bindings VALUES(?,?,?,?,?,?,?,?)',
                (binding.import_id, self.workspace_id, aggregate_job_id, ordinal, binding.source_id,
                 binding.import_job_id, value.decode(), sha256_bytes(value)))
        if self.batch(aggregate_job_id).records != records:
            raise codex_import_damaged()

    def batch(self, aggregate_job_id: str) -> CodexImportBatch:
        try:
            row = self.conn.execute('SELECT * FROM codex_import_batches WHERE aggregate_job_id=? AND workspace_id=?',
                (aggregate_job_id, self.workspace_id)).fetchone()
            if row is None:
                raise codex_import_damaged()
            raw = row['record_json'].encode()
            batch = CodexImportBatch.model_validate(strict_json(raw))
            if (canonical_bytes(batch) != raw or sha256_bytes(raw) != row['record_sha256']
                    or batch.workspace_id != self.workspace_id or batch.aggregate_job_id != aggregate_job_id):
                raise codex_import_damaged()
            members = self.conn.execute('SELECT * FROM codex_import_bindings WHERE aggregate_job_id=? ORDER BY ordinal',
                (aggregate_job_id,)).fetchall()
            if len(members) != len(batch.records):
                raise codex_import_damaged()
            for ordinal, (member, record) in enumerate(zip(members, batch.records, strict=True)):
                binding, value = record.binding, canonical_bytes(record)
                if (binding.workspace_id != self.workspace_id or binding.aggregate_job_id != aggregate_job_id
                        or tuple(member) != (binding.import_id, self.workspace_id, aggregate_job_id, ordinal,
                            binding.source_id, binding.import_job_id, value.decode(), sha256_bytes(value))):
                    raise codex_import_damaged()
            return batch
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise codex_import_damaged() from None

    def record(self, import_id: str) -> CodexImportRecord | None:
        row = self.conn.execute('SELECT aggregate_job_id FROM codex_import_bindings WHERE import_id=? AND workspace_id=?',
            (import_id, self.workspace_id)).fetchone()
        if row is None:
            return None
        found = [item for item in self.batch(row['aggregate_job_id']).records if item.binding.import_id == import_id]
        if len(found) != 1:
            raise codex_import_damaged()
        return found[0]

    def aggregate_members(self) -> set[str]:
        batches = {row[0] for row in self.conn.execute(
            'SELECT aggregate_job_id FROM codex_import_batches WHERE workspace_id=?', (self.workspace_id,))}
        bindings = {row[0] for row in self.conn.execute(
            'SELECT aggregate_job_id FROM codex_import_bindings WHERE workspace_id=?', (self.workspace_id,))}
        if batches != bindings:
            raise codex_import_damaged()
        imports = {item.binding.import_id for aggregate in batches for item in self.batch(aggregate).records}
        sources = {item.binding.source_id for aggregate in batches for item in self.batch(aggregate).records}
        jobs = {item.binding.import_job_id for aggregate in batches for item in self.batch(aggregate).records}
        source_claims = {row[0] for row in self.conn.execute(
            "SELECT id FROM sources WHERE workspace_id=? AND (json_type(metadata_json,'$.codex_import_binding') IS NOT NULL "
            "OR json_extract(metadata_json,'$.origin')='codex_user_selected_unreviewed' "
            "OR rights='user_selected_model_output; unreviewed; rights_not_verified')", (self.workspace_id,))}
        job_claims = {row[0] for row in self.conn.execute(
            "SELECT id FROM jobs WHERE workspace_id=? AND kind='import' AND json_type(input_json,'$.codex_import_binding') IS NOT NULL",
            (self.workspace_id,))}
        if sources != source_claims or jobs != job_claims:
            raise codex_import_damaged()
        previews = {row[0] for row in self.conn.execute(
            'SELECT import_id FROM codex_import_previews WHERE workspace_id=?', (self.workspace_id,))}
        if not previews <= imports:
            raise codex_import_damaged()
        return batches

    def check_events(self, record: CodexImportRecord, row: sqlite3.Row) -> None:
        if {'staged': 'queued', 'parsing': 'running', 'preview_ready': 'awaiting_approval',
                'committed': 'completed', 'failed': 'failed', 'cancelled': 'cancelled'}.get(row['status']) != row['job_status']:
            raise codex_import_damaged()
        events = self.conn.execute('SELECT * FROM job_events WHERE job_id=? ORDER BY seq',
            (record.binding.import_job_id,)).fetchall()
        if len(events) != row['job_revision'] or not events:
            raise codex_import_damaged()
        if canonical_bytes(dict(events[0])).decode() != record.initial_event_json:
            raise codex_import_damaged()
        for revision, event in enumerate(events, 1):
            if (event['seq'] != revision or event['type'] not in
                    {'queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled'}
                    or json_object(event['payload_json']) != {'status': event['type'], 'revision': revision}):
                raise codex_import_damaged()
        if events[-1]['type'] != row['job_status']:
            raise codex_import_damaged()

    def freeze_preview(self, record: CodexImportRecord, row: sqlite3.Row) -> None:
        binding = record.binding
        if row['status'] != 'preview_ready' or row['job_status'] != 'awaiting_approval':
            raise codex_import_damaged()
        events = self.conn.execute('SELECT * FROM job_events WHERE job_id=? ORDER BY seq',
            (binding.import_job_id,)).fetchall()
        value = CodexImportPreviewReceipt(version='codex-import-preview-v1', workspace_id=self.workspace_id,
            import_id=binding.import_id, binding_sha256=sha256_bytes(canonical_bytes(binding)),
            job_revision=row['job_revision'], preview_json=row['preview_json'],
            source_metadata_json=row['source_metadata'],
            event_prefix_json=canonical_bytes([dict(event) for event in events]).decode())
        raw = canonical_bytes(value)
        self.conn.execute('INSERT INTO codex_import_previews VALUES(?,?,?,?)',
            (binding.import_id, self.workspace_id, raw.decode(), sha256_bytes(raw)))
        self.preview_receipt(record, row)

    def preview_receipt(self, record: CodexImportRecord, row: sqlite3.Row) -> str | None:
        binding = record.binding
        stored = self.conn.execute('SELECT * FROM codex_import_previews WHERE import_id=? AND workspace_id=?',
            (binding.import_id, self.workspace_id)).fetchone()
        if stored is None:
            if row['parser_version'] is not None or row['status'] in {'preview_ready', 'committed'}:
                raise codex_import_damaged()
            return None
        try:
            raw = stored['record_json'].encode()
            value = CodexImportPreviewReceipt.model_validate(strict_json(raw))
            if (canonical_bytes(value) != raw or sha256_bytes(raw) != stored['record_sha256']
                    or value.workspace_id != self.workspace_id or value.import_id != binding.import_id
                    or value.binding_sha256 != sha256_bytes(canonical_bytes(binding))
                    or row['job_revision'] < value.job_revision):
                raise codex_import_damaged()
            preview = json_object(value.preview_json)
            current = json_object(row['preview_json'])
            if (canonical_bytes(preview).decode() != value.preview_json
                    or any(current.get(key) != item for key, item in preview.items())
                    or row['parser_version'] != preview['parser_version']):
                raise codex_import_damaged()
            metadata, frozen = json_object(row['source_metadata']), json_object(value.source_metadata_json)
            if row['status'] == 'committed':
                if metadata.get('original_symbols') != frozen.get('symbols'):
                    raise codex_import_damaged()
                # Ordinary explicit commit remaps symbols and retains their original array.
                metadata = {**metadata, 'symbols': metadata.get('original_symbols')}
                del metadata['original_symbols']
            if metadata != frozen or canonical_bytes(frozen).decode() != value.source_metadata_json:
                raise codex_import_damaged()
            events = self.conn.execute('SELECT * FROM job_events WHERE job_id=? AND seq<=? ORDER BY seq',
                (binding.import_job_id, value.job_revision)).fetchall()
            if (len(events) != value.job_revision
                    or [event['seq'] for event in events] != list(range(1, value.job_revision + 1))
                    or events[-1]['type'] != 'awaiting_approval'
                    or canonical_bytes([dict(event) for event in events]).decode() != value.event_prefix_json):
                raise codex_import_damaged()
            return str(stored['record_sha256'])
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise codex_import_damaged() from None
