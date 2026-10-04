from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.codex_answer_materializer import CheckedAnswerMaterializer
from tests.integration.test_codex_turn_dispatch_http import queued, consent_case, base_consent_case
__all__ = ['consent_case', 'base_consent_case']


def test_actual_model_result_survives_blob_storage_failure(consent_case, monkeypatch):
    case, _, _, _, _, _ = consent_case
    producer = CheckedAnswerMaterializer(case.app.state.settings.data_dir)
    case.app.state.codex_turn_service.artifacts.producer = producer
    prep, _, _, _ = queued(consent_case)
    def unavailable(*args, **kwargs):
        raise ApiError(503, 'BLOB_STORAGE_UNAVAILABLE', 'Synthetic storage failure')
    monkeypatch.setattr(producer.blobs, 'write', unavailable)
    assert case.app.state.codex_turn_worker.run_once() is True
    control = case.get('turns/'+prep['turn_id']).json()
    assert control['outcome'] == 'failed' and control['error_code'] == 'CODEX_SOURCE_UNAVAILABLE'
    assert control['manifest_id'] is None
    with case.app.state.database.transaction(immediate=False) as conn:
        states, _ = case.app.state.codex_turn_service.outbound_owner.owned_states(conn, case.app.state.database.workspace_id())
        result = states[prep['turn_id']].finished.execution_result
    assert result.outcome == 'completed' and result.consumed_provider_calls == 1
    assert result.answer == 'Synthetic exact answer α\n'
    assert case.app.state.codex_turn_worker.run_once() is False
    assert len(case.app.state.synthetic_transport_calls) == 1
