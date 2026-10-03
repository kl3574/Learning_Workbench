"""Actual registered edit routes have typed recursive JSON and preserve Import GET."""
from scripts.api_contracts import runtime_openapi
from scripts.schema_types import generate_types, typescript_type


def test_real_edit_route_projection_and_recursive_json_value_are_closed():
    openapi = runtime_openapi()
    schemas = openapi['components']['schemas']
    create = openapi['paths']['/api/v1/drafts']['post']
    patch = openapi['paths']['/api/v1/drafts/{id}']['patch']
    edit_read = openapi['paths']['/api/v1/draft-edits/{id}']['get']
    legacy = openapi['paths']['/api/v1/drafts/{id}']['get']
    def ref(name):
        return {'$ref': f'#/components/schemas/{name}'}
    assert create['requestBody']['content']['application/json']['schema'] == ref('DraftCreateWrite')
    assert create['responses']['201']['content']['application/json']['schema'] == ref('DraftCreated')
    assert patch['requestBody']['content']['application/json']['schema'] == ref('DraftPatchWrite')
    assert patch['responses']['200']['content']['application/json']['schema'] == ref('DraftPatched')
    assert edit_read['responses']['200']['content']['application/json']['schema'] == ref('EditDraftSnapshot')
    assert {entry['name']: entry['required'] for entry in edit_read['parameters'] if entry['in'] == 'query'} == {
        'revision': False}
    assert legacy['responses']['200']['content']['application/json']['schema'] == ref('ImportDraftSnapshot')
    assert {entry['name']: entry['required'] for entry in create['parameters'] if entry['in'] == 'header'}[
        'Idempotency-Key'] is True
    assert {entry['name']: entry['required'] for entry in patch['parameters'] if entry['in'] == 'header'}[
        'Idempotency-Key'] is False
    for name in ['DraftCreateWrite', 'DraftCreated', 'DraftPatch', 'DraftPatchWrite', 'DraftPatched',
                 'EditDraftSnapshot', 'DraftEditPayload']:
        assert schemas[name]['additionalProperties'] is False
    assert set(schemas['EditDraftSnapshot']['required']) == {
        'owner', 'candidate', 'base_ref', 'base_material_sha256', 'payload', 'warnings', 'state'}
    assert set(schemas['DraftEditPayload']['required']) == {
        'version', 'entity', 'kind', 'base_ref', 'body_path', 'citations', 'title',
        'body_markdown', 'body_sha256', 'base_material_sha256'}
    assert schemas['DraftPatch']['properties']['value'] == ref('DraftJsonValue')
    variants = schemas['DraftJsonValue']['anyOf']
    assert {'type': 'array', 'items': ref('DraftJsonValue')} in variants
    assert {'type': 'object', 'additionalProperties': ref('DraftJsonValue')} in variants
    assert {item['type'] for item in variants} == {'null', 'boolean', 'integer', 'number', 'string', 'array', 'object'}
    from pathlib import Path
    from packages.contracts.spec_catalog import spec_metadata
    generated = generate_types(schemas, spec_metadata(Path('PRODUCT_DESIGN.md')))
    line = next(value for value in generated.splitlines() if value.startswith('export type DraftJsonValue = '))
    assert '{ [key: string]: DraftJsonValue }' in line and 'Array<DraftJsonValue>' in line
    assert 'any' not in line and 'unknown' not in line


def test_only_named_recursive_json_map_is_admitted_by_typescript_projection():
    assert typescript_type({'type': 'object', 'additionalProperties': {
        '$ref': '#/components/schemas/DraftJsonValue'}}) == '{ [key: string]: DraftJsonValue }'
    for invalid in [True, {}, {'$ref': '#/components/schemas/OtherValue'}]:
        try:
            typescript_type({'type': 'object', 'additionalProperties': invalid})
        except ValueError:
            continue
        raise AssertionError('Unbounded or unrelated map was admitted')
    recursive = {'type': 'object', 'additionalProperties': {
        '$ref': '#/components/schemas/DraftJsonValue'}}
    for extra in [{'patternProperties': {'.*': {'type': 'string'}}},
                  {'unevaluatedProperties': False}, {'properties': {}}]:
        try:
            typescript_type({**recursive, **extra})
        except ValueError:
            continue
        raise AssertionError('Altered recursive map was admitted')
