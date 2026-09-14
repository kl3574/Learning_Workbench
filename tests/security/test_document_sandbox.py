"""Real Linux sandbox checks use only generated strings and disposable canaries."""

from contextlib import ExitStack
from dataclasses import asdict
import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import time

import pytest

from packages.contracts.budgets import ImportBudgets
from services.api.app.infrastructure import document_sandbox as sandbox


def arguments(stack, entry, limits):
    files = []
    for data, destination in ((b"SYNTHETIC DOCUMENT", "/input.bin"), (b"", "/extractors/document_extract/__init__.py"),
                              (json.dumps({"kind": "pdf", "budgets": asdict(ImportBudgets())}).encode(), "/request.json")):
        file = stack.enter_context(sandbox._memory_file(data))
        files.append((file.fileno(), destination))
    policy = stack.enter_context(sandbox._memory_file())
    sandbox._seccomp(policy.fileno())
    post = stack.enter_context(sandbox._memory_file())
    sandbox._seccomp(post.fileno(), post_exec=True)
    files.append((post.fileno(), "/post-exec.bpf"))
    return sandbox._command(tuple(files), limits, policy.fileno(), entry=entry), (policy.fileno(), *(fd for fd, _ in files))


def run_program(tmp_path, code, limits=None):
    entry = tmp_path / "entry.py"
    entry.write_text("import sys\nsys.path.insert(0,'/')\nfrom sandbox_bootstrap import lock_execution\nlock_execution()\n" + code, encoding="utf-8")
    limits = limits or sandbox.SandboxLimits(wall_seconds=5)
    with ExitStack() as stack:
        command, fds = arguments(stack, entry, limits)
        return sandbox._run(command, fds=fds, limits=limits)


def test_actual_namespace_filesystem_network_exec_and_secret_environment(tmp_path, monkeypatch):
    secret = "SYNTHETIC_ENVIRONMENT_CANARY_ONLY"
    monkeypatch.setenv("LEARNING_TEST_PRIVATE", secret)
    canary = tmp_path / "outside.txt"
    canary.write_text("SYNTHETIC OUTSIDE CANARY", encoding="utf-8")
    code = '''import errno,json,os,pathlib,socket
result={"host_canary":pathlib.Path(CANARY).exists(),"home_visible":pathlib.Path('/home').exists(),
        "environment_secret":'SYNTHETIC_ENVIRONMENT_CANARY_ONLY' in str(dict(os.environ)),
        "reaper_secret":b'SYNTHETIC_ENVIRONMENT_CANARY_ONLY' in pathlib.Path('/proc/1/environ').read_bytes()}
for name,operation in [('write_root',lambda:open('/new_file','wb')),('write_input',lambda:open('/input.bin','wb')),
                       ('network',lambda:socket.socket(socket.AF_INET,socket.SOCK_STREAM)),('fork',os.fork),
                       ('exec',lambda:os.execv('/runtime/bin/python3.12',['python','-c','raise SystemExit(99)']))]:
 try:operation();result[name]='ALLOWED'
 except OSError as error:result[name]=errno.errorcode[error.errno]
print(json.dumps(result))
'''.replace("CANARY", repr(str(canary)), 1)
    result = json.loads(run_program(tmp_path, code))
    assert result == {"host_canary": False, "home_visible": False, "environment_secret": False, "reaper_secret": False,
                      "write_root": "EROFS", "write_input": "EROFS", "network": "EPERM", "fork": "EPERM", "exec": "EPERM"}
    assert canary.read_text() == "SYNTHETIC OUTSIDE CANARY"


@pytest.mark.parametrize(("code", "limits", "expected"), [
    ("while True:pass\n", sandbox.SandboxLimits(wall_seconds=4, cpu_seconds=1), "EXTRACTION_RESOURCE_LIMIT"),
    ("import time\ntime.sleep(10)\n", sandbox.SandboxLimits(wall_seconds=.2), "EXTRACTION_TIMEOUT"),
    ("import os\nwhile True:os.write(1,b'x'*8192)\n", sandbox.SandboxLimits(output_bytes=1024), "EXTRACTION_OUTPUT_LIMIT"),
    ("import os\nwhile True:os.write(2,b'x'*8192)\n", sandbox.SandboxLimits(output_bytes=1024), "EXTRACTION_OUTPUT_LIMIT"),
])
def test_real_cpu_wall_and_stream_limits(tmp_path, code, limits, expected):
    with pytest.raises(sandbox.DocumentSandboxError) as error:
        run_program(tmp_path, code, limits)
    assert error.value.code == expected


