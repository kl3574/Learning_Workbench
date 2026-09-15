"""Frozen grants and one-dispatch ledger; all writes join the caller transaction."""

from datetime import datetime
import sqlite3
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, snapshot_sha256, strict_json
from pydantic import TypeAdapter

from ..application.errors import ApiError
from ..application.provider_models import PreparedOutboundMaterial, ProviderTerminalReceipt, CheckedProviderTerminal, UsageSnapshot
from ..application.provider_ports import DispatchRecord
from ..provider_dto import ConsentCreateAck, ConsentProposalView, FrozenOutboundSummary
from .provider_repository import ProviderRepository, digest, integrity_error, require_transaction


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def prepared_digest(workspace_id: str, value: PreparedOutboundMaterial) -> str:
    return digest({'version': 'prepared-outbound-v1', 'workspace_id': workspace_id, 'job_id': value.job_id,
        'source_input_sha256': value.job_input_sha256, 'purpose': value.purpose,
        'context_snapshot': value.context_snapshot.model_dump(mode='json'),
        'messages': [x.model_dump(mode='json') for x in value.messages],
        'evidence': [x.model_dump(mode='json') for x in value.evidence], 'preparation_version': value.preparation_version})


class ConsentRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id
        self.providers = ProviderRepository(connection, workspace_id)

    def _proposal(self, identifier: str) -> tuple[ConsentProposalView, PreparedOutboundMaterial, bytes]:
        row = self.connection.execute('SELECT * FROM provider_proposals WHERE id=? AND workspace_id=?',
                                       (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, 'PROPOSAL_MISSING', '授权提案不存在或不可访问。')
        try:
            summary = FrozenOutboundSummary.model_validate(strict_json(row['summary_json']))
            material = PreparedOutboundMaterial.model_validate(strict_json(row['material_json']))
            body = bytes(row['request_body'])
            command = self.providers.command(row['command_id'])
            ack = ConsentProposalView.model_validate(strict_json(command['result_json']))
            proposal_hash = digest({'version': 'outbound-proposal-v1', 'workspace_id': self.workspace_id,
                                   'id': identifier, 'summary': summary.model_dump(mode='json')})
            if (canonical_bytes(summary).decode() != row['summary_json']
                    or canonical_bytes(material).decode() != row['material_json']
                    or canonical_bytes(strict_json(body)) != body or proposal_hash != row['proposal_sha256']
                    or row['created_at'] != summary.created_at or ack.id != identifier or ack.proposal_sha256 != proposal_hash
                    or ack.summary != summary or summary.job_id != material.job_id
                    or summary.source_job_revision != material.job_revision or summary.source_input_sha256 != material.job_input_sha256
                    or summary.input_sha256 != material.prepared_input_sha256
                    or prepared_digest(self.workspace_id, material) != summary.input_sha256
                    or summary.purpose != material.purpose or summary.context_snapshot_id != material.context_snapshot.id
                    or summary.context_snapshot_sha256 != material.context_snapshot.snapshot_sha256
                    or snapshot_sha256(material.context_snapshot) != summary.context_snapshot_sha256
                    or summary.input_token_assurance.request_body_sha256 != sha256_bytes(body)):
                raise integrity_error()
            if len(summary.messages) != len(material.messages) or len(summary.references) != len(material.evidence):
                raise integrity_error()
            for shown, actual in zip(summary.messages, material.messages, strict=True):
                if shown.role != actual.role or shown.character_count != len(actual.content) or shown.content_sha256 != sha256_bytes(actual.content.encode()):
                    raise integrity_error()
            for shown_ref, actual_ref in zip(summary.references, material.evidence, strict=True):
                if (shown_ref.ref != actual_ref.ref or shown_ref.locator != actual_ref.locator
                        or shown_ref.character_count != len(actual_ref.text)
                        or shown_ref.excerpt_sha256 != sha256_bytes(actual_ref.text.encode())):
                    raise integrity_error()
            config = self.providers.config(summary.provider_id, summary.provider_revision)
            if (config.config_sha256 != summary.config_sha256 or config.adapter != summary.adapter
                    or config.base_url != summary.base_url or config.model != summary.model or config.endpoint_policy != summary.endpoint_policy):
                raise integrity_error()
            head = self.connection.execute('SELECT id FROM provider_consent_heads WHERE proposal_id=? AND workspace_id=?',
                                            (identifier, self.workspace_id)).fetchone()
            return ack.model_copy(update={'consent_id': head['id'] if head else None}), material, body
        except (ValueError, TypeError, KeyError):
            raise integrity_error() from None

    def proposal(self, identifier: str) -> ConsentProposalView:
        return self._proposal(identifier)[0]

    def proposal_material(self, identifier: str) -> tuple[ConsentProposalView, PreparedOutboundMaterial, bytes]:
        return self._proposal(identifier)

    def add_proposal(self, view: ConsentProposalView, material: PreparedOutboundMaterial,
                     body: bytes, command_id: str) -> None:
        self.providers.writable()
        self.connection.execute('INSERT INTO provider_proposals VALUES(?,?,?,?,?,?,?,?)',
            (view.id, self.workspace_id, view.proposal_sha256, canonical_bytes(view.summary).decode(),
             canonical_bytes(material).decode(), body, command_id, view.summary.created_at))

    def consent(self, identifier: str, revision: int | None = None) -> sqlite3.Row:
        head = self.connection.execute('SELECT * FROM provider_consent_heads WHERE id=? AND workspace_id=?',
                                       (identifier, self.workspace_id)).fetchone()
        if head is None:
            if self.connection.execute('SELECT 1 FROM provider_consent_history WHERE id=? AND workspace_id=?', (identifier, self.workspace_id)).fetchone():
                raise integrity_error()
            raise ApiError(404, 'CONSENT_MISSING', '授权不存在或不可访问。')
        rows = self.connection.execute('SELECT * FROM provider_consent_history WHERE id=? AND workspace_id=? '
                                       'AND (? IS NULL OR revision<=?) ORDER BY revision',
                                       (identifier, self.workspace_id, revision, revision)).fetchall()
        proposal = self.proposal(head['proposal_id'])
        previous = None
        for index, row in enumerate(rows, 1):
            value = {k: row[k] for k in ('id', 'workspace_id', 'revision', 'proposal_id', 'status',
                                        'created_at', 'revoked_at', 'previous_sha256', 'command_id')}
            command = self.providers.command(row['command_id'])
            try:
                ack = strict_json(command['result_json'])
                if (row['revision'] != index or row['proposal_id'] != proposal.id or row['previous_sha256'] != previous
                        or digest(value) != row['history_sha256'] or index > 2 or not isinstance(ack, dict)
                        or ack.get('id') != identifier or ack.get('revision') != index
                        or row['status'] != ('active' if index == 1 else 'revoked')
                        or (row['revoked_at'] is None) != (index == 1)
                        or row['created_at'] != rows[0]['created_at']):
                    raise integrity_error()
                if index == 1:
                    grant = ConsentCreateAck.model_validate(ack)
                    if grant.proposal_id != proposal.id or grant.proposal_sha256 != proposal.proposal_sha256 or grant.summary != proposal.summary:
                        raise integrity_error()
                else:
                    if dm.MutationAck.model_validate(ack).applied is not True or instant(row['revoked_at']) < instant(row['created_at']):
                        raise integrity_error()
                TypeAdapter(dm.UTC).validate_python(row['created_at'])
            except (ValueError, TypeError, KeyError):
                raise integrity_error() from None
            previous = row['history_sha256']
        if not rows or (revision is None and head['revision'] != len(rows)) or (revision is not None and revision != len(rows)):
            raise integrity_error()
        return rows[-1]

    def consent_ids(self) -> list[str]:
        heads = self.connection.execute('SELECT id FROM provider_consent_heads WHERE workspace_id=?', (self.workspace_id,)).fetchall()
        history_ids = {row[0] for row in self.connection.execute('SELECT DISTINCT id FROM provider_consent_history WHERE workspace_id=?', (self.workspace_id,))}
        if {row[0] for row in heads} != history_ids:
            raise integrity_error()
        return [row[0] for row in heads]

    def append_consent(self, identifier: str, proposal_id: str, command_id: str, now: str,
                       *, expected_revision: int | None = None) -> int:
        self.providers.writable()
        previous = None
        created_at = now
        if expected_revision is None:
            if self.connection.execute('SELECT 1 FROM provider_consent_heads WHERE proposal_id=?', (proposal_id,)).fetchone():
                raise ApiError(409, 'CONSENT_ALREADY_GRANTED', '此提案已经批准；再次授权需要新的预览。')
            revision, status, revoked_at = 1, 'active', None
        else:
            current = self.consent(identifier)
            if current['revision'] != expected_revision:
                raise ApiError(412, 'CONSENT_VERSION_CONFLICT', '授权状态已更新，请比较当前版本。')
            if current['status'] == 'revoked':
                return current['revision']
            revision, status, revoked_at = current['revision'] + 1, 'revoked', now
            previous, created_at = current['history_sha256'], current['created_at']
        value = {'id': identifier, 'workspace_id': self.workspace_id, 'revision': revision,
            'proposal_id': proposal_id, 'status': status, 'created_at': created_at, 'revoked_at': revoked_at,
            'previous_sha256': previous, 'command_id': command_id}
        self.connection.execute('INSERT INTO provider_consent_history VALUES(?,?,?,?,?,?,?,?,?,?)',
            (identifier, self.workspace_id, revision, proposal_id, status, created_at, revoked_at, previous, digest(value), command_id))
        self.connection.execute('INSERT INTO provider_consent_heads VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision',
                                (identifier, self.workspace_id, revision, proposal_id))
        return revision

    def dispatch_material(self, consent_id: str) -> tuple[FrozenOutboundSummary, PreparedOutboundMaterial, bytes]:
        consent = self.consent(consent_id)
        view, material, body = self.proposal_material(consent['proposal_id'])
        return view.summary, material, body

    def _allowed(self, consent_id: str, now: str) -> FrozenOutboundSummary:
        self.providers.require_workspace()
        if self.providers.backup_disabled():
            raise ApiError(409, 'CONSENT_REVOKED', '备份副本中的旧许可已降权，不能外发。')
        consent = self.consent(consent_id)
        summary = self.proposal(consent['proposal_id']).summary
        if consent['status'] == 'revoked':
            raise ApiError(409, 'CONSENT_REVOKED', '此许可已撤销。')
        if instant(summary.expires_at) <= instant(now):
            raise ApiError(409, 'CONSENT_EXPIRED', '此许可已到期。')
        current = self.providers.config(summary.provider_id)
        if current.revision != summary.provider_revision or current.config_sha256 != summary.config_sha256:
            raise ApiError(409, 'PROVIDER_CONFIGURATION_CHANGED', '提供商配置已变化，需要新的授权预览。')
        if not current.secret_present or self.providers.secret_locator(current.id, current.revision) is None:
            raise ApiError(409, 'PROVIDER_SECRET_UNAVAILABLE', '提供商秘密引用不可用。')
        return summary

    def _dispatch(self, dispatch_id: str) -> sqlite3.Row:
        row = self.connection.execute('SELECT * FROM provider_dispatches WHERE id=? AND workspace_id=?',
                                       (dispatch_id, self.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, 'DISPATCH_MISSING', '提供商派发记录不存在或不可访问。')
        value = {k: row[k] for k in ('id', 'workspace_id', 'consent_id', 'job_id', 'proposal_id', 'request_body_sha256', 'started_at')}
        summary, _, body = self.dispatch_material(row['consent_id'])
        if (digest(value) != row['integrity_sha256'] or row['job_id'] != summary.job_id
                or row['request_body_sha256'] != sha256_bytes(body)
                or row['proposal_id'] != self.consent(row['consent_id'])['proposal_id']):
            raise integrity_error()
        return row

    def _record(self, row: sqlite3.Row) -> DispatchRecord:
        return DispatchRecord(id=row['id'], job_id=row['job_id'], consent_id=row['consent_id'],
            proposal_id=row['proposal_id'], request_body_sha256=row['request_body_sha256'],
            started_at=row['started_at'], terminal=self.read_terminal(row['id']))

    def begin_dispatch(self, consent_id: str, job_id: str, request_body_sha256: str,
                       started_at: str) -> tuple[DispatchRecord, bool]:
        require_transaction(self.connection)
        summary, _, body = self.dispatch_material(consent_id)
        if summary.job_id != job_id or sha256_bytes(body) != request_body_sha256:
            raise ApiError(409, 'OUTBOUND_SOURCE_CHANGED', '派发身份不匹配原冻结请求。')
        existing = self.connection.execute('SELECT id FROM provider_dispatches WHERE consent_id=? AND workspace_id=?',
                                            (consent_id, self.workspace_id)).fetchone()
        if existing:
            return self._record(self._dispatch(existing['id'])), False
        try:
            TypeAdapter(dm.UTC).validate_python(started_at)
            if instant(started_at) < instant(summary.created_at):
                raise ValueError('dispatch precedes frozen proposal')
        except (ValueError, TypeError):
            raise ApiError(409, 'PROVIDER_PROTOCOL_ERROR', '派发时间与原提案不一致。') from None
        self._allowed(consent_id, started_at)
        value = {'id': 'dispatch_' + uuid4().hex, 'workspace_id': self.workspace_id, 'consent_id': consent_id,
            'job_id': job_id, 'proposal_id': self.consent(consent_id)['proposal_id'],
            'request_body_sha256': request_body_sha256, 'started_at': started_at}
        self.connection.execute('INSERT INTO provider_dispatches VALUES(?,?,?,?,?,?,?,?)', (*value.values(), digest(value)))
        return self._record(self._dispatch(value['id'])), True

    def check_dispatch(self, dispatch_id: str, now: str) -> DispatchRecord:
        row = self._dispatch(dispatch_id)
        self._allowed(row['consent_id'], now)
        return self._record(row)

    def dispatch_for_consent(self, consent_id: str) -> DispatchRecord | None:
        self.consent(consent_id)
        row = self.connection.execute('SELECT id FROM provider_dispatches WHERE consent_id=? AND workspace_id=?',
                                       (consent_id, self.workspace_id)).fetchone()
        return self._record(self._dispatch(row['id'])) if row else None

    def usage(self, dispatch_id: str) -> UsageSnapshot:
        self._dispatch(dispatch_id)
        previous = None
        current = UsageSnapshot(input_tokens=None, output_tokens=None)
        for index, row in enumerate(self.connection.execute('SELECT * FROM provider_dispatch_usage WHERE dispatch_id=? ORDER BY sequence', (dispatch_id,)), 1):
            try:
                value = UsageSnapshot.model_validate(strict_json(row['usage_json']))
                if (row['sequence'] != index or row['previous_sha256'] != previous
                        or canonical_bytes(value).decode() != row['usage_json']
                        or digest({'dispatch_id': dispatch_id, 'sequence': index, 'usage_json': row['usage_json'],
                                   'previous_sha256': previous}) != row['integrity_sha256']):
                    raise integrity_error()
                self._monotonic(current, value)
            except (ValueError, TypeError):
                raise integrity_error() from None
            current, previous = value, row['integrity_sha256']
        return current

    @staticmethod
    def _monotonic(previous: UsageSnapshot, current: UsageSnapshot) -> None:
        for name in ('input_tokens', 'output_tokens'):
            old, new = getattr(previous, name), getattr(current, name)
            if old is not None and (new is None or new < old):
                raise ApiError(409, 'PROVIDER_USAGE_INCONSISTENT', '提供商累计计量不能回退或清除已知值。')

    def record_usage(self, dispatch_id: str, usage: UsageSnapshot) -> None:
        require_transaction(self.connection)
        current = self.usage(dispatch_id)
        self._monotonic(current, usage)
        if current == usage:
            return
        if self.read_terminal(dispatch_id) is not None:
            raise ApiError(409, 'PROVIDER_PROTOCOL_ERROR', '派发已终结，不能再接受计量。')
        last = self.connection.execute('SELECT sequence,integrity_sha256 FROM provider_dispatch_usage WHERE dispatch_id=? ORDER BY sequence DESC LIMIT 1', (dispatch_id,)).fetchone()
        value = {'dispatch_id': dispatch_id, 'sequence': last['sequence'] + 1 if last else 1,
            'usage_json': canonical_bytes(usage).decode(), 'previous_sha256': last['integrity_sha256'] if last else None}
        self.connection.execute('INSERT INTO provider_dispatch_usage VALUES(?,?,?,?,?)', (*value.values(), digest(value)))

    def read_terminal(self, dispatch_id: str) -> ProviderTerminalReceipt | None:
        dispatch = self._dispatch(dispatch_id)
        row = self.connection.execute('SELECT * FROM provider_terminals WHERE dispatch_id=? AND workspace_id=?',
                                       (dispatch_id, self.workspace_id)).fetchone()
        if row is None:
            if self.connection.execute('SELECT 1 FROM provider_artifacts WHERE dispatch_id=?', (dispatch_id,)).fetchone():
                raise integrity_error()
            return None
        try:
            receipt = ProviderTerminalReceipt.model_validate(strict_json(row['receipt_json']))
            hashed = {'version': 'provider-terminal-v1', **receipt.model_dump(mode='json', exclude={'receipt_sha256'})}
            if (canonical_bytes(receipt).decode() != row['receipt_json'] or digest(hashed) != receipt.receipt_sha256
                    or row['receipt_sha256'] != receipt.receipt_sha256 or receipt.workspace_id != self.workspace_id
                    or receipt.dispatch_id != dispatch_id or receipt.job_id != dispatch['job_id']
                    or receipt.consent_id != dispatch['consent_id'] or receipt.proposal_id != dispatch['proposal_id']
                    or receipt.request_body_sha256 != dispatch['request_body_sha256']
                    or instant(receipt.recorded_at) < instant(dispatch['started_at'])
                    or receipt.terminal.usage != self.usage(dispatch_id)):
                raise integrity_error()
            artifacts = self.connection.execute('SELECT * FROM provider_artifacts WHERE dispatch_id=?', (dispatch_id,)).fetchall()
            expected = {key: identifier for key, identifier in [('answer', receipt.answer_artifact_id),
                        ('refusal', receipt.refusal_artifact_id)] if identifier is not None}
            if len(artifacts) != len(expected):
                raise integrity_error()
            for artifact in artifacts:
                data = bytes(artifact['bytes'])
                if (artifact['workspace_id'] != self.workspace_id or expected.get(artifact['channel']) != artifact['id']
                        or not data or sha256_bytes(data) != artifact['sha256']):
                    raise integrity_error()
                data.decode('utf-8')
            return receipt
        except (ValueError, TypeError):
            raise integrity_error() from None

    def finish_dispatch(self, dispatch_id: str, terminal: CheckedProviderTerminal, answer_bytes: bytes,
                        refusal_bytes: bytes, recorded_at: str) -> ProviderTerminalReceipt:
        require_transaction(self.connection)
        dispatch = self._dispatch(dispatch_id)
        previous = self.read_terminal(dispatch_id)
        if previous is not None:
            original_artifacts = {row['channel']: bytes(row['bytes']) for row in self.connection.execute(
                'SELECT channel,bytes FROM provider_artifacts WHERE dispatch_id=?', (dispatch_id,))}
            if (previous.terminal != terminal or original_artifacts.get('answer', b'') != answer_bytes
                    or original_artifacts.get('refusal', b'') != refusal_bytes):
                raise ApiError(409, 'PROVIDER_PROTOCOL_ERROR', '原派发终态已固定，不能替换。')
            return previous
        terminal = TypeAdapter(CheckedProviderTerminal).validate_python(terminal.model_dump(mode='json'))
        try:
            TypeAdapter(dm.UTC).validate_python(recorded_at)
            if instant(recorded_at) < instant(dispatch['started_at']):
                raise ValueError('terminal precedes dispatch')
        except (ValueError, TypeError):
            raise ApiError(409, 'PROVIDER_PROTOCOL_ERROR', '终态时间不能早于派发。') from None
        self._monotonic(self.usage(dispatch_id), terminal.usage)
        ids: dict[str, str | None] = {}
        artifacts = []
        for channel, data in [('answer', answer_bytes), ('refusal', refusal_bytes)]:
            data.decode('utf-8')
            ids[channel] = None
            if data:
                identifier = 'provider_artifact_' + uuid4().hex
                artifacts.append((identifier, self.workspace_id, dispatch_id, channel, data, sha256_bytes(data)))
                ids[channel] = identifier
        receipt = ProviderTerminalReceipt(id='provider_terminal_' + uuid4().hex, workspace_id=self.workspace_id,
            dispatch_id=dispatch_id, job_id=dispatch['job_id'], consent_id=dispatch['consent_id'],
            proposal_id=dispatch['proposal_id'], request_body_sha256=dispatch['request_body_sha256'],
            terminal=terminal, answer_artifact_id=ids['answer'], refusal_artifact_id=ids['refusal'],
            recorded_at=recorded_at, receipt_sha256='0' * 64)
        receipt = receipt.model_copy(update={'receipt_sha256': digest({'version': 'provider-terminal-v1',
            **receipt.model_dump(mode='json', exclude={'receipt_sha256'})})})
        # Validate the entire receipt before writes and isolate this operation
        # even when a caller handles a storage failure inside its transaction.
        self.connection.execute('SAVEPOINT provider_terminal_write')
        try:
            self.record_usage(dispatch_id, terminal.usage)
            self.connection.executemany('INSERT INTO provider_artifacts VALUES(?,?,?,?,?,?)', artifacts)
            self.connection.execute('INSERT INTO provider_terminals VALUES(?,?,?,?)',
                (dispatch_id, self.workspace_id, canonical_bytes(receipt).decode(), receipt.receipt_sha256))
            self.read_terminal(dispatch_id)
        except BaseException:
            self.connection.execute('ROLLBACK TO provider_terminal_write')
            raise
        finally:
            self.connection.execute('RELEASE provider_terminal_write')
        return receipt

    def unfinished_dispatches(self) -> list[DispatchRecord]:
        identifiers = [row[0] for row in self.connection.execute('SELECT id FROM provider_dispatches WHERE workspace_id=? ORDER BY started_at,id', (self.workspace_id,))]
        return [record for identifier in identifiers if (record := self._record(self._dispatch(identifier))).terminal is None]
