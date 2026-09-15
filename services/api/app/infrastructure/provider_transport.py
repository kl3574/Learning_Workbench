"""One pinned HTTP request; no SDK, retry, proxy, redirect or hidden request.

The caller must complete durable authorization before iterating this stream.
A fresh public httpcore pool uses one pinned backend; httpcore itself does not
read proxy environment variables. No network/filesystem work occurs on import
or construction. The dispatch owner enforces the total monotonic deadline.
"""
from collections.abc import AsyncGenerator
import ssl

import httpcore

from ..application.errors import ApiError
from ..provider_dto import ProviderConfigView
from .provider_network import NetworkGuard, PinnedNetworkBackend, Resolver, resolve_destination, validate_endpoint


class ProviderTransport:
    def __init__(self, *, resolver: Resolver | None = None, ssl_context: ssl.SSLContext | None = None):
        self.resolver, self.ssl_context = resolver, ssl_context

    async def stream(self, config: ProviderConfigView, body: bytes, secret: bytes, *,
                     guard: NetworkGuard | None = None) -> AsyncGenerator[bytes, None]:
        endpoint = validate_endpoint(config.base_url, config.endpoint_policy)
        if (not secret or any(value < 33 or value > 126 for value in secret)):
            raise ApiError(409, 'PROVIDER_SECRET_UNAVAILABLE', '提供商秘密不可用于当前请求。')
        destination = await resolve_destination(endpoint, config.endpoint_policy, self.resolver)
        if guard is not None:
            await guard()
        backend = PinnedNetworkBackend(destination, guard)
        async with httpcore.AsyncConnectionPool(ssl_context=self.ssl_context, proxy=None, retries=0,
                max_connections=1, max_keepalive_connections=0, http1=True, http2=False,
                network_backend=backend) as pool:
            try:
                async with pool.stream('POST', endpoint.url_for(config.adapter),
                        headers=[(b'Content-Type', b'application/json'), (b'Accept', b'text/event-stream'),
                                 (b'Authorization', b'Bearer ' + secret)], content=body,
                        extensions={'timeout': {'connect': 30.0, 'read': 180.0, 'write': 30.0, 'pool': 1.0}}) as response:
                    headers = {key.lower(): value for key, value in response.headers}
                    if (response.status != 200 or headers.get(b'content-type', b'').split(b';')[0].strip()
                            != b'text/event-stream' or headers.get(b'content-encoding', b'identity') != b'identity'):
                        raise ApiError(502, 'PROVIDER_TRANSPORT_ERROR', '提供商未返回可验证的文本流。')
                    async for chunk in response.aiter_stream():
                        yield chunk
            except httpcore.TimeoutException:
                raise ApiError(504, 'PROVIDER_TIMEOUT', '提供商请求超时。') from None
            except (httpcore.NetworkError, httpcore.ProtocolError):
                raise ApiError(502, 'PROVIDER_TRANSPORT_ERROR', '提供商连接或传输失败。') from None
