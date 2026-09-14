"""Linux document extraction in an empty read-only filesystem and network namespace.

Only the fixed extractor, its two locked packages, and a Python runtime are exposed.
A missing capability fails closed; there is no in-process extraction fallback.
"""

from contextlib import ExitStack
from dataclasses import asdict, dataclass
import fcntl
import ctypes
import ctypes.util
from functools import lru_cache
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import sysconfig
import time
from typing import TYPE_CHECKING, BinaryIO, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from packages.contracts.budgets import ImportBudgets

if TYPE_CHECKING:
    from ..application.import_extract_types import ExtractedDocument, ExtractionWarning


class DocumentSandboxError(ValueError):
    def __init__(self, code: str, warnings: tuple["ExtractionWarning", ...] = ()):
        super().__init__(code)
        self.code = code
        self.warnings = warnings


@dataclass(frozen=True)
class SandboxLimits:
    wall_seconds: float = 45.0
    cpu_seconds: int = 30
    memory_bytes: int = 512 * 1024 * 1024
    output_bytes: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.wall_seconds <= 0 or min(self.cpu_seconds, self.memory_bytes, self.output_bytes) <= 0:
            raise ValueError("Sandbox limits must be positive.")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _Warning(_Strict):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,79}$")
    message: str = Field(max_length=600)
    locator: str | None = Field(max_length=1024)
    severity: Literal["info", "warning", "error"]


class _Chunk(_Strict):
    kind: Literal["page", "heading", "paragraph", "table"]
    body_markdown: str
    locator: str = Field(max_length=1024)
    heading_level: int | None = Field(ge=1, le=6)


class _Document(_Strict):
    chunks: list[_Chunk]
    warnings: list[_Warning]
    extractor_version: str = Field(min_length=1, max_length=100)
    original_visibility: Literal["learner", "author_private"]


class _Success(_Strict):
    status: Literal["ok"]
    document: _Document


class _Failure(_Strict):
    status: Literal["error"]
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,79}$")
    warnings: list[_Warning]


def bind_parent_lifetime(expected_parent: int) -> None:
    """Close the spawn/PDEATHSIG race before any untrusted parsing starts."""
    if sys.platform != "linux":
        return
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
    if os.getppid() != expected_parent:
        os._exit(1)


def _regular(path: Path) -> Path:
    path = path.resolve(strict=True)
    if not path.is_file():
        raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
    return path


