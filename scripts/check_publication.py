"""Fail closed on suspect staged content before publishing this project.

This bounded scanner supplements provenance review; it is not a guarantee that
arbitrary personal prose can be recognized automatically.
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import zipfile
from pathlib import PurePosixPath

ALLOWED_ROOTS = {"PRODUCT_DESIGN.md", "README.md", "AGENTS.md", "Makefile", ".gitignore", ".gitattributes", ".env.example",
                 ".python-version", ".node-version", "pyproject.toml", "uv.lock", "apps", "services", "packages",
                 "migrations", "scripts", "tests", "fixtures", "progress", "docs", ".github"}
SUSPECT = [rb"gh[pousr]_[A-Za-z0-9]{30,}", rb"github_pat_[A-Za-z0-9_]{40,}",
           rb"sk-[A-Za-z0-9_-]{24,}", rb"AKIA[A-Z0-9]{16}", rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
           rb"/home/[A-Za-z0-9_.-]+/", rb"[?&#]bootstrap=[A-Za-z0-9_-]{20,}"]
FORBIDDEN = {"node_modules", ".venv", ".toolchain", ".local_data", "backups", "personal-notes", "secrets"}


def inspect(path: str, data: bytes) -> list[str]:
    parts = PurePosixPath(path).parts
    failures = []
    if not parts or parts[0] not in ALLOWED_ROOTS or ".." in parts:
        failures.append("path outside publication allowlist")
    if set(parts) & FORBIDDEN or (PurePosixPath(path).suffix in {".db", ".sqlite", ".sqlite3", ".pem", ".key", ".token"}):
        failures.append("private or runtime artifact")
    if PurePosixPath(path).name.startswith(".env") and path != ".env.example":
        failures.append("environment file")
    if any(re.search(pattern, data) for pattern in SUSPECT):
        failures.append("suspected credential or personal absolute path; inspect privately")
    if path.endswith(".zip"):
        if not path.startswith("fixtures/synthetic/"):
            failures.append("archive outside synthetic fixtures")
        else:
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    for member in archive.infolist():
                        if member.file_size > 2_000_000 or member.compress_size and member.file_size / member.compress_size > 100:
                            failures.append("archive member outside scan budget")
                            break
                        if any(re.search(pattern, archive.read(member)) for pattern in SUSPECT):
                            failures.append("suspect archive payload")
                            break
            except zipfile.BadZipFile:
                failures.append("invalid archive")
    return failures


def main(all_tracked: bool) -> int:
    command = ["git", "ls-files", "-z"] if all_tracked else ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
    paths = subprocess.check_output(command).decode().split("\0")
    count = 0
    failures = []
    for path in filter(None, paths):
        data = subprocess.check_output(["git", "show", ":" + path])
        failures.extend(f"{path}: {reason}" for reason in inspect(path, data))
        count += 1
    if failures:
        print("FAIL: publication stopped\n" + "\n".join(failures))
        return 1
    print(f"PASS: scanned {count} staged/tracked files against path and credential rules. Manual provenance review remains required.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-tracked", action="store_true")
    raise SystemExit(main(parser.parse_args().all_tracked))
