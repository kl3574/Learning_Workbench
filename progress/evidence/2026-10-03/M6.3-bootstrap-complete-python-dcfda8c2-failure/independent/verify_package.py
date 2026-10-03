import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

BASE = Path('$HOME/.cache/learning-workbench-acceptance')
ROOT = BASE / 'm62-public-safe-oct02'
NAME = 'm63-bootstrap-full-python-dcfda8c2-oct03'
PRODUCER = BASE / NAME
OUT = Path(__file__).parent
HEAD = 'dcfda8c270dff3e6db75011c50ffa7d6f5826512'
sha = lambda data: hashlib.sha256(data).hexdigest()
def check(path, record):
    assert not Path(path).is_absolute() and '..' not in Path(path).parts
    data = (PRODUCER / path).read_bytes()
    assert sha(data) == record['sha256'] and len(data) == record['bytes'], path
    return data
raw = json.loads((PRODUCER / 'RAW_MANIFEST.json').read_text())
assert raw['head'] == HEAD and raw['terminal_status'] == 'FAIL' and len(raw['files']) == raw['count'] == 14
for path, record in raw['files'].items():
    check(path, record)
safe = json.loads((PRODUCER / 'SAFE_SHARE.json').read_text())
assert safe['source_head'] == HEAD and safe['terminal_gate'] == 'FAIL' and safe['only_explicit_entries_authorized']
assert safe['count'] == len(safe['entries']) == 15
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
assert receipt['state'] == 'FAIL' and receipt['exit_code'] == 1 and receipt['inputs_unchanged'] and receipt['exact_git_bytes']
assert receipt['source_snapshot_error'] is None and receipt['runner'] == before['private_inputs']['run_full_python.py']
check('run_full_python.py', receipt['runner'])
assert sha((PRODUCER / 'inputs-before.json').read_bytes()) == receipt['inputs_before_sha256'] == receipt['inputs_after_sha256']
log = (PRODUCER / 'python.log').read_bytes()
assert sha(log) == receipt['log_sha256'] == '550d97bb81121f32b9992e3faedc4bcffa34e9d82a6368a39fefd5f64630e711'
for phrase in (b'3683 passed', b'1 failed', b'2 errors', b'2 skipped', b'2249.18s'):
    assert phrase in log
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
report = {'status': 'PASS_INDEPENDENT_READBACK_OF_FAILED_GATE', 'executed_head': HEAD,
 'complete_python_gate': 'FAIL/exit1;3683PASS1FAIL2setupERROR2physicalnumericENVSKIP2existingwarnings',
 'nonprogress_inputs': 1381, 'all_git_and_before_after_exact': True,
 'raw_manifest_files': 14, 'explicit_candidates': 15, 'outer_metadata': 4,
 'pytest_seconds': 2249.18, 'runner_monotonic_seconds': receipt['duration_seconds'],
 'utc_clock_difference_boundary': 'Original UTC interval6906.8653 differs from runner2250.136. Both retained; cause not investigated and not assigned to setup errors.',
 'failures': ['draft_candidate_owners missing-provider-owner single: fixture candidateNone; body not reached',
              'review_http extra-body decision: fixture no block draft/StopIteration; body not reached',
              'review_storage_migration backup: retained reviewer_session_id versus old test expectingNone'],
 'next': 'Separate legacy backup test-only correction under review; bounded own synthetic metadata investigation, no blind retries or lease/permission weakening. Full gate remains FAIL until applicable corrected complete run.',
 'boundary': 'Readback and log/source review only; no test/model/native/control rerun, no private DB/key/archive admission, no stage completion/source push/merge/release/deploy.'}
(OUT / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('package_helper', BASE / 'm62-v313-pushed-progress-sync-oct03/package.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
public = helper.package('M6.3-bootstrap-complete-python-dcfda8c2-failure', [
 ('python', NAME, [item['candidate_path'] for item in safe['entries']] + list(outer['files']) + ['PUBLIC_OUTER_ALLOWLIST.json']),
 ('independent', OUT.name, ['verify_package.py', 'READBACK.json']),
], report.copy())
(OUT / 'PACKAGE_RECEIPT.json').write_text(json.dumps({'report': public}, indent=2) + '\n')
print(json.dumps({'independent_readback': 'PASS', 'actual_complete_gate': 'FAIL', 'source_inputs': 1381, 'public_candidates_only': True}))
