#!/bin/bash
set -u
cd <LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-turn-interrupt-owner-oct04
export TMPDIR=<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-turn-interrupt-evidence-oct04/dev-01/tmp
uv run --frozen --no-sync pytest tests/integration/test_codex_turn_interrupt_http.py --basetemp="$TMPDIR/base" -o cache_dir="$TMPDIR/cache" --tb=short > <LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-turn-interrupt-evidence-oct04/dev-01/run.log 2>&1
result=$?
printf '%s\n' "$result" > <LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-turn-interrupt-evidence-oct04/dev-01/exit.txt
exit "$result"
