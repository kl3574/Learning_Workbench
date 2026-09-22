"""Explicit test-only app factory with an actual complete-byte loopback model.

Run only as ``uvicorn tests.authoring_native_fixture:create_test_app --factory``
with an isolated LEARNING_DATA_DIR. Production composition never imports this
module or discovers its proof from an environment variable. No credentials or
HTTP request bodies/headers are written to the safe runtime observation file.
"""

import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os

from fastapi import FastAPI

from services.api.app.infrastructure.config import Settings
from services.api.app.main import create_app
from services.api.app.application.provider_budget import RequestPreparer
from tests.provider_protocol_fixture import MODEL, complete_byte_count, local_provider, test_preparer


# Original synthetic worked-example JSON. No source claims or imported material.
PAYLOAD = {'version': 'worked-example-candidate-v1', 'kind': 'worked_example',
    'title': '原创合成双倍例题', 'body_markdown': '设 x=9，按本次声明复算 x*2=18。\n这份合成草稿未经数学、来源或教学审核。\n',
    'symbols': [{'name': 'x', 'tex': 'x', 'domain': 'real', 'dimension': 'number'}],
    'declared_source_refs': [], 'numeric_plan': {'version': 'finite-arithmetic-v1',
        'variables': [{'name': 'x', 'value': 9.0, 'unit': 'number'}],
        'assertions': [{'id': 'double_check', 'expression': 'x*2', 'expected': 18.0,
            'atol': 0.0, 'rtol': 0.0, 'unit': 'number'}], 'seed': None}}
ANSWER = json.dumps(PAYLOAD, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def create_test_app() -> FastAPI:
    """Construction is IO-free; servers and observation begin in lifespan."""
    settings = Settings.from_env()
    scenario = os.environ.get('AUTHORING_NATIVE_SCENARIO', 'no_proof')
    if scenario not in {'complete', 'no_proof'}:
        raise ValueError('Unknown explicit Authoring test scenario')
    preparer = RequestPreparer()
    application = create_app(settings, request_preparer=preparer)
    production_lifespan = application.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with local_provider(text=ANSWER) as provider:
            # The test server's actual allocated address is the only admitted
            # endpoint; construction and production registration remain empty.
            if scenario == 'complete':
                preparer.registry = test_preparer(provider.base_url).registry
            async with production_lifespan(app) as state:
                target = settings.data_dir / 'authoring-native-control.json'
                pending = target.with_suffix('.pending')
                stopped = asyncio.Event()

                def observe() -> None:
                    valid = []
                    invalid = 0
                    for body in provider.requests:
                        try:
                            complete_byte_count(body)
                        except (ValueError, TypeError, KeyError):
                            invalid += 1
                        else:
                            valid.append(hashlib.sha256(body).hexdigest())
                    value = {'version': 'authoring-native-fixture-v1', 'scenario': scenario,
                        'test_only': True, 'proof_registered': scenario == 'complete', 'adapter': 'compatible_chat', 'model': MODEL,
                        'base_url': provider.base_url, 'answer_markdown': ANSWER,
                        'connections': provider.connections, 'headers_received': provider.headers_received,
                        'received_request_count': len(provider.requests), 'validated_request_count': len(valid),
                        'invalid_request_count': invalid, 'request_body_sha256': valid}
                    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
                    descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
                    with os.fdopen(descriptor, 'wb') as stream:
                        stream.write(raw)
                    os.replace(pending, target)

                async def monitor() -> None:
                    # Only observe this test server; no request retry or product
                    # state mutation. Each observation is atomically replaced.
                    while not stopped.is_set():
                        try:
                            await asyncio.wait_for(stopped.wait(), 0.05)
                        except TimeoutError:
                            observe()

                observe()
                monitoring = asyncio.create_task(monitor())
                try:
                    yield state
                finally:
                    stopped.set()
                    await monitoring
                    observe()

    application.router.lifespan_context = lifespan
    return application
