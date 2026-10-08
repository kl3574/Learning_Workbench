"""Offline local frames are observations, never live transport or shutdown proof."""
from pathlib import Path


def test_local_interrupt_reply_and_terminal_are_separate_exact_observations():
    package = Path(__file__).parents[2] / 'services/api/app/infrastructure/codex_interrupt_protocol'
    assert (package / 'source-summary.json').is_file(), 'Interrupt RPC/event originals are not packaged'

    from services.api.app.infrastructure.codex_interrupt_protocol import (
        observe_interrupt, prepare_interrupt, read_interrupt_source,
    )

    source = read_interrupt_source()
    request = b'{"id":7,"method":"turn/interrupt","params":{"threadId":"thread-fixture","turnId":"turn-fixture"}}'
    exchange = prepare_interrupt(source, request)
    assert exchange.implemented is False
    assert exchange.production_qualification == 'unregistered'
    assert not exchange.control_reply_observed
    assert not exchange.terminal_notification_observed
    reply = b'{"id":7,"result":{}}'
    acknowledged = observe_interrupt(source, exchange, reply)
    assert acknowledged.accepted is True
    assert acknowledged.exchange.control_reply_observed
    assert not acknowledged.exchange.terminal_notification_observed
    terminal = b'{"method":"turn/completed","params":{"threadId":"thread-fixture","turn":{"id":"turn-fixture","items":[],"status":"interrupted"}}}'
    completed = observe_interrupt(source, acknowledged.exchange, terminal)
    assert completed.accepted is True
    assert completed.exchange.control_reply_observed
    assert completed.exchange.terminal_notification_observed
    assert completed.exchange.observations[0].frame.raw == reply
    assert completed.exchange.observations[1].frame.raw == terminal
    assert exchange.request.frame.raw == request
    assert not exchange.control_reply_observed



def test_original_exchange_detects_missing_observation_members():
    from services.api.app.infrastructure.codex_interrupt_protocol import (
        observe_interrupt, prepare_interrupt, read_interrupt_source, verify_interrupt_exchange,
    )
    import pytest

    source = read_interrupt_source()
    exchange = prepare_interrupt(source, b'{"id":7,"method":"turn/interrupt","params":{"threadId":"t","turnId":"u"}}')
    acknowledged = observe_interrupt(source, exchange, b'{"id":7,"result":{}}').exchange
    acknowledged.observations.clear()
    with pytest.raises(ValueError):
        verify_interrupt_exchange(source, acknowledged)


import json
import shutil
import subprocess

import pytest

from packages.contracts.canonical import sha256_bytes
from services.api.app.application.codex_interrupt_protocol_models import (
    MAX_FRAME_BYTES, InterruptExchange, InterruptProtocolSource, PrivateProtocolFrame,
)
from services.api.app.infrastructure import codex_interrupt_protocol as protocol
from services.api.app.infrastructure import codex_turn_protocol_catalog as selected9

REQUEST = b'{"id":7,"method":"turn/interrupt","params":{"threadId":"t","turnId":"u"}}'
REPLY = b'{"id":7,"result":{}}'
TERMINAL = b'{"method":"turn/completed","params":{"threadId":"t","turn":{"id":"u","items":[],"status":"interrupted"}}}'


def raw(body):
    return json.dumps(body, ensure_ascii=True, separators=(',', ':')).encode()


@pytest.fixture
def source():
    return protocol.read_interrupt_source()


