"""Persistence text adapters to the single shared canonical JSON implementation."""

from typing import Any

from packages.contracts.canonical import canonical_bytes, sha256_bytes


def canonical_json(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def content_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))
