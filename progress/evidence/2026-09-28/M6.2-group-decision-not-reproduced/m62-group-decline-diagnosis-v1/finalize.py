import hashlib
import json
import subprocess
from pathlib import Path

OUT = Path(__file__).parent
ROOT = OUT.parent / 'm62-group-decline-diagnosis-active'
RAW = OUT.parent / 'm62-sep28-native-gate-v1'
HEAD = '1fffd996e9334f7f28dcdeb970430c9aa4052ee3'
SPEC = '2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d'
def sha(b): return hashlib.sha256(b).hexdigest()
def write(path, value): (OUT / path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)

assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert sha((ROOT / 'PRODUCT_DESIGN.md').read_bytes()) == SPEC
manifest = json.loads((RAW / 'manifest.json').read_text())
assert sha((RAW / 'manifest.json').read_bytes()) == '3f3cd288aa5f9ee6a3c391f65ceae080df044e063c27f0785b64a254e1e23fc8'
for member in manifest['files']:
    data = (RAW / member['path']).read_bytes()
    assert len(data) == member['bytes'] and sha(data) == member['sha256']
failure = 'artifacts/authoring-groups-native-le-f0866-es-one-exact-numeric-member/error-context.md'
(OUT / 'original-failure-context.md').write_bytes((RAW / failure).read_bytes())
binding = json.loads((OUT / 'source-native-binding.json').read_text())
binding['actual_failure'] = 'source254 page.waitForResponse did not observe matching decline POST response within10000ms; absence of the request itself is not proven'
binding['raw_members_reverified'] = len(manifest['files'])
write('source-native-binding.json', binding)

stage = OUT / 'native-once'
receipt = json.loads((stage / 'receipt.json').read_text())
assert receipt['exit_code'] == 0 and receipt['before_after_unchanged']
assert b'1 passed (13.0s)' in (stage / 'run.log').read_bytes()
assert sha((stage / 'run.log').read_bytes()) == receipt['log_sha256']
data = json.loads((stage / 'mechanism.json').read_text())
rows = data['rows']; assert data['omitted'] == 0 and len(rows) == 154
events = [(i, r) for i, r in enumerate(rows) if r['kind'] == 'browser' and r['stage'] in ['pointerdown', 'pointerup', 'click']]
assert [r['stage'] for _, r in events] == ['pointerdown', 'pointerup', 'click']
assert all(r['trusted'] and r['selected_state'] == 'pending' and not r['decline_disabled'] and r['button_in_view'] for _, r in events)
decisions = [(i, r) for i, r in enumerate(rows) if r['kind'] == 'request' and r['method'] == 'POST' and '/group-numeric-checks/' in r['path'] and r['path'].endswith('/decision')]
assert len(decisions) == 2
joined = []
for index, request in decisions:
    response = [(i, r) for i, r in enumerate(rows) if r['kind'] == 'response' and r['id'] == request['id']]
    finish = [(i, r) for i, r in enumerate(rows) if r['kind'] == 'finished' and r['id'] == request['id']]
    assert len(response) == 1 and len(finish) == 1 and index < response[0][0] < finish[0][0]
    joined.append({'request_index': index, 'request': request, 'response_index': response[0][0], 'response': response[0][1], 'finished_index': finish[0][0], 'finished': finish[0][1], 'node_observed_request_to_response_ms': response[0][1]['delivered_ms'] - request['delivered_ms']})
assert [v['response']['status'] for v in joined] == [200, 202]
write('mechanism-readback.json', {'classification': 'ORIGINAL_FAILURE_NOT_REPRODUCED', 'root_cause': 'UNKNOWN', 'rows': len(rows), 'omitted': data['omitted'], 'click_events': [{'index': i, 'event': r} for i, r in events], 'decision_request_joins': joined, 'pageerrors': [r for r in rows if r['kind'] == 'pageerror'], 'request_failures_in_observed_scope': [r for r in rows if r['kind'] == 'failed'], 'timing_scope': 'Only same Node observation clock request/response intervals are derived. No browser-clock/Node-clock deadline claim. Observation covers only declared authoring/session paths and is from the later isolated run.'})

# Restore only the known, preserved diagnostic entry points; record raw before and
# the separate restored source state, never claim the process had no mutation.
changed = git('diff', '--name-only').decode().splitlines()
assert changed == ['tests/e2e/authoringRuntime.ts']
runtime = ROOT / changed[0]
assert runtime.read_bytes() == (stage / 'source' / changed[0]).read_bytes()
base_runtime = git('show', HEAD + ':' + changed[0])
runtime.write_bytes(base_runtime)
assert git('status', '--porcelain').decode() == ''
names = git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0')
after = {name: {'sha256': sha((ROOT / name).read_bytes()), 'bytes': (ROOT / name).stat().st_size} for name in sorted(set(names)) if name and not name.startswith('progress/') and (ROOT / name).is_file()}
write('inputs-after-instrumentation-removal.json', after)
before = json.loads((stage / 'inputs-before.json').read_text())
assert [name for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)] == ['tests/e2e/authoringRuntime.ts']
write('cleanup.json', {'head': HEAD, 'changed_during_setup': ['tests/e2e/authoringRuntime.ts'], 'during_actual_run_inputs_unchanged': True, 'restored_exact_base_paths': ['tests/e2e/authoringRuntime.ts'], 'status_porcelain': '', 'private_diagnostic_files_retained': True, 'product_changes': [], 'fixed_ports_used': False})