def test_real_memory_limit(tmp_path):
    result = run_program(tmp_path, "try:\n bytearray(512*1024*1024)\n print('ALLOWED')\nexcept MemoryError:print('DENIED')\n",
                         sandbox.SandboxLimits(memory_bytes=128*1024*1024))
    assert result == b"DENIED\n"


def test_missing_bubblewrap_fails_closed(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda *args, **kwargs: None)
    with pytest.raises(sandbox.DocumentSandboxError) as error:
        sandbox.extract_document(b"%PDF-synthetic", kind="pdf", filename="synthetic.pdf", source_id="source_synthetic", budgets=ImportBudgets())
    assert error.value.code == "EXTRACTION_ENVIRONMENT_UNAVAILABLE"


@pytest.mark.parametrize("raw", [b"[]", b"{}", b'{"status":"ok","status":"error"}',
    b'{"status":"error","code":"FAILED","warnings":[],"extra":true}',
    json.dumps({"status": "error", "code": "FAILED", "warnings": [{"code": "W", "message": "x", "locator": None, "severity": "warning"}] * 502}).encode(),
    json.dumps({"status": "error", "code": "FAILED", "warnings": [{"code": "W", "message": "x"*601, "locator": None, "severity": "warning"}]}).encode(),
])
def test_output_protocol_rejects_invalid_shapes_and_unbounded_diagnostics(raw):
    with pytest.raises(sandbox.DocumentSandboxError) as error:
        sandbox._decode(raw, ImportBudgets())
    assert error.value.code == "EXTRACTION_OUTPUT_INVALID"


def sandbox_daemon(channel, entry, expected_parent):
    sandbox.bind_parent_lifetime(expected_parent)
    limits = sandbox.SandboxLimits(wall_seconds=30)
    with ExitStack() as stack:
        command, fds = arguments(stack, Path(entry), limits)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                   pass_fds=fds, close_fds=True, start_new_session=True,
                                   env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
        try:
            assert process.stdout.readline() == b"READY\n"
            pids = [process.pid]
            pending = list(pids)
            while pending:
                pid = pending.pop()
                children = [int(value) for value in Path(f"/proc/{pid}/task/{pid}/children").read_text().split()]
                pids.extend(children)
                pending.extend(children)
            channel.send((os.getpid(), pids))
            while True:
                time.sleep(.1)
        finally:
            sandbox._kill_tree(process)


def parent_of_sandbox(channel, entry):
    context = multiprocessing.get_context("spawn")
    process = context.Process(target=sandbox_daemon, args=(channel, entry, os.getpid()), daemon=True)
    process.start()
    channel.close()
    while True:
        time.sleep(.1)


def test_abrupt_api_death_kills_daemon_reaper_and_parser(tmp_path):
    entry = tmp_path / "child.py"
    entry.write_text("import time\nprint('READY',flush=True)\ntime.sleep(30)\n", encoding="utf-8")
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(False)
    parent = context.Process(target=parent_of_sandbox, args=(send, str(entry)))
    parent.start()
    send.close()
    pids = []
    try:
        assert receive.poll(10), "The sandbox must start; missing isolation is a failing environment gate."
        daemon_pid, pids = receive.recv()
        pids.append(daemon_pid)
        assert len(pids) >= 4  # daemon, bwrap monitor, PID1 reaper, parser
        parent.kill()
        parent.join(3)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and any(Path(f"/proc/{pid}").exists() for pid in pids):
            time.sleep(.05)
        assert not any(Path(f"/proc/{pid}").exists() for pid in pids)
    finally:
        if parent.is_alive():
            parent.kill()
        parent.join(3)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        receive.close()
        parent.close()
