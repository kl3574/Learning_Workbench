"""Fail closed when a Provider target declaration lacks its runtime contracts.

The synthetic OpenAPI below tests the generator, not route implementation.
The actual router/OpenAPI equality tests remain a separate runtime check.
"""

from copy import deepcopy
from pathlib import Path

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.spec_catalog import route_catalog
from scripts.generate_contracts import PROVIDER_OPERATIONS, provider_ports_binding
from services.api.app import provider_dto as dto

ROOT = Path(__file__).resolve().parents[2]
PORTS = (ROOT / 'packages/contracts/module-ports.ts').read_text()
PROVENANCE = {'spec_version': '3.0.2', 'spec_sha256': 'a' * 64}


def test_binding_operation_set_matches_the_sole_specification():
    catalog = route_catalog(ROOT / 'PRODUCT_DESIGN.md')
    expected = {(row['path'], row['method'].lower()) for row in catalog['routes']
                if row['path'].startswith(('/api/v1/providers/', '/api/v1/consents'))}
    assert len(expected) == 10 and set(PROVIDER_OPERATIONS) == expected


def shape_openapi():
    result = {'paths': {}, 'components': {'schemas': {}}}
    for (path, method), (request, response, status) in PROVIDER_OPERATIONS.items():
        operation = {'responses': {status: {'content': {
            'application/json': {'schema': {'$ref': f'#/components/schemas/{response}'}}}}}, 'parameters': []}
        if request is not None:
            operation['requestBody'] = {'required': True, 'content': {
                'application/json': {'schema': {'$ref': f'#/components/schemas/{request}'}}}}
        for name in (request, response):
            if name is not None:
                model = dm.MutationAck if name == 'MutationAck' else getattr(dto, name)
                result['components']['schemas'][name] = model.model_json_schema()
        if method != 'get':
            operation['parameters'].append({'name': 'Idempotency-Key', 'in': 'header', 'required': True,
                'schema': {'type': 'string', 'pattern': '^[A-Za-z0-9_-]{1,128}$'}})
        if method == 'delete':
            operation['parameters'].append({'name': 'If-Match', 'in': 'header', 'required': True,
                'schema': {'type': 'string', 'pattern': '^"[0-9a-f]{64}"$'}})
        if (path, method) == ('/api/v1/consents', 'get'):
            operation['parameters'] += [
                {'name': 'consent_id', 'in': 'query', 'required': False, 'schema': {'type': 'string'}},
                {'name': 'cursor', 'in': 'query', 'required': False, 'schema': {'type': 'string'}},
                {'name': 'limit', 'in': 'query', 'required': False,
                 'schema': {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 20}},
            ]
        result['paths'].setdefault(path, {})[method] = operation
    return result


@pytest.mark.parametrize('target', list(PROVIDER_OPERATIONS))
def test_each_missing_operation_prevents_binding(target):
    value = shape_openapi()
    path, method = target
    del value['paths'][path][method]
    with pytest.raises(ValueError, match='all ten registered'):
        provider_ports_binding(PORTS, value, PROVENANCE)


@pytest.mark.parametrize('change', ['status', 'request', 'response', 'bodyless', 'nonclosed', 'key', 'match', 'query', 'limit', 'duplicate'])
def test_incorrect_transport_and_open_schema_cannot_bind(change):
    value = shape_openapi()
    grant = value['paths']['/api/v1/consents']['post']
    deletion = value['paths']['/api/v1/providers/{id}/secret']['delete']
    page = value['paths']['/api/v1/consents']['get']
    if change == 'status':
        grant['responses']['200'] = grant['responses'].pop('201')
    elif change == 'request':
        grant['requestBody']['required'] = False
    elif change == 'response':
        grant['responses']['201']['content']['application/json']['schema'] = {'type': 'object'}
    elif change == 'bodyless':
        deletion['requestBody'] = deepcopy(grant['requestBody'])
    elif change == 'nonclosed':
        value['components']['schemas']['ConsentCreate']['additionalProperties'] = True
    elif change == 'key':
        grant['parameters'][0]['required'] = False
    elif change == 'match':
        deletion['parameters'][1]['schema']['pattern'] = '.*'
    elif change == 'query':
        page['parameters'].pop()
    elif change == 'limit':
        page['parameters'][2]['schema']['maximum'] = 1000
    else:
        grant['parameters'].append(deepcopy(grant['parameters'][0]))
    with pytest.raises(ValueError):
        provider_ports_binding(PORTS, value, PROVENANCE)


@pytest.mark.parametrize('replacement', [
    ' ProviderSecretWrite: unknown; ProviderSecretWrite: unknown;',
    ' ProviderSecretWrite: any;',
    ' GenerationInput: unknown;',
])
def test_generic_map_cannot_rename_duplicate_or_widen_secret_input(replacement):
    changed = PORTS.replace(' ProviderSecretWrite: unknown;', replacement)
    assert changed != PORTS
    with pytest.raises(ValueError, match='unmapped or duplicate'):
        provider_ports_binding(changed, shape_openapi(), PROVENANCE)


def test_application_binding_stays_separate_from_core_and_query_body():
    value = shape_openapi()
    output = provider_ports_binding(PORTS, value, PROVENANCE)
    assert 'ProviderRuntimeDTOMap extends ProviderApplicationDTOMap' in output
    assert 'ProviderConfigView: Api.ProviderConfigView' in output
    assert 'ConsentCreate: Api.ConsentCreate' in output
    assert 'ProviderConsentQuery } from "../module-ports"' in output
    assert 'ConsentQuery' not in value['components']['schemas']
    assert 'GenerationInput' not in output and 'Api.ProviderConsentQuery' not in output
    core = PORTS.split('export interface DTOMap {', 1)[1].split('}', 1)[0]
    assert 'ProviderConfigView' not in core and len(dm.CONTRACTS) == 54
