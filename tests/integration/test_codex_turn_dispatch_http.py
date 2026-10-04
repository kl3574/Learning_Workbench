"""Real local consumption/lifecycle with an explicit protocol-only peer."""
from fastapi.testclient import TestClient
import pytest

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.codex_turn_worker import SyntheticCodexExecutor
from services.api.app.application.provider_codex_execution import SyntheticCodexResponse
from services.api.app.main import create_app
from tests.integration.test_codex_bootstrap_http import Case, make_case
from tests.integration.test_codex_turn_consent_http import consent_case as base_fixture, grant_fixture, make_consent_case

from tests.integration.test_assessment_learning_port import assessment_learning_state

base_consent_case = base_fixture
assessment_state = assessment_learning_state


@pytest.fixture
def consent_case(base_consent_case):
    yield from make_dispatch_case(base_consent_case)


def make_dispatch_case(base_values):
    case,runtime,sid,proofs,bootstrap_body,bootstrap_ack=base_values
    calls=[]
    def transport(body,endpoint,max_output):
        calls.append((body,endpoint,max_output))
        answer='Synthetic exact answer α\n'
        return canonical_bytes(SyntheticCodexResponse(version='codex-synthetic-response-v1',outcome='completed',
            answer=answer,input_tokens=len(body),output_tokens=len(answer.encode()),error_code=None))
    executor=SyntheticCodexExecutor(transport)
    app=create_app(case.app.state.settings,codex_bootstrap_runtime=runtime,codex_proofs=proofs,codex_executor=executor)
    app.state.synthetic_transport_calls=calls
    app.state.synthetic_executor=executor
    client=TestClient(app,base_url=app.state.settings.origin)
    client.cookies.update(case.client.cookies)
    try:
        yield Case(app,client,case.headers,case.actor_id),runtime,sid,proofs,bootstrap_body,bootstrap_ack
    finally:
        client.close()


def start_body(preparation, consent):
    return {'preparation_id': preparation['id'], 'preparation_sha256': preparation['preparation_sha256'],
        'consent_id': consent['id'], 'expected_session_revision': preparation['session_revision']}


def test_start_really_consumes_consent_and_queues_one_job_without_execution(consent_case):
    case, runtime, sid, _, bootstrap_body, bootstrap_ack = consent_case
    _, preparation, _, _, _, consent = grant_fixture(consent_case)
    body = start_body(preparation.json(), consent.json())
    response = case.post(f'sessions/{sid}/turns', body, 'start-original')
    assert response.status_code == 202
    value = response.json()
    assert value == {'turn_id': preparation.json()['turn_id'], 'session_revision': 4,
        'job': {'id': preparation.json()['job']['id'], 'status': 'queued'}}
    before = case.dump()
    control = case.get('turns/' + value['turn_id']).json()
    assert control['job'] == value['job'] and control['job_revision'] == 2
    assert control['execution'] == 'not_started' and control['started_at'] is None
    dispatch = case.get('consents/' + consent.json()['id']).json()['dispatch']
    assert dispatch is not None and dispatch['started_at'] is None and dispatch['consumed_provider_calls'] == 0
    assert case.post(f'sessions/{sid}/turns', body, 'start-original').content == response.content
    assert case.post(f'sessions/{sid}/turns', {**body, 'expected_session_revision': 4}, 'new-start').status_code == 409
    assert case.post('sessions', bootstrap_body, 'bootstrap-session').content == bootstrap_ack
    assert case.dump() == before and len(runtime.calls) == 1


