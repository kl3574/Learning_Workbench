"""Host/Origin, one-use launcher bootstrap, cookie session and CSRF policy."""

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import Request

from .database import Database, utc_now
from ..application.errors import ApiError

COOKIE_NAME = "learning_session"


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def csrf_for_token(token: str) -> str:
    # A separate deterministic secret is recoverable after refresh without persisting it in plaintext.
    return hmac.new(token.encode("ascii"), b"learning-workbench-csrf-v1", hashlib.sha256).hexdigest()


def expires_after(seconds: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat(timespec="microseconds").replace("+00:00", "Z")


def issue_bootstrap_code(database: Database) -> str:
    """Launcher-only Python port; callers place this in a browser fragment, never a log/query."""
    code = secrets.token_urlsafe(32)
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO bootstrap_codes(code_hash,workspace_id,expires_at) VALUES(?,?,?)",
            (token_hash(code), database.workspace_id(), expires_after(database.settings.bootstrap_seconds)),
        )
    return code


@dataclass(frozen=True)
class SessionIdentity:
    id: str
    workspace_id: str
    role: Literal["learner", "author"]
    csrf_token: str
    expires_at: str


def consume_bootstrap(database: Database, code: str) -> tuple[str, SessionIdentity]:
    token = secrets.token_urlsafe(32)
    csrf = csrf_for_token(token)
    with database.transaction() as connection:
        now = utc_now()
        row = connection.execute(
            "UPDATE bootstrap_codes SET used_at=? WHERE code_hash=? AND used_at IS NULL AND expires_at>? RETURNING workspace_id",
            (now, token_hash(code), now),
        ).fetchone()
        if not row:
            raise ApiError(401, "SESSION_BOOTSTRAP_INVALID", "启动凭证无效、已过期或已使用。请重新使用本机启动器。")
        identity = SessionIdentity(f"session_{uuid4().hex}", row["workspace_id"], "learner", csrf, expires_after(database.settings.session_seconds))
        connection.execute(
            "INSERT INTO local_sessions(id,workspace_id,token_hash,csrf_hash,role,expires_at) VALUES(?,?,?,?,?,?)",
            (identity.id, identity.workspace_id, token_hash(token), token_hash(csrf), identity.role, identity.expires_at),
        )
    return token, identity


def authenticate(database: Database, request: Request) -> SessionIdentity:
    token = request.cookies.get(COOKIE_NAME)
    if not token or not token.isascii() or len(token) > 128:
        raise ApiError(401, "SESSION_REQUIRED", "需要通过本机启动器建立会话。")
    with database.connect() as connection:
        row = connection.execute(
            "SELECT id,workspace_id,role,csrf_hash,expires_at FROM local_sessions WHERE token_hash=? AND revoked_at IS NULL AND expires_at>?",
            (token_hash(token), utc_now()),
        ).fetchone()
    if row is None:
        raise ApiError(401, "SESSION_REQUIRED", "本机会话已失效，请重新使用启动器。")
    csrf = csrf_for_token(token)
    if not hmac.compare_digest(token_hash(csrf), row["csrf_hash"]):
        raise ApiError(401, "SESSION_REQUIRED", "本机会话已失效，请重新使用启动器。")
    return SessionIdentity(row["id"], row["workspace_id"], row["role"], csrf, row["expires_at"])


def check_csrf(request: Request, identity: SessionIdentity) -> None:
    received = request.headers.get("x-csrf-token", "")
    if not received.isascii() or not hmac.compare_digest(received, identity.csrf_token):
        raise ApiError(403, "CSRF_INVALID", "请求未通过本机会话保护校验。")


def active_independent_attempt(connection: sqlite3.Connection, workspace_id: str) -> str | None:
    row = connection.execute(
        "SELECT id FROM attempts WHERE workspace_id=? AND mode='independent' AND status='active'",
        (workspace_id,),
    ).fetchone()
    return str(row["id"]) if row else None


def require_role(identity: SessionIdentity, role: Literal["learner", "author"]) -> None:
    if identity.role != role:
        raise ApiError(403, "POLICY_DENIED", "当前操作角色没有此项权限。")


def guard_subject_access(connection: sqlite3.Connection, workspace_id: str) -> None:
    """Shared policy port for later subject-data, download and provider adapters."""
    if active_independent_attempt(connection, workspace_id):
        raise ApiError(409, "ASSESSMENT_ACTIVE", "独立测试进行中，此操作暂不可用。")
