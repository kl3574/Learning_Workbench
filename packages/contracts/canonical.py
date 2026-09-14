"""Canonical metadata bytes required by PRODUCT_DESIGN.md sections 9.1/20.1.

This is a project algorithm, not a claim of RFC 8785 interoperability.
Raw file hashes must use sha256_bytes instead of reserializing their contents.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

CANONICAL_VERSION = "learning-json-1"
HASH_ALGORITHM = "sha256"


def canonical_bytes(value: Any) -> bytes:
    """Serialize a validated model or JSON value; reject non-finite numbers.

External metadata must be validated into its fixed model before calling this.
The serializer never normalizes source Markdown or other immutable file bytes.
"""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def metadata_sha256(value: BaseModel) -> str:
    return sha256_bytes(canonical_bytes(value))


def snapshot_sha256(value: BaseModel) -> str:
    """The snapshot hash explicitly excludes its own hash field."""
    return sha256_bytes(canonical_bytes(value.model_dump(mode="json", exclude={"snapshot_sha256"})))


def strict_json(data: bytes | str) -> Any:
    """Reject duplicate object keys and non-standard NaN/Infinity input."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=reject_constant)
