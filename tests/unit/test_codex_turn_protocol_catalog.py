"""Actual packaged offline originals and finite, non-executing wire codecs."""
from pathlib import Path


def test_packaged_catalog_binds_original_source_and_finite_safe_wire_bytes():
    package = (Path(__file__).parents[2] / 'services/api/app/infrastructure/codex_turn_protocol')
    assert (package / 'manifest.json').is_file(), 'The normative offline turn catalog is not packaged'

    from services.api.app.infrastructure.codex_turn_protocol_catalog import (
        read_catalog, serialize_denial, serialize_interrupt, verify_catalog,
    )

    catalog = read_catalog()
    assert catalog.version == 'codex-offline-turn-protocol-catalog-v1'
    assert catalog.scope == 'selected9_schema_shapes_only'
    assert catalog.implemented is False
    assert len(catalog.schemas) == 9
    assert sum(member.size for member in catalog.schemas) == 93287
    assert catalog.internal_ref_occurrences == 97
    assert catalog.source_receipt_sha256 == 'b64f43cd1b5a7024bcdcb421292cef93b61721ba76a4f325e7663be93931cd9c'
    original = catalog.model_dump()
    assert verify_catalog(catalog).model_dump() == original
    assert serialize_interrupt(catalog, {'threadId': 'fixture-thread', 'turnId': 'fixture-turn'}) == (
        b'{"threadId":"fixture-thread","turnId":"fixture-turn"}')
    assert serialize_denial(catalog, 'command', 'decline') == b'{"decision":"decline"}'
    assert serialize_denial(catalog, 'file_change', 'cancel') == b'{"decision":"cancel"}'
    assert catalog.model_dump() == original
