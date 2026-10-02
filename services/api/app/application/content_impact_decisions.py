"""Author decisions on immutable Content events; reads never reconcile state."""
from collections.abc import Iterator
from contextlib import contextmanager
import re
import sqlite3
from typing import Literal, Self

from pydantic import model_validator
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json
from ..authoring_dto import AuthoringModel, NonBlank
from ..content_impact_dto import (
    ContentImpactView, ImpactArtifact, ImpactClassification,
    ImpactObjectDecisionReceipt, ImpactObjectDecisionWrite,
)
from ..infrastructure.blobs import BlobStore
from ..infrastructure.content_repository import ContentRepository, reference, missing, damaged
from ..infrastructure.database import Database, utc_now
from ..infrastructure.security import SessionIdentity, current_session_identity, historical_session_belongs_to
from .artifacts import ArtifactsService
from .authoring_context import AuthoringContext
from .content import ContentService
from .content_impact import ContentImpactSnapshot, impact_snapshot
from .errors import ApiError
from .providers import validate_key


def integrity() -> ApiError:
    return ApiError(409, 'CONTENT_IMPACT_INTEGRITY_ERROR', '内容影响决定的持久历史未通过完整性校验。')


def conflict() -> ApiError:
    return ApiError(412, 'CONTENT_IMPACT_BASIS_CHANGED', '内容或决定依据已变化，请重新读取后明确决定。')


class ImpactDecisionRecord(AuthoringModel):
    version: Literal['content-impact-decision-v1']
    workspace_id: dm.Id
    old_ref: dm.ContentRef
    new_ref: dm.ContentRef
    route: NonBlank
    command_key: NonBlank
    request: ImpactObjectDecisionWrite
    previous_receipt_sha256: dm.Sha256 | None
    receipt: ImpactObjectDecisionReceipt

    @model_validator(mode='after')
    def bound_command(self) -> Self:
        r, request = self.receipt, self.request
        if (self.route != f'POST /content/impacts/{r.event_id}/decisions'
                or r.target_id != request.target_id or r.observed_ref != request.observed_ref
                or r.decision_revision != request.expected_decision_revision + 1
                or r.event_snapshot_sha256 != request.expected_event_snapshot_sha256
                or r.decision != request.decision or r.reason != request.reason
                or r.request_sha256 != metadata_sha256(request)
                or [x.id for x in r.evidence_artifacts] != request.evidence_artifact_ids
                or (r.decision_revision == 1) != (self.previous_receipt_sha256 is None)):
            raise ValueError('Decision must retain its complete original command and adjacent revision')
        validate_key(self.command_key)
        return self


