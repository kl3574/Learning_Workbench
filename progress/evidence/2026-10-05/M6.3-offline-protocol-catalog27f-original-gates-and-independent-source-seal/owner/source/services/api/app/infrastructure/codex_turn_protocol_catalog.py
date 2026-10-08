"""Read checked offline originals and serialize finite, non-executing shapes.

No process, runtime freeze/probe, user config, secret, network, approval or
executor is accessed. The provenance file is an explicitly reviewed summary,
not the full private historical receipt. This catalog is never production
admission; it lacks complete RPC/response/timing/input/runtime qualification.
"""
import os
from pathlib import Path
import stat
from typing import Literal

from jsonschema import Draft7Validator  # type: ignore[import-untyped]

from packages.contracts.canonical import canonical_bytes, strict_json
from ..application.codex_turn_protocol_models import (
    ClosedOperationDenial, ClosedTurnInterruptParams, OfflineProtocolManifest,
    OfflineProtocolSourceSummary, OfflineTurnProtocolCatalog, ProtocolPath,
    ProtocolSchemaOriginal,
)

PACKAGE_DIRECTORY = Path(__file__).with_name('codex_turn_protocol')


def _read_member(path: Path, maximum: int) -> bytes:
    """Bounded regular packaged source read; no caller-selected host paths."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError('The fixed packaged source is unavailable')
        raw = stream.read(maximum + 1)
        if len(raw) != info.st_size or len(raw) > maximum:
            raise ValueError('The fixed packaged source is incomplete')
    return raw


def read_catalog() -> OfflineTurnProtocolCatalog:
    """Read and verify all nine immutable schema/source-summary originals."""
    manifest = OfflineProtocolManifest.model_validate(strict_json(_read_member(PACKAGE_DIRECTORY / 'manifest.json', 8192)))
    raw_source = _read_member(PACKAGE_DIRECTORY / 'source-receipt.json', 8192)
    source = OfflineProtocolSourceSummary.model_validate(strict_json(raw_source))
    originals = []
    for identity in manifest.schemas:
        raw = _read_member(PACKAGE_DIRECTORY / identity.path, identity.size)
        originals.append(ProtocolSchemaOriginal(**identity.model_dump(), raw_utf8=raw.decode('utf-8')))
    return OfflineTurnProtocolCatalog(version='codex-offline-turn-protocol-catalog-v1',
        scope=manifest.scope, implemented=manifest.implemented, source_projection=source,
        source_projection_sha256=manifest.source_projection_sha256, source_projection_utf8=raw_source.decode('utf-8'),
        schemas=originals)


def verify_catalog(catalog: OfflineTurnProtocolCatalog) -> OfflineTurnProtocolCatalog:
    """Recheck complete original bytes even after nested-list/object mutation."""
    if not isinstance(catalog, OfflineTurnProtocolCatalog):
        raise ValueError('A checked offline source catalog is required')
    return OfflineTurnProtocolCatalog.model_validate(catalog.model_dump())


def _schema(catalog: OfflineTurnProtocolCatalog, path: ProtocolPath) -> dict:
    checked = verify_catalog(catalog)
    return strict_json(next(m.raw_utf8 for m in checked.schemas if m.path == path))


def serialize_interrupt(catalog: OfflineTurnProtocolCatalog, params: object) -> bytes:
    """Canonical params only: no RPC envelope, owned mapping or send action."""
    schema = _schema(catalog, 'v2/TurnInterruptParams.json')
    parsed = strict_json(params) if isinstance(params, (str, bytes)) else params
    if isinstance(parsed, ClosedTurnInterruptParams):
        parsed = parsed.model_dump(by_alias=True)
    closed = ClosedTurnInterruptParams.model_validate(parsed)
    wire = closed.model_dump(by_alias=True)
    Draft7Validator(schema).validate(wire)
    return canonical_bytes(wire)


def serialize_denial(catalog: OfflineTurnProtocolCatalog, kind: Literal['command', 'file_change'],
                     decision: Literal['decline', 'cancel']) -> bytes:
    """Only exact single denial/cancel response bytes; never implicit execution."""
    if kind not in {'command', 'file_change'}:
        raise ValueError('Only the two fixed denial response kinds are supported')
    path: ProtocolPath = ('CommandExecutionRequestApprovalResponse.json' if kind == 'command'
                          else 'FileChangeRequestApprovalResponse.json')
    schema = _schema(catalog, path)
    closed = ClosedOperationDenial(decision=decision)
    wire = closed.model_dump()
    Draft7Validator(schema).validate(wire)
    return canonical_bytes(wire)