@pytest.mark.parametrize('status', ['completed', 'interrupted', 'failed'])
@pytest.mark.parametrize('terminal_first', [False, True])
def test_ack_and_terminal_pair_in_either_order_without_shutdown_claim(source, status, terminal_first):
    body = json.loads(TERMINAL)
    body['params']['turn']['status'] = status
    terminal = raw(body)
    first, second = (terminal, REPLY) if terminal_first else (REPLY, terminal)
    original = protocol.prepare_interrupt(source, REQUEST)
    observed = protocol.observe_interrupt(source, original, first)
    assert observed.accepted
    assert observed.exchange.control_reply_observed is (not terminal_first)
    assert observed.exchange.terminal_notification_observed is terminal_first
    final = protocol.observe_interrupt(source, observed.exchange, second)
    assert final.accepted
    assert [m.frame.raw for m in final.exchange.observations] == [first, second]
    assert final.exchange.observation_count == 2
    assert final.exchange.implemented is False
    assert final.exchange.production_qualification == 'unregistered'
    assert 'process_stopped' not in final.exchange.model_dump()
    assert 'files_stable' not in final.exchange.model_dump()
    assert not original.observations


@pytest.mark.parametrize('request_id', ['rpc-fixture', 0, -(2**63), 2**63-1])
def test_request_ids_keep_exact_json_type_and_int64_range(source, request_id):
    request = json.loads(REQUEST)
    request['id'] = request_id
    exchange = protocol.prepare_interrupt(source, raw(request))
    reply = raw({'id': request_id, 'result': {}})
    assert protocol.observe_interrupt(source, exchange, reply).accepted


@pytest.mark.parametrize('bad_id', [True, 7.0, None, '', [], 2**63, -(2**63)-1])
def test_invalid_or_coerced_request_ids_are_not_prepared(source, bad_id):
    request = json.loads(REQUEST)
    request['id'] = bad_id
    with pytest.raises(ValueError):
        protocol.prepare_interrupt(source, raw(request))


@pytest.mark.parametrize('damage', ['trace', 'jsonrpc', 'method', 'missing_params', 'params_extra', 'snake', 'surrogate', 'float_id'])
def test_original_request_is_a_closed_shape_not_generic_jsonrpc_passthrough(source, damage):
    request = json.loads(REQUEST)
    if damage == 'trace':
        request['trace'] = None
    elif damage == 'jsonrpc':
        request['jsonrpc'] = '2.0'
    elif damage == 'method':
        request['method'] = 'turn/start'
    elif damage == 'missing_params':
        del request['params']
    elif damage == 'params_extra':
        request['params']['latest'] = True
    elif damage == 'snake':
        request['params'] = {'thread_id': 't', 'turn_id': 'u'}
    elif damage == 'surrogate':
        request['params']['turnId'] = '\ud800'
    else:
        request['id'] = 7.0
    with pytest.raises(ValueError):
        protocol.prepare_interrupt(source, raw(request))


@pytest.mark.parametrize('frame', [
    b'{"id":8,"result":{}}', b'{"id":"7","result":{}}',
    b'{"method":"turn/completed","params":{"threadId":"other","turn":{"id":"u","items":[],"status":"interrupted"}}}',
    b'{"method":"turn/completed","params":{"threadId":"t","turn":{"id":"other","items":[],"status":"interrupted"}}}',
])
def test_unpaired_id_thread_or_turn_retains_private_frame_and_original_exchange(source, frame):
    exchange = protocol.prepare_interrupt(source, REQUEST)
    observed = protocol.observe_interrupt(source, exchange, frame)
    assert observed.accepted is False
    assert observed.reason == 'unpaired'
    assert observed.frame.raw == frame
    assert observed.frame.sha256 == sha256_bytes(frame)
    assert observed.exchange == exchange
    assert not exchange.observations


@pytest.mark.parametrize('damage', ['result_extra', 'error_rpc', 'id_bool', 'id_float', 'reply_extra',
    'event_extra', 'params_extra', 'turn_extra', 'nonempty_items', 'error_object', 'in_progress',
    'items_view_unknown', 'items_view_null', 'timing_bool', 'timing_float', 'timing_overflow', 'missing_items', 'snake'])
