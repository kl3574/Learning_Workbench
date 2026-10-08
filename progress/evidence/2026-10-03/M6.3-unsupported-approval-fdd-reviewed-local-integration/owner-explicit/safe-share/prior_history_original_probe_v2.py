import pytest
from services.api.app.application.errors import ApiError
from tests.integration.test_codex_generic_approval_boundaries import exercise, body_for, decision
from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case

def test_prior_approval_damage_blocks_next_claim_before_request(consent_case):
    from tests.integration.test_codex_turn_consent_http import consent_preparation, full_preview_body
    from tests.integration.test_codex_turn_dispatch_http import start_body
    def observe(case, prepared, raw, identifier):
        assert decision(case, identifier, body_for(case, prepared['turn_id'])).status_code == 200
    case, prepared, _, identifier = exercise(consent_case, observe)
    sid = prepared['session_id']
    _, next_prepared = consent_preparation(case, sid, case.get('sessions/'+sid).json()['revision'], 'next-prepare')
    value = next_prepared.json()
    proposal = case.post('consent-previews', full_preview_body(value), 'next-preview')
    consent = case.post('consents', {'proposal_id': proposal.json()['id'],
        'proposal_sha256': proposal.json()['proposal_sha256']}, 'next-grant')
    assert case.post(f'sessions/{sid}/turns', start_body(value, consent.json()), 'next-start').status_code == 202
    with case.app.state.database.transaction() as conn:
        conn.execute('DELETE FROM approvals WHERE id=?', (identifier,))
    case.app.state.synthetic_executor.peer = None
    before, calls = case.dump(), len(case.app.state.synthetic_transport_calls)
    with pytest.raises(ApiError) as error:
        case.app.state.codex_turn_worker.run_once()
    assert error.value.code == 'CODEX_HISTORY_DAMAGED'
    assert len(case.app.state.synthetic_transport_calls) == calls and case.dump() == before
