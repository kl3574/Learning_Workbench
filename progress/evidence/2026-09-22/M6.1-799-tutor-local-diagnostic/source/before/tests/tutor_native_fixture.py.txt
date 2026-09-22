"""Explicit test-only app factory with an actual complete-byte loopback model.

Run only as ``uvicorn tests.tutor_native_fixture:create_test_app --factory``
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


ANSWER = '这是原创合成协议返回的完整助教回答。\n它只用于验证持久化与浏览器恢复，不表示数学质量已验收。\n'


def create_test_app() -> FastAPI:
    """Construction is IO-free; servers and observation begin in lifespan."""
    settings = Settings.from_env()
    scenario = os.environ.get('TUTOR_NATIVE_SCENARIO', 'complete')
    if scenario not in {'complete', 'hold'}:
        raise ValueError('Unknown explicit Tutor test scenario')
    preparer = RequestPreparer()
    application = create_app(settings, request_preparer=preparer)
    production_lifespan = application.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with local_provider(text=ANSWER, hold=scenario == 'hold') as provider:
            # The test server's actual allocated address is the only admitted
            # endpoint; construction and production registration remain empty.
            preparer.registry = test_preparer(provider.base_url).registry
            async with production_lifespan(app) as state:
                target = settings.data_dir / 'tutor-native-control.json'
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
                    value = {'version': 'tutor-native-fixture-v1', 'scenario': scenario,
                        'test_only': True, 'adapter': 'compatible_chat', 'model': MODEL,
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
