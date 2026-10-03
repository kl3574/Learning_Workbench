"""Remove authentication from an independent backup without erasing historical actors."""

from pathlib import Path
import sqlite3

from ..infrastructure.database import utc_now
from .errors import ApiError


def sanitize_session_backup(connection: sqlite3.Connection, *, live_database_path: Path) -> dict[str, object]:
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '会话备份降权需要有效事务。')
    if connection.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
        raise ApiError(409, 'SESSION_BACKUP_TARGET_INVALID', '会话备份降权需要启用外键约束。')
    main = next(row for row in connection.execute('PRAGMA database_list') if row[1] == 'main')
    if (not main[2] or Path(main[2]).resolve() == live_database_path.resolve()
            or Path(main[2]).samefile(live_database_path)):
        raise ApiError(409, 'SESSION_BACKUP_TARGET_INVALID', '会话备份降权只能作用于独立备份副本。')
    count = connection.execute('SELECT count(*) FROM local_sessions').fetchone()[0]
    # IDs/workspace/role/expiry are historical facts referenced by immutable
    # owner records. Credential hashes are not. These public sentinels cannot
    # equal the hexadecimal SHA-256 values accepted by authenticate(), even if
    # somebody later clears revoked_at. No original credential digest survives.
    connection.execute('PRAGMA secure_delete=ON')
    connection.execute("UPDATE local_sessions SET token_hash='backup-disabled:' || id, "
                       "csrf_hash='backup-disabled', revoked_at=COALESCE(revoked_at, ?)", (utc_now(),))
    connection.execute('DELETE FROM bootstrap_codes')
    connection.execute('DELETE FROM idempotency')
    # The packaging owner must commit, VACUUM and close this copy before export.
    return {'version': 'session-backup-v1', 'historical_actors_retained': count,
            'authentication_disabled': True, 'scope': 'sensitive_personal_backup_not_public'}
