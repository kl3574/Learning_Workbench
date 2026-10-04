"""Actual packaged offline originals and finite, non-executing wire codecs."""
from pathlib import Path
import json
import shutil
import subprocess

import pytest

from packages.contracts.canonical import sha256_bytes
from services.api.app.application.codex_turn_protocol_models import (
    ClosedOperationDenial, ClosedTurnInterruptParams, OfflineTurnProtocolCatalog,
    verify_internal_refs,
)
from services.api.app.infrastructure import codex_turn_protocol_catalog as codecs


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


@pytest.fixture
def package_copy(tmp_path, monkeypatch):
    destination = tmp_path / 'source-package'
    shutil.copytree(codecs.PACKAGE_DIRECTORY, destination)
    monkeypatch.setattr(codecs, 'PACKAGE_DIRECTORY', destination)
    return destination


@pytest.mark.parametrize('alias', [0, 0.0, True])
def test_catalog_implemented_false_is_an_exact_boolean(alias):
    body = codecs.read_catalog().model_dump()
    body['implemented'] = alias
    with pytest.raises(ValueError):
        OfflineTurnProtocolCatalog.model_validate(body)


@pytest.mark.parametrize('damage', ['tail', 'all', 'duplicate', 'order', 'size', 'sha', 'path', 'extra', 'false_alias', 'source'])
def test_manifest_member_or_source_damage_is_not_a_new_source(package_copy, damage):
    path = package_copy / 'manifest.json'
    body = json.loads(path.read_text())
    if damage == 'tail':
        body['schemas'].pop()
    elif damage == 'all':
        body['schemas'] = []
    elif damage == 'duplicate':
        body['schemas'][1] = body['schemas'][0]
    elif damage == 'order':
        body['schemas'][0], body['schemas'][1] = body['schemas'][1], body['schemas'][0]
    elif damage == 'size':
        body['schemas'][0]['size'] += 1
    elif damage == 'sha':
        body['schemas'][0]['sha256'] = '0' * 64
    elif damage == 'path':
        body['schemas'][0]['path'] = '../outside.json'
    elif damage == 'extra':
        body['available'] = True
    elif damage == 'false_alias':
        body['implemented'] = 0
    else:
        body['source_projection_sha256'] = '0' * 64
    path.write_text(json.dumps(body))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        codecs.read_catalog()
    assert path.read_bytes() == before


@pytest.mark.parametrize('name', ['manifest.json', 'source-receipt.json', 'v2/TurnStartParams.json', 'PermissionsRequestApprovalResponse.json'])
def test_missing_originals_fail_without_rebuilding_them(package_copy, name):
    path = package_copy / name
    path.unlink()
    with pytest.raises(FileNotFoundError):
        codecs.read_catalog()
    assert not path.exists()


@pytest.mark.parametrize('kind', ['changed_byte', 'extra_byte', 'projection', 'private_argv', 'duplicate_member'])
def test_original_bytes_and_reviewed_source_summary_cannot_be_reinterpreted(package_copy, kind):
    if kind in {'changed_byte', 'extra_byte'}:
        path = package_copy / 'v2/TurnStartParams.json'
        raw = path.read_bytes()
        path.write_bytes(b'[' + raw[1:] if kind == 'changed_byte' else raw + b'\n')
    else:
        path = package_copy / 'source-receipt.json'
        body = json.loads(path.read_text())
        if kind == 'projection':
            body['export_profile'] = 'experimental'
        elif kind == 'private_argv':
            body['command'] = ['/private/not-a-source-fact']
        else:
            body['selected_files'][1] = body['selected_files'][0]
        path.write_text(json.dumps(body))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        codecs.read_catalog()
    assert path.read_bytes() == before


@pytest.mark.parametrize('damage', ['raw_schema', 'tail', 'summary', 'implemented'])
def test_reverification_detects_nested_or_forced_model_mutation(damage):
    catalog = codecs.read_catalog()
    if damage == 'raw_schema':
        original = catalog.schemas[0]
        object.__setattr__(original, 'raw_utf8', original.raw_utf8 + '\n')
    elif damage == 'tail':
        catalog.schemas.pop()
    elif damage == 'summary':
        catalog.source_projection.selected_files.pop()
    else:
        object.__setattr__(catalog, 'implemented', 0)
    with pytest.raises(ValueError):
        codecs.verify_catalog(catalog)
    with pytest.raises(ValueError):
        codecs.serialize_denial(catalog, 'command', 'decline')


