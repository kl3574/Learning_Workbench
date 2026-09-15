"""Explicit, private immutable secret versions; construction performs no I/O."""

from contextlib import contextmanager
from collections.abc import Iterator
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Protocol
from uuid import uuid4

from ..application.errors import ApiError


def unavailable() -> ApiError:
    return ApiError(503, 'PROVIDER_SECRET_UNAVAILABLE', '提供商秘密存储不可用，请检查本机安全设置。')


class SecretStore(Protocol):
    """An explicitly supplied system adapter takes precedence over file fallback."""

    def initialize(self) -> None: ...
    def put(self, secret: str) -> str: ...
    def read(self, locator: str) -> str: ...
    def delete(self, locator: str) -> None: ...
    def available(self, locator: str) -> bool: ...
    def fingerprint(self, canonical_command: bytes) -> str: ...
    def versions(self) -> frozenset[str]: ...


def preferred_secret_store(root: Path, *, system_adapter: SecretStore | None = None) -> SecretStore:
    """Selection is explicit and performs no credential discovery or storage I/O."""
    return system_adapter if system_adapter is not None else FileSecretStore(root)


class FileSecretStore:
    """Fallback adapter. Only initialize() creates the private storage boundary."""

    def __init__(self, root: Path):
        self.root = root.absolute()
        if '..' in self.root.parts:
            raise ValueError('Private storage requires a non-traversing path.')

    @contextmanager
    def _directory(self, *, create: bool = False) -> Iterator[int]:
        descriptor = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in self.root.parts[1:]:
                if create:
                    try:
                        os.mkdir(part, mode=0o700, dir_fd=descriptor)
                    except FileExistsError:
                        pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            info = os.fstat(descriptor)
            if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise unavailable()
            yield descriptor
        except OSError:
            raise unavailable() from None
        finally:
            os.close(descriptor)

    def _read(self, directory: int, name: str, *, limit: int) -> bytes:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            info = os.fstat(descriptor)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1 or info.st_size > limit):
                raise unavailable()
            with os.fdopen(os.dup(descriptor), 'rb') as stream:
                return stream.read(limit + 1)
        finally:
            os.close(descriptor)

    def _write(self, directory: int, name: str, data: bytes) -> None:
        temporary = '.staging-' + uuid4().hex
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=directory)
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            # A new immutable name becomes visible only with complete bytes.
            os.link(temporary, name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        finally:
            os.unlink(temporary, dir_fd=directory)
            os.fsync(directory)

    def initialize(self) -> None:
        with self._directory(create=True) as directory:
            names = os.listdir(directory)
            if 'fingerprint.key' not in names and any(re.fullmatch(r'secret_[0-9a-f]{32}', name) for name in names):
                raise unavailable()  # Never silently replace a lost key for existing versions.
            try:
                self._write(directory, 'fingerprint.key', secrets.token_bytes(32))
            except FileExistsError:
                pass
            if len(self._read(directory, 'fingerprint.key', limit=32)) != 32:
                raise unavailable()

    def fingerprint(self, canonical_command: bytes) -> str:
        with self._directory() as directory:
            key = self._read(directory, 'fingerprint.key', limit=32)
            if len(key) != 32:
                raise unavailable()
            return hmac.new(key, b'provider-command-v1\0' + canonical_command, hashlib.sha256).hexdigest()

    def put(self, secret: str) -> str:
        if not isinstance(secret, str) or not secret.strip() or len(secret.encode('utf-8')) > 65536:
            raise ApiError(422, 'SCHEMA_INVALID', '提供商秘密必须为非空且符合大小限制的文本。')
        locator = 'secret_' + uuid4().hex
        with self._directory() as directory:
            key = self._read(directory, 'fingerprint.key', limit=32)
            if len(key) != 32:
                raise unavailable()
            data = secret.encode('utf-8')
            signature = hmac.new(key, b'provider-secret-v1\0' + locator.encode() + b'\0' + data, hashlib.sha256).digest()
            self._write(directory, locator, b'LWPS1\n' + signature + data)
        return locator

    def _name(self, locator: str) -> str:
        if not isinstance(locator, str) or re.fullmatch(r'secret_[0-9a-f]{32}', locator) is None:
            raise unavailable()
        return locator

    def read(self, locator: str) -> str:
        try:
            with self._directory() as directory:
                raw = self._read(directory, self._name(locator), limit=65574)
                key = self._read(directory, 'fingerprint.key', limit=32)
                if len(key) != 32 or len(raw) <= 38 or not raw.startswith(b'LWPS1\n'):
                    raise unavailable()
                expected = hmac.new(key, b'provider-secret-v1\0' + locator.encode() + b'\0' + raw[38:], hashlib.sha256).digest()
                if not hmac.compare_digest(raw[6:38], expected):
                    raise unavailable()
                value = raw[38:].decode('utf-8')
                if not value.strip():
                    raise unavailable()
                return value
        except UnicodeError:
            raise unavailable() from None

    def available(self, locator: str) -> bool:
        try:
            self.read(locator)
            return True
        except ApiError:
            return False

    def versions(self) -> frozenset[str]:
        """Private opaque names for explicitly authorized recovery, not an HTTP DTO."""
        with self._directory() as directory:
            return frozenset(name for name in os.listdir(directory) if re.fullmatch(r'secret_[0-9a-f]{32}', name))

    def delete(self, locator: str) -> None:
        with self._directory() as directory:
            name = self._name(locator)
            try:
                # Validate before unlink: an attacker-created symlink is not a secret version.
                self._read(directory, name, limit=65574)
                os.unlink(name, dir_fd=directory)
                os.fsync(directory)
            except FileNotFoundError:
                return
