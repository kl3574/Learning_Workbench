"""Run one actual check and preserve a sanitized, hash-bound receipt and output."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.id) or not command:
        parser.error("A safe check id and actual command are required")
    start = datetime.now(timezone.utc)
    code_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    diff = subprocess.check_output(["git", "diff", "HEAD"], cwd=ROOT)
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    output = result.stdout.replace(str(ROOT), "<REPO>")
    data_path = os.environ.get("LEARNING_DATA_DIR")
    if data_path:
        output = output.replace(data_path, "<DATA_DIR>")
    output = re.sub(r"/home/[^/\s]+/", "<USER_HOME>/", output)
    output = re.sub(r"/tmp/(?:pytest-of-[^/\s]+|learning-workbench[^/\s]*)", "<TEMP>", output)
    # A secret detector rejects saving; it never quietly converts a leaked test
    # credential into an apparently safe green public report.
    from check_publication import SUSPECT
    if any(re.search(pattern, output.encode()) for pattern in SUSPECT):
        raise SystemExit("Suspect secret in check output; public receipt was not written")
    directory = ROOT / "progress/evidence" / start.strftime("%Y-%m-%d")
    directory.mkdir(parents=True, exist_ok=True)
    logfile = directory / (args.id + ".log")
    logfile.write_text(output, encoding="utf-8")
    receipt = {"check_id": args.id, "category": args.category, "command": shlex.join(command),
               "started_at": start.isoformat(), "finished_at": datetime.now(timezone.utc).isoformat(),
               "implementation_commit": code_sha, "tracked_worktree_diff_sha256": hashlib.sha256(diff).hexdigest() if diff else None,
               "spec_sha256": hashlib.sha256((ROOT / "PRODUCT_DESIGN.md").read_bytes()).hexdigest(),
               "exit_code": result.returncode, "status": "PASS" if result.returncode == 0 else "FAIL",
               "output_path": str(logfile.relative_to(ROOT)), "output_sha256": hashlib.sha256(logfile.read_bytes()).hexdigest(),
               "scope": "Only the command executed; no implication for unrun business, real-provider, Codex or learning-effectiveness tests."}
    (directory / (args.id + ".json")).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    sys.stdout.write(output)
    print(f"Receipt: {directory.relative_to(ROOT)}/{args.id}.json")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