class ContentImpactDecisionService:
    def __init__(self, database: Database, artifacts: ArtifactsService):
        self.database, self.artifacts = database, artifacts
        self.content = ContentService(database)

    @contextmanager
    def _access(self, identity: SessionIdentity, *, readonly: bool) -> Iterator[tuple[sqlite3.Connection, SessionIdentity]]:
        try:
            with self.database.transaction() as conn:
                if readonly:
                    conn.execute('PRAGMA query_only=ON')
                current = current_session_identity(conn, identity)
                ContentRepository(conn, current.workspace_id).require_workspace()
                AuthoringContext.check_access(conn, current)
                yield conn, current
        except sqlite3.Error:
            raise ApiError(503, 'CONTENT_STORAGE_UNAVAILABLE', '内容存储暂不可用。', True) from None

    def _body(self, repo: ContentRepository, value: object) -> str | None:
        if not isinstance(value, dm.ContentBlock):
            return None
        info = repo.body_info(value)
        raw = BlobStore(self.database.settings.data_dir, max_bytes=max(info.size, 1)).read(
            info.sha256, expected_size=info.size)
        try:
            text = raw.decode('utf-8')
            if '\r' in text or len(text) > 400000:
                raise damaged()
        except UnicodeError:
            raise damaged() from None
        return info.sha256

    @staticmethod
    def _classification(snapshot: ContentImpactSnapshot, ref: dm.ContentRef) -> ImpactClassification:
        return 'exact_ref' if ref in snapshot.exact_dependency_refs else 'id_only_candidate'

    @staticmethod
    def _target_ids(repo: ContentRepository, snapshot: ContentImpactSnapshot) -> list[str]:
        result = []
        for identifier in snapshot.affected_ids:
            if identifier == snapshot.old_ref.id:
                continue
            row = repo.connection.execute(
                'SELECT kind,current_revision FROM objects WHERE id=? AND workspace_id=?',
                (identifier, repo.workspace_id)).fetchone()
            # Other owner IDs stay in affected_ids, never become Content decisions.
            if row is not None and row['kind'] not in {'note', 'route'}:
                if row['current_revision'] is None:
                    raise integrity()
                result.append(identifier)
        return result

    def _evidence(self, conn: sqlite3.Connection, identity: SessionIdentity, identifiers: list[str]) -> list[ImpactArtifact]:
        result = []
        for identifier in identifiers:
            _, artifact = self.artifacts.read_in_transaction(conn, identity, identifier)
            result.append(ImpactArtifact(id=identifier, sha256=artifact.sha256))
        return result

    def _history(self, conn: sqlite3.Connection, identity: SessionIdentity,
                 snapshot: ContentImpactSnapshot) -> list[ImpactDecisionRecord]:
        rows = conn.execute('SELECT * FROM content_impact_decisions WHERE event_id=? '
                            'ORDER BY target_id,decision_revision', (snapshot.event_id,)).fetchall()
        records: list[ImpactDecisionRecord] = []
        heads: dict[str, ImpactObjectDecisionReceipt] = {}
        repo = ContentRepository(conn, identity.workspace_id)
        targets = self._target_ids(repo, snapshot)
        for row in rows:
            try:
                raw = row['record_json']
                record = ImpactDecisionRecord.model_validate(strict_json(raw))
                r = record.receipt
                previous = heads.get(r.target_id)
                if (canonical_bytes(record).decode() != raw or metadata_sha256(record) != row['record_sha256']
                        or row['workspace_id'] != identity.workspace_id or record.workspace_id != identity.workspace_id
                        or row['event_id'] != snapshot.event_id or r.event_id != snapshot.event_id
                        or row['target_id'] != r.target_id or r.target_id not in targets
                        or row['decision_revision'] != r.decision_revision
                        or row['actor_session_id'] != r.actor_session_id
                        or row['route'] != record.route or row['command_key'] != record.command_key
                        or record.old_ref != snapshot.old_ref or record.new_ref != snapshot.new_ref
                        or snapshot.snapshot_sha256 is None or r.event_snapshot_sha256 != snapshot.snapshot_sha256
                        or r.classification != self._classification(snapshot, r.observed_ref)
                        or r.decision_revision != (previous.decision_revision + 1 if previous else 1)
                        or record.previous_receipt_sha256 != (previous.receipt_sha256 if previous else None)):
                    raise integrity()
                if not historical_session_belongs_to(conn, record.workspace_id, r.actor_session_id):
                    raise integrity()
                original = repo.load(r.observed_ref.entity, r.target_id, r.observed_ref.revision).value
                if reference(original) != r.observed_ref or self._body(repo, original) != r.target_body_sha256:
                    raise integrity()
                if self._evidence(conn, identity, record.request.evidence_artifact_ids) != r.evidence_artifacts:
                    raise integrity()
            except ApiError as error:
                if error.status in {404, 412}:
                    raise integrity() from None
                raise
            except (ValueError, TypeError, KeyError, AttributeError):
                raise integrity() from None
            records.append(record)
            heads[r.target_id] = r
        head_rows = conn.execute('SELECT * FROM content_impact_decision_heads WHERE event_id=?',
                                 (snapshot.event_id,)).fetchall()
        if len(head_rows) != len(heads):
            raise integrity()
        for row in head_rows:
            head = heads.get(row['target_id'])
            if (head is None or row['workspace_id'] != identity.workspace_id
                    or row['decision_revision'] != head.decision_revision
                    or row['receipt_sha256'] != head.receipt_sha256):
                raise integrity()
        return records

    def read(self, identity: SessionIdentity, event_id: str, *, target_id: str | None = None,
             limit: int = 20, cursor: str | None = None) -> ContentImpactView:
        self.content._identity(event_id)
        if target_id is not None:
            self.content._identity(target_id)
        context = self.content._context(identity.workspace_id, 'impact:' + event_id, target_id or '', limit)
        with self._access(identity, readonly=True) as (conn, current):
            snapshot = impact_snapshot(conn, current.workspace_id, event_id)
            repo = ContentRepository(conn, current.workspace_id)
            targets = self._target_ids(repo, snapshot)
            if target_id is not None and target_id not in targets:
                raise missing()
            records = self._history(conn, current, snapshot)
            # A signed cursor freezes the first page's history high-water mark;
            # target/ref validity is always evaluated at the current read.
            position = self.content._position(cursor, context, str)
            maximum = conn.execute('SELECT COALESCE(MAX(rowid),0) FROM content_impact_decisions '
                                   'WHERE event_id=?', (event_id,)).fetchone()[0]
            last_target, last_revision = '', 0
            if position is not None:
                match = re.fullmatch(r'([0-9]+):([A-Za-z][A-Za-z0-9_-]{0,79}):([1-9][0-9]*)', str(position))
                if match is None:
                    raise ApiError(422, 'SCHEMA_INVALID', '影响决定分页游标无效。')
                watermark, last_target, last_revision = int(match[1]), match[2], int(match[3])
                if watermark > maximum:
                    raise ApiError(422, 'SCHEMA_INVALID', '影响决定分页游标无效。')
            else:
                watermark = maximum
            selected_rows = conn.execute('SELECT target_id,decision_revision FROM content_impact_decisions '
                'WHERE event_id=? AND rowid<=? ORDER BY target_id,decision_revision', (event_id, watermark)).fetchall()
            selected = {(row['target_id'], row['decision_revision']) for row in selected_rows}
            page = [record.receipt for record in records
                    if (record.receipt.target_id, record.receipt.decision_revision) in selected
                    and (target_id is None or record.receipt.target_id == target_id)
                    and (record.receipt.target_id, record.receipt.decision_revision) > (last_target, last_revision)]
            heads = {record.receipt.target_id: record.receipt for record in records}
            pending, action = [], []
            for identifier in targets:
                stored = repo.current(identifier)
                target = reference(stored.value)
                body_sha = self._body(repo, stored.value)
                decision = heads.get(identifier)
                if (decision is None or stored.lifecycle != 'active' or decision.observed_ref != target
                        or decision.target_body_sha256 != body_sha):
                    pending.append(identifier)
                elif decision.decision == 'new_revision_required':
                    action.append(identifier)
            items = page[:limit]
            next_cursor = (self.content._cursor(context, f'{watermark}:{items[-1].target_id}:{items[-1].decision_revision}')
                           if len(page) > limit else None)
            return ContentImpactView(event_id=event_id, old_ref=snapshot.old_ref, new_ref=snapshot.new_ref,
                reason=snapshot.reason, evidence_version=snapshot.evidence_version,
                event_snapshot_sha256=snapshot.snapshot_sha256, affected_ids=list(snapshot.affected_ids),
                exact_dependency_refs=list(snapshot.exact_dependency_refs),
                conservative_only_ids=list(snapshot.conservative_only_ids), pending_target_ids=pending,
                action_required_target_ids=action,
                target_decision_head=(heads[target_id].decision_revision if target_id in heads else 0)
                    if target_id is not None else None,
                decisions=items, next_cursor=next_cursor)

    def decide(self, identity: SessionIdentity, event_id: str, body: ImpactObjectDecisionWrite,
               key: str) -> ImpactObjectDecisionReceipt:
        self.content._identity(event_id)
        key = validate_key(key)
        body = ImpactObjectDecisionWrite.model_validate(body.model_dump(mode='python', warnings='error'))
        with self._access(identity, readonly=False) as (conn, current):
            snapshot = impact_snapshot(conn, current.workspace_id, event_id)
            repo = ContentRepository(conn, current.workspace_id)
            records = self._history(conn, current, snapshot)
            route = f'POST /content/impacts/{event_id}/decisions'
            for record in records:
                if record.receipt.actor_session_id == current.id and record.route == route and record.command_key == key:
                    if record.request != body:
                        raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '同一命令键不能用于不同内容。')
                    return record.receipt
            if snapshot.snapshot_sha256 is None:
                raise ApiError(409, 'CONTENT_IMPACT_LEGACY_UNVERIFIED', '历史事件没有发布时冻结的依据，只能读取。')
            if body.target_id not in self._target_ids(repo, snapshot):
                raise missing()
            if body.expected_event_snapshot_sha256 != snapshot.snapshot_sha256:
                raise conflict()
            history = [record.receipt for record in records if record.receipt.target_id == body.target_id]
            latest = history[-1] if history else None
            if body.expected_decision_revision != (latest.decision_revision if latest else 0):
                raise conflict()
            target = repo.current(body.target_id)
            actual_ref = reference(target.value)
            if target.lifecycle != 'active' or actual_ref != body.observed_ref:
                raise conflict()
            body_sha = self._body(repo, target.value)
            artifacts = self._evidence(conn, current, body.evidence_artifact_ids)
            fields = dict(event_id=event_id, target_id=body.target_id,
                decision_revision=body.expected_decision_revision + 1,
                classification=self._classification(snapshot, actual_ref), observed_ref=actual_ref.model_dump(mode='json'),
                target_metadata_sha256=actual_ref.sha256, target_body_sha256=body_sha,
                event_snapshot_sha256=snapshot.snapshot_sha256, decision=body.decision, reason=body.reason,
                evidence_artifacts=[x.model_dump(mode='json') for x in artifacts], actor_session_id=current.id,
                decided_at=utc_now(), request_sha256=metadata_sha256(body))
            receipt = ImpactObjectDecisionReceipt.model_validate({**fields, 'receipt_sha256': sha256_bytes(canonical_bytes(fields))})
            record = ImpactDecisionRecord(version='content-impact-decision-v1', workspace_id=current.workspace_id,
                old_ref=snapshot.old_ref, new_ref=snapshot.new_ref, route=route, command_key=key, request=body,
                previous_receipt_sha256=latest.receipt_sha256 if latest else None, receipt=receipt)
            conn.execute('INSERT INTO content_impact_decisions(workspace_id,event_id,target_id,decision_revision,'
                'actor_session_id,route,command_key,record_json,record_sha256) VALUES(?,?,?,?,?,?,?,?,?)',
                (current.workspace_id, event_id, body.target_id, receipt.decision_revision, current.id,
                 route, key, canonical_bytes(record).decode(), metadata_sha256(record)))
            conn.execute('INSERT INTO content_impact_decision_heads(workspace_id,event_id,target_id,'
                'decision_revision,receipt_sha256) VALUES(?,?,?,?,?) ON CONFLICT(event_id,target_id) DO UPDATE '
                'SET decision_revision=excluded.decision_revision,receipt_sha256=excluded.receipt_sha256',
                (current.workspace_id, event_id, body.target_id, receipt.decision_revision, receipt.receipt_sha256))
            self._history(conn, current, snapshot)
            return receipt
