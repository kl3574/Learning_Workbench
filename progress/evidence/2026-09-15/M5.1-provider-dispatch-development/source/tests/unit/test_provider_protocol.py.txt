import asyncio
from collections.abc import AsyncIterator
from services.api.app.infrastructure.provider_sse import checked_stream
import pytest
from packages.contracts.canonical import canonical_bytes, strict_json
from tests.provider_protocol_fixture import MODEL, chat_stream, responses_stream

def collect(data: bytes, adapter: str = 'compatible_chat'):
    async def chunks() -> AsyncIterator[bytes]:
        for byte in data:
            yield bytes([byte])
    async def run():
        return [event async for event in checked_stream(chunks(), adapter, 'test-byte-model')]
    return asyncio.run(run())


def test_chat_preserves_whitespace_and_unknown_usage_without_synthetic_eof_success() -> None:
    data = (b'data: {"id":"c1","model":"test-byte-model","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}\r\n\r\n'
            b'data: {"id":"c1","model":"test-byte-model","choices":[{"index":0,"delta":{"content":" \\n"},"finish_reason":null}]}\n\n')
    events = collect(data)
    assert [(e.channel, e.text) for e in events if e.type == 'delta'] == [('answer', ' \n')]
    terminal = events[-1]
    assert terminal.type == 'error' and terminal.error_code == 'PROVIDER_OUTCOME_UNKNOWN'
    assert terminal.output_state == 'partial' and terminal.usage.input_tokens is None




def collect_fixture(data: bytes, adapter: str):
    async def chunks():
        for offset in range(0, len(data), 7):
            yield data[offset:offset + 7]
    async def run():
        return [event async for event in checked_stream(chunks(), adapter, MODEL)]
    return asyncio.run(run())


@pytest.mark.parametrize('adapter', ['official_responses', 'compatible_chat'])
@pytest.mark.parametrize('refusal', [False, True])
def test_realistic_text_and_refusal_parts_finish_once_with_usage_after_text(adapter, refusal):
    data = (responses_stream if adapter == 'official_responses' else chat_stream)('中 \n', input_tokens=41, refusal=refusal)
    events = collect_fixture(data, adapter)
    assert ''.join(e.text for e in events if e.type == 'delta') == '中 \n'
    assert {e.channel for e in events if e.type == 'delta'} == {'refusal' if refusal else 'answer'}
    assert len([e for e in events if e.type in {'finished', 'error'}]) == 1
    assert events[-1].type == 'finished' and events[-1].outcome == ('refused' if refusal else 'complete')
    assert events[-1].usage.model_dump() == {'input_tokens': 41, 'output_tokens': 5}
    assert events[-1].output_state == 'complete'


@pytest.mark.parametrize('adapter', ['official_responses', 'compatible_chat'])
def test_output_limit_is_partial_not_normal_completion(adapter):
    data = (responses_stream(status='incomplete') if adapter == 'official_responses'
            else chat_stream(finish='length'))
    terminal = collect_fixture(data, adapter)[-1]
    assert terminal.type == 'finished' and terminal.outcome == 'incomplete'
    assert terminal.reason == 'output_limit' and terminal.output_state == 'partial'
    assert terminal.usage.input_tokens is None


@pytest.mark.parametrize('bad', ['multi_choice', 'wrong_id', 'tools', 'wrong_index', 'wrong_model'])
def test_chat_rejects_unqualified_identity_choice_or_tool_changes(bad):
    data = chat_stream()
    records = [strict_json(line[6:]) for line in data.splitlines() if line.startswith(b'data: {')]
    value = records[1]
    if bad == 'multi_choice':
        value['choices'].append(value['choices'][0])
    elif bad == 'wrong_id':
        value['id'] = 'another_response'
    elif bad == 'tools':
        value['choices'][0]['delta']['tool_calls'] = []
    elif bad == 'wrong_index':
        value['choices'][0]['index'] = 1
    else:
        value['model'] = 'another_model'
    data = b''.join(b'data: ' + canonical_bytes(r) + b'\n\n' for r in records) + b'data: [DONE]\n\n'
    terminal = collect_fixture(data, 'compatible_chat')[-1]
    assert terminal.type == 'error' and terminal.error_code == 'PROVIDER_PROTOCOL_ERROR'


def test_usage_is_cumulative_not_added_null_cannot_erase_and_rollback_fails_closed():
    prefix = chat_stream(input_tokens=10, done=False)
    repeated = {'id': 'chat_test_1', 'model': MODEL, 'choices': [],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12}}
    nulls = dict(repeated, usage={'prompt_tokens': None, 'completion_tokens': 2})
    suffix = b'data: ' + canonical_bytes(repeated) + b'\n\ndata: ' + canonical_bytes(nulls) + b'\n\ndata: [DONE]\n\n'
    events = collect_fixture(prefix + suffix, 'compatible_chat')
    assert len([e for e in events if e.type == 'usage']) == 1
    assert events[-1].usage.input_tokens == 10
    broken = dict(repeated, usage={'prompt_tokens': 9, 'completion_tokens': 2})
    events = collect_fixture(prefix + b'data: ' + canonical_bytes(broken) + b'\n\n', 'compatible_chat')
    assert events[-1].error_code == 'PROVIDER_USAGE_INCONSISTENT'
    assert events[-1].provider_outcome == 'completed' and events[-1].usage.input_tokens == 10