report = '''# Group numeric decline diagnostic receipt

The original combined native gate remains FAIL (92 passed / 9 failed). Its
authoring-groups.spec.ts:235 case failed at source254: the 10-second response
waiter did not observe the exact decline decision response. The retained
original error context does not establish that no POST was sent. Root cause:
UNKNOWN. No product repair is claimed.

The authorized single targeted execution of the unchanged original case passed
(case12.7s, Playwright13.0s, wrapper13.326481820s), exit0. The probe records154
metadata events, zero omitted: one trusted decline pointerdown/up/click with an
enabled pending button in view, exact decision request18 / response200 / finish;
the separate later approval request25 / response202 / finish. The original test
checks the original ACK, independent stored decline readback and later numeric
execution, and these assertions remain unmodified. This later PASS is not an
explanation or closure of the original failure.

Four code-grounded hypotheses were kept falsifiable: (1) actionability/scroll
prevented click delivery; (2) ready/busy/pending-command guards rejected the
operation; (3) local persistence prevented dispatch; (4) request/response failed
at the network boundary. None explains a reproduced failure, because this run
did not reproduce it. The observed run progresses beyond every boundary;
historical alternatives remain unresolved. No fabricated focused RED or
speculative product change was added.

Scope: fixed1fffd996e9334f7f28dcdeb970430c9aa4052ee3, unchanged original test,
three diagnostic-only runtime lines importing a private metadata observer.
The private config omits the unrelated global web servers; the original test's
own AuthoringRuntime uses dynamic API/UI ports. Original120s case timeout,
10s actions/responses, 5s assertions and retry0 remain. The981 actual engineering
inputs were identical before/after execution, including the disclosed observer
entry points. Only those entry points were then restored byte-exact to HEAD;
the separate after-removal snapshot and clean status are recorded. No main tree
or fixed8765/5173 service was touched.

Two preceding harness errors are retained: ESM config-load exit1, then anchored
grep selection exit1 (No tests found). Both executed zero cases and are neither
product RED nor PASS. A corrected --list returned exactly the source235 case
before the sole execution. Original native190-member manifest was reverified
without modifying any member. Screenshots and local synthetic fixture evidence
are private; this package has not been published or publication-scanned.

Next: preserve UNKNOWN for this failure. Further diagnosis needs an observed
failure with the same bounded click/request/persistence boundary evidence under
the relevant scheduling conditions; do not infer a cause from this isolated
PASS, rerun the full suite for green, or relax deadlines. No further browser run
is performed in this task. Real provider, human content approval and release:
NOT_RUN.
'''
(OUT / 'REPORT.md').write_text(report)
write('TASK_RECEIPT.json', {'task_id': 'M6.2-native-authoring-group-decline-diagnosis', 'requirement_ids': ['R-21', 'R-22', 'R-24', 'R-27', 'R-29'], 'spec_sha256': SPEC, 'implementation_commit': None, 'source_commit': HEAD, 'changed_paths': [], 'diagnostic_setup_paths': ['tests/e2e/authoringRuntime.ts'], 'commands': [json.loads((OUT / name / 'receipt.json').read_text())['command'] for name in ['native-config-error-v1', 'native-selection-error-v1', 'native-once']], 'exit_codes': [1, 1, 0], 'test_summary': {'original_native_gate': 'FAIL 92 passed 9 failed', 'harness_errors': '2, zero cases executed', 'targeted_original_case': 'PASS once 13.0s; not original failure closure', 'root_cause': 'UNKNOWN', 'focused_RED_reproduction': 'NOT_REPRODUCED', 'product_fix': 'NOT_IMPLEMENTED_NO_CONFIRMED_CAUSE'}, 'screenshot_paths': [p.relative_to(OUT).as_posix() for p in sorted(stage.rglob('*.png'))], 'migrations': 'none', 'security_review': 'Private bounded metadata only; observer does not record headers, cookies, bodies or private text. Fixture uses original controlled loopback provider. No real vendor or user key accessed. Not publication-scanned; retain private.', 'not_run': ['additional native runs', 'full suite', 'real provider', 'human content approval', 'publication', 'new static checks because no product code changed'], 'blockers': ['Original failure lacks click/request ledger; the single targeted execution did not reproduce it.'], 'next_task_id': 'M6.2-preserve-decline-UNKNOWN-until-observed-failure', 'evidence': ['source-native-binding.json', 'original-failure-context.md', 'native-once/receipt.json', 'native-once/mechanism.json', 'mechanism-readback.json', 'cleanup.json', 'inputs-after-instrumentation-removal.json']})
members = [{'path': p.relative_to(OUT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'manifest.json']
write('manifest.json', {'head': HEAD, 'scope': 'Private diagnostic receipt; original failure remains UNKNOWN', 'files': members})
print(json.dumps({'files': len(members), 'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()), 'product_changes': 0, 'root_cause': 'UNKNOWN'}))
