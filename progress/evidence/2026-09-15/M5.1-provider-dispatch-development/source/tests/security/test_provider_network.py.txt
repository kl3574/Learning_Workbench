"""Provider destination and real local transport boundaries; never paid endpoints."""

import asyncio
import socket

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.provider_network import resolve_destination, validate_endpoint


def test_public_policy_rejects_cleartext_before_any_dns_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_dns(*args: object, **kwargs: object) -> object:
        pytest.fail('Saving a provider destination must not resolve DNS.')

    monkeypatch.setattr(socket, 'getaddrinfo', forbidden_dns)
    with pytest.raises(ApiError) as error:
        validate_endpoint('http://provider.example/v1', 'public_https')
    assert error.value.code == 'CAPABILITY_UNSUPPORTED'


def test_mixed_public_and_private_dns_answer_is_rejected_without_selecting_a_public_fallback() -> None:
    calls: list[tuple[str, int]] = []

    async def resolver(host: str, port: int) -> tuple[str, ...]:
        calls.append((host, port))
        return ('93.184.216.34', '127.0.0.1')

    endpoint = validate_endpoint('https://provider.example/v1', 'public_https')
    with pytest.raises(ApiError) as error:
        asyncio.run(resolve_destination(endpoint, 'public_https', resolver))
    assert error.value.code == 'CAPABILITY_UNSUPPORTED'
    assert calls == [('provider.example', 443)]


def test_pinned_backend_uses_one_selected_address_and_checks_actual_peer() -> None:
    from services.api.app.infrastructure.provider_network import PinnedDestination, PinnedNetworkBackend

    async def run() -> None:
        connections = []
        async def accepted(reader, writer):
            connections.append(writer.get_extra_info('peername'))
            writer.close()
            await writer.wait_closed()
        server = await asyncio.start_server(accepted, '127.0.0.1', 0)
        try:
            port = server.sockets[0].getsockname()[1]
            endpoint = validate_endpoint(f'http://localhost:{port}/v1', 'explicit_loopback')
            backend = PinnedNetworkBackend(PinnedDestination(endpoint, '127.0.0.1'))
            stream = await backend.connect_tcp('localhost', port, timeout=1)
            assert stream.get_extra_info('server_addr')[0] == '127.0.0.1'
            await stream.aclose()
            with pytest.raises(Exception, match='single connection'):
                await backend.connect_tcp('localhost', port, timeout=1)
            assert len(connections) == 1
        finally:
            server.close()
            await server.wait_closed()
    asyncio.run(run())


@pytest.mark.parametrize('url,policy', [
    ('https://user:password@provider.example/v1', 'public_https'),
    ('https://provider.example/v1?api_key=x', 'public_https'),
    ('https://provider.example/v1#fragment', 'public_https'),
    ('https://127.0.0.1/v1', 'public_https'),
    ('https://10.0.0.1/v1', 'public_https'),
    ('https://[::ffff:127.0.0.1]/v1', 'public_https'),
    ('http://192.168.1.2:8000/v1', 'explicit_loopback'),
    ('http://localhost.example:8000/v1', 'explicit_loopback'),
    ('http://127.0.0.2:8000/v1', 'explicit_loopback'),
    ('http://localhost:8000/v1/%2e%2e/admin', 'explicit_loopback'),
    ('http://localhost:8000/v1/%252e%252e/admin', 'explicit_loopback'),
    ('http://localhost:8000/v1/%0aHeader', 'explicit_loopback'),
])
def test_invalid_endpoint_grammar_or_nonpublic_address_is_locally_rejected(url, policy):
    with pytest.raises(ApiError):
        validate_endpoint(url, policy)


def test_loopback_dns_rebinding_is_rejected():
    async def resolver(host, port):
        return ('127.0.0.1', '192.168.1.1')
    with pytest.raises(ApiError):
        asyncio.run(resolve_destination(validate_endpoint('http://localhost:8080/v1', 'explicit_loopback'),
                                        'explicit_loopback', resolver))


def test_real_redirect_does_not_follow_or_retry_and_frozen_bytes_are_sent(tmp_path, monkeypatch):
    from services.api.app.infrastructure.provider_repository import ProviderRepository
    from services.api.app.infrastructure.consent_repository import ConsentRepository
    from services.api.app.infrastructure.provider_transport import ProviderTransport
    from tests.provider_protocol_fixture import authorized_source, local_provider
    # Synthetic poison proxies: no existing environment credential is read.
    monkeypatch.setenv('HTTP_PROXY', 'http://127.0.0.1:1')
    monkeypatch.setenv('HTTPS_PROXY', 'http://127.0.0.1:1')
    monkeypatch.setenv('ALL_PROXY', 'http://127.0.0.1:1')
    async def run():
        async with local_provider(status=307) as server:
            db, identity, _, _, _, _, _, _, grant, _ = authorized_source(tmp_path, server.base_url)
            with db.transaction() as conn:
                summary, _, body = ConsentRepository(conn, identity.workspace_id).dispatch_material(grant.id)
                config = ProviderRepository(conn, identity.workspace_id).config(summary.provider_id)
            with pytest.raises(ApiError) as error:
                async for _ in ProviderTransport().stream(config, body, b'synthetic-only'):
                    pass
            assert error.value.code == 'PROVIDER_TRANSPORT_ERROR'
            assert server.requests == [body]
            assert server.connections == 1
    asyncio.run(run())


@pytest.mark.parametrize('trusted,correct_name', [(True, True), (True, False), (False, True)])
def test_real_tls_requires_trusted_chain_and_original_hostname(tmp_path, trusted, correct_name):
    import ssl
    import subprocess
    from services.api.app.infrastructure.provider_repository import ProviderRepository
    from services.api.app.infrastructure.consent_repository import ConsentRepository
    from services.api.app.infrastructure.provider_transport import ProviderTransport
    from tests.provider_protocol_fixture import authorized_source, local_provider
    key, certificate = tmp_path / 'generated-test-key.pem', tmp_path / 'generated-test-cert.pem'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
        '-keyout', str(key), '-out', str(certificate)], check=True, capture_output=True, timeout=10)
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certificate, key)
    client_context = ssl.create_default_context(cafile=str(certificate) if trusted else None)
    async def resolver(host, port):
        return ('127.0.0.1',)
    async def run():
        async with local_provider(tls=server_context, host='localhost' if correct_name else '127.0.0.1') as server:
            db, identity, _, _, _, _, _, _, grant, _ = authorized_source(tmp_path, server.base_url)
            with db.transaction() as conn:
                summary, _, body = ConsentRepository(conn, identity.workspace_id).dispatch_material(grant.id)
                config = ProviderRepository(conn, identity.workspace_id).config(summary.provider_id)
            transport = ProviderTransport(resolver=resolver, ssl_context=client_context)
            if trusted and correct_name:
                assert b'[DONE]' in b''.join([chunk async for chunk in transport.stream(config, body, b'synthetic-only')])
                assert server.requests == [body]
            else:
                with pytest.raises(ApiError) as error:
                    async for _ in transport.stream(config, body, b'synthetic-only'):
                        pass
                assert error.value.code == 'PROVIDER_TRANSPORT_ERROR'
                assert server.requests == []
    asyncio.run(run())
