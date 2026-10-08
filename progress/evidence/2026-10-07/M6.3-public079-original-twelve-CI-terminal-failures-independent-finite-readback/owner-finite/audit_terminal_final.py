"""One bounded local read of the root collector; no fetch, watcher or CI action."""
from pathlib import Path
import hashlib
import json
import re
import sys

SOURCE = Path('$HOME/.cache/learning-workbench-acceptance/m63-ci-public079a008-observation-oct07')
OUTPUT = Path(__file__).parent
MERGE = Path('$HOME/.cache/learning-workbench-acceptance/m63-public079-pr-merge-source-readback-oct07/READBACK.json')
PUBLIC = '079a008cf88b37e4517cb391503a1e7393ccf374'
CHECKOUT = 'e9eb82d41dd87649be6c8090c35b5052ccb1319c'
EXPECTED = {
    37632652743: {112830648507: 'backend', 112830648805: 'integration', 112830648865: 'frontend',
                 112830648905: 'spec-contracts', 112830649006: 'security-publication', 112830649019: 'browser'},
    37632662238: {112830674580: 'spec-contracts', 112830674741: 'integration', 112830674820: 'security-publication',
                 112830674842: 'frontend', 112830674907: 'backend', 112830674946: 'browser'},
}
COMMANDS = {
    'npm ci --prefix apps/web', 'python -m pip install uv==0.11.21', 'uv sync --frozen',
    'uv run --frozen pytest tests/contract tests/unit/test_spec_*.py', 'make verify-spec',
    'npm --prefix apps/web run lint', 'npm --prefix apps/web run typecheck',
    'npm --prefix apps/web run test', 'make build', 'make test-e2e',
    'uv run --frozen ruff check .', 'uv run --frozen mypy',
    'uv run --frozen python scripts/probe_document_sandbox.py',
    'uv run --frozen pytest tests/unit tests/security', 'uv run --frozen pytest tests/integration',
    'python scripts/check_publication.py --all-tracked',
    'npm --prefix apps/web exec -- playwright install --with-deps chromium',
}
KNOWN_SAFE = {
    'E       assert 503 == 202', 'tests/integration/test_codex_turn_consent_http.py:91: AssertionError',
    'FAILED tests/integration/test_codex_artifact_repair_boundaries.py::test_forward_guards_preserve_existing_source_rows_rowids_and_original_http_acks - assert 503 == 202',
    "Error: Test timeout of 30000ms exceeded",
    "> 147 |   await expect.poll(() => new URL(page.url()).searchParams.has('reader')).toBe(true)",
    'at $RUNNER_HOME/work/Learning_Workbench/Learning_Workbench/tests/e2e/review.spec.ts:147:75',
    '1) ../../tests/e2e/review.spec.ts:36:1 › real history and exact material review preserve original submitted text, null scores and a selected old revision after reload',
    '../../tests/e2e/review.spec.ts:36:1 › real history and exact material review preserve original submitted text, null scores and a selected old revision after reload',
    'SKIPPED [1] tests/integration/test_authoring_numeric_runtime.py:46: BLOCKED_ENVIRONMENT: real sealed runtime did not execute the calculator; original FAIL retained',
    'SKIPPED [1] tests/integration/test_restore_numeric_actual_runtime.py:42: BLOCKED_ENVIRONMENT: actual sealed Restore evaluator did not return a numeric PASS; no fallback',
    'All checks passed!', 'Success: no issues found in 295 source files',
    'PASS: scanned 23175 staged/tracked files against path and credential rules. Manual provenance review remains required.',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def normalize(line):
    text = re.sub(r'^\d{4}-\d\d-\d\dT\S+\s*', '', line)
    return re.sub(r'\x1b\[[0-9;]*m', '', text).strip()


def safe_lines(lines):
    kept = []
    for number, line in enumerate(lines, 1):
        text = normalize(line)
        category = None
        if text in (PUBLIC, CHECKOUT):
            category = 'checkout_identity'
        elif text.startswith('##[group]Run ') and text.removeprefix('##[group]Run ') in COMMANDS:
            category = 'original_ci_command'
        elif re.fullmatch(r'(?:node: v\d+\.\d+\.\d+|npm: \d+\.\d+\.\d+|platform linux -- Python \d+\.\d+\.\d+, pytest-[\d.]+, pluggy-[\d.]+)', text):
            category = 'tool_version'
        elif re.fullmatch(r'collected \d+ items|Running \d+ tests using \d+ workers?|Test Files\s+\d+ passed \(\d+\)|Tests\s+\d+ passed \(\d+\)|=+ \d+ (?:passed|failed)[^=]* =+|\d+ (?:failed|passed|skipped)(?: \([\d.msh]+\))?', text):
            category = 'original_footer'
        elif re.fullmatch(r'##\[error\]Process completed with exit code \d+\.', text):
            category = 'original_step_exit'
        elif text in KNOWN_SAFE:
            category = 'reviewed_safe_failure_env_or_static_context'
        else:
            # Future completed logs may have different failed IDs. Admit only the
            # bare repository test identifier, never its fixture repr or suffix.
            match = re.match(r'^FAILED (tests/integration/[A-Za-z0-9_/]+\.py::[A-Za-z0-9_]+)', text)
            if match:
                text = 'FAILED ' + match[1]
                category = 'bare_failed_test_identifier_only'
        if category:
            kept.append({'line': number, 'category': category, 'text': text})
    return kept


def run(stage):
    assert stage in ('11', 'final')
    snapshots = sorted((f for f in SOURCE.glob('*-SNAPSHOT.json') if f.name.split('-')[0].isdigit()), key=lambda f: int(f.name.split('-')[0]))
    snap_path = snapshots[-1]
    snap_raw = snap_path.read_bytes()
    snapshot = json.loads(snap_raw)
    assert snapshot['source'] == PUBLIC and snapshot['actual_event_count'] == 2
    assert {event['id'] for event in snapshot['actual_events']} == set(EXPECTED)
    merge_raw = MERGE.read_bytes()
    merge = json.loads(merge_raw)
    assert merge['actual_fixed_PR_checkout'] == CHECKOUT and merge['public_head'] == PUBLIC
    assert merge['whole_git_tree_equal'] and merge['whole_entry_count'] == 23175
    assert merge['public_tree'] == merge['PR_merge_tree'] == 'eea569fec4f6b3fd209ed96eb29e6d052f0e9b1e'
    records, events = [], []
    for event in snapshot['actual_events']:
        assert event['head_sha'] == PUBLIC and event['run_attempt'] == 1
        assert {job['id']: job['name'] for job in event['jobs']} == EXPECTED[event['id']]
        events.append({key: event[key] for key in ('id', 'event', 'head_sha', 'status', 'conclusion', 'run_attempt')})
        for job in event['jobs']:
            record = {key: job[key] for key in ('id', 'name', 'status', 'conclusion', 'started_at', 'completed_at')}
            record.update(run_id=event['id'], event=event['event'], run_attempt=1)
            if job['status'] != 'completed':
                record.update(original_complete_log='NOT_YET_CAPTURED', independent_read='NOT_RUN')
                records.append(record)
                continue
            stem = f"job-{job['id']}-logs-01"
            raw = (SOURCE / (stem + '.stdout')).read_bytes()
            stderr = (SOURCE / (stem + '.stderr')).read_bytes()
            receipt_raw = (SOURCE / (stem + '-receipt.json')).read_bytes()
            command_raw = (SOURCE / (stem + '-command.json')).read_bytes()
            receipt, command = json.loads(receipt_raw), json.loads(command_raw)
            assert receipt['status'] == 'ACTUAL_COMPLETE_JOB_LOG_CAPTURED' and receipt['exit_code'] == 0
            assert receipt['stdout_sha256'] == digest(raw) and receipt['stdout_bytes'] == len(raw)
            assert receipt['stderr_sha256'] == digest(stderr) and receipt['stderr_bytes'] == len(stderr) == 0
            assert receipt['run_id'] == event['id'] and receipt['job_id'] == job['id']
            assert command['run_attempt'] == 1 and command['job']['conclusion'] == job['conclusion']
            assert command['argv'] == ['gh', 'api', f"repos/kl3574/Learning_Workbench/actions/jobs/{job['id']}/logs"]
            lines = raw.decode('utf-8').splitlines()
            excerpt = safe_lines(lines)
            wanted_checkout = PUBLIC if event['event'] == 'push' else CHECKOUT
            assert any(item['text'] == wanted_checkout for item in excerpt)
            footers = [item for item in excerpt if item['category'] == 'original_footer']
            failed_ids = sorted({item['text'].split(' - ')[0].removeprefix('FAILED ') for item in excerpt if item['text'].startswith('FAILED tests/')})
            record.update(original_complete_log='HASH_MATCHED_ROOT_CAPTURE', independent_read='COMPLETE_ORIGINAL_BYTES_AND_RELEVANT_FOOTERS_READ',
                          original_file=stem + '.stdout', original_bytes=len(raw), original_sha256=digest(raw), original_lines=len(lines),
                          collector_command_sha256=digest(command_raw), collector_receipt_sha256=digest(receipt_raw),
                          actual_checkout=wanted_checkout, safe_excerpt=excerpt, footer_line_count=len(footers), failed_test_identifiers=failed_ids,
                          raw_api_payload_and_fixture_exported=False, ci_working_before='NOT_CAPTURED', ci_working_after='NOT_CAPTURED')
            records.append(record)
    complete = sum(record['independent_read'] != 'NOT_RUN' for record in records)
    if stage == '11':
        assert complete == 11
    else:
        assert complete == 12 and all(event['status'] == 'completed' for event in events)
    result = {
        'scope': 'Original079 attempt1 events only; local read of sole root producer captures; counts never added across events or jobs',
        'status': 'ELEVEN_COMPLETE_JOB_READBACK_WITH_ONE_PENDING' if stage == '11' else 'ALL_TWELVE_ORIGINAL_JOB_AND_TWO_EVENT_TERMINALS_READ',
        'source_snapshot': snap_path.name, 'snapshot_sha256': digest(snap_raw), 'snapshot_observed_utc': snapshot['observed_utc'],
        'events': events, 'jobs': records, 'readback_job_count': complete,
        'original_root_merge_readback': {'filename': str(MERGE), 'sha256': digest(merge_raw), 'actual_fixed_PR_checkout': CHECKOUT,
                                         'public_head': PUBLIC, 'tree': merge['public_tree'], 'entries': 23175,
                                         'method': 'Read existing root exact current079 receipt; no fresh Git fetch or older tree borrowed'},
        'ci_working_before': 'NOT_CAPTURED', 'ci_working_after': 'NOT_CAPTURED',
        'whole_M6_3': 'NOT_ACCEPTED', 'new_ci_or_local_product_tests': 'NOT_RUN', 'actual_model_execution': 'NOT_RUN',
        'actions': {'new_fetch': False, 'new_watcher': False, 'retry_dispatch_cancel': False, 'tree_modified': False},
        'publication_allowlist': ['explicit original command/version/footer lines with physical line numbers',
                                  'reviewed safe failed assertion and test location', 'named ENV skip reasons',
                                  'raw-log byte/hash metadata and projected job/event identity'],
        'publication_excluded': ['AUTH Case repr', 'fixture bodies', 'raw API payloads', 'database/archive/image/profile content',
                                 'unselected arbitrary raw log lines', 'older CI evidence', '90c8 or later patch results'],
    }
    destination = OUTPUT / ('11-COMPLETED-READBACK.json' if stage == '11' else 'FINAL-READBACK.json')
    assert not destination.exists()
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'stage': stage, 'snapshot': snap_path.name, 'jobs_read': complete, 'output': str(destination),
                      'sha256': digest(destination.read_bytes()), 'source_sha': PUBLIC}, sort_keys=True))


if __name__ == '__main__':
    run(sys.argv[1])
