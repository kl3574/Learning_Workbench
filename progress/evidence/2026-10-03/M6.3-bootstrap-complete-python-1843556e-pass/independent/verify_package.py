import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

BASE = Path('$HOME/.cache/learning-workbench-acceptance')
ROOT = BASE / 'm62-public-safe-oct02'
NAME = 'm63-bootstrap-full-python-1843556e-oct04'
PRODUCER = BASE / NAME
OUT = Path(__file__).parent
HEAD = '1843556e1c01b48e60082969e78d2a82b3848b45'
sha = lambda data: hashlib.sha256(data).hexdigest()
def check(path, record):
    assert not Path(path).is_absolute() and '..' not in Path(path).parts
    data = (PRODUCER / path).read_bytes()
    assert sha(data) == record['sha256'] and len(data) == record['bytes'], path
    return data
raw = json.loads((PRODUCER / 'RAW_MANIFEST.json').read_text())
assert raw['head'] == HEAD and raw['terminal_status'] == 'PASS with two environment skips' and len(raw['files']) == raw['count'] == 11
for path, record in raw['files'].items():
    check(path, record)
safe = json.loads((PRODUCER / 'SAFE_SHARE.json').read_text())
assert safe['source_head'] == HEAD and safe['terminal_gate'] == 'PASS with two environment skips' and safe['only_explicit_entries_authorized']
assert safe['count'] == len(safe['entries']) == 12
for item in safe['entries']:
    original = check(item['raw_path'], item['raw'])
    candidate = check(item['candidate_path'], item['candidate'])
    assert candidate == original.replace(b'$HOME', b'$HOME')
outer = json.loads((PRODUCER / 'PUBLIC_OUTER_ALLOWLIST.json').read_text())
assert len(outer['files']) == 4
for path, record in outer['files'].items():
    check(path, record)
before = json.loads((PRODUCER / 'inputs-before.json').read_text())
after = json.loads((PRODUCER / 'inputs-after.json').read_text())
receipt = json.loads((PRODUCER / 'receipt.json').read_text())
assert before == after and before['head'] == receipt['head'] == HEAD
assert before['count'] == len(before['files']) == receipt['input_count'] == 1381
assert receipt['state'] == 'PASS' and receipt['exit_code'] == 0 and receipt['inputs_unchanged'] and receipt['exact_git_bytes']
assert receipt['source_snapshot_error'] is None and receipt['runner'] == before['private_inputs']['run_full_python.py']
check('run_full_python.py', receipt['runner'])
assert sha((PRODUCER / 'inputs-before.json').read_bytes()) == receipt['inputs_before_sha256'] == receipt['inputs_after_sha256']
log = (PRODUCER / 'python.log').read_bytes()
assert sha(log) == receipt['log_sha256'] == '94f854ac04d5ad986045ce415f3b9d2366cc8c9af2f89ed2449e98072488aede'
assert b'3686 passed, 2 skipped, 2 warnings in 2199.36s' in log
assert receipt['command'][0:8] == ['uv', 'run', '--frozen', '--no-sync', 'pytest', 'tests/contract', 'tests/unit', 'tests/integration']
assert not any(x in receipt['command'] for x in ('-k','-x','--lf','--ff'))
tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', HEAD], cwd=ROOT, text=True).splitlines()
assert set(before['files']) == {path for path in tracked if not path.startswith('progress/')}
paths = sorted(before['files'])
data = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT, input=''.join(HEAD + ':' + path + '\n' for path in paths).encode())
offset = 0
for path in paths:
    end = data.index(b'\n', offset)
    oid, kind, length = data[offset:end].split(); length = int(length)
    assert kind == b'blob'
    blob = data[end + 1:end + 1 + length]
    record = before['files'][path]
    assert oid.decode() == record['git_blob'] and len(blob) == record['bytes'] and sha(blob) == record['sha256'] and record['exact_git_bytes']
    offset = end + 2 + length
assert offset == len(data)
original = BASE / 'm63-bootstrap-full-python-dcfda8c2-oct03'
assert sha((original / 'python.log').read_bytes()) == '550d97bb81121f32b9992e3faedc4bcffa34e9d82a6368a39fefd5f64630e711'
assert sha((original / 'REPORT.md').read_bytes()) == '5fdeca9c7260120674723063887b53eb5bb55d3afc323e899c44858528fe47fc'
assert json.loads((original / 'receipt.json').read_text())['exit_code'] == 1
for line in (PRODUCER / 'SHA256SUMS').read_text().splitlines():
    digest, name = line.split('  ')
    assert sha((PRODUCER / name).read_bytes()) == digest
report = {
 'status': 'PASS_INDEPENDENT_READBACK_OF_COMPLETE_PYTHON', 'source_head': HEAD,
 'complete_gate': {'pass':3686,'fail':0,'error':0,'environment_skip':2,'existing_warnings':2,'exit_code':0,'collected':3688},
 'nonprogress_inputs':1381, 'all_git_and_before_after_exact':True,
 'raw_manifest_files':11, 'explicit_candidates':12, 'outer_metadata':4,
 'runner_sha256':receipt['runner']['sha256'], 'log_sha256':receipt['log_sha256'],
 'pytest_seconds':2199.36, 'runner_monotonic_seconds':receipt['duration_seconds'],
 'preserved': 'OriginalDCF completeFAIL3683PASS1F2E2ENVskip/exit1 report and log remain exact original hash. Original two setup causes UNKNOWN; new PASS does not establish cause or explain old UTC/monotonic difference.',
 'physical_numeric': 'Two existing Authoring/Restore actual sealed runtime/evaluator environment skips retained; no fallback or numericPASS.',
 'current_source_boundary': 'Execution anchored184; later canonical edits are progress/evidence, immutable path attributes and explanatory docs. Runtime/frontend/test business source must separately be compared before source push.',
 'boundary': 'Independent full source/log/manifest readback only, no new product/tests/control/model execution; no DB/ZIP/key/cache copying. This passes Python contract/unit/integration scope, not extended security review, wholeBroker/M6.3/AC21/quality/M7. No sourcepush/merge/release/deploy by this receipt.'
}
(OUT / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('package_helper', BASE / 'm62-v313-pushed-progress-sync-oct03/package.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
public = helper.package('M6.3-bootstrap-complete-python-1843556e-pass', [
 ('python', NAME, [item['candidate_path'] for item in safe['entries']] + list(outer['files']) + ['PUBLIC_OUTER_ALLOWLIST.json']),
 ('independent', OUT.name, ['verify_package.py', 'READBACK.json']),
], report.copy())
(OUT / 'PACKAGE_RECEIPT.json').write_text(json.dumps({'report': public}, indent=2) + '\n')
print(json.dumps({'independent_readback': 'PASS', 'actual_complete_gate': 'PASS with2ENVskip', 'source_inputs': 1381, 'public_candidates_only': True}))