def test_unsupported_nested_shapes_reject_without_ignoring_fields_or_previous_ack(source, damage):
    body = json.loads(REPLY if damage in {'result_extra', 'error_rpc', 'id_bool', 'id_float', 'reply_extra'} else TERMINAL)
    if damage == 'result_extra':
        body['result'] = {'stopped': True}
    elif damage == 'error_rpc':
        body = {'id': 7, 'error': {'code': -1, 'message': 'fixture-private-message'}}
    elif damage == 'id_bool':
        body['id'] = True
    elif damage == 'id_float':
        body['id'] = 7.0
    elif damage == 'reply_extra':
        body['unknown'] = None
    elif damage == 'event_extra':
        body['id'] = 7
    elif damage == 'params_extra':
        body['params']['extra'] = 1
    elif damage == 'turn_extra':
        body['params']['turn']['unexpected'] = 1
    elif damage == 'nonempty_items':
        body['params']['turn']['items'] = [{'type': 'agentMessage', 'id': 'item-fixture', 'text': 'fixture-output'}]
    elif damage == 'error_object':
        body['params']['turn']['error'] = {'message': 'fixture-error'}
    elif damage == 'in_progress':
        body['params']['turn']['status'] = 'inProgress'
    elif damage == 'items_view_unknown':
        body['params']['turn']['itemsView'] = 'guess'
    elif damage == 'items_view_null':
        body['params']['turn']['itemsView'] = None
    elif damage == 'timing_bool':
        body['params']['turn']['completedAt'] = True
    elif damage == 'timing_float':
        body['params']['turn']['durationMs'] = 1.0
    elif damage == 'timing_overflow':
        body['params']['turn']['startedAt'] = 2**63
    elif damage == 'missing_items':
        del body['params']['turn']['items']
    else:
        body['params']['thread_id'] = body['params'].pop('threadId')
    exchange = protocol.observe_interrupt(source, protocol.prepare_interrupt(source, REQUEST), REPLY).exchange
    snapshot = exchange.model_dump(by_alias=True)
    frame = raw(body)
    observed = protocol.observe_interrupt(source, exchange, frame)
    assert observed.accepted is False
    assert observed.reason == 'unsupported_shape'
    assert observed.frame.raw == frame
    assert observed.exchange.model_dump(by_alias=True) == snapshot
    assert exchange.model_dump(by_alias=True) == snapshot


@pytest.mark.parametrize('items_view', ['full', 'summary', 'notLoaded'])
def test_optional_terminal_fields_preserve_actual_values_and_raw_shape(source, items_view):
    body = json.loads(TERMINAL)
    body['params']['turn'].update(error=None, startedAt=-(2**63), completedAt=2**63-1, durationMs=None, itemsView=items_view)
    frame = raw(body)
    observed = protocol.observe_interrupt(source, protocol.prepare_interrupt(source, REQUEST), frame)
    assert observed.accepted
    turn = observed.exchange.observations[0].wire.params.turn
    assert turn.items_view == items_view
    assert turn.started_at == -(2**63)
    assert turn.completed_at == 2**63-1
    assert turn.duration_ms is None
    assert observed.frame.raw == frame
    assert not observed.exchange.control_reply_observed


@pytest.mark.parametrize('frame', [b'{"method":"turn/started","params":{}}', b'{"method":"unknown-fixture"}'])
def test_unknown_method_returns_safe_reason_and_private_original_only(source, frame):
    exchange = protocol.prepare_interrupt(source, REQUEST)
    observed = protocol.observe_interrupt(source, exchange, frame)
    assert observed.reason == 'unknown_method'
    assert observed.frame.raw == frame
    assert observed.exchange == exchange
    assert 'unknown-fixture' not in repr(observed)


@pytest.mark.parametrize('frame', [b'{', b'\xff', b'{"id":7,"id":8,"result":{}}',
    b'{"id":NaN,"result":{}}', b'{"id":Infinity,"result":{}}', b'['*6000+b'0'+b']'*6000],
    ids=['syntax', 'utf8', 'duplicate', 'nan', 'infinity', 'deep-parser-bound'])
def test_malformed_duplicate_or_deep_json_is_a_private_rejection(source, frame):
    exchange = protocol.prepare_interrupt(source, REQUEST)
    observed = protocol.observe_interrupt(source, exchange, frame)
    assert observed.accepted is False
    assert observed.reason == 'invalid_json'
    assert observed.frame.raw == frame
    assert observed.exchange == exchange


