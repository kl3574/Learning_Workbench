"""Local provider control operations; no source read or remote request."""

import re
import sqlite3

from pydantic import BaseModel, TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes

from ..infrastructure.database import Database
from ..infrastructure.provider_repository import ProviderRepository, command_id
from ..infrastructure.provider_secret_store import FileSecretStore, SecretStore
from ..infrastructure.security import SessionIdentity
from ..provider_dto import (
    ProviderCapabilitiesResponse, ProviderConfigAck, ProviderConfigView, ProviderConfigWrite,
    ProviderSecretAck, ProviderSecretWrite,
)
from .errors import ApiError
from .provider_ports import ProviderRequestPreparer


def validate_key(key: str | None) -> str:
    if not isinstance(key, str) or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key) is None:
        raise ApiError(400, 'IDEMPOTENCY_KEY_REQUIRED', '需要单个有效的幂等键。')
    return key


def identifier(value: str) -> None:
    try:
        TypeAdapter(dm.Id).validate_python(value)
    except (ValueError, TypeError):
        raise ApiError(422, 'SCHEMA_INVALID', '提供商标识无效。') from None


def validate_destination(request: ProviderConfigWrite) -> None:
    from ..infrastructure.provider_network import validate_endpoint
    validate_endpoint(request.base_url, request.endpoint_policy)


def provider_configuration_present(connection: sqlite3.Connection, workspace_id: str) -> bool:
    """Runtime reads configuration existence through its owner, without secret I/O."""
    return bool(ProviderRepository(connection, workspace_id).configs())