def test_actual_single_protocol_dispatch_and_repeat_never_request_again(consent_case):
    case,_,sid,_,_,_=consent_case
    _,preparation,_,_,_,consent=grant_fixture(consent_case)
    body=start_body(preparation.json(),consent.json())
    ack=case.post(f'sessions/{sid}/turns',body,'start')
    assert ack.status_code==202
    worker=case.app.state.codex_turn_worker
    assert case.app.state.synthetic_transport_calls==[]
    assert worker.run_once() is True
    assert len(case.app.state.synthetic_transport_calls)==1
    current=case.get('turns/'+preparation.json()['turn_id'])
    assert current.status_code==200
    assert current.json()['outcome']=='completed' and current.json()['job_revision']==4
    dispatch=case.get('consents/'+consent.json()['id']).json()['dispatch']
    assert dispatch['outcome']=='completed' and dispatch['consumed_provider_calls']==1
    assert dispatch['input_tokens']==len(case.app.state.synthetic_transport_calls[0][0])
    assert case.get('sessions/'+sid).json()['revision']==5
    before=case.dump()
    assert worker.run_once() is False and worker.recover()==0
    assert case.post(f'sessions/{sid}/turns',body,'start').content==ack.content
    assert case.dump()==before and len(case.app.state.synthetic_transport_calls)==1


def queued(consent_case):
    case,_,sid,_,_,_=consent_case
    _,preparation,_,_,_,consent=grant_fixture(consent_case)
    body=start_body(preparation.json(),consent.json())
    ack=case.post(f'sessions/{sid}/turns',body,'start')
    assert ack.status_code==202
    return preparation.json(),consent.json(),body,ack


@pytest.mark.parametrize('change,code',[('revoke','CODEX_CONSENT_REVOKED'),('learner','POLICY_DENIED'),
    ('expiry','CODEX_CONSENT_EXPIRED'),('proof','CODEX_INPUT_PROOF_UNAVAILABLE')])
def test_queued_permission_loss_converges_without_actual_request(consent_case,monkeypatch,change,code):
    from services.api.app.application import provider_codex_consents as owner
    case,_,sid,proofs,_,_=consent_case
    prep,consent,body,ack=queued(consent_case)
    if change=='revoke':
        assert case.post('consents/'+consent['id']+'/revoke',{'expected_revision':1},'revoke').status_code==200
    elif change=='learner':
        assert case.client.post('/api/v1/session/role',json={'role':'learner'},
            headers={**case.headers,'Idempotency-Key':'lose-role'}).status_code==200
    elif change=='expiry':
        monkeypatch.setattr(owner,'utc_now',lambda:consent['summary']['expires_at'])
    else:
        monkeypatch.setattr(proofs.codex,'_withdrawn',frozenset([consent['summary']['input_token_assurance']['proof_sha256']]))
    assert case.app.state.codex_turn_worker.run_once() is True
    control=case.get('turns/'+prep['turn_id'])
    assert control.status_code==200
    assert control.json()['outcome']=='failed' and control.json()['error_code']==code
    assert case.app.state.synthetic_transport_calls==[]
    assert case.get('sessions/'+sid).json()['revision']==5
    before=case.dump()
    assert case.app.state.codex_turn_worker.run_once() is False
    assert case.dump()==before


def test_second_request_is_blocked_after_retaining_first_response(consent_case):
    from services.api.app.application.errors import ApiError
    case,_,_,_,_,_=consent_case
    prep,consent,_,_=queued(consent_case)
    executor=case.app.state.synthetic_executor
    owner=case.app.state.codex_turn_service.outbound_owner
    with case.app.state.database.transaction(immediate=False) as conn:
        state=owner.owned_states(conn,case.app.state.database.workspace_id())[0][prep['turn_id']]
        request=owner.prepared_request(state)
    def twice(gate):
        gate.request(request.body,endpoint=request.endpoint,max_output_tokens=64)
        try:
            gate.request(request.body,endpoint=request.endpoint,max_output_tokens=64)
        except ApiError:
            pass
    executor.peer=twice
    assert case.app.state.codex_turn_worker.run_once() is True
    control=case.get('turns/'+prep['turn_id']).json()
    assert control['outcome']=='failed' and control['error_code']=='CODEX_NEW_OUTBOUND_CONSENT_REQUIRED'
    assert len(case.app.state.synthetic_transport_calls)==1
    with case.app.state.database.transaction(immediate=False) as conn:
        states,_=case.app.state.codex_turn_service.outbound_owner.owned_states(conn,case.app.state.database.workspace_id())
        result=states[prep['turn_id']].finished.execution_result
    assert result.answer=='Synthetic exact answer α\n' and result.first_response is not None
    assert case.get('consents/'+consent['id']).json()['dispatch']['consumed_provider_calls']==1