@pytest.mark.parametrize('frame', [b'[]', b'null', b'7', b'"fixture"'])
def test_non_object_json_is_not_a_protocol_message(source, frame):
    observed = protocol.observe_interrupt(source, protocol.prepare_interrupt(source, REQUEST), frame)
    assert observed.reason == 'unsupported_shape'
    assert observed.frame.raw == frame


@pytest.mark.parametrize('first', [REPLY, TERMINAL])
@pytest.mark.parametrize('changed_spacing', [False, True])
def test_duplicate_ack_or_terminal_is_not_appended_or_used_to_replace_original(source, first, changed_spacing):
    exchange = protocol.observe_interrupt(source, protocol.prepare_interrupt(source, REQUEST), first).exchange
    duplicate = b' '+first+b' ' if changed_spacing else first
    rejected = protocol.observe_interrupt(source, exchange, duplicate)
    assert rejected.reason == 'duplicate'
    assert rejected.frame.raw == duplicate
    assert rejected.exchange == exchange
    assert rejected.exchange.observations[0].frame.raw == first
    assert rejected.exchange.observation_count == 1


@pytest.mark.parametrize('value', [b'', b'x'*(MAX_FRAME_BYTES+1), 'not-bytes', None])
def test_frame_bound_does_not_truncate_or_admit_a_prefix(source, value):
    exchange = protocol.prepare_interrupt(source, REQUEST)
    with pytest.raises(ValueError):
        protocol.observe_interrupt(source, exchange, value)
    assert not exchange.observations


@pytest.mark.parametrize('damage', ['tail', 'all', 'order', 'count', 'count_bool', 'hash', 'raw', 'wire', 'implemented'])
def test_local_membership_or_captured_original_damage_fails_closed(source, damage):
    exchange = protocol.observe_interrupt(source, protocol.prepare_interrupt(source, REQUEST), REPLY).exchange
    exchange = protocol.observe_interrupt(source, exchange, TERMINAL).exchange
    if damage == 'tail':
        exchange.observations.pop()
    elif damage == 'all':
        exchange.observations.clear()
    elif damage == 'order':
        exchange.observations.reverse()
    elif damage == 'count':
        object.__setattr__(exchange, 'observation_count', 1)
    elif damage == 'count_bool':
        object.__setattr__(exchange, 'observation_count', True)
    elif damage == 'hash':
        object.__setattr__(exchange, 'observations_sha256', '0'*64)
    elif damage == 'raw':
        object.__setattr__(exchange.observations[0].frame, 'raw', b'{"id":8,"result":{}}')
    elif damage == 'wire':
        object.__setattr__(exchange.request.wire.params, 'turn_id', 'other')
    else:
        object.__setattr__(exchange, 'implemented', 0)
    with pytest.raises(ValueError):
        protocol.verify_interrupt_exchange(source, exchange)
    with pytest.raises(ValueError):
        protocol.observe_interrupt(source, exchange, REPLY)


@pytest.mark.parametrize('bad_false', [0, 0.0, True])
def test_source_and_exchange_unregistered_false_are_strict(source, bad_false):
    body = source.model_dump(by_alias=True)
    body['implemented'] = bad_false
    with pytest.raises(ValueError):
        InterruptProtocolSource.model_validate(body)
    body = protocol.prepare_interrupt(source, REQUEST).model_dump(by_alias=True)
    body['implemented'] = bad_false
    with pytest.raises(ValueError):
        InterruptExchange.model_validate(body)


@pytest.fixture
def source_copy(tmp_path, monkeypatch):
    destination = tmp_path/'source-package'
    shutil.copytree(protocol.PACKAGE_DIRECTORY, destination)
    monkeypatch.setattr(protocol, 'PACKAGE_DIRECTORY', destination)
    return destination


