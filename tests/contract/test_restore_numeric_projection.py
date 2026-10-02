"""The three Restore declarations count only when real composition registers them."""
import json
from pathlib import Path

from scripts.api_contracts import runtime_openapi
from scripts.restore_numeric_contracts import MODEL_NAMES


OPERATIONS = {
    ('/api/v1/content/restore-drafts/{id}/numeric-checks', 'post'):
        ('RestoreNumericCheckPreviewWrite', 'RestoreNumericCheckView', {'201'}),
    ('/api/v1/content/restore-numeric-checks/{id}', 'get'):
        (None, 'RestoreNumericCheckView', {'200'}),
    ('/api/v1/content/restore-numeric-checks/{id}/decision', 'post'):
        ('ApprovalDecision', 'NumericCheckDecisionAck', {'200', '202'}),
}


def test_actual_restore_numeric_operations_keep_strict_security_models_and_statuses():
    actual = runtime_openapi()
    for (path, method), (request, response, statuses) in OPERATIONS.items():
        operation = actual['paths'][path][method]
        assert operation['security'] == [{'LocalSession': []}]
        assert {status for status in operation['responses'] if status.startswith('2')} == statuses
        for status in statuses:
            assert operation['responses'][status]['content'] == {
                'application/json': {'schema': {'$ref': '#/components/schemas/' + response}}}
        parameters = operation['parameters']
        assert len({(item['in'], item['name'].lower()) for item in parameters}) == len(parameters)
        assert not any(item['in'] == 'query' for item in parameters)
        assert [item['name'] for item in parameters if item['in'] == 'path'] == ['id']
        if request is None:
            assert 'requestBody' not in operation
        else:
            assert operation['requestBody'] == {'required': True, 'content': {
                'application/json': {'schema': {'$ref': '#/components/schemas/' + request}}}}
            headers = {item['name'].lower(): item for item in parameters if item['in'] == 'header'}
            assert all(headers[name]['required'] for name in ['origin', 'x-csrf-token', 'idempotency-key'])
            assert headers['idempotency-key']['schema'] == {'type': 'string', 'pattern': '^[A-Za-z0-9_-]{1,128}$'}
    for name in MODEL_NAMES:
        model = actual['components']['schemas'][name]
        assert model['additionalProperties'] is False
        assert set(model['required']) == set(model['properties'])
    snapshot = actual['components']['schemas']['ContentRestoreDraftSnapshot']
    assert {'numeric_material', 'numeric_check_ids'} <= set(snapshot['required'])


def test_generated_mock_boundary_lists_actual_restore_routes_and_keeps_core_54():
    directory = Path('packages/contracts/generated')
    coverage = json.loads((directory / 'runtime-route-coverage.json').read_text())
    for path, method in OPERATIONS:
        key = f'{method.upper()} {path}'
        assert key in coverage['registered_operations']
        assert key not in coverage['not_registered_operations']
    assert len(json.loads((directory / 'manifest.json').read_text())['models']) == 54
    routes = json.loads(Path('docs/requirements/routes.json').read_text())
    for path, method in OPERATIONS:
        match = [item for item in routes['routes'] if item['method'] == method.upper() and item['path'] == path]
        assert len(match) == 1
        assert match[0]['task_id'] == 'M6.2'
