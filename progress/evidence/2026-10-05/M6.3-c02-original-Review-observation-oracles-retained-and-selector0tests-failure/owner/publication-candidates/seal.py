"""Seal only named source/metadata. Never read native screenshots or body files."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

base = Path(__file__).parent
root = Path('$HOME/.cache/learning-workbench-acceptance/m63-review-history-timing-oct05')
before_head = '35aebd3039241abb3393300affd593f4826a4a0c'
head = 'c02e9e5c73d7da5e8e1617731fbefdf94f44f0e8'
owned = 'tests/e2e/review.spec.ts'
seal = base / 'seal-c02e'
seal.mkdir(mode=0o700)
candidate = seal / 'publication-candidates'
candidate.mkdir(mode=0o700)
sha = lambda value: hashlib.sha256(value).hexdigest()
def write(path, value):
    with path.open('x') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == head
assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True) == ''
assert subprocess.check_output(['git', 'diff', '--name-only', before_head, head], cwd=root, text=True).splitlines() == [owned]
maps = {}
all_blobs = set()
for commit in (before_head, head):
    files = {}
    for row in subprocess.check_output(['git', 'ls-tree', '-rz', commit], cwd=root).split(b'\0'):
        if not row:
            continue
        meta, name = row.decode().split('\t')
        if name.startswith('progress/'):
            continue
        mode, kind, oid = meta.split()
        payload = subprocess.check_output(['git', 'cat-file', 'blob', oid], cwd=root)
        if commit == head:
            assert (root / name).read_bytes() == payload
        all_blobs.add(oid)
        files[name] = dict(mode=mode, type=kind, git_blob=oid, bytes=len(payload), sha256=sha(payload))
    assert len(files) == 1524
    maps[commit] = files
    write(base / ('git-' + commit[:8] + '.json'), dict(head=commit, count=len(files), files=files))
assert [name for name in maps[head] if maps[head][name] != maps[before_head][name]] == [owned]
assert maps[head]['PRODUCT_DESIGN.md']['sha256'] == 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
fixed_copy = base / 'fixed-review.spec.ts'
with fixed_copy.open('xb') as output:
    output.write((root / owned).read_bytes())
with (base / 'source.patch').open('xb') as output:
    output.write(subprocess.check_output(['git', 'diff', '--binary', before_head, head, '--', owned], cwd=root))
stages = ['wip-observation-bytes', 'wip-strict', 'wip-official-types', 'fixed-observation-bytes',
          'fixed-official-types', 'fixed-diff', 'fixed-first-list']
source_bindings = []
for stage in [*stages, 'native-run-01', 'native-run-02']:
    first = json.loads((base / stage / 'before.json').read_text())
    last = json.loads((base / stage / 'after.json').read_text())
    assert first == last and first['count'] == 1524
    for name, meta in first['files'].items():
        assert meta['sha256'] == maps[head][name]['sha256'] and meta['bytes'] == maps[head][name]['bytes']
    source_bindings.append(dict(stage=stage, head=first['head'], before_after_equal=True,
        source_state='WIP exact final working bytes; original Git-head blob metadata retained' if stage.startswith('wip-') else 'fixed clean c02e',
        count=1524, before_sha256=sha((base / stage / 'before.json').read_bytes()), after_sha256=sha((base / stage / 'after.json').read_bytes())))
write(base / 'SOURCE_BINDINGS.json', dict(parent=before_head, fixed=head, owned_paths=[owned],
    head_count=2, complete_head_bindings=3048, stage_maps=18, stage_bindings=27432, stages=source_bindings,
    qualification='WIP stages name original HEAD35ae plus dirty status and actual final bytes. They are not falsely described as clean35ae runs. All fixed stages bind c02e. Only one original source file differs.'))
report = '''# Bounded Review history timing instrumentation

Fixed source c02e9e5c73d7da5e8e1617731fbefdf94f44f0e8; parent35aebd3039241abb3393300affd593f4826a4a0c. Sole PRODUCT_DESIGN v3.0.15 SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. Scope follows original AC-13/R-14/R-20 Review coverage plus evidence discipline; no new product contract.

Only tests/e2e/review.spec.ts changes. All added runtime observation is inside the first historical Review case. It records body-relative monotonic stages and browser request/response-header/finished/failed metadata using static route templates and numeric status/times. No query, raw ID, token, header, request/response body, DOM, console text or failure error text is collected by this observer. Its caps are128 phase rows/512 HTTP rows, with explicit dropped counts. The bounded file is written once with wx in finally; failed diagnostic persistence produces a fixed annotation while preserving the original assertion error. A killed worker before finally remains a possible missing-diagnostic boundary.

The observer adds synchronous CPU/memory work and the final disk write. Measurement can change scheduling; it is not zero-overhead or a synchronization barrier. No new await, sleep, route handler, polling, timeout, retry or request is introduced. Browser events do not observe page.request helper polling, fixture/bootstrap time, JSON consumption, React scheduling or all network/OS behavior. Existing test payload reads/assertions remain unchanged; they are not copied into the new diagnostic. The original case still begins atline36.

The byte proof removes only explicitly added observation text and recovers all original first-case statements exactly and in order, including every locator/assertion/oracle. Everything before the first case and the entire second delayed-response case remains byte-exact. The original30000ms total/worker1/defaultretry0/config and helper files are unchanged. No production, dependency, spec or server configuration file changed; no canonical write, merge, push or CI execution occurred.

## Actual execution

- WIP direct strict command exited1 because relative @playwright/test/index.mjs imports lack declaration resolution in that invocation (TS7016 and dependent implicit-any diagnostics). Original full log/source maps remain. The subsequent private declaration mapping points only to the installed official Playwright types, using the existing reviewed22eb pattern; it introduces no any or product/dependency change.
- Fixed observation-byte proof, focused official-type strict check and git diff check each exit0, with full1524 input maps before/after. Static file:36 --list exit0 selected exactly1 first case; the second case was not selected.
- Native-run-01 used an incorrectly anchored bare-title grep and exited1/No tests found. It executed0 tests; business case/timing NOT_RUN. Its raw command/log/receipt/maps remain untouched. This is a selector error, not a product failure. Root then explicitly authorized the first actual case via the already-listed file:line selector.
- Native-run-02 ran `bash scripts/node.sh npm --prefix apps/web run test:e2e -- review.spec.ts:36` once under the unchanged original config after root's previous suite released8765/5173. Test1PASS15.4s; Playwright total18.3s; command/wrapper0. UTC2026-10-04T20:11:12.595022Z to20:11:31.290659Z; wrapper18.695523884991417s. Raw log SHAd8d1faaabf0e9f7da7be1187f05f89147756909da72f84b6c8905ab595ae7e3f. No retry or later repeat was performed. NO_COLOR warnings remain in original logs.

The new timing file is65459bytes, SHA26dd74a9a9e50c2f44e3dd267224228e171d69668bf27817ba2aa103a248a4ba. It contains43 phase rows and298 HTTP event rows, dropped0/0, observed_timeout_ms30000/retry0. Body-finally is13.109398223s from the observer start, excluding fixture preparation. The Review tab return begins12.0013s, click resolves12.0247s, and the next original mobile-screenshot statement starts12.8222s. This is elapsed observation of the actual local path, not an attribution of that interval to a particular process or subsystem.

The recorded result GET response headers include6x200 and2x202; other metadata includes an Import GET403 and Workbench save412. No body was inspected by this observer, so these codes alone are not assigned a product cause. The original test's full unchanged assertions passed. TIMING_READBACK.json gives exact stage times and static-route status groups. HTTP-header/finished events do not prove downstream JSON/React completion.

## Limits and prior CI failures

Only the CI owner's explicitly approved6-file handoff and its hash-bound allowlist were read. Its two original full-suite events each remain132PASS/1FAIL at the first Review total30000ms, with different final locator/DOM observations; the second delayed case passed. Original PNG/DOM simultaneity was not established. Their unique root cause remains UNKNOWN. This local1PASS is diagnostic coverage, not a CI fix, reproducibility proof, whole-suite PASS or evidence that observer overhead has no effect. No root prior full-suite PASS is borrowed. Actual model/Provider/Codex CLI/host-tool execution is NOT_RUN; no new execution sentinel or global monitoring claim is made.

All1524 current engineering inputs are byte-equal to fixed Git;1523 nonowned original inputs are unchanged. Two complete Git-head maps/3048bindings and9 run stages/18maps/27432bindings were reread. WIP maps honestly retain HEAD35ae/dirty status with final working bytes, rather than falsely calling them clean35ae gates. Fixed/native maps are cleanc02e.

Only exact SAFE_CANDIDATES.json entries are proposed for sharing, without byte transformations. New timing/summary, bounded ordinary command logs, source, static receipts and complete Git maps are candidates. All native screenshots, original actual-review-history.json business output, DB/profile/cookie/key/cache, temporary application data and any unspecified runtime output remain private and are not read or admitted. Existing22dade native seal and all earlier failures remain unchanged. No source was merged/pushed; independent review is pending.
'''
with (base / 'REPORT.md').open('x') as output:
    output.write(report)
timing_name = 'native-run-02/results/review-real-history-and-ex-756c0-d-old-revision-after-reload/review-history-timing.json'
names = ['REPORT.md', 'seal.py', 'SOURCE_BINDINGS.json', 'base-inputs.json', 'git-' + before_head[:8] + '.json', 'git-' + head[:8] + '.json',
    'original-review.spec.ts', 'fixed-review.spec.ts', 'source.patch', 'check_observation_only.py', 'run_gate.py',
    'run_native.py', 'run_native02.py', 'playwright-official-types.d.ts', 'focused-types.json', 'NATIVE_PLAN.json',
    'CI_HANDOFF_BINDING.json', 'TIMING_READBACK.json', timing_name]
for stage in stages:
    names += [stage + '/' + name for name in ['before.json', 'after.json', 'command.json', 'receipt.json', 'output.log']]
for stage in ['native-run-01', 'native-run-02']:
    names += [stage + '/' + name for name in ['before.json', 'after.json', 'command.json', 'run-receipt.json', 'output.log']]
assert len(names) == len(set(names))
candidates = []
for name in names:
    source = base / name
    payload = source.read_bytes()
    destination = candidate / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as output:
        output.write(payload)
    assert destination.read_bytes() == payload
    candidates.append(dict(candidate_path=name, raw_path=str(source), sha256=sha(payload), bytes=len(payload), transformation='none'))
write(seal / 'SAFE_CANDIDATES.json', dict(version=1, candidate_base=str(candidate), source=head, files=candidates,
    excluded='Everything not named: all screenshots, actual-review-history business JSON, DB/profile/auth/key/cache/private runtime are excluded.'))
write(seal / 'READBACK.json', dict(source=head, parent=before_head, checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    candidate_count=len(candidates), engineering_inputs=1524, unchanged_nonowned_original_inputs=1523,
    head_maps=2, complete_head_bindings=3048, distinct_git_blobs=len(all_blobs), stage_maps=18, stage_bindings=27432,
    all_current_files_match_fixed_git=True, clean=True, screenshot_candidates=0,
    native_run01='SELECTOR_FAIL_0_TESTS_PRODUCT_NOT_RUN', native_run02='FIRST_ACTUAL_CASE_1_PASS_ONCE', unique_CI_root_cause='UNKNOWN'))
print(json.dumps(dict(seal=str(seal), candidates=len(candidates), distinct_git_blobs=len(all_blobs),
    outer_sha256={name: sha((seal / name).read_bytes()) for name in ['SAFE_CANDIDATES.json', 'READBACK.json']},
    report_sha256=sha((base / 'REPORT.md').read_bytes())), indent=2))