@pytest.mark.parametrize('damage', ['tail', 'all', 'order', 'duplicate', 'extra', 'profile', 'hash', 'path', 'private_argv'])
def test_source_summary_whole_membership_and_reviewed_projection_are_checked_without_repair(source_copy, damage):
    path = source_copy/'source-summary.json'
    body = json.loads(path.read_bytes())
    if damage == 'tail':
        body['selected_files'].pop()
    elif damage == 'all':
        body['selected_files'] = []
    elif damage == 'order':
        body['selected_files'].reverse()
    elif damage == 'duplicate':
        body['selected_files'][1] = body['selected_files'][0]
    elif damage == 'extra':
        body['available'] = True
    elif damage == 'profile':
        body['export_profile'] = 'experimental'
    elif damage == 'hash':
        body['selected_files'][0]['sha256'] = '0'*64
    elif damage == 'path':
        body['selected_files'][0]['path'] = '../outside.json'
    else:
        body['argv'] = ['not-a-source-fact']
    path.write_bytes(raw(body))
    original = path.read_bytes()
    with pytest.raises(ValueError):
        protocol.read_interrupt_source()
    assert path.read_bytes() == original


@pytest.mark.parametrize('name', ['RequestId.json', 'JSONRPCRequest.json', 'JSONRPCResponse.json', 'JSONRPCNotification.json',
    'ClientRequest.json', 'ServerNotification.json', 'v2/TurnInterruptResponse.json', 'v2/TurnCompletedNotification.json'])
def test_every_additional_original_is_required_and_never_rebuilt(source_copy, name):
    path = source_copy/name
    path.unlink()
    with pytest.raises(FileNotFoundError):
        protocol.read_interrupt_source()
    assert not path.exists()


@pytest.mark.parametrize('name', ['ClientRequest.json', 'ServerNotification.json', 'v2/TurnCompletedNotification.json'])
def test_changed_original_bytes_are_not_a_new_compatible_schema(source_copy, name):
    path = source_copy/name
    path.write_bytes(path.read_bytes()+b'\n')
    original = path.read_bytes()
    with pytest.raises(ValueError):
        protocol.read_interrupt_source()
    assert path.read_bytes() == original


@pytest.mark.parametrize('damage', ['schema_raw', 'tail', 'projection', 'source_summary', 'selected9', 'implemented'])
def test_source_reverification_checks_nested_catalogs_and_forced_mutation(source, damage):
    if damage == 'schema_raw':
        object.__setattr__(source.schemas[0], 'raw_utf8', '{}')
    elif damage == 'tail':
        source.schemas.pop()
    elif damage == 'projection':
        object.__setattr__(source, 'source_summary_utf8', '{}')
    elif damage == 'source_summary':
        source.source_summary.selected_files.pop()
    elif damage == 'selected9':
        source.selected9.schemas.pop()
    else:
        object.__setattr__(source, 'implemented', 0)
    with pytest.raises(ValueError):
        protocol.verify_interrupt_source(source)
    with pytest.raises(ValueError):
        protocol.prepare_interrupt(source, REQUEST)


def test_existing_selected9_originals_remain_required_without_repair(tmp_path, monkeypatch):
    destination = tmp_path/'selected9'
    shutil.copytree(selected9.PACKAGE_DIRECTORY, destination)
    monkeypatch.setattr(selected9, 'PACKAGE_DIRECTORY', destination)
    path = destination/'v2/TurnInterruptParams.json'
    path.unlink()
    with pytest.raises(FileNotFoundError):
        protocol.read_interrupt_source()
    assert not path.exists()


def test_exact_private_frame_hash_and_repr_do_not_turn_bytes_into_public_details():
    with pytest.raises(ValueError):
        PrivateProtocolFrame(raw=b'fixture-private-bytes', sha256='0'*64)
    frame = PrivateProtocolFrame(raw=b'fixture-private-bytes', sha256=sha256_bytes(b'fixture-private-bytes'))
    assert 'fixture-private-bytes' not in repr(frame)