@pytest.mark.parametrize('when',['queued','inside_transport'])
def test_cancel_is_same_owner_and_original_ack_survives(consent_case,when):
    case,_,sid,_,_,_=consent_case
    prep,consent,body,ack=queued(consent_case)
    executor=case.app.state.synthetic_executor
    def cancel():
        response=case.client.post('/api/v1/jobs/'+prep['job']['id']+'/cancel',json={'expected_revision':2 if when=='queued' else 3},
            headers={**case.headers,'Idempotency-Key':'cancel'})
        assert response.status_code==200
        return response
    if when=='queued':
        cancel()
        assert case.app.state.codex_turn_worker.run_once() is False
    else:
        original=executor.transport
        def transport(*args):
            cancel()
            return original(*args)
        executor.transport=transport
        assert case.app.state.codex_turn_worker.run_once() is True
    control=case.get('turns/'+prep['turn_id'])
    assert control.status_code==200 and control.json()['outcome']=='cancelled'
    assert case.get('sessions/'+sid).json()['revision']==6
    assert len(case.app.state.synthetic_transport_calls)==(0 if when=='queued' else 1)
    before=case.dump()
    assert case.post(f'sessions/{sid}/turns',body,'start').content==ack.content
    assert case.dump()==before


def test_actual_response_survives_actor_loss_without_renewing_permission(consent_case):
    case,_,sid,_,_,_=consent_case
    prep,_,_,_=queued(consent_case)
    executor=case.app.state.synthetic_executor
    original=executor.transport
    def transport(*args):
        assert case.client.post('/api/v1/session/role',json={'role':'learner'},
            headers={**case.headers,'Idempotency-Key':'lose-role'}).status_code==200
        return original(*args)
    executor.transport=transport
    assert case.app.state.codex_turn_worker.run_once() is True
    control=case.get('turns/'+prep['turn_id'])
    assert control.status_code==200 and control.json()['outcome']=='failed'
    assert control.json()['error_code']=='POLICY_DENIED'
    assert case.get('sessions/'+sid).json()['active_turn_id'] is None
    assert len(case.app.state.synthetic_transport_calls)==1
    with case.app.state.database.transaction(immediate=False) as conn:
        states,_=case.app.state.codex_turn_service.outbound_owner.owned_states(conn,case.app.state.database.workspace_id())
        assert states[prep['turn_id']].finished.execution_result.answer=='Synthetic exact answer α\n'


def test_new_turn_freezes_last_two_actual_completed_pairs(consent_case):
    from tests.integration.test_codex_turn_consent_http import consent_preparation,full_preview_body
    case,_,sid,_,_,_=consent_case
    turns=[]
    for index in range(3):
        revision=case.get('sessions/'+sid).json()['revision']
        _,prepared=consent_preparation(case,sid,revision,key='prepare-'+str(index))
        value=prepared.json()
        assert value['summary']['history_turn_ids']==turns[-2:]
        preview=case.post('consent-previews',full_preview_body(value),'preview-'+str(index))
        assert preview.status_code==201
        assert len(preview.json()['summary']['messages'])==2+2*min(index,2)
        grant=case.post('consents',{'proposal_id':preview.json()['id'],'proposal_sha256':preview.json()['proposal_sha256']},'grant-'+str(index))
        assert grant.status_code==201
        assert case.post(f'sessions/{sid}/turns',start_body(value,grant.json()),'start-'+str(index)).status_code==202
        assert case.app.state.codex_turn_worker.run_once() is True
        result=case.get('turns/'+value['turn_id']+'/result')
        assert result.status_code==200 and result.json()['control']['outcome']=='completed'
        assert result.json()['answer_markdown']=='Synthetic exact answer α\n'
        assert result.json()['mathematical']==result.json()['sources']==result.json()['independent_pedagogy']=='NOT_RUN'
        turns.append(value['turn_id'])
    revision=case.get('sessions/'+sid).json()['revision']
    _,prepared=consent_preparation(case,sid,revision,key='next')
    assert prepared.json()['summary']['history_turn_ids']==turns[-2:]
    before=case.dump()
    assert case.get('turn-preparations/'+prepared.json()['id']).status_code==200
    assert case.dump()==before and len(case.app.state.synthetic_transport_calls)==3


