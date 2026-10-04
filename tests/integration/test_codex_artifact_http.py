"""Real artifact routes and owned source boundaries; no untrusted scan claims."""
from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case

__all__ = ['consent_case', 'base_consent_case']


def test_codex_artifact_routes_are_real_and_no_manifest_is_registered_by_get(consent_case):
    case, _, sid, _, _, _ = consent_case
    paths = case.app.openapi()['paths']
    assert 'get' in paths.get('/api/v1/codex/sessions/{id}/turns/{turn_id}/artifacts', {})
    assert 'post' in paths.get('/api/v1/codex/sessions/{id}/artifacts/import', {})
    assert 'get' in paths.get('/api/v1/codex/artifact-imports/{job_id}', {})
    before = case.dump()
    response = case.get(f'sessions/{sid}/turns/missing_turn/artifacts')
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'REFERENCE_MISSING'
    unchanged = case.dump() == before
    assert unchanged
