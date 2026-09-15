"""Configuration and secret command recovery using native SQLite and synthetic keys."""

from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import SessionIdentity
from contextlib import contextmanager
import pytest


def test_first_config_secret_rotation_and_original_ack_survive_reopen(tmp_path):
    from services.api.app.application.providers import ProviderService
    from services.api.app.infrastructure.provider_secret_store import FileSecretStore
    from services.api.app.provider_dto import ProviderConfigWrite, ProviderSecretWrite

    database = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    identity = SessionIdentity('session_provider_test', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    secrets = FileSecretStore(tmp_path / 'secrets')
    secrets.initialize()
    service = ProviderService(database, secrets)
    request = ProviderConfigWrite(expected_revision=0, adapter='compatible_chat',
        base_url='https://provider.example/v1', model='unregistered-model', embedding_model=None,
        endpoint_policy='public_https', pricing=None)
    created = service.save_config(identity, 'provider_test', request, 'create-config')
    assert created.revision == 1 and not created.secret_present
    first = ProviderSecretWrite(expected_revision=1, secret='synthetic-key-first')
    ack = service.save_secret(identity, 'provider_test', first, 'original-secret')
    assert ack.revision == 2 and ack.secret_present
    rotated = service.save_secret(identity, 'provider_test',
        ProviderSecretWrite(expected_revision=2, secret='synthetic-key-second'), 'rotate-secret')
    assert rotated.revision == 3
    reopened = ProviderService(Database(database.settings), FileSecretStore(tmp_path / 'secrets'))
    assert reopened.save_secret(identity, 'provider_test', first, 'original-secret') == ack
    current = reopened.read_config(identity, 'provider_test')
    assert current.revision == 3 and current.config_sha256 == rotated.config_sha256
    assert 'synthetic-key' not in current.model_dump_json()
    capabilities = reopened.capabilities(identity)
    assert len(capabilities.items) == 1
    assert not capabilities.items[0].chat and not capabilities.items[0].streaming


def config_storage(tmp_path, database_type=Database):
    from services.api.app.application.providers import ProviderService
    from services.api.app.infrastructure.provider_secret_store import FileSecretStore
    from services.api.app.provider_dto import ProviderConfigWrite

    database = database_type(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    identity = SessionIdentity('session_provider_test', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    store = FileSecretStore(tmp_path / 'secrets')
    store.initialize()
    service = ProviderService(database, store)
    service.save_config(identity, 'provider_test', ProviderConfigWrite(expected_revision=0,
        adapter='compatible_chat', base_url='https://provider.example/v1', model='unregistered-model',
        embedding_model=None, endpoint_policy='public_https', pricing=None), 'create-config')
    return database, identity, store, service


def test_original_secret_ack_checks_its_history_prefix_not_a_later_damaged_revision(tmp_path):
    from services.api.app.application.errors import ApiError
    from services.api.app.provider_dto import ProviderSecretWrite

    database, identity, _, service = config_storage(tmp_path)
    original = ProviderSecretWrite(expected_revision=1, secret='synthetic-first')
    ack = service.save_secret(identity, 'provider_test', original, 'original-secret')
    service.save_secret(identity, 'provider_test', ProviderSecretWrite(expected_revision=2,
        secret='synthetic-later'), 'later-secret')
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER provider_config_history_no_update')
        connection.execute("UPDATE provider_config_history SET config_json='{}' WHERE provider_id='provider_test' AND revision=3")
    assert service.save_secret(identity, 'provider_test', original, 'original-secret') == ack
    with pytest.raises(ApiError) as failed:
        service.read_config(identity, 'provider_test')
    assert failed.value.code == 'PROVIDER_INTEGRITY_INVALID'


def test_exception_after_commit_never_deletes_a_committed_secret_version(tmp_path):
    from services.api.app.infrastructure.provider_repository import ProviderRepository
    from services.api.app.provider_dto import ProviderSecretWrite

    class InterruptedReceiptDatabase(Database):
        interrupt_receipt = False

        @contextmanager
        def transaction(self):
            with super().transaction() as connection:
                yield connection
            if self.interrupt_receipt:
                self.interrupt_receipt = False
                raise RuntimeError('synthetic interruption after committed transaction')

    database, identity, store, service = config_storage(tmp_path, InterruptedReceiptDatabase)
    request = ProviderSecretWrite(expected_revision=1, secret='synthetic-committed-key')
    database.interrupt_receipt = True
    with pytest.raises(RuntimeError, match='synthetic interruption'):
        service.save_secret(identity, 'provider_test', request, 'committed-secret')
    current = service.read_config(identity, 'provider_test')
    assert current.revision == 2 and current.secret_present
    with database.transaction() as connection:
        locator = ProviderRepository(connection, identity.workspace_id).secret_locator('provider_test', 2)
    assert locator is not None and store.available(locator)
    assert service.save_secret(identity, 'provider_test', request, 'committed-secret').revision == 2


def test_orphan_cleanup_requires_complete_reference_history_before_deleting(tmp_path):
    from services.api.app.application.errors import ApiError
    from services.api.app.provider_dto import ProviderSecretWrite

    database, identity, store, service = config_storage(tmp_path)
    service.save_secret(identity, 'provider_test', ProviderSecretWrite(expected_revision=1,
        secret='synthetic-preserved-key'), 'secret')
    versions = store.versions()
    with database.transaction() as connection:
        connection.execute('DELETE FROM provider_private_references')  # Controlled corruption, not an application operation.
    with pytest.raises(ApiError) as error:
        service.cleanup_orphan_secrets(identity)
    assert error.value.code == 'PROVIDER_INTEGRITY_INVALID'
    assert store.versions() == versions


def test_explicit_cleanup_removes_only_uncommitted_versions_and_keeps_old_history(tmp_path):
    from services.api.app.provider_dto import ProviderSecretWrite

    _, identity, store, service = config_storage(tmp_path)
    service.save_secret(identity, 'provider_test', ProviderSecretWrite(expected_revision=1,
        secret='synthetic-key-A'), 'key-A')
    service.save_secret(identity, 'provider_test', ProviderSecretWrite(expected_revision=2,
        secret='synthetic-key-B'), 'key-B')
    committed = store.versions()
    orphan = store.put('synthetic-uncommitted-orphan')
    assert service.cleanup_orphan_secrets(identity) == 1
    assert not store.available(orphan) and store.versions() == committed
    assert all(store.available(locator) for locator in committed)
    assert service.cleanup_orphan_secrets(identity) == 0


def test_secret_delete_requires_current_sha_and_old_ack_does_not_erase_replacement(tmp_path):
    from services.api.app.application.errors import ApiError
    from services.api.app.provider_dto import ProviderSecretWrite

    _, identity, store, service = config_storage(tmp_path)
    before = service.read_config(identity, 'provider_test')
    saved = service.save_secret(identity, 'provider_test', ProviderSecretWrite(expected_revision=1,
        secret='synthetic-key-A'), 'save-A')
    with pytest.raises(ApiError) as stale:
        service.delete_secret(identity, 'provider_test', before.config_sha256, 'delete-stale')
    assert stale.value.status == 412
    removed = service.delete_secret(identity, 'provider_test', saved.config_sha256, 'delete-A')
    assert removed.revision == 3 and not removed.secret_present
    no_op = service.delete_secret(identity, 'provider_test', removed.config_sha256, 'delete-empty')
    assert no_op.revision == 3
    replacement = service.save_secret(identity, 'provider_test', ProviderSecretWrite(expected_revision=3,
        secret='synthetic-key-B'), 'save-B')
    current_versions = store.versions()
    assert service.delete_secret(identity, 'provider_test', saved.config_sha256, 'delete-A') == removed
    assert service.read_config(identity, 'provider_test').revision == replacement.revision == 4
    assert store.versions() == current_versions


def test_secret_command_identity_includes_secret_route_and_revision(tmp_path):
    from services.api.app.application.errors import ApiError
    from services.api.app.provider_dto import ProviderSecretWrite

    database, identity, store, service = config_storage(tmp_path)
    request = ProviderSecretWrite(expected_revision=1, secret='synthetic-key-A')
    original = service.save_secret(identity, 'provider_test', request, 'command')
    for changed in [request.model_copy(update={'secret': 'synthetic-key-B'}), request.model_copy(update={'expected_revision': 2})]:
        with pytest.raises(ApiError) as conflict:
            service.save_secret(identity, 'provider_test', changed, 'command')
        assert conflict.value.code == 'IDEMPOTENCY_CONFLICT'
    with pytest.raises(ApiError) as different_route:
        service.delete_secret(identity, 'provider_test', original.config_sha256, 'command')
    assert different_route.value.code == 'IDEMPOTENCY_CONFLICT'
    assert service.save_secret(identity, 'provider_test', request, 'command') == original
    assert len(store.versions()) == 1
    with database.transaction() as conn:
        assert conn.execute('SELECT COUNT(*) FROM provider_config_history').fetchone()[0] == 2


def test_cross_workspace_cannot_read_or_occupy_existing_provider_id(tmp_path):
    from dataclasses import replace
    from services.api.app.application.errors import ApiError
    from services.api.app.provider_dto import ProviderConfigWrite
    from services.api.app.infrastructure.database import utc_now

    database, identity, _, service = config_storage(tmp_path)
    with database.transaction() as conn:
        conn.execute('INSERT INTO workspace(id,title,preferences_json,created_at) VALUES(?,?,?,?)',
            ('workspace_other', 'Synthetic second workspace', '{}', utc_now()))
    other = replace(identity, workspace_id='workspace_other')
    with pytest.raises(ApiError) as read:
        service.read_config(other, 'provider_test')
    assert read.value.status == 404
    with pytest.raises(ApiError) as create:
        service.save_config(other, 'provider_test', ProviderConfigWrite(expected_revision=0,
            adapter='compatible_chat', base_url='https://provider.example/v1', model='unregistered-model',
            embedding_model=None, endpoint_policy='public_https', pricing=None), 'other-create')
    assert create.value.status == 404
    assert service.read_config(identity, 'provider_test').revision == 1