@pytest.mark.parametrize('bad', ['sequence', 'part_id', 'final_text', 'annotation', 'output_type'])
def test_responses_preserves_instance_part_and_final_content_integrity(bad):
    records = [strict_json(line[6:]) for line in responses_stream().splitlines() if line.startswith(b'data: ')]
    if bad == 'sequence':
        records[3]['sequence_number'] = 2
    elif bad == 'part_id':
        records[3]['item_id'] = 'another_message'
    elif bad == 'final_text':
        records[-1]['response']['output'][0]['content'][0]['text'] = 'different'
    elif bad == 'annotation':
        records[-1]['response']['output'][0]['content'][0]['annotations'] = [{'type': 'url_citation'}]
    else:
        records[1]['item']['type'] = 'web_search_call'
    data = b''.join(b'data: ' + canonical_bytes(r) + b'\n\n' for r in records)
    terminal = collect_fixture(data, 'official_responses')[-1]
    assert terminal.type == 'error' and terminal.error_code == 'PROVIDER_PROTOCOL_ERROR'


@pytest.mark.parametrize('payload', [b'data: {"x":1,"x":2}\n\n', b'data: \xff\n\n', b'data: [DONE]\n\n'])
def test_invalid_framing_json_or_early_done_cannot_create_success(payload):
    terminal = collect_fixture(payload, 'compatible_chat')[-1]
    assert terminal.type == 'error'
    assert terminal.output_state == 'none'


def test_conflicting_frame_already_received_with_terminal_is_rejected_before_commit():
    async def chunks():
        yield chat_stream() + b'data: {"id":"different","choices":[]}\n\n'
    async def run():
        return [event async for event in checked_stream(chunks(), 'compatible_chat', MODEL)]
    events = asyncio.run(run())
    assert events[-1].type == 'error' and events[-1].error_code == 'PROVIDER_PROTOCOL_ERROR'
    assert events[-1].provider_outcome == 'completed'
    assert len([event for event in events if event.type in {'finished', 'error'}]) == 1


@pytest.mark.parametrize('event_index', [1, 2, 6])
def test_responses_rejects_boolean_output_index(event_index):
    records = [strict_json(line[6:]) for line in responses_stream().splitlines() if line.startswith(b'data: ')]
    records[event_index]['output_index'] = False
    data = b''.join(b'data: ' + canonical_bytes(value) + b'\n\n' for value in records)
    terminal = collect_fixture(data, 'official_responses')[-1]
    assert terminal.type == 'error' and terminal.error_code == 'PROVIDER_PROTOCOL_ERROR'


def test_near_resource_limits_do_not_block_event_loop_heartbeat():
    import time
    base = {'id': 'chat_test_1', 'model': MODEL, 'choices': [{'index': 0,
        'delta': {'content': 'x' * 240000}, 'finish_reason': None}]}
    payload = ((b':' + b'c' * 240000 + b'\n\n') * 16
               + (b'data: ' + canonical_bytes(base) + b'\n\n') * 16
               + chat_stream(''))
    assert len(payload) < 8 * 1024 * 1024
    async def run():
        async def chunks():
            yield payload
        async def consume():
            return [event async for event in checked_stream(chunks(), 'compatible_chat', MODEL)]
        task = asyncio.create_task(consume())
        start = time.monotonic()
        await asyncio.sleep(0.01)
        delay = time.monotonic() - start
        events = await task
        assert ''.join(event.text for event in events if event.type == 'delta') == 'x' * 3840000
        assert events[-1].type == 'finished'
        print(f'provider_parser_heartbeat_seconds={delay:.6f}; payload_bytes={len(payload)}; output_bytes=3840000')
        assert delay < 0.2
    asyncio.run(run())


@pytest.mark.parametrize('bad', ['role_array', 'finish_array', 'negative_usage_with_text'])
def test_malformed_json_field_types_produce_one_safe_error_and_preserve_accepted_text(bad):
    value = {'id': 'chat_test_1', 'model': MODEL, 'choices': [
        {'index': 0, 'delta': {'content': 'accepted'}, 'finish_reason': None}]}
    if bad == 'role_array':
        value['choices'][0]['delta']['role'] = []
    elif bad == 'finish_array':
        value['choices'][0]['finish_reason'] = []
    else:
        value['usage'] = {'prompt_tokens': -1, 'completion_tokens': 0}
    events = collect_fixture(b'data: ' + canonical_bytes(value) + b'\n\n', 'compatible_chat')
    assert events[-1].type == 'error'
    if bad != 'role_array':
        assert ''.join(e.text for e in events if e.type == 'delta') == 'accepted'
        assert events[-1].output_state == 'partial'