@lru_cache(maxsize=1)
def _runtime_mounts() -> tuple[tuple[Path, str], ...]:
    """Resolve only trusted runtime files, never run ldd on uploaded bytes."""
    if sys.platform != "linux" or sys.version_info[:2] != (3, 12):
        raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
    executable = _regular(Path(sys.executable))
    stdlib = Path(sysconfig.get_path("stdlib")).resolve(strict=True)
    mounts: list[tuple[Path, str]] = [(executable, "/runtime/bin/python3.12"), (stdlib, "/runtime/lib/python3.12")]
    libraries: dict[str, Path] = {}
    # uv's standalone build has built-in extensions; setup-python uses .so files.
    binaries = [executable]
    for name in ("_io", "_json", "_struct", "_datetime", "_bisect", "_heapq", "_random", "_sha2", "_hashlib",
                 "_csv", "_typing", "_ctypes", "math", "zlib", "binascii", "unicodedata", "pyexpat", "select",
                 "_socket", "array", "fcntl", "resource", "_elementtree", "_lzma", "_bz2", "_ssl"):
        module = importlib.util.find_spec(name)
        if module is not None and module.origin not in {None, "built-in", "frozen"}:
            path = _regular(Path(module.origin))
            if path.suffix == ".so":
                binaries.append(path)
    for binary in binaries:
        output = subprocess.run(["/usr/bin/ldd", str(binary)], capture_output=True, timeout=5, check=False,
                                env={"PATH": "/usr/bin:/bin", "LANG": "C"})
        if output.returncode != 0 or b"not found" in output.stdout:
            raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
        for line in output.stdout.splitlines():
            fields = line.split(b"=>", 1)
            match = re.search(rb"(/[^\s()]+)", fields[-1])
            if match is None:
                continue  # linux-vdso has no backing file.
            original = Path(os.fsdecode(match[1]))
            library = _regular(original)
            # Resolve the trusted source without losing the ELF loader's SONAME.
            # e.g. libbz2.so.1.0 resolves to libbz2.so.1.0.4 on Ubuntu.
            aliases = {original.name}
            if len(fields) == 2:
                aliases.add(os.fsdecode(fields[0].strip()))
            for alias in aliases:
                if (not alias or alias in {".", ".."} or Path(alias).name != alias
                        or any(character.isspace() for character in alias)):
                    raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
                if alias in libraries and libraries[alias] != library:
                    raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
                libraries[alias] = library
    for alias, library in sorted(libraries.items()):
        mounts.append((library, f"/runtime/lib/{alias}"))
    # The dynamic linker path is embedded in the ELF interpreter.
    for loader_path in (Path("/lib64/ld-linux-x86-64.so.2"), Path("/lib/ld-linux-aarch64.so.1")):
        if loader_path.is_file():
            mounts.append((_regular(loader_path), str(loader_path)))
    for package in ("pypdf", "defusedxml"):
        spec = importlib.util.find_spec(package)
        if spec is None or spec.origin is None:
            raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
        mounts.append((_regular(Path(spec.origin)).parent, f"/deps/{package}"))
    return tuple(dict.fromkeys(mounts))


def _seccomp(fd: int, *, post_exec: bool = False) -> None:
    """Generate architecture-aware BPF; parser cannot create network or child processes."""
    name = ctypes.util.find_library("seccomp")
    if name is None:
        raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
    lib = ctypes.CDLL(name)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_rule_add.restype = ctypes.c_int
    lib.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not context:
        raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
    try:
        syscalls = (
            "socket", "socketpair", "connect", "bind", "listen", "accept", "accept4", "clone", "clone3", "fork", "vfork",
            "ptrace", "mount", "umount2", "pivot_root", "unshare", "setns", "bpf", "keyctl", "add_key", "request_key",
            "open_by_handle_at", "process_vm_readv", "process_vm_writev",
        )
        for syscall in (*syscalls, *(("execve", "execveat") if post_exec else ())):
            number = lib.seccomp_syscall_resolve_name(syscall.encode("ascii"))
            if number >= 0 and lib.seccomp_rule_add(context, 0x00050001, number, 0) != 0:  # EPERM
                raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
        if lib.seccomp_export_bpf(context, fd) != 0:
            raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
        os.lseek(fd, 0, os.SEEK_SET)
    finally:
        lib.seccomp_release(context)


