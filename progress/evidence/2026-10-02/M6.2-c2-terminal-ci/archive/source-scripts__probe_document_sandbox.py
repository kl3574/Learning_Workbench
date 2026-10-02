"""Diagnose only a fixed synthetic sandbox entry; never accept document input."""
from contextlib import ExitStack
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.api.app.infrastructure import document_sandbox as sandbox  # noqa: E402


def sanitized(value: bytes) -> str:
    text = value.decode("utf-8", errors="replace")[:12000]
    text = text.replace(str(ROOT), "<REPO>")
    return re.sub(r"/home/[^/\s]+/", "<USER_HOME>/", text)


def main() -> int:
    result: dict[str, object] = {"scope": "fixed synthetic runtime probe; no uploaded document or environment dump",
                                "python_version": sys.version.split()[0]}
    with tempfile.TemporaryDirectory(prefix="learning-workbench-sandbox-probe-") as directory, ExitStack() as stack:
        entry = Path(directory) / "entry.py"
        entry.write_text("import sys\nsys.path.insert(0,'/')\n"
                         "from sandbox_bootstrap import lock_execution\nlock_execution()\n"
                         "import ctypes,json,zlib,xml.etree.ElementTree\n"
                         "print(json.dumps({'synthetic_runtime_ready':True}))\n", encoding="utf-8")
        limits = sandbox.SandboxLimits(wall_seconds=5, output_bytes=16384)
        policy = stack.enter_context(sandbox._memory_file())
        sandbox._seccomp(policy.fileno())
        post = stack.enter_context(sandbox._memory_file())
        sandbox._seccomp(post.fileno(), post_exec=True)
        try:
            command = sandbox._command(((post.fileno(), "/post-exec.bpf"),), limits, policy.fileno(), entry=entry)
            with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  pass_fds=(policy.fileno(), post.fileno()), close_fds=True, start_new_session=True,
                                  env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}) as process:
                try:
                    stdout, stderr = process.communicate(timeout=5)
                    result.update(exit_code=process.returncode, stdout=sanitized(stdout), stderr=sanitized(stderr))
                except subprocess.TimeoutExpired:
                    sandbox._kill_tree(process)
                    stdout, stderr = process.communicate()
                    result.update(exit_code=process.returncode, timeout=True, stdout=sanitized(stdout), stderr=sanitized(stderr))
        except sandbox.DocumentSandboxError as error:
            result.update(error_code=error.code)
    passed = result.get("exit_code") == 0 and result.get("stdout") == '{"synthetic_runtime_ready": true}\n'
    result["status"] = "PASS" if passed else "FAIL"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
