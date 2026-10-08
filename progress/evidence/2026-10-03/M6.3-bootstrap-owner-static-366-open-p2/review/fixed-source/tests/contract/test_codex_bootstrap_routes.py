"""The five registered controls bind exact strict DTOs and original commands."""
from services.api.app.main import create_app


def test_five_runtime_operations_bind_declared_transport_without_future_routes(tmp_path):
    from services.api.app.config import Settings
    app = create_app(Settings(data_dir=tmp_path / 'not-created'))
    schema = app.openapi()
    contracts = {
        ('/session-preparations', 'post'): ('CodexBootstrapPreparationWrite', 'CodexBootstrapPreparationView', '201'),
        ('/session-preparations/{id}', 'get'): (None, 'CodexBootstrapPreparationView', '200'),
        ('/session-preparations/{id}/decision', 'post'): ('ApprovalDecision', 'CodexBootstrapDecisionAck', '200'),
        ('/sessions', 'post'): ('CodexSessionCreateWrite', 'CodexSessionCreateAck', '201'),
        ('/sessions/{id}', 'get'): (None, 'CodexSessionView', '200'),
    }
    for (path, method), (request, response, status) in contracts.items():
        operation = schema['paths']['/api/v1/codex' + path][method]
        assert operation['responses'][status]['content']['application/json']['schema'] == {'$ref': '#/components/schemas/' + response}
        parameters = operation.get('parameters', [])
        assert not any(item['in'] == 'query' for item in parameters)
        if request is None:
            assert 'requestBody' not in operation
        else:
            assert operation['requestBody'] == {'required': True, 'content': {
                'application/json': {'schema': {'$ref': '#/components/schemas/' + request}}}}
            headers = {item['name'].lower(): item for item in parameters if item['in'] == 'header'}
            assert all(headers[name]['required'] for name in ('origin', 'x-csrf-token', 'idempotency-key'))
            assert headers['idempotency-key']['schema']['pattern'] == '^[A-Za-z0-9_-]{1,128}$'
    assert '/api/v1/codex/turns' not in schema['paths']
    assert not (tmp_path / 'not-created').exists()
