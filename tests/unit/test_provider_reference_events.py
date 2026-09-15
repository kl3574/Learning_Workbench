"""Actual reference-generator semantics, not hosted model acceptance."""
import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from services.api.app.infrastructure.provider_sse import ProtocolDecoder


FIXTURES = Path(__file__).parents[1] / 'fixtures/provider_recipe_0_1_1'


def reference(name):
    manifest = json.loads((FIXTURES / 'manifest.json').read_text())
    entry = next(item for item in manifest['files'] if item['path'] == name + '.jsonl')
    raw = (FIXTURES / entry['path']).read_bytes()
    assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256']
    return [json.loads(line) for line in raw.splitlines()]


def decode(values, bytewise=False):
    # The SDK generated semantic events. This SSE envelope and fragmentation
    # are test inputs, not a claim that an actual HTTP service sent these bytes.
    raw = b''.join(('event: ' + value['type'] + '\ndata: '
        + json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n\n').encode()
        for value in values)

    async def run():
        async def chunks():
            if bytewise:
                for index in range(len(raw)):
                    yield raw[index:index + 1]
            else:
                yield raw
        return [event async for event in ProtocolDecoder('official_responses', 'deepseek-flash').stream(chunks())]
    return asyncio.run(run())


@pytest.mark.parametrize('bytewise', [False, True])
@pytest.mark.parametrize('name,outcome,reason,text', [
    ('complete', 'complete', None, '原创协议样例：42\n'),
    ('output-limit', 'incomplete', 'output_limit', '实际部分文字'),
    ('content-filter', 'incomplete', 'content_filter', '保留已收到文字'),
    ('whitespace', 'complete', None, ' \n'),
])
def test_official_generator_text_and_terminal_semantics(name, outcome, reason, text, bytewise):
    values = reference(name)
    events = decode(values, bytewise)
    assert ''.join(event.text for event in events if event.type == 'delta') == text
    assert events[-1].type == 'finished' and events[-1].outcome == outcome
    assert events[-1].reason == reason
    assert events[-1].usage.input_tokens == values[-1]['response']['usage']['input_tokens']
    assert events[-1].usage.output_tokens == values[-1]['response']['usage']['output_tokens']
    # A syntactically complete whitespace reply remains raw protocol output;
    # Tutor's separate nonblank answer check must not be bypassed by this test.
    assert sum(event.type in {'finished', 'error'} for event in events) == 1


@pytest.mark.parametrize('bytewise', [False, True])
def test_official_generator_reasoning_is_rejected_without_answer_adoption(bytewise):
    events = decode(reference('unexpected-reasoning'), bytewise)
    assert not any(event.type == 'delta' for event in events)
    assert events[-1].type == 'error' and events[-1].error_code == 'PROVIDER_PROTOCOL_ERROR'


@pytest.mark.parametrize('mutation', ['sequence', 'model', 'role', 'text', 'eof'])
def test_mutated_reference_cannot_manufacture_a_completed_result(mutation):
    values = reference('complete')
    if mutation == 'sequence':
        values[4]['sequence_number'] += 1
    elif mutation == 'model':
        values[-1]['response']['model'] = 'another-model'
    elif mutation == 'role':
        values[-1]['response']['output'][0]['role'] = 'user'
    elif mutation == 'text':
        values[-1]['response']['output'][0]['content'][0]['text'] += ' changed'
    else:
        values.pop()  # A closed HTTP body cannot replace the missing terminal.
    events = decode(values)
    assert events[-1].type == 'error'
    assert not any(event.type == 'finished' for event in events)
