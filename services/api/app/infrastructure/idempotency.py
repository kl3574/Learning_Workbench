"""Replay and payload conflict protection must run inside the caller's write transaction."""

import json
import re
import sqlite3
from collections.abc import Callable
from typing import Any

from .database import utc_now
from ..application.errors import ApiError
from .security import expires_after
from ..serialization import canonical_json, content_sha256


def execute_idempotent(
    connection: sqlite3.Connection,
    *,
    actor: str,
    route: str,
    key: str | None,
    payload: Any,
    operation: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    if key is None or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", key) is None:
        raise ApiError(400, "IDEMPOTENCY_KEY_REQUIRED", "此操作需要有效的 Idempotency-Key。")
    request_hash = content_sha256(payload)
    previous = connection.execute(
        "SELECT request_sha256,result_json,expires_at FROM idempotency WHERE actor=? AND route=? AND key=?",
        (actor, route, key),
    ).fetchone()
    if previous and (previous["expires_at"] is None or previous["expires_at"] > utc_now()):
        if previous["request_sha256"] != request_hash:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "相同幂等键不能用于不同请求。")
        if previous["result_json"] is None:
            raise ApiError(409, "OPERATION_PENDING", "该操作尚未完成。", retryable=True)
        return dict(json.loads(previous["result_json"]))
    if previous:
        connection.execute("DELETE FROM idempotency WHERE actor=? AND route=? AND key=?", (actor, route, key))
    result = operation()
    connection.execute(
        "INSERT INTO idempotency(actor,route,key,request_sha256,result_json,created_at,expires_at) VALUES(?,?,?,?,?,?,?)",
        (actor, route, key, request_hash, canonical_json(result), utc_now(), expires_after(86400)),
    )
    return result
