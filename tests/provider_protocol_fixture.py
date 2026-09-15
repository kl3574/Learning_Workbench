"""Test-only artificial byte-token protocol and real loopback HTTP server.

The model is defined here, not an OpenAI tokenizer or production capability:
its complete input count is exactly the UTF-8 bytes of the canonical HTTP JSON
body (all fields and formatting included). The server and local proof use that
same public rule. Output tokens are UTF-8 bytes of the emitted text; fixtures
must honor max_output_tokens/max_completion_tokens unless testing a violation.
"""
import asyncio
import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from packages.contracts.canonical import canonical_bytes, strict_json
from services.api.app.application.provider_budget import InputProof, ProofRegistry, RequestPreparer
from services.api.app.application.consents import ConsentsService
from services.api.app.application.providers import ProviderService
from services.api.app.infrastructure.provider_secret_store import FileSecretStore
from services.api.app.provider_dto import (
    ConsentCreate, ConsentPreviewWrite, OutboundBudget, ProviderConfigWrite, ProviderSecretWrite,
)
from tests.provider_fixture import provider_source

MODEL = 'test-only-complete-byte-model-v1'


def complete_byte_count(body: bytes) -> int:
    value = strict_json(body)
    responses = 'input' in value
    allowed = ({'model', 'stream', 'input', 'max_output_tokens', 'truncation', 'store', 'reasoning'} if responses
               else {'model', 'stream', 'messages', 'max_completion_tokens', 'n', 'stream_options'})
    if set(value) != allowed or value['model'] != MODEL or value['stream'] is not True or canonical_bytes(value) != body:
        raise ValueError('Outside the complete artificial protocol.')
    if responses and (value['store'] is not False or value['truncation'] != 'disabled'
                      or value['reasoning'] != {'effort': 'none'}):
        raise ValueError('Automatic truncation or storage is outside this profile.')
    if not responses and (value['n'] != 1 or value['stream_options'] != {'include_usage': True}):
        raise ValueError('Only one choice and explicit usage are supported.')
    for message in value['input' if responses else 'messages']:
        if (set(message) != {'role', 'content'} or message['role'] not in {'system', 'user', 'assistant'}
                or not isinstance(message['content'], str)):
            raise ValueError('Only the complete frozen text message shape is supported.')
    return len(body)


def test_preparer(base_url: str, *, upper_bound: bool = False) -> RequestPreparer:
    evidence = (__doc__ + '\nBoth adapters support a 200000-byte shared context, 190000 input and 10000 output. '
                'Version 2 includes explicit nonthinking Responses and rejects every field outside the exact allowlist; changing the rule invalidates this proof.').encode()
    return RequestPreparer(ProofRegistry(InputProof(model=MODEL, adapter=adapter,
        base_url=base_url, endpoint_policy='explicit_loopback',
        model_versions=(MODEL,), validity_evidence=b'Test-only literal immutable byte model; no vendor alias. Only this exact endpoint and v2 request grammar are covered. A rule or endpoint change requires a new registration; no time expiry is claimed or needed for this artificial immutable definition.',
        checker_version='test-complete-byte-counter-v2', kind='local_upper_bound' if upper_bound else 'local_exact',
        max_input_tokens=190000, max_output_tokens=10000, shared_context_tokens=200000,
        evidence=evidence, check=(lambda body: complete_byte_count(body) + 10) if upper_bound else complete_byte_count)
        for adapter in ('official_responses', 'compatible_chat')))

test_preparer.__test__ = False


