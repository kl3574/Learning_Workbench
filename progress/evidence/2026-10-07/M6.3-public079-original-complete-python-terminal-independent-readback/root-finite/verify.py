import datetime
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

O = Path(__file__).resolve().parent
B = O.parent
E = B / 'm63-public079-complete-python-originals-v2-oct07'
R = B / 'm62-public-safe-oct02'
H = '079a008cf88b37e4517cb391503a1e7393ccf374'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def load(p):
    return json.loads(p.read_bytes())

mraw = (E / 'finite-originals-manifest.json').read_bytes()
assert sha(mraw) == '786ff4e54c257678a8a79426eff6a6056a9fa5b1e61c1e010eab4d6f12591ed1'
m = json.loads(mraw)
assert m['head'] == H and m['count'] == 62
bindings = []
for e in m['files']:
    p = Path(e['path'])
    assert not p.is_absolute() and '..' not in p.parts
    b = (E / p).read_bytes()
    assert len(b) == e['size'] and sha(b) == e['sha256'], e['path']
    bindings.append(e)
actual = {str(p.relative_to(E)) for p in E.rglob('*') if p.is_file()}
assert actual == {e['path'] for e in m['files']} | {'finite-originals-manifest.json'}

fixed = load(E / 'fixed-inputs.json')
assert fixed['head'] == H and fixed['count'] == 1561
assert fixed['excluded_prefix_only'] == 'progress/'
byname = {e['path']: e for e in fixed['entries']}
assert len(byname) == 1561
maps = {}
for p in sorted(E.glob('*/before.json')) + sorted(E.glob('*/after.json')):
    d = load(p)
    assert d['head'] == H and d['count'] == 1561 and d['complete_exact'] is True
    assert d['status'] == '' and d['errors'] == []
    assert {e['path'] for e in d['entries']} == set(byname)
    for e in d['entries']:
        f = byname[e['path']]
        assert e['fixed_git'] == f and e['matches_fixed_git'] is True
        assert e['index']['stage'] == '0'
        for k in ('mode', 'type', 'blob'):
            assert e['index'][k] == e['live'][k] == f[k]
        for k in ('size', 'sha256'):
            assert e['live'][k] == f[k]
    maps[str(p.relative_to(E))] = sha(p.read_bytes())
assert len(maps) == 12
stages = []
for p in sorted(E.glob('*/receipt.json')):
    if p.parent.name == 'canonical-descendant-readback':
        continue
    rc = load(p)
    cmd_raw = (p.parent / 'command.json').read_bytes()
    assert sha(cmd_raw) == rc['command_sha256']
    for stream in ('stdout', 'stderr'):
        raw = (p.parent / (stream + '.bin')).read_bytes()
        assert len(raw) == rc[stream + '_size'] and sha(raw) == rc[stream + '_sha256']
    assert rc['command_started'] and rc['input_count'] == 1561
    assert rc['before_after_complete_exact'] and rc['launch_error'] is None and rc['after_error'] is None
    assert rc['command_exit_code'] == (1 if p.parent.name == 'complete-python' else 0)
    assert rc['wrapper_exit_code'] == rc['command_exit_code']
    stages.append({'stage': p.parent.name, 'command_exit': rc['command_exit_code'],
                   'wrapper_exit': rc['wrapper_exit_code'], 'stdout_sha256': rc['stdout_sha256'],
                   'stderr_sha256': rc['stderr_sha256'], 'complete_input_count': 1561})
assert len(stages) == 6

result = load(E / 'RESULT.json')
assert result['status'] == 'FAIL' and result['source_head'] == H
assert [result[k] for k in ('collected', 'passed', 'failed', 'skipped', 'warnings')] == [4583, 4580, 1, 2, 3]
assert result['full_launch_count'] == 1
cmd = load(E / 'complete-python/command.json')
assert cmd['argv'] == ['uv', 'run', '--frozen', '--offline', 'pytest']
raw = (E / 'complete-python/stdout.bin').read_bytes()
assert sha(raw) == result['original_stdout_sha256']
# Exact finite source lines; no dataclass representation, cookie/CSRF, fixture JSON or private page content.
patterns = [
    r'^platform linux -- Python ', r'^collected 4583 items',
    r'^_+ test_forward_guards_preserve_existing_source_rows_rowids_and_original_http_acks _+$',
    r'^tests/integration/test_codex_artifact_repair_boundaries.py:174:',
    r'^>\s+assert response.status_code == 202$',
    r'^E\s+assert 503 == 202$',
    r'^E\s+\+\s+where 503 = <Response \[503 Service Unavailable\]>.status_code$',
    r'^tests/integration/test_codex_turn_consent_http.py:91: AssertionError$',
    r'^SKIPPED \[1\] tests/integration/test_(authoring_numeric_runtime|restore_numeric_actual_runtime).py:',
    r'^FAILED tests/integration/test_codex_artifact_repair_boundaries.py::test_forward_guards_preserve_existing_source_rows_rowids_and_original_http_acks',
    r'^=+ 1 failed, 4580 passed, 2 skipped, 3 warnings in 3075.18s \(0:51:15\) =+$',
]
selected = []
linebindings = []
for i, line in enumerate(raw.splitlines(keepends=True), 1):
    if any(re.search(pattern, line.decode('utf-8').rstrip('\r\n')) for pattern in patterns):
        selected.append(line)
        linebindings.append({'line': i, 'bytes': len(line), 'sha256': sha(line)})
