"""Install the locked local toolchain without changing system Python or Node."""
from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_VERSION = "24.21.0"
NODE_SHA256 = "fd8e59d5a511510f6a298afb548f18c7d2b1be404d8b4a27d94fbe49f56cb2d6"
NODE_ROOT = ROOT / ".toolchain" / f"node-v{NODE_VERSION}-linux-x64"


def run(*args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def setup() -> None:
    if not shutil.which("uv"):
        raise SystemExit("Install uv from https://docs.astral.sh/uv/getting-started/installation/ then rerun make setup.")
    run("uv", "sync", "--frozen", "--python", (ROOT / ".python-version").read_text().strip())
    candidate = shutil.which("node")
    system_matches = candidate and subprocess.check_output([candidate, "--version"], text=True).strip() == f"v{NODE_VERSION}"
    if not system_matches and not (NODE_ROOT / "bin/node").exists():
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise SystemExit(f"Install Node {NODE_VERSION} for this architecture; automatic installer supports Linux x86_64.")
        archive = ROOT / ".toolchain" / f"node-v{NODE_VERSION}-linux-x64.tar.xz"
        archive.parent.mkdir(exist_ok=True)
        run("curl", "--fail", "--show-error", "--location", "--proto", "=https", "--connect-timeout", "10",
            "--max-time", "180", f"https://nodejs.org/dist/v{NODE_VERSION}/{archive.name}", "--output", str(archive))
        if hashlib.sha256(archive.read_bytes()).hexdigest() != NODE_SHA256:
            raise SystemExit("Node archive checksum mismatch; refusing extraction")
        with tarfile.open(archive) as source:
            source.extractall(archive.parent, filter="data")
    environment = dict(os.environ)
    if (NODE_ROOT / "bin/node").exists():
        environment["PATH"] = str(NODE_ROOT / "bin") + os.pathsep + environment["PATH"]
    run("npm", "ci", "--prefix", "apps/web", env=environment)
    print("Locked Python and Node dependencies installed; no model provider contacted.")


if __name__ == "__main__":
    setup()