def _command(files: tuple[tuple[int, str], ...], limits: SandboxLimits, seccomp_fd: int, *, entry: Path | None = None) -> list[str]:
    bwrap, prlimit = shutil.which("bwrap", path="/usr/bin:/bin"), shutil.which("prlimit", path="/usr/bin:/bin")
    if bwrap is None or prlimit is None:
        raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
    command = [prlimit, f"--cpu={limits.cpu_seconds}:{limits.cpu_seconds + 1}", f"--as={limits.memory_bytes}",
               f"--fsize={limits.output_bytes}", "--nofile=64", "--core=0", "--", bwrap,
               "--unshare-user", "--unshare-ipc", "--unshare-pid", "--unshare-net", "--unshare-uts",
               "--disable-userns", "--cap-drop", "ALL", "--die-with-parent", "--new-session", "--clearenv",
               "--setenv", "LANG", "C.UTF-8", "--setenv", "LD_LIBRARY_PATH", "/runtime/lib",
               "--setenv", "LEARNING_DOCUMENT_SANDBOX", "1"]
    # Keep bwrap's default PID1 reaper. --as-pid-1 broke death propagation in a real probe.
    for source, destination in _runtime_mounts():
        command.extend(("--ro-bind", str(source), destination))
    application = Path(__file__).resolve().parents[1] / "application"
    for name in ("import_extract_types.py", "import_extract_pdf.py", "import_extract_docx.py"):
        command.extend(("--ro-bind", str(_regular(application / name)), f"/extractors/document_extract/{name}"))
    command.extend(("--ro-bind", str(_regular(Path(__file__).with_name("import_archive.py"))), "/extractors/document_extract/import_archive.py"))
    entry = _regular(entry or Path(__file__).with_name("document_sandbox_entry.py"))
    for fd, destination in files:
        command.extend(("--ro-bind-data", str(fd), destination))
    command.extend(("--ro-bind", str(entry), "/entry.py",
                    "--ro-bind", str(_regular(Path(__file__).with_name("document_sandbox_bootstrap.py"))), "/sandbox_bootstrap.py",
                    "--tmpfs", "/runtime/lib/python3.12/site-packages", "--remount-ro", "/runtime/lib/python3.12/site-packages",
                    "--dev", "/dev", "--proc", "/proc", "--dir", "/tmp", "--chdir", "/", "--remount-ro", "/",
                    "--seccomp", str(seccomp_fd), "--", "/runtime/bin/python3.12", "-I", "-S", "-B", "/entry.py"))
    return command


def _kill_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=3)