class ProviderService:
    def __init__(self, database: Database, secret_store: SecretStore,
                 preparer: ProviderRequestPreparer | None = None):
        self.database = database
        self.secret_store = secret_store
        self.preparer = preparer

    def _fingerprint(self, identity: SessionIdentity, route: str, key: str, payload: object) -> str:
        if isinstance(payload, BaseModel):
            payload = payload.model_dump(mode='json')
        return self.secret_store.fingerprint(canonical_bytes({'workspace_id': identity.workspace_id,
            'actor': identity.workspace_id, 'route': route, 'key': key, 'payload': payload}))

    def read_config(self, identity: SessionIdentity, provider_id: str) -> ProviderConfigView:
        identifier(provider_id)
        with self.database.transaction() as connection:
            return ProviderRepository(connection, identity.workspace_id).config(provider_id)

    def capabilities(self, identity: SessionIdentity) -> ProviderCapabilitiesResponse:
        with self.database.transaction() as connection:
            repo = ProviderRepository(connection, identity.workspace_id)
            items = []
            for config in repo.configs():
                locator = repo.secret_locator(config.id, config.revision)
                available = locator is not None and self.secret_store.available(locator)
                if self.preparer is None:
                    item = dm.ProviderCapabilities(provider_id=config.id, configured=True, chat=False,
                        streaming=False, structured_output=False, web_search=False, tool_calls=False,
                        version_evidence='INPUT_BOUND_UNAVAILABLE: 没有已注册的完整输入计量依据。')
                else:
                    item = self.preparer.capabilities(config, available)
                items.append(item)
            return ProviderCapabilitiesResponse(items=items)

    def save_config(self, identity: SessionIdentity, provider_id: str, request: ProviderConfigWrite,
                    key: str | None) -> ProviderConfigAck:
        identifier(provider_id)
        key = validate_key(key)
        request = ProviderConfigWrite.model_validate(request.model_dump(mode='json'))
        route = f'PUT /providers/{provider_id}/config'
        fingerprint = self._fingerprint(identity, route, key, request)
        with self.database.transaction() as connection:
            repo = ProviderRepository(connection, identity.workspace_id)
            repo.require_workspace()
            original = repo.replay(route, key, fingerprint, ProviderConfigAck)
            if original is not None:
                repo.config(provider_id, original.revision)
                return original
            validate_destination(request)
            locator = None if request.expected_revision == 0 else repo.secret_locator(provider_id, repo.config(provider_id).revision)
            cid = command_id()
            config = repo.append_config(provider_id, request, cid, locator=locator)
            result = ProviderConfigAck(id=config.id, revision=config.revision, config_sha256=config.config_sha256,
                                       configured=True, secret_present=config.secret_present)
            repo.record_command(cid, route, key, request, fingerprint, result)
            return result

    def save_secret(self, identity: SessionIdentity, provider_id: str, request: ProviderSecretWrite,
                    key: str | None) -> ProviderSecretAck:
        identifier(provider_id)
        key = validate_key(key)
        request = ProviderSecretWrite.model_validate(request.model_dump(mode='json'))
        route = f'POST /providers/{provider_id}/secret'
        fingerprint = self._fingerprint(identity, route, key, request)
        locator = None
        try:
            with self.database.transaction() as connection:
                repo = ProviderRepository(connection, identity.workspace_id)
                repo.require_workspace()
                original = repo.replay(route, key, fingerprint, ProviderSecretAck)
                if original is not None:
                    repo.config(provider_id, original.revision)
                    return original
                current = repo.config(provider_id)
                if current.revision != request.expected_revision:
                    raise ApiError(412, 'PROVIDER_VERSION_CONFLICT', '提供商配置已更新，请比较当前版本。')
                locator = self.secret_store.put(request.secret)
                cid = command_id()
                config_request = ProviderConfigWrite(expected_revision=current.revision,
                    **current.model_dump(exclude={'id', 'revision', 'config_sha256', 'configured', 'secret_present'}))
                config = repo.append_config(provider_id, config_request, cid, locator=locator)
                result = ProviderSecretAck(id=config.id, revision=config.revision,
                    config_sha256=config.config_sha256, secret_present=True)
                repo.record_command(cid, route, key, {'expected_revision': request.expected_revision,
                    'operation': 'replace_secret'}, fingerprint, result)
            return result
        except BaseException:
            # An exception at the commit/ACK boundary does not prove rollback.
            # Explicit cleanup below first proves absence from committed history.
            raise

    def cleanup_orphan_secrets(self, identity: SessionIdentity) -> int:
        """Explicit recovery only; the write lock excludes every secret CAS writer."""
        with self.database.transaction() as connection:
            repo = ProviderRepository(connection, identity.workspace_id)
            repo.writable()
            # A missing reference is not an orphan proof until every owning
            # configuration chain has been checked under this same write lock.
            for row in connection.execute('SELECT id FROM workspace'):
                ProviderRepository(connection, row[0]).configs()
            if isinstance(self.secret_store, FileSecretStore):
                self.secret_store.recover_staging()
            retained = {row[0] for row in connection.execute('SELECT locator FROM provider_private_references')}
            removed = 0
            for locator in self.secret_store.versions():
                if locator not in retained:
                    self.secret_store.delete(locator)
                    removed += 1
            return removed

    def delete_secret(self, identity: SessionIdentity, provider_id: str, expected_sha256: str,
                      key: str | None) -> ProviderSecretAck:
        identifier(provider_id)
        key = validate_key(key)
        if not isinstance(expected_sha256, str) or re.fullmatch('[0-9a-f]{64}', expected_sha256) is None:
            raise ApiError(400, 'IF_MATCH_REQUIRED', '删除秘密需要所读配置的有效强 If-Match。')
        route = f'DELETE /providers/{provider_id}/secret'
        payload = {'if_match': expected_sha256}
        fingerprint = self._fingerprint(identity, route, key, payload)
        locator = None
        with self.database.transaction() as connection:
            repo = ProviderRepository(connection, identity.workspace_id)
            repo.require_workspace()
            original = repo.replay(route, key, fingerprint, ProviderSecretAck)
            if original is not None:
                repo.config(provider_id, original.revision)
                return original
            current = repo.config(provider_id)
            if current.config_sha256 != expected_sha256:
                raise ApiError(412, 'PROVIDER_VERSION_CONFLICT', '提供商配置已更新，请比较当前版本。')
            locator = repo.secret_locator(provider_id, current.revision)
            cid = command_id()
            if current.secret_present:
                request = ProviderConfigWrite(expected_revision=current.revision,
                    **current.model_dump(exclude={'id', 'revision', 'config_sha256', 'configured', 'secret_present'}))
                current = repo.append_config(provider_id, request, cid, locator=None)
            result = ProviderSecretAck(id=current.id, revision=current.revision,
                config_sha256=current.config_sha256, secret_present=False)
            repo.record_command(cid, route, key, payload, fingerprint, result)
        if locator is not None:
            try:
                self.secret_store.delete(locator)
            except ApiError:
                pass  # The reference is already disabled; erasure is not promised.
        return result
