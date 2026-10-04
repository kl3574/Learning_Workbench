import pytest
from tests.integration.test_assessment_learning_port import assessment_learning_state

from tests.integration.test_codex_artifact_import_http import selected, consent_case, base_consent_case
__all__ = ['consent_case', 'base_consent_case']
assessment_state = assessment_learning_state


def test_learner_can_read_safe_aggregate_job_revision_before_explicit_cancel(consent_case):
    case, sid, _, body = selected(consent_case)
    created = case.post(f'sessions/{sid}/artifacts/import', body, 'original-import')
    assert created.status_code == 202
    identifier = created.json()['id']
    changed = case.client.post('/api/v1/session/role', json={'role':'learner'},
        headers={**case.headers, 'Idempotency-Key':'learner'})
    assert changed.status_code == 200
    before = case.dump()
    current = case.client.get('/api/v1/jobs/'+identifier)
    assert current.status_code == 200
    assert current.json()['result_refs'] == [] and current.json()['error'] is None
    assert case.dump() == before
    assert case.get('artifact-imports/'+identifier).status_code == 403
    cancelled = case.client.post('/api/v1/jobs/'+identifier+'/cancel',
        json={'expected_revision':current.json()['revision']},
        headers={**case.headers, 'Idempotency-Key':'cancel'})
    assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_active_policy_keeps_safe_job_get_cancel_without_subject_material(assessment_state, mode):
    from tests.integration.test_assessment_policy import start
    from tests.integration.test_codex_turn_preparation_http import identity
    from tests.integration.test_codex_turn_consent_http import make_consent_case
    from tests.integration.test_codex_turn_dispatch_http import make_dispatch_case
    database, _, fixture, assessment = assessment_state
    for original in make_consent_case(database.settings.data_dir):
        for values in make_dispatch_case(original):
            case, sid, _, body = selected(values)
            created = case.post(f'sessions/{sid}/artifacts/import', body, 'policy-import')
            assert created.status_code == 202
            identifier = created.json()['id']
            if mode == 'independent':
                from services.api.app.application.errors import ApiError
                # Real exclusive assessment admission must not be bypassed to
                # fabricate a queued-work/independent state. First stop the
                # owned children; then verify safe terminal observation there.
                before = case.dump()
                with pytest.raises(ApiError) as blocked:
                    start((database, identity(case), fixture, assessment), mode=mode)
                assert blocked.value.code == 'SUBJECT_WORK_ACTIVE' and case.dump() == before
                basis = case.client.get('/api/v1/jobs/'+identifier)
                assert basis.status_code == 200
                stopped = case.client.post('/api/v1/jobs/'+identifier+'/cancel',
                    json={'expected_revision':basis.json()['revision']},
                    headers={**case.headers, 'Idempotency-Key':'before-independent'})
                assert stopped.status_code == 200 and stopped.json()['status'] == 'cancelled'
            start((database, identity(case), fixture, assessment), mode=mode)
            before = case.dump()
            current = case.client.get('/api/v1/jobs/'+identifier)
            assert current.status_code == 200
            assert current.json()['result_refs'] == [] and current.json()['warnings'] == [] and current.json()['error'] is None
            assert 'Synthetic exact answer' not in current.text and 'artifact_ids' not in current.text
            assert case.get('artifact-imports/'+identifier).status_code == 409
            assert case.dump() == before
            cancelled = case.client.post('/api/v1/jobs/'+identifier+'/cancel',
                json={'expected_revision':current.json()['revision']},
                headers={**case.headers, 'Idempotency-Key':'policy-cancel'})
            assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'
            assert len(case.app.state.synthetic_transport_calls) == 1
