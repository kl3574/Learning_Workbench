"""Publication-owned permanent commands, full history and server-private CAS."""
import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..application.errors import ApiError
from ..application.publication_admission_models import DraftPublishWrite
from ..application.publication_models import (
    PublicationEvent, PublicationHistory, PublicationRecord, EditPublicationRecord, RestorePublicationRecord, SinglePublicationRecord, PublicationState, integrity, validated, publication_record,
)


class PublicationRepository:
    def __init__(self, conn: sqlite3.Connection, workspace_id: str):
        if not conn.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '发布持久操作需要当前事务。')
        self.conn, self.workspace_id = conn, workspace_id

    @staticmethod
    def _decode(model, raw, digest):
        try:
            value = publication_record(strict_json(raw)) if model is None else validated(model, strict_json(raw))
            if canonical_bytes(value).decode() != raw or sha256_bytes(raw.encode()) != digest:
                raise integrity()
            return value
        except (ValueError, TypeError, AttributeError):
            raise integrity() from None

    def load(self, identifier: str) -> PublicationHistory:
        row = self.conn.execute('SELECT * FROM draft_publications WHERE id=? AND workspace_id=?',
                                (identifier, self.workspace_id)).fetchone()
        result = self.conn.execute('SELECT * FROM draft_publication_results WHERE publication_id=?',
                                   (identifier,)).fetchone()
        if row is None or result is None or row['state'] != 'published' or row['revision'] != 4:
            raise integrity()
        record = self._decode(None, result['record_json'], result['sha256'])
        candidate = record.candidate
        if (record.id != row['id'] or record.workspace_id != row['workspace_id']
                or record.owner != row['owner'] or candidate.draft_id != row['draft_id']
                or candidate.draft_revision != row['draft_revision'] or candidate.entity != row['entity']
                or candidate.candidate_sha256 != row['candidate_sha256'] or record.adopted_at != row['adopted_at']):
            raise integrity()
        events = []
        for event in self.conn.execute('SELECT * FROM draft_publication_events WHERE publication_id=? ORDER BY revision',
                                       (identifier,)):
            decoded = self._decode(PublicationEvent, event['event_json'], event['sha256'])
            if decoded.publication_id != identifier or decoded.revision != event['revision']:
                raise integrity()
            events.append(decoded)
        commands = self.conn.execute('SELECT * FROM draft_publication_commands WHERE publication_id=?',
                                     (identifier,)).fetchall()
        if (len(commands) != 1 or tuple(commands[0]) != (record.workspace_id, record.actor_id, record.route,
                                                       record.command_key, record.id)):
            raise integrity()
        if isinstance(record, SinglePublicationRecord):
            binding = self.conn.execute('SELECT * FROM single_publication_bindings WHERE publication_id=?',
                                        (identifier,)).fetchone()
            if binding is None or tuple(binding) != (record.workspace_id, candidate.draft_id,
                    candidate.draft_revision, candidate.candidate_sha256, record.id, result['sha256']):
                raise integrity()
        return validated(PublicationHistory, dict(record=record, events=events))

    def replay(self, actor_id: str, route: str, key: str, body: DraftPublishWrite) -> PublicationHistory | None:
        row = self.conn.execute('SELECT publication_id FROM draft_publication_commands WHERE workspace_id=? '
            'AND actor_id=? AND route=? AND command_key=?', (self.workspace_id, actor_id, route, key)).fetchone()
        if row is None:
            return None
        history = self.load(row[0])
        if canonical_bytes(validated(DraftPublishWrite, body)) != canonical_bytes(history.record.request):
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原发布命令键已用于不同的完整命令。')
        return history

    def for_candidate(self, candidate: dm.DraftCandidate) -> PublicationHistory | None:
        row = self.conn.execute('SELECT id FROM draft_publications WHERE workspace_id=? AND draft_id=? '
            'AND draft_revision=?', (self.workspace_id, candidate.draft_id, candidate.draft_revision)).fetchone()
        if row is None:
            return None
        history = self.load(row[0])
        if history.record.candidate != candidate:
            raise integrity()
        return history

    def retained_source_claim(self, ref: dm.ContentRef) -> bool:
        """An older publication can witness a frozen origin lost before a later migration."""
        rows = self.conn.execute('SELECT r.* FROM draft_publication_results r JOIN draft_publications p ON p.id=r.publication_id '
            "WHERE p.workspace_id=? AND json_extract(r.record_json,'$.result.id')=? AND json_extract(r.record_json,'$.result.revision')=?",
            (self.workspace_id, ref.id, ref.revision)).fetchall()
        for row in rows:
            record = self._decode(None, row['record_json'], row['sha256'])
            if record.result == ref and isinstance(record, (PublicationRecord, RestorePublicationRecord)) and record.source is not None:
                return True
        return False

    def single_for_candidate(self, candidate: dm.DraftCandidate) -> PublicationHistory | None:
        """A lost terminal association is corruption, never a fresh draft projection."""
        history = self.for_candidate(candidate)
        bindings = self.conn.execute('SELECT publication_id FROM single_publication_bindings '
            'WHERE workspace_id=? AND draft_id=?', (self.workspace_id, candidate.draft_id)).fetchall()
        results = self.conn.execute("SELECT publication_id FROM draft_publication_results WHERE "
            "json_extract(record_json,'$.version')='single-worked-example-publication-v1' AND "
            "json_extract(record_json,'$.workspace_id')=? AND json_extract(record_json,'$.candidate.draft_id')=?",
            (self.workspace_id, candidate.draft_id)).fetchall()
        expected = [] if history is None else [history.record.id]
        if ([row[0] for row in bindings] != expected or [row[0] for row in results] != expected
                or (history is not None and not isinstance(history.record, SinglePublicationRecord))):
            raise integrity()
        return history

    def require_unpublished_draft(self, draft_id: str) -> None:
        """A committed publication is terminal for new commands on this producer Draft."""
        row = self.conn.execute('SELECT id FROM draft_publications WHERE workspace_id=? AND draft_id=? LIMIT 1',
                                (self.workspace_id, draft_id)).fetchone()
        if row is not None:
            self.load(row['id'])
            raise ApiError(409, 'DRAFT_ALREADY_PUBLISHED', '此草稿已经发布；请从明确选择的正式修订创建新草稿。')

    def _event(self, identifier: str, revision: int, state: PublicationState, now: str) -> None:
        value = validated(PublicationEvent, dict(version='draft-publication-event-v1', publication_id=identifier,
                                                 revision=revision, state=state, recorded_at=now))
        raw = canonical_bytes(value)
        self.conn.execute('INSERT INTO draft_publication_events VALUES(?,?,?,?)',
                          (identifier, revision, raw.decode(), sha256_bytes(raw)))

    def adopt(self, identifier: str, candidate: dm.DraftCandidate, now: str, *, owner: str = 'import') -> None:
        candidate = validated(dm.DraftCandidate, candidate)
        if self.for_candidate(candidate) is not None:
            raise ApiError(409, 'DRAFT_ALREADY_PUBLISHED', '此精确候选已经发布。')
        self.conn.execute('INSERT INTO draft_publications(id,workspace_id,draft_id,draft_revision,owner,entity,'
            'candidate_sha256,state,revision,adopted_at) VALUES(?,?,?,?,?,?,?,\'draft\',1,?)',
            (identifier, self.workspace_id, candidate.draft_id, candidate.draft_revision, owner, candidate.entity,
             candidate.candidate_sha256, now))
        self._event(identifier, 1, 'draft', now)

    def advance(self, identifier: str, expected_revision: int, expected_state: PublicationState,
                state: PublicationState, now: str) -> None:
        changed = self.conn.execute('UPDATE draft_publications SET state=?,revision=revision+1 WHERE id=? '
            'AND workspace_id=? AND revision=? AND state=?',
            (state, identifier, self.workspace_id, expected_revision, expected_state))
        if changed.rowcount != 1:
            raise ApiError(409, 'PUBLICATION_STATE_CONFLICT', '发布内部状态已经改变。')
        self._event(identifier, expected_revision + 1, state, now)

    def finish(self, record: PublicationRecord | EditPublicationRecord | RestorePublicationRecord | SinglePublicationRecord) -> PublicationHistory:
        record = publication_record(record)
        if record.workspace_id != self.workspace_id:
            raise integrity()
        raw = canonical_bytes(record)
        self.conn.execute('INSERT INTO draft_publication_results VALUES(?,?,?)',
                          (record.id, raw.decode(), sha256_bytes(raw)))
        if isinstance(record, SinglePublicationRecord):
            self.conn.execute('INSERT INTO single_publication_bindings VALUES(?,?,?,?,?,?)',
                (self.workspace_id, record.candidate.draft_id, record.candidate.draft_revision,
                 record.candidate.candidate_sha256, record.id, sha256_bytes(raw)))
        self.conn.execute('INSERT INTO draft_publication_commands VALUES(?,?,?,?,?)',
                          (self.workspace_id, record.actor_id, record.route, record.command_key, record.id))
        self.advance(record.id, 3, 'approved', 'published', record.published_at)
        return self.load(record.id)
