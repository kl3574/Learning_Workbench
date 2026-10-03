"""Shared Jobs and Artifacts transport must retain the Review header boundary."""
import pytest

from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_review_http import prepared_review_http as prepared_review_http, review_create


@pytest.mark.parametrize('operation', ['cancel', 'download'])
@pytest.mark.parametrize('header', ['Idempotency-Key', 'X-CSRF-Token'])
def test_review_control_and_report_reject_duplicate_headers(prepared_review_http, operation, header):
    case = prepared_review_http
    _, _, review_path = review_create(case)
    identifier = review_path.rsplit('/', 1)[1]
    if operation == 'download':
        assert case.app.state.review_worker.run_once()
        path = case.client.get(review_path).json()['evidence_paths'][0]
    else:
        path = '/api/v1/jobs/' + identifier + '/cancel'
    headers = [*command(case.headers, 'control').items(), (header, 'synthetic-conflict')]
    before = table_hashes(case.database)
    response = (case.client.get(path, headers=headers) if operation == 'download' else
                case.client.post(path, json={'expected_revision': 1}, headers=headers))
    assert response.status_code == 400, response.text
    assert response.json()['error']['code'] == 'SCHEMA_INVALID'
    assert table_hashes(case.database) == before
