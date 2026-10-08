"""Private, explicit pure memory fixture. Actual HTTP owners; no host operation.
First turn waits for UI approve, then explicit private harness release before the
literal interpreter. Next turn uses an EMPTY operation registry for safe decline.
No fixture route or model socket is exposed; only a private file releases memory.
"""
import json
import time
from dataclasses import replace
from unittest.mock import patch
from packages.contracts.canonical import canonical_bytes
from services.api.app.config import Settings
from services.api.app.application.codex_operation_profile import CodexOperationRegistry, LiteralCommand, LiteralOperationProfile
from tests.integration.test_codex_turn_consent_http import make_consent_case
from tests.integration.test_codex_turn_dispatch_http import make_dispatch_case
from tests.integration.test_codex_generic_approval_http import callback_turn

_generators = []


def create_app():
    settings = Settings.from_env()
    def configured(**kwargs):
        return replace(settings, **kwargs)
    with patch('tests.integration.test_codex_bootstrap_http.Settings', configured):
        base = make_consent_case(settings.data_dir)
        _generators.append(base)
        values = next(base)
        dispatch = make_dispatch_case(values)
        _generators.append(dispatch)
        active = next(dispatch)
        case, prepared, _, _ = callback_turn(active)
        worker = case.app.state.codex_turn_worker
        approvals = case.app.state.codex_turn_service.approvals
        approvals.operations = CodexOperationRegistry([LiteralOperationProfile.current()])
        transport = case.app.state.synthetic_executor.transport
        counter = 0
        def counted(*args):
            response = transport(*args)
            with (settings.data_dir / 'synthetic-memory-count.txt').open('a') as output:
                output.write('request\n')
            return response
        case.app.state.synthetic_executor.transport = counted
        def peer(gate):
            nonlocal counter
            counter += 1
            current = case.get('sessions/' + values[2]).json()
            turn = current['active_turn_id']
            owner = case.app.state.codex_turn_service.outbound_owner
            with case.app.state.database.transaction(immediate=False) as conn:
                state = owner.owned_states(conn, case.app.state.database.workspace_id())[0][turn]
                request = owner.prepared_request(state)
            gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
            text = canonical_bytes(LiteralCommand(version='codex-synthetic-literal-command-v1', text='Synthetic approved memory α')).decode()
            if counter > 1:
                approvals.operations = CodexOperationRegistry()
            frame = canonical_bytes({'version': 'codex-synthetic-operation-callback-v1', 'rpc_id': 'native_rpc_' + str(counter),
                'thread_id': 'synthetic-thread', 'turn_id': turn, 'item_id': 'native_item_' + str(counter),
                'method': 'command/requestApproval', 'request_text': text})
            identifier = worker.receive_operation(frame)
            (settings.data_dir / ('approval-' + str(counter) + '.json')).write_text(json.dumps({'id': identifier, 'turn_id': turn}))
            until = time.monotonic() + 25
            while time.monotonic() < until:
                response = case.get('turns/' + turn)
                assert response.status_code == 200
                control = next(a for a in response.json()['approval_controls'] if a['id'] == identifier)
                if control['decision'] == 'decline':
                    return
                if control['decision'] == 'approve_once' and (settings.data_dir / 'execute-release').exists():
                    result = worker.execute_operation(identifier)
                    assert result.text == 'Synthetic approved memory α'
                    assert result.host_actions == result.provider_requests == result.files_written == 0
                    (settings.data_dir / 'literal-operation-completed.json').write_text(json.dumps(result.model_dump()))
                    return
                time.sleep(0.05)
            raise RuntimeError('Private fixture decision wait exhausted; no operation replay')
        case.app.state.synthetic_executor.peer = peer
        fixture = {'session_id': values[2], 'turn_id': prepared['turn_id'], 'actor': case.actor_id,
            'workspace': case.app.state.database.workspace_id(), 'synthetic_bootstrap_calls': len(values[1].calls),
            'cookies': [{'name': c.name, 'value': c.value, 'domain': '127.0.0.1', 'path': '/'} for c in case.client.cookies.jar]}
        (settings.data_dir / 'private-fixture.json').write_text(json.dumps(fixture))
        return case.app
