"""Read-only source/candidate verification and new private sealed text copies."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

base = Path(__file__).parent
tree = Path('$HOME/.cache/learning-workbench-acceptance/m63-session-interrupt-ui-oct05')
head = '22dade7996f13634202250ef5e1c05dc976214a5'
seal = base / 'seal-22dade'
seal.mkdir(mode=0o700)
target = seal / 'publication-candidates'
target.mkdir(mode=0o700)
sha = lambda data: hashlib.sha256(data).hexdigest()
def write(path, value):
    assert not path.exists()
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
first_script_hashes = {'native.mjs': '3c6d7ecfd59888ac6c3618515a37c2fd8056a40793e204636e6b5540ce9a290a',
    'controlled_api.py': '7e2204275d9e1a1ccc75acd19aefdd768432a82b8c519b747ce22368cc524f69',
    'run.py': 'ff62ca669d545de3997283ae56298066039c8feba9ce01344bf1bdfb63ad0436'}
for name, digest in first_script_hashes.items():
    assert sha((base / 'run-01' / name).read_bytes()) == digest
loss = {
 'status': 'ORIGINAL_FIRST_DYNAMIC_RAW_LOST_NO_RECONSTRUCTION',
 'first_attempt': {'started_utc': '2026-10-04T19:43:29.226773+00:00', 'ended_utc': '2026-10-04T19:43:36.920849+00:00', 'exit': 1,
   'native_started_utc': '2026-10-04T19:43:29.964120+00:00', 'native_ended_utc': '2026-10-04T19:43:36.790436+00:00',
   'native_log_sha256_from_original_tool_output': 'e0fd9fbe7404227caee7e3944fc3286b9720477ceefd41bbdf0cc4a9089f9fc0',
   'build_log_sha256_from_original_tool_output': '40f0b328b6ab613bb2835aaf93294e838f71425090bff1f0f9d035ee07538e36',
   'dynamic_files_retained': False, 'browser_started': False, 'product_verification': 'NOT_RUN',
   'sentinels': 'NOT_AVAILABLE_STARTUP_NOT_REACHED'},
 'accidental_second_attempt_in_run01': json.loads((base / 'run-01/run-receipt.json').read_text()),
 'loss': 'After creating run-02 scripts, the author accidentally invoked python run.py from the old run-01 cwd. Old dynamic command/log/receipt/failure files were overwritten by a second same-script failure. Original script bytes remain exact; the original dynamic raw files are lost. The first failure/error and receipt had appeared in earlier tool output. No reconstruction or false raw-retention claim is made.',
 'same_original_script_hashes': first_script_hashes,
 'source_maps': 'Current accidental-run01 maps and run02 maps fully match the fixed1525 inputs. The first runner reached its before/after equality and printed its receipt, but its original snapshot files were overwritten; do not claim separately retained first-run snapshots.',
 'second_run01_browser_started': False, 'second_run01_product_verification': 'NOT_RUN',
 'second_run01_sentinels': 'NOT_AVAILABLE_STARTUP_NOT_REACHED',
 'run02': 'A fresh unique directory contained only the three new scripts before execution. The actual runner refuses preexisting command.json/run-receipt.json/native.log/build.log. Root later requested failure.json/receipt.json too, after run02 was already complete; those extra guards are not falsely attributed to the recorded script. Any future run must refuse all six and use an absolute script path.',
 'run02_command': ['python', str(base / 'run-02/run.py')],
}
write(base / 'LOSS_V2.json', loss)
report = '''# Session interrupt UI: bounded actual Chrome verification

Source is fixed 22dade7996f13634202250ef5e1c05dc976214a5, sole PRODUCT_DESIGN v3.0.15 SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. No product, spec, dependency, tracked output or canonical file was edited, staged or committed. The Vite output is in the separate private harness directory.

## Actual successful run

run-02 started 2026-10-04T19:44:59.205906Z and finished 19:45:07.478729Z. Build exit0; native exit0 in7.543486384s; wrapper exit0. Native log SHA78d183295b68aa7076bb6cde05821bb24301f979bcea07d423ffef0f2d860241. The original bounded assertions used15000ms unchanged from the reviewed reference. Browser version154.0.8037.97. Build retains external-outDir and large-chunk warnings.

The unchanged source was served through actual loopback Uvicorn, original app lifespan, SQLite owners and real Chrome IndexedDB. Existing pure-memory ControlledRuntime performs one explicitly synthetic bootstrap. The ordinary provider config contains example.invalid/synthetic-model and no provider secret. Two real preparations return unavailable proof/awaiting_approval; no Provider grant/start exists and the default Codex executor stays None.

The learner explicitly reads current session and safe turn control. The first UI POST is intercepted only after the complete original actor/workspace/key/body/session+turn basis is in IndexedDB, then sent once to the real owner. Its real200 interrupt_requested ACK is deliberately lost. The actual turn is cancelled/terminal, started_at null, cancel_requested true. Reload and explicit local reads send zero automatic POST. Explicit original-key replay sends byte-identical body and receives byte-identical full original ACK, which is saved durably. Independent current GET shows the released session/cancelled turn without replacing the ACK.

A second actual awaiting preparation produces a fresh session revision. An explicit competing HTTP interrupt advances it before the UI sends its saved basis. The UI receives real412, keeps the original actor/key/full body/basis/error, preserves it through a reload/current GET, and explicit same-key replay remains412. Switching to a separately issued learner actor leaves both records intact and disables the old unknown command replay. Four browser UI interrupt POSTs plus one explicitly separate fixture competing interrupt POST are asserted. No other browser POST is asserted; fixture bootstrap/config/role/prepare writes are separate setup actions, not omitted from the boundary.

Four named application seam sentinels (SyntheticCodexExecutor.execute, ProviderTransport.stream, CodexOperationRegistry.execute, subsequent ControlledRuntime.execute) are all0. Synthetic bootstrap count1; executorNone. Terminal sentinel phase is lifespan-exited. The harness awaited Chrome close and the owned Uvicorn shutdown. These are scoped application-seam observations, not a global OS/network monitor. No actual model/Codex CLI/host tool execution, running-job interrupt, independent/open_book browser path, all-AppServer, M6.3 acceptance or M7 restore claim is made. No CI result is borrowed.

## Original failures and preservation loss

The first run-01 failed before Chrome at the private config setup assertion. The fixture omitted secret_store.initialize present in the existing turn_case. Its finally then read a nonexistent sentinel file and raised ENOENT; no zero count may be inferred. Its initial outcome/raw hashes were emitted in tool output, but the author accidentally ran the old absolute directory's script again while preparing run-02. This overwritten first dynamic raw is LOST, not retained or reconstructed. The second accidental execution also failed before Chrome. Current run-01 files are that second execution, not the first. LOSS_V2.json gives both exact UTC intervals, first observed hashes and the retained second receipt. Both are harness setup failures, not demonstrated product failures. Source scripts stayed byte-identical. Do not call the later PASS a same-test product RED/GREEN.

run-02 only adds the missing private store initialization, records missing sentinels as NOT_AVAILABLE on early startup failure, and refuses four preexisting dynamic output paths. Root's later six-path no-overwrite requirement arrived after run-02 terminated; the recorded script was not rewritten to claim it already had that requirement. Future attempts must use a fresh numbered directory, absolute runner path and all-six guard. No further product run was needed.

## Input and candidate limits

All current retained before/after/terminal source maps contain all1525 non-progress Git inputs with modes, Git blob IDs, SHA256 and lengths; all agree, and the sealing script reads every corresponding Git blob plus all current files. Engineering status remains clean. The first execution's overwritten maps are not represented as separately retained raw maps.

The six original PNGs (three stages at1440/390) were individually viewed by the author: awaiting learner safe control; original ACK beside independent current GET; new actor's read-only old command/412. Only synthetic safe IDs/status/idempotency keys are visible, with no cookie, CSRF token, authentication secret or academic content. The dialog/document geometry checks found no horizontal overflow. The390 screenshot viewport naturally shows a subset of the long scrollable panel; it is not a full-page content proof.

Only exact entries in SAFE_CANDIDATES.json are admitted as sharing candidates, still subject to root readback. Bytes are copied exactly; no transformations. Private fixture/auth files, runtime data/DB/encryption keys/browser profile/cache, private-paths.json, built bundles and all unspecified files are excluded. Existing prior evidence and canonical trees remain untouched.
'''
(base / 'REPORT.md').write_text(report)
common = ['native.mjs', 'controlled_api.py', 'run.py', 'command.json', 'run-receipt.json', 'native.log', 'build.log',
          'runner-before.json', 'runner-after.json', 'before.json', 'terminal-source.json', 'built-assets.json']
names = ['FIRST_RUN_PRESERVATION_LOSS.json', 'LOSS_V2.json', 'REPORT.md', 'seal.py']
names += ['run-01/' + name for name in [*common, 'failure.json']]
names += ['run-02/' + name for name in [*common, 'after.json', 'receipt.json', 'terminal-sentinels.json',
    'learner-awaiting-safe-control-1440.png', 'learner-awaiting-safe-control-390.png',
    'durable-original-ack-independent-current-1440.png', 'durable-original-ack-independent-current-390.png',
    'new-actor-original-command-isolated-1440.png', 'new-actor-original-command-isolated-390.png']]
assert len(names) == len(set(names))
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tree, text=True).strip() == head
assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=tree, text=True) == ''
maps = [name for name in names if name.endswith(('before.json', 'after.json', 'terminal-source.json'))]
expected = json.loads((base / maps[0]).read_text())
for name in maps:
    assert json.loads((base / name).read_text()) == expected
assert expected['count'] == 1525
distinct = set()
for name, meta in expected['files'].items():
    data = (tree / name).read_bytes()
    assert sha(data) == meta['sha256'] and len(data) == meta['bytes']
    blob = subprocess.check_output(['git', 'cat-file', 'blob', meta['git_blob']], cwd=tree)
    assert blob == data
    distinct.add(meta['git_blob'])
assert expected['files']['PRODUCT_DESIGN.md']['sha256'] == 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
candidates = []
for name in names:
    source = base / name
    data = source.read_bytes()
    destination = target / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert not destination.exists()
    destination.write_bytes(data)
    assert destination.read_bytes() == data
    candidates.append(dict(candidate_path=name, raw_path=str(source), sha256=sha(data), bytes=len(data), transformation='none'))
write(seal / 'SAFE_CANDIDATES.json', dict(version=1, source=head, candidate_base=str(target), files=candidates,
    excluded='Everything not explicitly listed; runtime DB/key/fixture cookies/profile/cache/private-paths/bundles excluded. No broad directory grant.'))
readback = dict(source=head, checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    candidate_count=len(candidates), screenshot_count=6, source_maps=maps, source_map_count=len(maps),
    map_bindings=len(maps) * 1525, engineering_inputs=1525, distinct_git_blobs=len(distinct),
    all_retained_maps_equal=True, all_current_files_git_blobs_exact=True, source_clean=True,
    original_first_raw_status='LOST_NOT_RECONSTRUCTED', admitted_current_run01='second accidental execution',
    run02='BOUNDED_PASS', scope='Learner awaiting-approval interrupt UI only; actual model/CLI/tool NOT_RUN')
write(seal / 'READBACK.json', readback)
print(json.dumps({'seal': str(seal), 'readback': readback,
    'outer_sha256': {name: sha((seal / name).read_bytes()) for name in ['SAFE_CANDIDATES.json', 'READBACK.json']},
    'report_sha256': sha((base / 'REPORT.md').read_bytes())}, indent=2))
