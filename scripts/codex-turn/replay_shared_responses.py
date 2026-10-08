#!/usr/bin/env python3
"""Replay the pinned shared Responses producer's complete 190-test API library.

This uses the same guarded archive, task-owned toolchain, source verification,
and actual-command recorder as the HTTP gate replay. It runs no Codex CLI,
AppServer or real model and does not register a production profile.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from replay_http_gate import execute, sha256, utc, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, help="Original pinned local Codex archive")
    parser.add_argument("--output-dir", required=True, help="New nonexistent private output directory")
    parser.add_argument("--toolchain-dir", help="Task-owned standalone Rust 1.95.0 prefix")
    parser.add_argument("--cargo-home", help="Separately prepared task-owned Cargo cache")
    parser.add_argument("--prepare-only", action="store_true", help="Check/apply source; execute no Cargo")
    args = parser.parse_args()
    args.all_lib = True
    args.offline = True
    output = Path(args.output_dir).absolute()
    try:
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
    except OSError as error:
        print(f"Output directory must be new; nothing overwritten: {error}", file=sys.stderr)
        return 1
    output = output.resolve()
    report = {
        "schema_version": 1, "started_at_utc": utc(), "status": "RUNNING",
        "replay_wrapper_sha256": sha256(Path(__file__).resolve()),
        "production": "INCOMPLETE / NOT_ADMITTED", "invocation": [sys.executable, *sys.argv],
        "commands": [], "graph": {"nodes": [], "edges": []},
        "test_scope": "complete codex-api library, strict --locked --offline",
        "historical_http_client": "114 PASS / 6 FAIL retained; not superseded by API tests",
        "not_run": ["core/guardian compile", "Codex CLI", "AppServer", "models",
                    "platform acceptance", "production profile admission"],
    }
    write_json(output / "report.json", report)
    try:
        result = execute(args, output, report, Path(__file__).with_name("shared-responses-source.json"))
        report["status"] = "PASS" if result == 0 else "FAIL"
    except KeyboardInterrupt:
        result = 130
        report.update(status="INTERRUPTED", error="KeyboardInterrupt; receipts retained, no automatic rerun")
    except Exception as error:
        result = 1
        report.update(status="FAIL", error=f"{type(error).__name__}: {error}")
    report["ended_at_utc"] = utc()
    report["replay_exit_code"] = result
    write_json(output / "report.json", report)
    print(json.dumps({
        "status": report["status"], "exit_code": result, "test": report.get("test"),
        "report": str(output / "report.json"), "production": report["production"],
    }, ensure_ascii=False))
    if "error" in report:
        print(report["error"], file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