def test_completed_history_is_retained_when_current_proof_disappears(consent_case,monkeypatch):
    case,_,sid,proofs,_,_=consent_case
    prep,consent,_,_=queued(consent_case)
    assert case.app.state.codex_turn_worker.run_once() is True
    monkeypatch.setattr(proofs.codex,'_withdrawn',frozenset([consent['summary']['input_token_assurance']['proof_sha256']]))
    body={**prep['request'],'expected_session_revision':5}
    response=case.post(f'sessions/{sid}/turn-preparations',body,'unavailable-history')
    assert response.status_code==202
    assert response.json()['validity']=='unavailable' and response.json()['summary']['history_turn_ids']==[prep['turn_id']]
    before=case.dump()
    assert case.get('turn-preparations/'+response.json()['id']).json()==response.json()
    assert case.dump()==before and len(case.app.state.synthetic_transport_calls)==1


def test_crash_permit_recovery_is_unknown_not_a_new_execution(consent_case,monkeypatch):
    from contextlib import ExitStack
    from datetime import datetime,timedelta,timezone
    from services.api.app.application import codex_turn_worker as module
    case,runtime,sid,proofs,_,_=consent_case
    prep,consent,body,ack=queued(consent_case)
    worker=case.app.state.codex_turn_worker
    with ExitStack() as stack:
        claim=worker._claim(stack)
        assert claim and worker.recover()==0
        assert case.get('turns/'+prep['turn_id']).json()['execution']=='active'
    assert worker.recover()==0  # live lease, even though owner lock is now free
    later=(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat().replace('+00:00','Z')
    monkeypatch.setattr(module,'utc_now',lambda:later)
    restarted=create_app(case.app.state.settings,codex_bootstrap_runtime=runtime,codex_proofs=proofs)
    replacement=restarted.state.codex_turn_worker
    assert replacement.recover()==1
    assert case.get('turns/'+prep['turn_id']).json()['outcome']=='unknown'
    dispatch=case.get('consents/'+consent['id']).json()['dispatch']
    assert dispatch['consumed_provider_calls']==1 and dispatch['input_tokens'] is None
    result=case.get('turns/'+prep['turn_id']+'/result').json()
    assert result['output_state']=='none' and result['answer_markdown']==''
    before=case.dump()
    assert replacement.recover()==0 and replacement.run_once() is False
    assert case.post(f'sessions/{sid}/turns',body,'start').content==ack.content
    assert case.dump()==before and case.app.state.synthetic_transport_calls==[]


@pytest.mark.parametrize('phase',['consume','claim','terminal'])
def test_owner_transactions_rollback_without_partial_cross_owner_facts(consent_case,monkeypatch,phase):
    from services.api.app.infrastructure.codex_turn_repository import CodexTurnRepository
    from services.api.app.application.codex_turn_models import TurnStarted,TurnLifecycle
    case,_,sid,_,_,_=consent_case
    _,prepared,_,_,_,consent=grant_fixture(consent_case)
    body=start_body(prepared.json(),consent.json())
    if phase!='consume':
        assert case.post(f'sessions/{sid}/turns',body,'start').status_code==202
    before=case.dump()
    original=CodexTurnRepository.append
    def append(self,state,event,now):
        if (phase=='consume' and isinstance(event,TurnStarted) or
            isinstance(event,TurnLifecycle) and event.phase==phase):
            raise RuntimeError('synthetic transaction failure')
        return original(self,state,event,now)
    monkeypatch.setattr(CodexTurnRepository,'append',append)
    if phase=='consume':
        response=case.post(f'sessions/{sid}/turns',body,'start')
        assert response.status_code==500
    else:
        with pytest.raises(RuntimeError,match='synthetic transaction failure'):
            case.app.state.codex_turn_worker.run_once()
    if phase!='terminal':
        assert case.dump()==before and case.app.state.synthetic_transport_calls==[]
    else:
        current=case.get('turns/'+prepared.json()['turn_id']).json()
        assert current['execution']=='active' and current['outcome'] is None
        assert len(case.app.state.synthetic_transport_calls)==1
        assert case.app.state.codex_turn_worker.run_once() is False


def test_current_production_has_no_dispatch_adapter_and_never_consumes(consent_case):
    case,runtime,sid,proofs,_,_=consent_case
    _,prep,_,_,_,consent=grant_fixture(consent_case)
    app=create_app(case.app.state.settings,codex_bootstrap_runtime=runtime,codex_proofs=proofs)
    with TestClient(app,base_url=app.state.settings.origin) as client:
        client.cookies.update(case.client.cookies)
        response=client.post('/api/v1/codex/sessions/'+sid+'/turns',json=start_body(prep.json(),consent.json()),
            headers={**case.headers,'Idempotency-Key':'no-adapter'})
        assert response.status_code==503 and response.json()['error']['code']=='CODEX_RUNTIME_UNAVAILABLE'
        # Compare owner tables rather than unrelated ordinary startup workers.
        with app.state.database.transaction(immediate=False) as conn:
            states,_=app.state.codex_turn_service.outbound_owner.owned_states(conn,app.state.database.workspace_id())
            assert states[prep.json()['turn_id']].queued is None
        assert case.get('turns/'+prep.json()['turn_id']).json()['job_revision']==1
        assert app.state.codex_turn_worker.run_once() is False
    assert case.app.state.synthetic_transport_calls==[]


@pytest.mark.parametrize('stage',['consume','claim'])
def test_expiry_at_durable_start_boundary_is_normal_refusal(consent_case,monkeypatch,stage):
    from services.api.app.application import provider_codex_consents as owner
    from services.api.app.infrastructure import authoring_job_repository as job_owner
    case,_,sid,_,_,_=consent_case
    _,prep,_,_,_,consent=grant_fixture(consent_case)
    body=start_body(prep.json(),consent.json())
    expired=consent.json()['summary']['expires_at']
    if stage=='consume':
        service=case.app.state.codex_turn_service.outbound_owner
        original=service.require_current
        def check(*args):
            original(*args)
            monkeypatch.setattr(owner,'utc_now',lambda:expired)
        monkeypatch.setattr(service,'require_current',check)
        before=case.dump()
        response=case.post(f'sessions/{sid}/turns',body,'start')
        assert response.status_code==409 and response.json()['error']['code']=='CODEX_CONSENT_EXPIRED'
        assert case.dump()==before
    else:
        assert case.post(f'sessions/{sid}/turns',body,'start').status_code==202
        from datetime import datetime,timedelta
        monkeypatch.setattr(job_owner,'utc_now',lambda:expired)
        monkeypatch.setattr(job_owner,'expires_after',lambda seconds:(datetime.fromisoformat(expired.replace('Z','+00:00'))+timedelta(seconds=seconds)).isoformat().replace('+00:00','Z'))
        assert case.app.state.codex_turn_worker.run_once() is True
        control=case.get('turns/'+prep.json()['turn_id'])
        assert control.status_code==200 and control.json()['error_code']=='CODEX_CONSENT_EXPIRED'
        assert case.get('consents/'+consent.json()['id']).json()['dispatch']['consumed_provider_calls']==0
    assert case.app.state.synthetic_transport_calls==[]


@pytest.mark.parametrize('same_key',[True,False])
def test_parallel_start_consumes_once_and_parallel_workers_never_redeliver(consent_case,same_key):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier,Event
    from services.api.app.application.codex_turn_worker import CodexTurnWorker
    case,_,sid,_,_,_=consent_case
    _,prep,_,_,_,consent=grant_fixture(consent_case)
    body=start_body(prep.json(),consent.json())
    barrier=Barrier(2)
    def start(index):
        barrier.wait(timeout=5)
        return case.post(f'sessions/{sid}/turns',body,'start' if same_key else 'start-'+str(index))
    with ThreadPoolExecutor(2) as pool:
        responses=list(pool.map(start,range(2)))
    assert sorted(response.status_code for response in responses)==([202,202] if same_key else [202,412])
    if same_key:
        assert responses[0].content==responses[1].content
    assert case.get('sessions/'+sid).json()['revision']==4
    entered,release=Event(),Event()
    executor=case.app.state.synthetic_executor
    original=executor.transport
    def transport(*args):
        entered.set()
        assert release.wait(timeout=5)
        return original(*args)
    executor.transport=transport
    service=case.app.state.codex_turn_service
    other=CodexTurnWorker(service,service.outbound_owner,executor)
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(case.app.state.codex_turn_worker.run_once)
        assert entered.wait(timeout=5)
        try:
            assert other.run_once() is False and other.recover()==0
            assert case.get('turns/'+prep.json()['turn_id']).json()['execution']=='active'
        finally:
            release.set()
        assert future.result(timeout=5) is True
    assert len(case.app.state.synthetic_transport_calls)==1
    assert case.get('sessions/'+sid).json()['revision']==5


def test_unknown_actual_request_is_not_retried_or_implicitly_selected_as_history(consent_case):
    from tests.integration.test_codex_turn_consent_http import consent_preparation
    case,runtime,sid,proofs,_,_=consent_case
    prep,consent,body,ack=queued(consent_case)
    actual=[]
    def transport(*args):
        actual.append(True)
        raise OSError('synthetic peer lost response')
    case.app.state.synthetic_executor.transport=transport
    assert case.app.state.codex_turn_worker.run_once() is True
    current=case.get('turns/'+prep['turn_id']).json()
    assert current['outcome']=='unknown'
    assert case.get('consents/'+consent['id']).json()['dispatch']['consumed_provider_calls']==1
    restarted=create_app(case.app.state.settings,codex_bootstrap_runtime=runtime,codex_proofs=proofs,
        codex_executor=case.app.state.synthetic_executor)
    before=case.dump()
    assert restarted.state.codex_turn_worker.recover()==0 and restarted.state.codex_turn_worker.run_once() is False
    assert case.post(f'sessions/{sid}/turns',body,'start').content==ack.content
    assert case.post(f'sessions/{sid}/turns',{**body,'expected_session_revision':5},'retry').status_code==409
    assert case.dump()==before and actual==[True]
    _,following=consent_preparation(case,sid,5,key='explicit-new-turn')
    assert following.json()['turn_id']!=prep['turn_id'] and following.json()['summary']['history_turn_ids']==[]


def test_result_delivery_rechecks_role_after_original_read_snapshot(consent_case,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    case,_,_,_,_,_=consent_case
    prep,_,_,_=queued(consent_case)
    assert case.app.state.codex_turn_worker.run_once() is True
    service=case.app.state.codex_turn_service
    original=service._control_views
    entered,release=Event(),Event()
    def held(*args):
        result=original(*args)
        entered.set()
        assert release.wait(timeout=5)
        return result
    monkeypatch.setattr(service,'_control_views',held)
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(case.get,'turns/'+prep['turn_id']+'/result')
        assert entered.wait(timeout=5)
        try:
            assert case.client.post('/api/v1/session/role',json={'role':'learner'},
                headers={**case.headers,'Idempotency-Key':'revoke-delivery'}).status_code==200
            before=case.dump()
        finally:
            release.set()
        response=future.result(timeout=5)
    assert response.status_code==403 and 'answer_markdown' not in response.json()
    assert case.dump()==before


def test_permission_loss_after_permit_before_transport_has_zero_actual_requests(consent_case):
    case,_,_,_,_,_=consent_case
    prep,consent,_,_=queued(consent_case)
    owner=case.app.state.codex_turn_service.outbound_owner
    with case.app.state.database.transaction(immediate=False) as conn:
        state=owner.owned_states(conn,case.app.state.database.workspace_id())[0][prep['turn_id']]
        request=owner.prepared_request(state)
    def peer(gate):
        assert case.client.post('/api/v1/session/role',json={'role':'learner'},
            headers={**case.headers,'Idempotency-Key':'lose-before-send'}).status_code==200
        gate.request(request.body,endpoint=request.endpoint,max_output_tokens=64)
    case.app.state.synthetic_executor.peer=peer
    assert case.app.state.codex_turn_worker.run_once() is True
    current=case.get('turns/'+prep['turn_id']).json()
    assert current['outcome']=='failed' and current['error_code']=='POLICY_DENIED'
    assert case.app.state.synthetic_transport_calls==[]
    with case.app.state.database.transaction(immediate=False) as conn:
        state=owner.owned_states(conn,case.app.state.database.workspace_id())[0][prep['turn_id']]
        assert state.started is not None and state.finished.execution_result.consumed_provider_calls==0
    # The outer dispatch conservatively counts its persisted possible-send
    # permission; the original checked receipt separately proves zero actual calls.
    assert current['consent_control']['id']==consent['id']


def test_selected_completed_history_is_omitted_only_as_a_whole_pair(consent_case):
    from tests.integration.test_codex_turn_consent_http import full_preview_body
    case,_,sid,_,_,_=consent_case
    request={'message':'s'*7000,'context_refs':[],'expected_session_revision':2,'provider_id':'codex_peer',
        'tools':{'max_tool_calls':0,'wall_seconds':30}}
    response=case.post(f'sessions/{sid}/turn-preparations',request,'large-history')
    assert response.status_code==202
    prep=response.json()
    preview=case.post('consent-previews',full_preview_body(prep),'large-preview')
    assert preview.status_code==201
    consent=case.post('consents',{'proposal_id':preview.json()['id'],'proposal_sha256':preview.json()['proposal_sha256']},'large-grant')
    assert consent.status_code==201
    assert case.post(f'sessions/{sid}/turns',start_body(prep,consent.json()),'large-start').status_code==202
    assert case.app.state.codex_turn_worker.run_once() is True
    assert case.get('turns/'+prep['turn_id']).json()['outcome']=='completed'
    request={**request,'message':'x'*8000,'expected_session_revision':5}
    second=case.post(f'sessions/{sid}/turn-preparations',request,'long-next')
    assert second.status_code==202
    assert second.json()['request']['message']==request['message']
    assert second.json()['summary']['history_turn_ids']==[]
    assert [item['code'] for item in second.json()['summary']['warnings']]==['CODEX_CONTEXT_HISTORY_OMITTED']
    owner=case.app.state.codex_turn_service.outbound_owner
    with case.app.state.database.transaction(immediate=False) as conn:
        _,sources=owner.owned_states(conn,case.app.state.database.workspace_id())
        frozen=sources[second.json()['turn_id']].material.context
        assert frozen.history==[] and len(frozen.omitted_history)==1
        assert frozen.omitted_history[0].user=='s'*7000
        assert frozen.omitted_history[0].answer=='Synthetic exact answer α\n'


def test_missing_production_proof_is_not_reported_as_only_missing_adapter(consent_case):
    from services.api.app.application.provider_budget import ProofRegistry
    case,runtime,sid,_,_,_=consent_case
    _,prep,_,_,_,consent=grant_fixture(consent_case)
    app=create_app(case.app.state.settings,codex_bootstrap_runtime=runtime,codex_proofs=ProofRegistry())
    client=TestClient(app,base_url=app.state.settings.origin)
    try:
        client.cookies.update(case.client.cookies)
        before=case.dump()
        response=client.post('/api/v1/codex/sessions/'+sid+'/turns',json=start_body(prep.json(),consent.json()),
            headers={**case.headers,'Idempotency-Key':'missing-proof'})
        assert response.status_code==503 and response.json()['error']['code']=='CODEX_INPUT_PROOF_UNAVAILABLE'
        assert case.dump()==before and case.app.state.synthetic_transport_calls==[]
    finally:
        client.close()


def test_actual_logout_after_request_keeps_response_but_new_actor_cannot_restart(consent_case):
    case,runtime,sid,proofs,_,_=consent_case
    prep,_,body,_=queued(consent_case)
    executor=case.app.state.synthetic_executor
    original=executor.transport
    def transport(*args):
        assert case.client.post('/api/v1/session/logout',json={},headers=case.headers).status_code==200
        return original(*args)
    executor.transport=transport
    assert case.app.state.codex_turn_worker.run_once() is True
    assert case.get('turns/'+prep['turn_id']).status_code==401
    new=make_case(case.app.state.settings.data_dir,codex_bootstrap_runtime=runtime,codex_proofs=proofs)
    try:
        assert new.actor_id!=case.actor_id
        before=case.dump()
        result=new.get('turns/'+prep['turn_id']+'/result')
        assert result.status_code==200 and result.json()['answer_markdown']=='Synthetic exact answer α\n'
        assert result.json()['control']['outcome']=='failed' and result.json()['control']['error_code']=='POLICY_DENIED'
        assert new.post(f'sessions/{sid}/turns',body,'start').status_code==403
        assert new.get('sessions/'+sid).json()['revision']==5
        assert case.dump()==before and len(case.app.state.synthetic_transport_calls)==1
    finally:
        new.client.close()


def test_real_open_book_policy_stops_queued_dispatch_without_a_request(assessment_state):
    from tests.integration.test_assessment_policy import start
    from tests.integration.test_codex_turn_preparation_http import identity
    database,_,fixture,assessment=assessment_state
    for original in make_consent_case(database.settings.data_dir):
        for values in make_dispatch_case(original):
            case,_,sid,_,_,_=values
            prep,_,_,_=queued(values)
            start((database,identity(case),fixture,assessment),mode='open_book')
            assert case.app.state.codex_turn_worker.run_once() is True
            control=case.get('turns/'+prep['turn_id'])
            assert control.status_code==200 and control.json()['outcome']=='failed'
            assert control.json()['error_code'] in {'POLICY_DENIED','ASSESSMENT_ACTIVE'}
            assert case.get('turns/'+prep['turn_id']+'/result').status_code==409
            assert case.get('sessions/'+sid).json()['revision']==5
            assert case.app.state.synthetic_transport_calls==[]


@pytest.mark.parametrize('damage',['provider_tail','codex_tail','job_tail','run','lease','context'])
def test_dispatch_current_and_original_ack_reject_damaged_owned_graph(consent_case,damage):
    from contextlib import ExitStack
    case,_,sid,_,_,_=consent_case
    prep,_,body,_=queued(consent_case)
    if damage=='lease':
        with ExitStack() as stack:
            assert case.app.state.codex_turn_worker._claim(stack)
    else:
        assert case.app.state.codex_turn_worker.run_once() is True
    with case.app.state.database.transaction() as conn:
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND (name LIKE 'provider_codex_%' OR name LIKE 'codex_turn_%')").fetchall():
            conn.execute('DROP TRIGGER '+row[0])
        if damage=='provider_tail':
            conn.execute('DELETE FROM provider_codex_events WHERE turn_id=? AND seq=(SELECT MAX(seq) FROM provider_codex_events WHERE turn_id=?)',(prep['turn_id'],prep['turn_id']))
        elif damage=='codex_tail':
            conn.execute('DELETE FROM codex_turn_events WHERE session_id=? AND seq=(SELECT MAX(seq) FROM codex_turn_events WHERE session_id=?)',(sid,sid))
        elif damage=='job_tail':
            conn.execute('DELETE FROM job_events WHERE job_id=? AND seq=(SELECT MAX(seq) FROM job_events WHERE job_id=?)',(prep['job']['id'],prep['job']['id']))
        elif damage=='run':
            conn.execute("UPDATE runs SET state_json='{}' WHERE id=?",(prep['job']['id'],))
        elif damage=='lease':
            conn.execute("UPDATE jobs SET lease_owner='lease_other' WHERE id=?",(prep['job']['id'],))
        else:
            conn.execute("UPDATE context_snapshots SET envelope_json='{}' WHERE id=?",(prep['summary']['context_snapshot_id'],))
    before=case.dump()
    responses=[case.get('turns/'+prep['turn_id']),case.get('turns/'+prep['turn_id']+'/result'),
        case.get('sessions/'+sid),case.post(f'sessions/{sid}/turns',body,'start')]
    assert [(response.status_code,response.json()['error']['code']) for response in responses]==[(409,'CODEX_HISTORY_DAMAGED')]*4
    assert case.dump()==before