candidate = b''.join(selected)
assert b'4580 passed' in candidate and b'assert 503 == 202' in candidate
assert candidate.count(b'SKIPPED [1]') == 2
assert all(token not in candidate.lower() for token in (b'csrf', b'cookie', b'case(', b'authorization'))
(O / 'SAFE-ORIGINAL-LINES.txt').write_bytes(candidate)
(O / 'ORIGINAL-LINE-BINDINGS.json').write_text(json.dumps({
    'source_relative': 'complete-python/stdout.bin', 'source_bytes': len(raw), 'source_sha256': sha(raw),
    'scope': 'Exact finite lines only; full raw stdout stays private because traceback can contain fixture credentials.',
    'candidate_bytes': len(candidate), 'candidate_sha256': sha(candidate), 'lines': linebindings}, indent=2) + '\n')

c = load(E / 'canonical-descendant-readback/receipt.json')
assert c['actual_canonical_head'] == '7f1669db921fac285226bebeb6a829336b4248b3'
assert c['fixed_is_ancestor_exit_code'] == 0 and c['runtime_input_equivalence']
assert c['strict_fixed_HEAD_snapshot_complete_exact'] is False
canonical = load(E / 'canonical-descendant-readback/canonical-live.json')
assert len(canonical['entries']) == 1561 and all(e['matches_fixed_git'] for e in canonical['entries'])
head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=R, capture_output=True, check=True).stdout.decode().strip()
assert head == c['actual_canonical_head']

(O / 'ROOT-READBACK.json').write_text(json.dumps({
    'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'FAIL_ORIGINAL_COMPLETE_GATE_INDEPENDENTLY_BOUND', 'source': H,
    'originals': 62, 'originals_manifest_sha256': sha(mraw), 'input_count': 1561,
    'all12_before_after_maps_validated_entry_by_entry': True, 'map_hashes': maps,
    'all6_original_command_receipt_stream_quartets_bound': stages,
    'result': {'collected': 4583, 'passed': 4580, 'failed': 1, 'blocked_environment_skips': 2, 'warnings': 3},
    'actual_pytest_exit': 1, 'wrapper_exit': 1, 'source_lines': len(linebindings),
    'trace_qualification': 'Original HTTP 503 vs 202; original trace does not name SQLite or Broker schema. Static fixture diagnosis and later patch are separate.',
    'canonical_documentary_descendant_runtime_equivalent': True,
    'whole_model_host_M63_AC21_M7_acceptance': 'NOT_ACCEPTED',
    'network': 'Original setup installed public locked dependencies; no zero-network claim.',
    'no_rerun_canonical_mutation_source_push': True,
    'review_scope': 'All finite hashes, receipt bindings, exact metadata maps and selected original lines. No claim of root manual semantic reading of the entire original stdout.'}, indent=2) + '\n')

spec = importlib.util.spec_from_file_location('helper', B / 'm63-public079a008-progress-record-oct07/package-helper.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
path = helper.package('M6.3-public079-original-complete-python-terminal-independent-readback', [
    ('owner-finite', E.name, ['RESULT.json', 'finite-originals-manifest.json', 'fixed-inputs.json',
                           'complete-python/before.json', 'complete-python/after.json',
                           'complete-python/command.json', 'complete-python/receipt.json',
                           'complete-python/stderr.bin', 'node-version/receipt.json', 'node-version/stdout.bin',
                           'canonical-descendant-readback/receipt.json']),
    ('root-finite', O.name, ['verify.py', 'ROOT-READBACK.json', 'SAFE-ORIGINAL-LINES.txt', 'ORIGINAL-LINE-BINDINGS.json'])],
    {'status': 'FAIL', 'source': H, 'scope': 'Original full 4583 collected gate, single launch; preserve failure.',
     'passed': 4580, 'failed': 1, 'blocked_environment_skips': 2, 'warnings': 3, 'actual_exit': 1, 'wrapper_exit': 1,
     'all1561_inputs_before_after_exact': True, 'finite_originals_qualified': 62,
     'raw_stdout': 'PRIVATE_EXCLUDED_AUTH_FIXTURE_REPR', 'new_fixture_fix': 'SEPARATE_QUALIFIED_CANDIDATE_NOT_THIS_SOURCE',
     'whole_M63_AC21_M7': 'NOT_ACCEPTED', 'real_model_requests': 0, 'source_push': False})
(O / 'INSTALL-READBACK.json').write_text(json.dumps({'evidence': path, 'status': 'FAIL', 'source': H}, indent=2) + '\n')
print('Original complete FAIL bound; 62 originals / 12 exact1561 maps / 6 quartet bindings; finite safe lines admitted.')
