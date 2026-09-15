"""Recommendation-owned immutable batches, decision chains and command instances."""

from datetime import datetime
import sqlite3
from typing import Any
from uuid import uuid4

from pydantic import Field, TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json

from ..application.errors import ApiError
from ..recommendation_dto import RecommendationDecisionWrite, RecommendationRuleParameters, RecommendationView
from .database import utc_now


def invalid_recommendations() -> ApiError:
    return ApiError(409, 'RECOMMENDATION_INTEGRITY_INVALID', '推荐快照、决定历史或命令回执未通过完整性校验。')


def decision_sha256(workspace_id: str, recommendation_id: str, snapshot_sha256: str,
                    revision: int, decision: str, reason: str | None) -> str:
    return sha256_bytes(canonical_bytes({'version': 'recommendation-decision-v1',
        'workspace_id': workspace_id, 'recommendation_id': recommendation_id,
        'snapshot_sha256': snapshot_sha256, 'revision': revision, 'decision': decision, 'reason': reason}))


class FrozenRecommendationSnapshot(dm.StrictModel):
    id: dm.Id
    workspace_id: dm.Id
    generation: int = Field(ge=1)
    sequence: int = Field(ge=1)
    basis: dict[str, Any]
    basis_sha256: dm.Sha256
    generated_at: dm.UTC
    valid_until: dm.UTC | None
    rule_version: str = Field(min_length=1)
    rule_parameters: RecommendationRuleParameters
    items: list[RecommendationView]
    warnings: list[dm.Warning]

    def fingerprint(self) -> str:
        # The batch identifies the immutable recommendation, not the mutable
        # choice. Exclusion also avoids a circular initial decision hash.
        value = self.model_dump(mode='json', exclude={'items': {'__all__': {
            'decision', 'decision_revision', 'decision_sha256', 'decision_reason'}}})
        return sha256_bytes(canonical_bytes(value))


class RecommendationRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def state(self) -> sqlite3.Row | None:
        return self.connection.execute('SELECT * FROM recommendation_projection_state WHERE workspace_id=?',
                                       (self.workspace_id,)).fetchone()

    def inputs_changed(self, source: str) -> None:
        if not self.connection.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '推荐失效登记必须与来源动作处于同一事务。')
        if not isinstance(source, str) or not source or len(source) > 100 or any(
                character not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-' for character in source):
            raise ValueError('input source must be a safe application event name')
        present = self.connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='recommendation_projection_state'").fetchone()
        if present is None:
            versions = [row[0] for row in self.connection.execute('SELECT version FROM schema_migrations')]
            # Explicit pre-0009 migration/recovery execution can record the old
            # native actions. A damaged current schema must never take this path.
            if versions and all(version[:4].isdigit() and int(version[:4]) < 9 for version in versions):
                return
        state = self.state()
        generation = state['generation'] + 1 if state is not None else 1
        self.connection.execute('INSERT INTO recommendation_input_events VALUES(?,?,?,?)',
                                (self.workspace_id, generation, source, utc_now()))
        if state is None:
            self.connection.execute('INSERT INTO recommendation_projection_state(workspace_id,generation) VALUES(?,?)',
                                    (self.workspace_id, generation))
        else:
            self.connection.execute('UPDATE recommendation_projection_state SET generation=?,failure_json=NULL,retry_at=NULL '
                                    'WHERE workspace_id=?', (generation, self.workspace_id))

    def checked(self) -> tuple[sqlite3.Row | None, list[FrozenRecommendationSnapshot], dict[str, sqlite3.Row]]:
        """Validate the complete workspace history before any ID/course filtering."""
        try:
            state = self.state()
            events = self.connection.execute('SELECT * FROM recommendation_input_events WHERE workspace_id=? ORDER BY generation',
                                             (self.workspace_id,)).fetchall()
            snapshots = []
            originals: dict[str, tuple[FrozenRecommendationSnapshot, RecommendationView, str]] = {}
            for index, row in enumerate(self.connection.execute(
                    'SELECT * FROM recommendation_snapshots WHERE workspace_id=? ORDER BY sequence', (self.workspace_id,)), 1):
                value = FrozenRecommendationSnapshot.model_validate(strict_json(row['snapshot_json']))
                from ..application.recommendation_rules import RecommendationInputs
                inputs = RecommendationInputs.model_validate(value.basis)
                digest = value.fingerprint()
                if (canonical_bytes(value).decode() != row['snapshot_json'] or row['id'] != value.id
                        or value.workspace_id != self.workspace_id or row['sequence'] != value.sequence
                        or value.sequence != index or row['generation'] != value.generation
                        or row['basis_sha256'] != value.basis_sha256
                        or value.basis_sha256 != sha256_bytes(canonical_bytes(inputs))
                        or row['snapshot_sha256'] != digest or row['created_at'] != value.generated_at
                        or value.generation > len(events) or inputs.profile.workspace_id != self.workspace_id
                        or value.valid_until is not None and datetime.fromisoformat(value.valid_until.replace('Z', '+00:00'))
                           <= datetime.fromisoformat(value.generated_at.replace('Z', '+00:00'))):
                    raise invalid_recommendations()
                for item in value.items:
                    if (item.id in originals or item.decision != 'pending' or item.decision_revision != 1
                            or item.decision_reason is not None or item.staleness != 'current'
                            or item.generated_at != value.generated_at or item.rule_version != value.rule_version
                            or item.decision_sha256 != decision_sha256(self.workspace_id, item.id, digest, 1, 'pending', None)):
                        raise invalid_recommendations()
                    originals[item.id] = value, item, digest
                snapshots.append(value)
            if state is None:
                if events or snapshots:
                    raise invalid_recommendations()
            else:
                if (len(events) != state['generation'] or any(row['generation'] != index for index, row in enumerate(events, 1))
                        or state['completed_generation'] < 0 or state['completed_generation'] > state['generation']
                        or (state['snapshot_id'] is None) != (not snapshots)
                        or snapshots and (state['snapshot_id'] != snapshots[-1].id
                                          or state['completed_generation'] < snapshots[-1].generation)
                        or not snapshots and state['completed_generation'] != 0):
                    raise invalid_recommendations()
                for event in events:
                    TypeAdapter(dm.UTC).validate_python(event['occurred_at'])
                if state['failure_json'] is not None:
                    warning = dm.Warning.model_validate(strict_json(state['failure_json']))
                    if canonical_bytes(warning).decode() != state['failure_json'] or state['retry_at'] is None:
                        raise invalid_recommendations()
                    TypeAdapter(dm.UTC).validate_python(state['retry_at'])
                elif state['retry_at'] is not None:
                    raise invalid_recommendations()
            history: dict[str, list[sqlite3.Row]] = {}
            for row in self.connection.execute('SELECT * FROM recommendation_decision_history WHERE workspace_id=? '
                                               'ORDER BY recommendation_id,revision', (self.workspace_id,)):
                if row['recommendation_id'] not in originals:
                    raise invalid_recommendations()
                batch, item, digest = originals[row['recommendation_id']]
                previous = history.setdefault(item.id, [])
                TypeAdapter(dm.UTC).validate_python(row['created_at'])
                if (row['revision'] != len(previous) + 1 or row['snapshot_id'] != batch.id
                        or row['decision_sha256'] != decision_sha256(self.workspace_id, item.id, digest,
                            row['revision'], row['decision'], row['reason'])
                        or row['previous_sha256'] != (previous[-1]['decision_sha256'] if previous else None)):
                    raise invalid_recommendations()
                if not previous:
                    if (row['decision'] != 'pending' or row['reason'] is not None or row['created_at'] != batch.generated_at):
                        raise invalid_recommendations()
                else:
                    RecommendationDecisionWrite(decision=row['decision'], reason=row['reason'])
                    if (row['decision'], row['reason']) == (previous[-1]['decision'], previous[-1]['reason']):
                        raise invalid_recommendations()
                previous.append(row)
            heads = {row['recommendation_id']: row for row in self.connection.execute(
                'SELECT * FROM recommendation_decision_heads WHERE workspace_id=?', (self.workspace_id,))}
            if set(heads) != set(originals) or set(history) != set(originals):
                raise invalid_recommendations()
            for identifier, head in heads.items():
                last = history[identifier][-1]
                if head['revision'] != last['revision'] or head['decision_sha256'] != last['decision_sha256']:
                    raise invalid_recommendations()
            applied_commands: dict[tuple[str, int], int] = {}
            for row in self.connection.execute('SELECT * FROM recommendation_command_receipts WHERE workspace_id=?', (self.workspace_id,)):
                ack = dm.MutationAck.model_validate(strict_json(row['result_json']))
                records = history.get(row['recommendation_id'], [])
                if (row['actor'] != self.workspace_id or row['route'] != f"POST /recommendations/{row['recommendation_id']}/decision"
                        or ack.id != row['recommendation_id'] or ack.revision != row['revision']
                        or not 2 <= ack.revision <= len(records)
                        or row['decision_sha256'] != records[ack.revision - 1]['decision_sha256']
                        or canonical_bytes(ack).decode() != row['result_json']):
                    raise invalid_recommendations()
                TypeAdapter(dm.Sha256).validate_python(row['request_sha256'])
                TypeAdapter(dm.UTC).validate_python(row['command_created_at'])
                changed = records[ack.revision - 1]
                command_basis = changed['previous_sha256'] if ack.applied else changed['decision_sha256']
                expected_request = {'body': {'decision': changed['decision'], 'reason': changed['reason']}, 'if_match': command_basis}
                if row['request_sha256'] != sha256_bytes(canonical_bytes(expected_request)):
                    raise invalid_recommendations()
                if ack.applied:
                    pair = ack.id, ack.revision
                    applied_commands[pair] = applied_commands.get(pair, 0) + 1
            if (set(applied_commands) != {(identifier, row['revision']) for identifier, rows in history.items() for row in rows[1:]}
                    or any(count != 1 for count in applied_commands.values())):
                raise invalid_recommendations()
            for command in self.connection.execute("SELECT * FROM idempotency WHERE actor=? AND route LIKE 'POST /recommendations/%/decision'",
                                                   (self.workspace_id,)):
                TypeAdapter(dm.UTC).validate_python(command['created_at'])
                if command['expires_at'] is not None:
                    TypeAdapter(dm.UTC).validate_python(command['expires_at'])
                binding = self.connection.execute('SELECT * FROM recommendation_command_receipts WHERE actor=? AND route=? '
                    'AND key=? AND command_created_at=?',
                    (self.workspace_id, command['route'], command['key'], command['created_at'])).fetchone()
                if (binding is None or binding['request_sha256'] != command['request_sha256']
                        or binding['result_json'] != command['result_json']):
                    raise invalid_recommendations()
            return state, snapshots, {identifier: rows[-1] for identifier, rows in history.items()}
        except (ValueError, TypeError, KeyError, IndexError):
            raise invalid_recommendations() from None

    def publish(self, *, generation: int, basis: dict[str, Any], generated_at: str, valid_until: str | None,
                rule_version: str, parameters: RecommendationRuleParameters,
                items: list[RecommendationView], warnings: list[dm.Warning]) -> FrozenRecommendationSnapshot | None:
        state, snapshots, _ = self.checked()
        if state is None or state['generation'] != generation:
            return None
        basis_hash = sha256_bytes(canonical_bytes(basis))
        previous = snapshots[-1] if snapshots else None
        if (previous is not None and previous.basis_sha256 == basis_hash and previous.rule_version == rule_version
                and previous.rule_parameters == parameters and (previous.valid_until is None or previous.valid_until > generated_at)):
            self.connection.execute('UPDATE recommendation_projection_state SET completed_generation=?,failure_json=NULL,retry_at=NULL '
                                    'WHERE workspace_id=?', (generation, self.workspace_id))
            return previous
        value = FrozenRecommendationSnapshot(id=f'recommendations_{uuid4().hex}', workspace_id=self.workspace_id,
            generation=generation, sequence=len(snapshots) + 1, basis=basis, basis_sha256=basis_hash,
            generated_at=generated_at, valid_until=valid_until, rule_version=rule_version,
            rule_parameters=parameters, items=items, warnings=warnings)
        digest = value.fingerprint()
        value = value.model_copy(update={'items': [item.model_copy(update={'decision_sha256': decision_sha256(
            self.workspace_id, item.id, digest, 1, 'pending', None)}) for item in items]})
        self.connection.execute('INSERT INTO recommendation_snapshots VALUES(?,?,?,?,?,?,?,?)',
            (value.id, self.workspace_id, value.sequence, generation, basis_hash, digest, canonical_bytes(value).decode(), generated_at))
        for item in value.items:
            self.connection.execute('INSERT INTO recommendation_decision_history VALUES(?,?,1,?,\'pending\',NULL,?,NULL,?)',
                                    (self.workspace_id, item.id, value.id, item.decision_sha256, generated_at))
            self.connection.execute('INSERT INTO recommendation_decision_heads VALUES(?,?,1,?)',
                                    (self.workspace_id, item.id, item.decision_sha256))
        self.connection.execute('UPDATE recommendation_projection_state SET completed_generation=?,snapshot_id=?,failure_json=NULL,retry_at=NULL '
                                'WHERE workspace_id=? AND generation=?', (generation, value.id, self.workspace_id, generation))
        self.checked()
        return value

    def decide(self, snapshot: FrozenRecommendationSnapshot, item: RecommendationView,
               current: sqlite3.Row, request: RecommendationDecisionWrite) -> dm.MutationAck:
        if current['decision'] == request.decision and current['reason'] == request.reason:
            return dm.MutationAck(id=item.id, revision=current['revision'], applied=False)
        revision = current['revision'] + 1
        digest = decision_sha256(self.workspace_id, item.id, snapshot.fingerprint(), revision, request.decision, request.reason)
        self.connection.execute('INSERT INTO recommendation_decision_history VALUES(?,?,?,?,?,?,?,?,?)',
            (self.workspace_id, item.id, revision, snapshot.id, request.decision, request.reason, digest,
             current['decision_sha256'], utc_now()))
        changed = self.connection.execute('UPDATE recommendation_decision_heads SET revision=?,decision_sha256=? '
            'WHERE workspace_id=? AND recommendation_id=? AND revision=? AND decision_sha256=?',
            (revision, digest, self.workspace_id, item.id, current['revision'], current['decision_sha256']))
        if changed.rowcount != 1:
            raise ApiError(412, 'REVISION_CONFLICT', '推荐决定已更新，请读取原推荐后比较。')
        return dm.MutationAck(id=item.id, revision=revision, applied=True)

    def checked_receipt(self, *, route: str, key: str, request_hash: str, result: dict[str, Any],
                        applied: bool) -> dm.MutationAck:
        try:
            ack = dm.MutationAck.model_validate(result)
            command = self.connection.execute('SELECT * FROM idempotency WHERE actor=? AND route=? AND key=?',
                                              (self.workspace_id, route, key)).fetchone()
            history = self.connection.execute('SELECT * FROM recommendation_decision_history WHERE workspace_id=? '
                'AND recommendation_id=? AND revision=?', (self.workspace_id, ack.id, ack.revision)).fetchone()
            if (command is None or history is None or command['request_sha256'] != request_hash
                    or route != f'POST /recommendations/{ack.id}/decision'
                    or canonical_bytes(ack).decode() != command['result_json']):
                raise invalid_recommendations()
            if applied:
                self.connection.execute('INSERT INTO recommendation_command_receipts VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (self.workspace_id, route, key, command['created_at'], request_hash, self.workspace_id,
                     ack.id, ack.revision, history['decision_sha256'], canonical_bytes(ack).decode()))
            binding = self.connection.execute('SELECT * FROM recommendation_command_receipts WHERE actor=? AND route=? '
                'AND key=? AND command_created_at=?', (self.workspace_id, route, key, command['created_at'])).fetchone()
            if (binding is None or binding['workspace_id'] != self.workspace_id or binding['recommendation_id'] != ack.id
                    or binding['request_sha256'] != request_hash or binding['revision'] != ack.revision
                    or binding['decision_sha256'] != history['decision_sha256']
                    or binding['result_json'] != canonical_bytes(ack).decode()):
                raise invalid_recommendations()
            self.checked()
            return ack
        except (ValueError, TypeError, KeyError):
            raise invalid_recommendations() from None
