"""Validated provider destinations and pinned, single-connection networking."""

from dataclasses import dataclass
from collections.abc import Awaitable, Callable
import asyncio
import ipaddress
import re
import socket
import ssl
from typing import Any, Literal
import httpcore
from urllib.parse import unquote, urlsplit

from ..application.errors import ApiError


@dataclass(frozen=True)
class ProviderEndpoint:
    scheme: str
    host: str
    port: int
    base_path: str

    def url_for(self, adapter: Literal['official_responses', 'compatible_chat']) -> str:
        host = f'[{self.host}]' if ':' in self.host else self.host
        suffix = '/responses' if adapter == 'official_responses' else '/chat/completions'
        return f'{self.scheme}://{host}:{self.port}{self.base_path}{suffix}'


@dataclass(frozen=True)
class PinnedDestination:
    endpoint: ProviderEndpoint
    address: str


Resolver = Callable[[str, int], Awaitable[tuple[str, ...]]]
NetworkGuard = Callable[[], Awaitable[None]]


async def resolve_destination(endpoint: ProviderEndpoint, policy: Literal['public_https', 'explicit_loopback'],
                              resolver: Resolver | None = None) -> PinnedDestination:
    # Resolution is a dispatch operation, never a configuration/save operation.
    async def system_resolver(host: str, port: int) -> tuple[str, ...]:
        records = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
        return tuple(dict.fromkeys(str(record[4][0]) for record in records))

    try:
        addresses = await (resolver or system_resolver)(endpoint.host, endpoint.port)
    except (OSError, ValueError):
        raise endpoint_error() from None
    if not addresses or any(
        not is_public_address(address) if policy == 'public_https'
        else address not in {'127.0.0.1', '::1'}
        for address in addresses
    ):
        raise endpoint_error()
    return PinnedDestination(endpoint, str(ipaddress.ip_address(addresses[0])))


def endpoint_error() -> ApiError:
    return ApiError(422, 'CAPABILITY_UNSUPPORTED', '提供商地址不符合所选目的地策略。')


def is_public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    if not address.is_global or address.is_multicast or address.is_reserved:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return is_public_address(str(address.ipv4_mapped))
        if address.sixtofour is not None:
            return is_public_address(str(address.sixtofour))
        if address.teredo is not None:
            return all(is_public_address(str(item)) for item in address.teredo)
    return True


def validate_endpoint(base_url: str, policy: Literal['public_https', 'explicit_loopback']) -> ProviderEndpoint:
    if not isinstance(base_url, str) or not base_url or len(base_url) > 8192:
        raise endpoint_error()
    if any(ord(char) <= 32 or ord(char) == 127 for char in base_url) or any(c in base_url for c in '? #\\'):
        raise endpoint_error()
    try:
        parsed = urlsplit(base_url)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        raise endpoint_error() from None
    if (policy not in {'public_https', 'explicit_loopback'} or parsed.scheme not in {'http', 'https'}
            or host is None or parsed.username is not None or parsed.password is not None):
        raise endpoint_error()
    if policy == 'public_https' and parsed.scheme != 'https':
        raise endpoint_error()
    if '%' in host or host.endswith('.'):
        raise endpoint_error()
    try:
        host = host.encode('idna').decode('ascii').lower()
    except UnicodeError:
        raise endpoint_error() from None
    port = port if port is not None else (443 if parsed.scheme == 'https' else 80)
    if not 1 <= port <= 65535:
        raise endpoint_error()
    if policy == 'explicit_loopback':
        if host not in {'localhost', '127.0.0.1', '::1'}:
            raise endpoint_error()
    else:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if (host == 'localhost' or host.endswith('.localhost')
                    or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host)
                    or any(not label or len(label) > 63 or label.startswith('-') or label.endswith('-')
                           for label in host.split('.'))):
                raise endpoint_error()
        else:
            if not is_public_address(str(address)):
                raise endpoint_error()
    path = parsed.path
    if (not path.isascii() or re.search(r'%(?![0-9A-Fa-f]{2})', path)
            or any(ord(char) <= 32 or ord(char) == 127 for char in unquote(path))):
        raise endpoint_error()
    decoded = unquote(path)
    if ('\\' in decoded or '//' in decoded or any(part in {'.', '..'} for part in decoded.split('/'))
            or unquote(decoded) != decoded):
        raise endpoint_error()
    return ProviderEndpoint(parsed.scheme, host, port, path.rstrip('/'))