def chat_stream(text: str = 'ok', *, input_tokens: int | None = None, finish: str = 'stop',
                refusal: bool = False, done: bool = True) -> bytes:
    base = {'id': 'chat_test_1', 'model': MODEL, 'object': 'chat.completion.chunk'}
    chunks = [dict(base, choices=[{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]),
              dict(base, choices=[{'index': 0, 'delta': {'refusal' if refusal else 'content': text}, 'finish_reason': None}]),
              dict(base, choices=[{'index': 0, 'delta': {}, 'finish_reason': finish}])]
    if input_tokens is not None:
        chunks.append(dict(base, choices=[], usage={'prompt_tokens': input_tokens,
            'completion_tokens': len(text.encode()), 'total_tokens': input_tokens + len(text.encode())}))
    return b''.join(b'data: ' + canonical_bytes(value) + b'\n\n' for value in chunks) + (b'data: [DONE]\n\n' if done else b'')


def responses_stream(text: str = 'ok', *, input_tokens: int | None = None, refusal: bool = False,
                     status: str = 'completed') -> bytes:
    channel = 'refusal' if refusal else 'output_text'
    field_name = 'refusal' if refusal else 'text'
    part = {'type': channel, field_name: text}
    if not refusal:
        part['annotations'] = []
    item = {'id': 'message_test_1', 'type': 'message', 'role': 'assistant', 'content': [part]}
    response = {'id': 'response_test_1', 'model': MODEL, 'status': 'in_progress', 'output': []}
    binding = {'item_id': item['id'], 'output_index': 0, 'content_index': 0}
    events = [dict(type='response.created', response=response),
        dict(type='response.output_item.added', output_index=0, item=dict(item, content=[])),
        dict(type='response.content_part.added', **binding, part=dict(part, **{field_name: ''})),
        dict(type='response.' + channel + '.delta', **binding, delta=text),
        dict(type='response.' + channel + '.done', **binding, **{field_name: text}),
        dict(type='response.content_part.done', **binding, part=part),
        dict(type='response.output_item.done', output_index=0, item=item)]
    final = dict(response, status=status, output=[item], usage=None if input_tokens is None else {
        'input_tokens': input_tokens, 'output_tokens': len(text.encode()), 'total_tokens': input_tokens + len(text.encode())})
    if status == 'incomplete':
        final['incomplete_details'] = {'reason': 'max_output_tokens'}
    events.append(dict(type='response.' + status, response=final))
    return b''.join(b'event: ' + value['type'].encode() + b'\ndata: ' + canonical_bytes(dict(value, sequence_number=i))
                    + b'\n\n' for i, value in enumerate(events))


@dataclass
class LocalProvider:
    base_url: str
    requests: list[bytes] = field(default_factory=list, repr=False)
    request_seen: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    release: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    connections: int = 0
    headers_received: int = 0


@asynccontextmanager
async def local_provider(*, adapter: str = 'compatible_chat', text: str = 'ok', status: int = 200,
                         hold: bool = False, payload: bytes | None = None,
                         tls: ssl.SSLContext | None = None, host: str = '127.0.0.1',
                         stall_after: int | None = None) -> AsyncIterator[LocalProvider]:
    local = LocalProvider('')
    tasks: set[asyncio.Task] = set()
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        task = asyncio.current_task()
        tasks.add(task)
        local.connections += 1
        try:
            headers = await reader.readuntil(b'\r\n\r\n')
            local.headers_received += 1
            length = next(int(line.split(b':', 1)[1]) for line in headers.split(b'\r\n')
                          if line.lower().startswith(b'content-length:'))
            body = await reader.readexactly(length)
            local.requests.append(body)
            local.request_seen.set()
            complete_byte_count(body)
            if hold:
                await local.release.wait()
            result = payload if payload is not None else (
                chat_stream(text, input_tokens=len(body)) if adapter == 'compatible_chat'
                else responses_stream(text, input_tokens=len(body)))
            writer.write(f'HTTP/1.1 {status} Fixture\r\nContent-Type: text/event-stream\r\n'.encode()
                         + b'Location: http://127.0.0.1:1/redirected\r\n'
                         + f'Content-Length: {len(result)}\r\nConnection: close\r\n\r\n'.encode()
                         + (result if stall_after is None else result[:stall_after]))
            await writer.drain()
            if stall_after is not None:
                await local.release.wait()
                writer.write(result[stall_after:])
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            tasks.discard(task)
    server = await asyncio.start_server(handle, '127.0.0.1', 0, ssl=tls)
    local.base_url = f'{"https" if tls else "http"}://{host}:{server.sockets[0].getsockname()[1]}/v1'
    try:
        yield local
    finally:
        local.release.set()
        server.close()
        await server.wait_closed()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def authorized_source(tmp_path: Path, base_url: str, *, adapter: str = 'compatible_chat',
                      timeout: int = 10, max_output: int = 100):
    db, identity, source, registry, job_id = provider_source(tmp_path)
    secrets = FileSecretStore(tmp_path / 'isolated-test-secrets')
    secrets.initialize()
    preparer = test_preparer(base_url)
    providers = ProviderService(db, secrets, preparer)
    config = providers.save_config(identity, 'provider_test', ProviderConfigWrite(expected_revision=0,
        adapter=adapter, base_url=base_url, model=MODEL, embedding_model=None,
        endpoint_policy='explicit_loopback', pricing=None), 'test-config')
    saved = providers.save_secret(identity, config.id, ProviderSecretWrite(expected_revision=1,
        secret='synthetic-local-protocol-key'), 'test-secret')
    consents = ConsentsService(db, secrets, registry, preparer)
    proposal = consents.preview(identity, ConsentPreviewWrite(job_id=job_id, expected_job_revision=1,
        provider_id=config.id, expected_provider_revision=saved.revision,
        expires_at=(datetime.now(UTC) + timedelta(minutes=5)).isoformat().replace('+00:00', 'Z'),
        budget=OutboundBudget(max_input_tokens=20000, max_output_tokens=max_output, max_provider_calls=1,
            max_search_calls=0, max_tool_calls=0, timeout_seconds=timeout, max_cost_usd=None)), 'test-preview')
    grant = consents.grant(identity, ConsentCreate(proposal_id=proposal.id,
        proposal_sha256=proposal.proposal_sha256), 'test-grant')
    lease = source.claim(identity, job_id)
    return db, identity, source, registry, job_id, secrets, preparer, consents, grant, lease
