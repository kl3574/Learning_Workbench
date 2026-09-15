"""Downgrade only an independent sensitive backup; preserve owned audit bytes."""

from pathlib import Path
import sqlite3

from packages.contracts.canonical import canonical_bytes

from ..infrastructure.consent_repository import ConsentRepository
from ..infrastructure.database import utc_now
from ..infrastructure.provider_repository import ProviderRepository, digest, historical_scope_digest, require_transaction
from .errors import ApiError


def sanitize_provider_backup(connection: sqlite3.Connection, *, live_database_path: Path) -> dict[str, object]:
    require_transaction(connection)
    main = next(row for row in connection.execute('PRAGMA database_list') if row[1] == 'main')
    if not main[2] or Path(main[2]).resolve() == live_database_path.resolve() or Path(main[2]).samefile(live_database_path):
        raise ApiError(409, 'PROVIDER_BACKUP_TARGET_INVALID', '提供商备份降权只能作用于独立备份副本。')
    if connection.row_factory is not sqlite3.Row:
        raise ApiError(409, 'PROVIDER_BACKUP_TARGET_INVALID', '备份需要受控的数据库行映射。')
    workspaces = [row[0] for row in connection.execute('SELECT id FROM workspace ORDER BY id')]
    summaries = []
    for workspace_id in workspaces:
        providers = ProviderRepository(connection, workspace_id)
        if providers.backup_disabled():
            continue
        providers.configs()
        repo = ConsentRepository(connection, workspace_id)
        for row in connection.execute('SELECT id FROM provider_command_history WHERE workspace_id=?', (workspace_id,)):
            providers.command(row['id'])
        for row in connection.execute('SELECT id FROM provider_proposals WHERE workspace_id=?', (workspace_id,)):
            repo.proposal(row['id'])
        for identifier in repo.consent_ids():
            repo.consent(identifier)
            record = repo.dispatch_for_consent(identifier)
            if record is not None:
                repo.usage(record.id)
                repo.read_terminal(record.id)
        summaries.append((workspace_id, historical_scope_digest(connection, workspace_id)))
    authentication_records = connection.execute('SELECT count(*) FROM provider_private_commands').fetchone()[0]
    authentication_records += connection.execute('SELECT count(*) FROM provider_private_references').fetchone()[0]
    # Delete cell payloads from this copy's pages too. The export owner still
    # closes/checkpoints and VACUUMs its independent file before packaging it.
    connection.execute('PRAGMA secure_delete=ON')
    # No preparation, request, answer, refusal or immutable historical ACK is removed.
    connection.execute('DELETE FROM provider_private_commands')
    connection.execute('DELETE FROM provider_private_references')
    # Legacy physical locators are authentication metadata, not native grants.
    connection.execute('UPDATE provider_configs SET secret_store_locator=NULL WHERE secret_store_locator IS NOT NULL')
    for workspace_id, historical_hash in summaries:
        now = utc_now()
        value = {'version': 'provider-backup-v1', 'workspace_id': workspace_id, 'created_at': now,
                 'historical_scope_sha256': historical_hash, 'dispatch_disabled': True,
                 'scope': 'sensitive_personal_backup_not_public'}
        connection.execute('INSERT INTO provider_backup_projections VALUES(?,?,?,?,?)',
            (workspace_id, now, historical_hash, canonical_bytes(value).decode(), digest(value)))
    return {'workspaces_downgraded': len(summaries), 'authentication_records_removed': authentication_records,
            'dispatch_disabled': True, 'scope': 'sensitive_personal_backup_not_public'}