# httpcore's public network seam retains HTTP Host/TLS SNI while the socket uses
# exactly the already-admitted address. No DNS lookup happens in connect_tcp.
class PinnedNetworkStream(httpcore.AsyncNetworkStream):
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 destination: PinnedDestination, guard: NetworkGuard | None = None):
        self.reader, self.writer, self.destination = reader, writer, destination
        self.guard = guard

    def verify_peer(self) -> None:
        peer = self.writer.get_extra_info('peername')
        if (not isinstance(peer, tuple) or len(peer) < 2
                or ipaddress.ip_address(peer[0]) != ipaddress.ip_address(self.destination.address)
                or peer[1] != self.destination.endpoint.port):
            self.writer.close()
            raise httpcore.ConnectError('Pinned provider peer mismatch.')

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        try:
            return await asyncio.wait_for(self.reader.read(max_bytes), timeout)
        except TimeoutError:
            raise httpcore.ReadTimeout('Provider read timed out.') from None
        except OSError:
            raise httpcore.ReadError('Provider read failed.') from None

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        if self.guard is not None:
            await self.guard()
        try:
            self.writer.write(buffer)
            await asyncio.wait_for(self.writer.drain(), timeout)
        except TimeoutError:
            raise httpcore.WriteTimeout('Provider write timed out.') from None
        except OSError:
            raise httpcore.WriteError('Provider write failed.') from None

    async def aclose(self) -> None:
        self.writer.close()
        try:
            await asyncio.wait_for(self.writer.wait_closed(), 1)
        except (OSError, TimeoutError):
            pass

    async def start_tls(self, ssl_context: ssl.SSLContext, server_hostname: str | None = None,
                        timeout: float | None = None) -> httpcore.AsyncNetworkStream:
        if (server_hostname != self.destination.endpoint.host or not ssl_context.check_hostname
                or ssl_context.verify_mode != ssl.CERT_REQUIRED):
            raise httpcore.ConnectError('Provider TLS verification is required.')
        if self.guard is not None:
            await self.guard()
        try:
            await asyncio.wait_for(self.writer.start_tls(ssl_context, server_hostname=server_hostname), timeout)
            self.verify_peer()
            return self
        except TimeoutError:
            await self.aclose()
            raise httpcore.ConnectTimeout('Provider TLS timed out.') from None
        except (OSError, ValueError):
            await self.aclose()
            raise httpcore.ConnectError('Provider TLS verification failed.') from None

    def get_extra_info(self, info: str) -> Any:
        return self.writer.get_extra_info({'server_addr': 'peername', 'client_addr': 'sockname',
            'ssl_object': 'ssl_object', 'socket': 'socket'}.get(info, info))


class PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, destination: PinnedDestination, guard: NetworkGuard | None = None):
        self.destination, self.attempted = destination, False
        self.guard = guard

    async def connect_tcp(self, host: str, port: int, timeout: float | None = None,
                          local_address: str | None = None, socket_options: Any = None
                          ) -> httpcore.AsyncNetworkStream:
        if self.attempted:
            raise httpcore.ConnectError('Provider permits a single connection attempt.')
        self.attempted = True
        if (host != self.destination.endpoint.host or port != self.destination.endpoint.port
                or local_address is not None or socket_options):
            raise httpcore.ConnectError('Provider destination mismatch.')
        if self.guard is not None:
            await self.guard()
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(self.destination.address, port), timeout)
            stream = PinnedNetworkStream(reader, writer, self.destination, self.guard)
            stream.verify_peer()
            return stream
        except TimeoutError:
            raise httpcore.ConnectTimeout('Provider connection timed out.') from None
        except OSError:
            raise httpcore.ConnectError('Provider connection failed.') from None

    async def connect_unix_socket(self, path: str, timeout: float | None = None,
                                 socket_options: Any = None) -> httpcore.AsyncNetworkStream:
        raise httpcore.ConnectError('Provider Unix sockets are not supported.')

    async def sleep(self, seconds: float) -> None:
        raise httpcore.ConnectError('Provider automatic retries are forbidden.')