@pytest.mark.parametrize('params', [
    {}, {'threadId': 'x'}, {'threadId': '', 'turnId': 'y'}, {'threadId': 1, 'turnId': 'y'},
    {'threadId': True, 'turnId': 'y'}, {'threadId': 'x', 'turnId': None},
    {'threadId': 'x', 'turnId': 'y', 'lastTurn': True}, {'thread_id': 'x', 'turn_id': 'y'},
    {'threadId': '\ud800', 'turnId': 'y'},
    b'{"threadId":"x","threadId":"other","turnId":"y"}',
    b'{"threadId":NaN,"turnId":"y"}',
])
def test_interrupt_is_a_closed_exact_shape(params):
    with pytest.raises(ValueError):
        codecs.serialize_interrupt(codecs.read_catalog(), params)


@pytest.mark.parametrize('kind', ['command', 'file_change'])
@pytest.mark.parametrize('decision', ['accept', 'acceptForSession', 'allow', None, True, {'acceptWithExecpolicyAmendment': {}}])
def test_denial_codec_never_opens_approval_or_permissions(kind, decision):
    with pytest.raises(ValueError):
        codecs.serialize_denial(codecs.read_catalog(), kind, decision)


def test_denial_body_and_unknown_kind_are_closed():
    with pytest.raises(ValueError):
        ClosedOperationDenial.model_validate({'decision': 'decline', 'grantRoot': '/not-authorized'})
    with pytest.raises(ValueError):
        codecs.serialize_denial(codecs.read_catalog(), 'network', 'decline')


@pytest.mark.parametrize('reference', ['https://not-allowed.invalid/schema.json', 'file:///not-allowed.json', '#/definitions/missing', '#/definitions/bad~2', '#/definitions/value'])
def test_internal_ref_checker_never_fetches_or_guesses(reference):
    with pytest.raises(ValueError):
        verify_internal_refs({'$ref': reference, 'definitions': {'value': 'not-a-schema'}})


def test_internal_pointer_escapes_lists_and_cycles_are_resolved_without_expansion():
    schema = {'definitions': {'a/b': {}, 'a~b': False},
              'allOf': [{'$ref': '#/definitions/a~1b'}, {'$ref': '#/definitions/a~0b'}, {'$ref': '#/allOf/0'}]}
    assert verify_internal_refs(schema) == 3
    with pytest.raises(ValueError):
        verify_internal_refs({'$ref': '#/allOf/01', 'allOf': [{}]})


def test_normative_bytes_and_summary_have_no_physical_receipt_paths():
    catalog = codecs.read_catalog()
    assert '/home/' not in catalog.source_projection_utf8
    assert 'command' not in catalog.source_projection.model_fields
    assert catalog.source_projection.scope == 'manually_checked_selected9_only'
    for schema in catalog.schemas:
        assert sha256_bytes(schema.raw_utf8.encode()) == schema.sha256
        assert schema.sha256 in (Path(__file__).parents[2] / 'PRODUCT_DESIGN.md').read_text()


def test_catalog_and_codec_zero_execution_seams(monkeypatch):
    from services.api.app.infrastructure.codex_bootstrap_runtime import LocalCodexBootstrapRuntime
    from services.api.app.infrastructure.codex_probe import LocalCodexProbe
    from services.api.app.application.provider_codex_execution import _Gate

    counts = dict(process=0, freeze=0, validity=0, bootstrap=0, probe=0, model_transport=0)

    def forbidden(name):
        def called(*args, **kwargs):
            counts[name] += 1
            raise AssertionError('Offline sources/codecs must not enter an execution seam')
        return called

    monkeypatch.setattr(subprocess, 'Popen', forbidden('process'))
    monkeypatch.setattr(LocalCodexBootstrapRuntime, 'freeze', forbidden('freeze'))
    monkeypatch.setattr(LocalCodexBootstrapRuntime, 'validity', forbidden('validity'))
    monkeypatch.setattr(LocalCodexBootstrapRuntime, 'execute', forbidden('bootstrap'))
    monkeypatch.setattr(LocalCodexProbe, 'read', forbidden('probe'))
    monkeypatch.setattr(_Gate, 'request', forbidden('model_transport'))
    catalog = codecs.read_catalog()
    codecs.verify_catalog(catalog)
    assert codecs.serialize_interrupt(catalog, {'threadId': 'fixture-thread', 'turnId': 'fixture-turn'})
    assert codecs.serialize_denial(catalog, 'command', 'decline')
    assert codecs.serialize_denial(catalog, 'file_change', 'cancel')
    assert counts == dict(process=0, freeze=0, validity=0, bootstrap=0, probe=0, model_transport=0)
