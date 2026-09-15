"""Provider-owned configuration and durable command history in caller transactions."""

import hmac
import re
import sqlite3
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel, TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json

from ..application.errors import ApiError
from ..provider_dto import ProviderConfigView, ProviderConfigWrite
from .database import utc_now

Model = TypeVar('Model', bound=BaseModel)


def integrity_error() -> ApiError:
    return ApiError(503, 'PROVIDER_INTEGRITY_INVALID', '提供商授权历史无法通过完整性校验。')


def require_transaction(connection: sqlite3.Connection) -> None:
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '提供商写入需要有效的调用方事务。')


def digest(value: object) -> str:
    return sha256_bytes(canonical_bytes(value))


def config_digest(workspace: str, value: ProviderConfigView) -> str:
    fields = value.model_dump(mode='json', exclude={'config_sha256', 'configured'})
    return digest({'version': 'provider-config-v1', 'workspace_id': workspace, **fields})


def historical_scope_digest(connection: sqlite3.Connection, workspace_id: str) -> str:
    """Hashes owned audit bytes without authentication locators or HMAC material."""
    tables = ('provider_command_history', 'provider_config_history', 'provider_config_heads',
        'provider_proposals', 'provider_consent_history', 'provider_consent_heads',
        'provider_dispatches', 'provider_dispatch_usage', 'provider_artifacts', 'provider_terminals')
    result = {}
    for table in tables:
        predicate = ('dispatch_id IN (SELECT id FROM provider_dispatches WHERE workspace_id=?)'
                     if table == 'provider_dispatch_usage' else 'workspace_id=?')
        rows = connection.execute(f'SELECT * FROM {table} WHERE {predicate}', (workspace_id,)).fetchall()
        values = [{key: {'sha256': sha256_bytes(row[key]), 'bytes': len(row[key])} if isinstance(row[key], bytes)
                   else row[key] for key in row.keys()} for row in rows]
        result[table] = sorted(values, key=canonical_bytes)
    return digest(result)


class ProviderRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def require_workspace(self) -> None:
        if not self.connection.execute('SELECT 1 FROM workspace WHERE id=?', (self.workspace_id,)).fetchone():
            raise ApiError(404, 'WORKSPACE_MISSING', '工作区不存在或不可访问。')

    def backup_disabled(self) -> bool:
        row = self.connection.execute('SELECT * FROM provider_backup_projections WHERE workspace_id=?',
                                      (self.workspace_id,)).fetchone()
        if row is None:
            return False
        try:
            value = strict_json(row['projection_json'])
            if (canonical_bytes(value).decode() != row['projection_json'] or digest(value) != row['projection_sha256']
                    or not isinstance(value, dict) or value.get('workspace_id') != self.workspace_id
                    or value.get('dispatch_disabled') is not True
                    or value.get('historical_scope_sha256') != row['historical_scope_sha256']
                    or historical_scope_digest(self.connection, self.workspace_id) != row['historical_scope_sha256']):
                raise integrity_error()
        except (ValueError, TypeError):
            raise integrity_error() from None
        return True

    def writable(self) -> None:
        require_transaction(self.connection)
        self.require_workspace()
        if self.backup_disabled():
            raise ApiError(409, 'PROVIDER_BACKUP_DISABLED', '恢复副本的旧提供商许可不可继续执行。')

    def _command(self, row: sqlite3.Row) -> None:
        try:
            command = strict_json(row['command_json'])
            result = strict_json(row['result_json'])
            material = {key: row[key] for key in ('id', 'workspace_id', 'actor', 'route', 'command_key',
                                                 'command_json', 'result_json', 'created_at')}
            if (row['workspace_id'] != self.workspace_id or row['actor'] != self.workspace_id
                    or canonical_bytes(command).decode() != row['command_json']
                    or canonical_bytes(result).decode() != row['result_json']
                    or digest(material) != row['integrity_sha256']
                    or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', row['command_key']) is None):
                raise integrity_error()
            TypeAdapter(dm.UTC).validate_python(row['created_at'])
            private = self.connection.execute('SELECT * FROM provider_private_commands WHERE command_id=?', (row['id'],)).fetchone()
            if private is None:
                if not self.backup_disabled():
                    raise integrity_error()
            elif (re.fullmatch(r'[0-9a-f]{64}', private['fingerprint']) is None
                  or digest({'command_id': row['id'], 'fingerprint': private['fingerprint']}) != private['integrity_sha256']):
                raise integrity_error()
        except (ValueError, TypeError, KeyError):
            raise integrity_error() from None

    def command(self, identifier: str) -> sqlite3.Row:
        row = self.connection.execute('SELECT * FROM provider_command_history WHERE id=? AND workspace_id=?',
                                      (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise integrity_error()
        self._command(row)
        return row

    def replay(self, route: str, key: str, fingerprint: str, model: type[Model]) -> Model | None:
        row = self.connection.execute('SELECT * FROM provider_command_history WHERE workspace_id=? AND actor=? AND command_key=?',
                                      (self.workspace_id, self.workspace_id, key)).fetchone()
        if row is None:
            return None
        self._command(row)
        if self.backup_disabled():
            raise ApiError(409, 'PROVIDER_BACKUP_DISABLED', '恢复副本不能重放旧秘密或许可命令。')
        private = self.connection.execute('SELECT fingerprint FROM provider_private_commands WHERE command_id=?', (row['id'],)).fetchone()
        if row['route'] != route or not hmac.compare_digest(private['fingerprint'], fingerprint):
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '该幂等键已用于不同的完整命令。')
        try:
            return model.model_validate(strict_json(row['result_json']))
        except (ValueError, TypeError):
            raise integrity_error() from None

    def record_command(self, identifier: str, route: str, key: str, command: object,
                       fingerprint: str, result: BaseModel) -> None:
        self.writable()
        value = {'id': identifier, 'workspace_id': self.workspace_id, 'actor': self.workspace_id,
                 'route': route, 'command_key': key, 'command_json': canonical_bytes(command).decode(),
                 'result_json': canonical_bytes(result).decode(), 'created_at': utc_now()}
        self.connection.execute('INSERT INTO provider_command_history VALUES(?,?,?,?,?,?,?,?,?)',
            (*value.values(), digest(value)))
        private = {'command_id': identifier, 'fingerprint': fingerprint}
        self.connection.execute('INSERT INTO provider_private_commands VALUES(?,?,?)',
                                (identifier, fingerprint, digest(private)))

    def configs(self) -> list[ProviderConfigView]:
        self.require_workspace()
        identifiers = [row[0] for row in self.connection.execute(
            'SELECT DISTINCT provider_id FROM provider_config_history WHERE workspace_id=? ORDER BY provider_id', (self.workspace_id,))]
        heads = [row[0] for row in self.connection.execute(
            'SELECT provider_id FROM provider_config_heads WHERE workspace_id=? ORDER BY provider_id', (self.workspace_id,))]
        if identifiers != heads:
            raise integrity_error()
        return [self.config(identifier) for identifier in identifiers]

    def config(self, provider_id: str, revision: int | None = None) -> ProviderConfigView:
        self.require_workspace()
        head = self.connection.execute('SELECT * FROM provider_config_heads WHERE provider_id=? AND workspace_id=?',
                                       (provider_id, self.workspace_id)).fetchone()
        if head is None:
            if self.connection.execute('SELECT 1 FROM provider_config_history WHERE provider_id=? AND workspace_id=?',
                                        (provider_id, self.workspace_id)).fetchone():
                raise integrity_error()
            raise ApiError(404, 'PROVIDER_MISSING', '提供商配置不存在或不可访问。')
        rows = self.connection.execute('SELECT * FROM provider_config_history WHERE provider_id=? AND workspace_id=? '
                                       'AND (? IS NULL OR revision<=?) ORDER BY revision',
                                       (provider_id, self.workspace_id, revision, revision)).fetchall()
        previous = None
        configs = []
        try:
            for index, row in enumerate(rows, 1):
                value = ProviderConfigView.model_validate(strict_json(row['config_json']))
                material = {key: row[key] for key in ('provider_id', 'workspace_id', 'revision', 'config_json',
                    'config_sha256', 'previous_sha256', 'command_id', 'created_at')}
                command = self.command(row['command_id'])
                ack = strict_json(command['result_json'])
                if (row['revision'] != index or value.revision != index or value.id != provider_id
                        or value.config_sha256 != row['config_sha256'] or config_digest(self.workspace_id, value) != value.config_sha256
                        or canonical_bytes(value).decode() != row['config_json'] or row['previous_sha256'] != previous
                        or digest(material) != row['history_sha256'] or not isinstance(ack, dict)
                        or ack.get('id') != provider_id or ack.get('revision') != index
                        or ack.get('config_sha256') != value.config_sha256 or ack.get('secret_present') != value.secret_present):
                    raise integrity_error()
                TypeAdapter(dm.UTC).validate_python(row['created_at'])
                self._locator(value)
                configs.append(value)
                previous = row['history_sha256']
            if not configs or (revision is None and head['revision'] != len(configs)):
                raise integrity_error()
            if revision is not None:
                if not 1 <= revision <= len(configs):
                    raise integrity_error()
                return configs[revision - 1]
            return configs[-1]
        except (ValueError, TypeError, KeyError):
            raise integrity_error() from None

    def _locator(self, config: ProviderConfigView) -> str | None:
        row = self.connection.execute('SELECT * FROM provider_private_references WHERE provider_id=? AND revision=?',
                                       (config.id, config.revision)).fetchone()
        if self.backup_disabled():
            if row is not None:
                raise integrity_error()
            return None
        if row is None:
            if config.secret_present:
                raise integrity_error()
            return None
        if not config.secret_present or digest({'workspace_id': self.workspace_id, 'provider_id': config.id,
                'revision': config.revision, 'config_sha256': config.config_sha256,
                'locator': row['locator']}) != row['integrity_sha256']:
            raise integrity_error()
        if re.fullmatch(r'secret_[0-9a-f]{32}', row['locator']) is None:
            raise integrity_error()
        return str(row['locator'])

    def secret_locator(self, provider_id: str, revision: int) -> str | None:
        return self._locator(self.config(provider_id, revision))

    def append_config(self, provider_id: str, request: ProviderConfigWrite, command_id: str,
                      *, locator: str | None) -> ProviderConfigView:
        self.writable()
        old = None
        if request.expected_revision == 0:
            occupied = self.connection.execute('SELECT workspace_id FROM provider_config_heads WHERE provider_id=?', (provider_id,)).fetchone()
            legacy = self.connection.execute('SELECT workspace_id FROM provider_configs WHERE id=?', (provider_id,)).fetchone()
            if occupied is not None or legacy is not None:
                owner = occupied if occupied is not None else legacy
                raise ApiError(404 if owner['workspace_id'] != self.workspace_id else 412,
                               'PROVIDER_VERSION_CONFLICT', '提供商配置基准已变化或不可访问。')
        else:
            old = self.config(provider_id)
            if old.revision != request.expected_revision:
                raise ApiError(412, 'PROVIDER_VERSION_CONFLICT', '提供商配置已更新，请比较当前版本。')
        value = ProviderConfigView(id=provider_id, revision=request.expected_revision + 1, config_sha256='0' * 64,
            configured=True, secret_present=locator is not None, **request.model_dump(exclude={'expected_revision'}))
        value = value.model_copy(update={'config_sha256': config_digest(self.workspace_id, value)})
        previous = self.connection.execute('SELECT history_sha256 FROM provider_config_history WHERE provider_id=? AND revision=?',
                                           (provider_id, old.revision)).fetchone()[0] if old else None
        material = {'provider_id': provider_id, 'workspace_id': self.workspace_id, 'revision': value.revision,
                    'config_json': canonical_bytes(value).decode(), 'config_sha256': value.config_sha256,
                    'previous_sha256': previous, 'command_id': command_id, 'created_at': utc_now()}
        self.connection.execute('INSERT INTO provider_config_history VALUES(?,?,?,?,?,?,?,?,?)',
            (provider_id, self.workspace_id, value.revision, material['config_json'], value.config_sha256,
             previous, digest(material), command_id, material['created_at']))
        self.connection.execute('INSERT INTO provider_config_heads VALUES(?,?,?) ON CONFLICT(provider_id) DO UPDATE SET revision=excluded.revision',
                                (provider_id, self.workspace_id, value.revision))
        if locator is not None:
            private = {'workspace_id': self.workspace_id, 'provider_id': provider_id, 'revision': value.revision,
                       'config_sha256': value.config_sha256, 'locator': locator}
            self.connection.execute('INSERT INTO provider_private_references VALUES(?,?,?,?)',
                                    (provider_id, value.revision, locator, digest(private)))
        return value


def command_id() -> str:
    return 'provider_command_' + uuid4().hex
