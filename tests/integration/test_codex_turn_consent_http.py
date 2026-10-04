"""Real Provider/Codex local consent seams; never an external model request."""
from datetime import datetime, timedelta, timezone

from tests.integration.test_codex_turn_preparation_http import prepared, turn_case

__all__ = ['turn_case']


def preview_body(value, provider_revision=1):
    return {'preparation_id': value['id'], 'preparation_sha256': value['preparation_sha256'],
        'expected_job_revision': 1, 'expected_provider_revision': provider_revision,
        'budget': {'max_input_tokens': 4096, 'max_output_tokens': 64, 'max_provider_calls': 1,
                   'max_search_calls': 0, 'max_cost_usd': None},
        'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat().replace('+00:00', 'Z')}


def test_unregistered_codex_complete_input_proof_refuses_real_preview_without_mutation(turn_case, monkeypatch):
    case, runtime, _, _, _ = turn_case
    value = prepared(turn_case).json()
    def forbidden(*args, **kwargs):
        raise AssertionError('local preview attempted bootstrap or external execution')
    monkeypatch.setattr(runtime, 'execute', forbidden)
    before = case.dump()
    response = case.post('consent-previews', preview_body(value), 'preview-original')
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'CODEX_INPUT_PROOF_UNAVAILABLE'
    assert case.dump() == before
    assert case.get('turn-preparations/' + value['id']).json() == value