def _run(command: list[str], *, fds: tuple[int, ...], limits: SandboxLimits) -> bytes:
    output = bytearray()
    with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          pass_fds=fds, close_fds=True, start_new_session=True,
                          env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}) as process:
        assert process.stdout is not None and process.stderr is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        selector.register(process.stderr, selectors.EVENT_READ)
        deadline = time.monotonic() + limits.wall_seconds
        stderr_size = 0
        try:
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise DocumentSandboxError("EXTRACTION_TIMEOUT")
                for key, _ in selector.select(0.05):
                    chunk = os.read(key.fd, 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.fileobj is process.stderr:
                        stderr_size += len(chunk)
                        if stderr_size > 65536:
                            raise DocumentSandboxError("EXTRACTION_OUTPUT_LIMIT")
                    else:
                        if len(output) + len(chunk) > limits.output_bytes:
                            raise DocumentSandboxError("EXTRACTION_OUTPUT_LIMIT")
                        output.extend(chunk)
            try:
                status = process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                raise DocumentSandboxError("EXTRACTION_TIMEOUT") from None
            if status != 0:
                code = "EXTRACTION_RESOURCE_LIMIT" if status in (137, 152, -9, -24) else "EXTRACTION_ENVIRONMENT_UNAVAILABLE"
                raise DocumentSandboxError(code)
            return bytes(output)
        finally:
            selector.close()
            _kill_tree(process)


def _decode(data: bytes, budgets: ImportBudgets) -> "ExtractedDocument":
    from ..application.import_extract_types import ExtractedChunk, ExtractedDocument, ExtractionWarning
    try:
        raw = json.loads(data, object_pairs_hook=_unique_pairs)
        if not isinstance(raw, dict):
            raise ValueError("Invalid result")
        payload = raw if raw.get("status") == "error" else raw.get("document")
        if not isinstance(payload, dict) or not isinstance(payload.get("warnings"), list) or len(payload["warnings"]) > 501:
            raise DocumentSandboxError("EXTRACTION_OUTPUT_INVALID")
        if raw.get("status") == "ok":
            chunks = payload.get("chunks")
            if not isinstance(chunks, list) or len(chunks) > budgets.max_package_files:
                raise DocumentSandboxError("EXTRACTION_OUTPUT_LIMIT")
        if raw.get("status") == "error":
            failure = _Failure.model_validate(raw)
            raise DocumentSandboxError(failure.code, tuple(ExtractionWarning(**warning.model_dump()) for warning in failure.warnings))
        result = _Success.model_validate(raw).document
        if (len(result.chunks) > budgets.max_package_files
                or any(len(chunk.body_markdown) > budgets.max_block_characters for chunk in result.chunks)
                or sum(len(chunk.body_markdown.encode("utf-8")) for chunk in result.chunks) > budgets.max_package_bytes):
            raise DocumentSandboxError("EXTRACTION_OUTPUT_LIMIT")
        return ExtractedDocument(chunks=tuple(ExtractedChunk(**chunk.model_dump()) for chunk in result.chunks),
                                 warnings=tuple(ExtractionWarning(**warning.model_dump()) for warning in result.warnings),
                                 extractor_version=result.extractor_version, original_visibility=result.original_visibility)
    except DocumentSandboxError:
        raise
    except (ValidationError, UnicodeError, ValueError, TypeError, KeyError):
        raise DocumentSandboxError("EXTRACTION_OUTPUT_INVALID") from None


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate result field")
        result[key] = value
    return result


def extract_document(data: bytes, *, kind: str, filename: str, source_id: str,
                     budgets: ImportBudgets, limits: SandboxLimits | None = None) -> "ExtractedDocument":
    """The only production PDF/DOCX execution port. The sandbox never sees DB or filenames."""
    if kind not in {"pdf", "docx"} or type(data) is not bytes or len(data) > budgets.max_source_bytes:
        raise DocumentSandboxError("EXTRACTION_INPUT_INVALID")
    limits = limits or SandboxLimits(output_bytes=budgets.max_package_bytes + 1024 * 1024)
    try:
        with ExitStack() as stack:
            files = []
            for value, destination in ((data, "/input.bin"), (b"", "/extractors/document_extract/__init__.py"),
                                       (json.dumps({"kind": kind, "budgets": asdict(budgets)}).encode(), "/request.json")):
                file = stack.enter_context(_memory_file(value))
                files.append((file.fileno(), destination))
            policy = stack.enter_context(_memory_file())
            _seccomp(policy.fileno())
            post = stack.enter_context(_memory_file())
            _seccomp(post.fileno(), post_exec=True)
            files.append((post.fileno(), "/post-exec.bpf"))
            arguments = _command(tuple(files), limits, policy.fileno())
            raw = _run(arguments, fds=(policy.fileno(), *(fd for fd, _ in files)), limits=limits)
            return _decode(raw, budgets)
    except (OSError, subprocess.SubprocessError):
        raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE") from None


def _memory_file(data: bytes | None = None) -> BinaryIO:
    """Anonymous input disappears even if the API and parser are killed abruptly."""
    if sys.platform != "linux":
        raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
    # uv standalone Python can omit os.memfd_create / fcntl seal constants.
    # Call the host libc ABI with Linux UAPI MFD_CLOEXEC|MFD_ALLOW_SEALING.
    library = ctypes.CDLL(None, use_errno=True)
    try:
        create = library.memfd_create
    except AttributeError:
        raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE") from None
    create.argtypes = [ctypes.c_char_p, ctypes.c_uint]
    create.restype = ctypes.c_int
    fd = create(b"learning-document", 0x0001 | 0x0002)
    if fd < 0:
        raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
    file = os.fdopen(fd, "w+b", buffering=0)
    try:
        if data is not None:
            remaining = memoryview(data)
            while remaining:
                count = file.write(remaining)
                if not count:
                    raise DocumentSandboxError("EXTRACTION_ENVIRONMENT_UNAVAILABLE")
                remaining = remaining[count:]
            file.seek(0)
            fcntl.fcntl(fd, 1033, 0x0008 | 0x0004 | 0x0002 | 0x0001)  # WRITE|GROW|SHRINK|SEAL
        return file
    except BaseException:
        file.close()
        raise
