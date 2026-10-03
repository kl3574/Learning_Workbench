import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

BASE = Path('$HOME/.cache/learning-workbench-acceptance')
ROOT = BASE / 'm62-public-safe-oct02'
FOLDER = BASE / 'm63-bootstrap-setup-metadata-dcf-oct04'
OUT = Path(__file__).parent
HEAD = 'dcfda8c270dff3e6db75011c50ffa7d6f5826512'
sha = lambda data: hashlib.sha256(data).hexdigest()
load = lambda name: json.loads((FOLDER / name).read_text())
raw, safe, outer = load('RAW_MANIFEST.json'), load('SAFE_SHARE.json'), load('PUBLIC_OUTER_ALLOWLIST.json')
assert raw['head'] == HEAD and raw['count'] == len(raw['files']) == 10
assert safe['source_head'] == HEAD and safe['count'] == len(safe['entries']) == 11
for name, item in raw['files'].items():
    data = (FOLDER / name).read_bytes()
    assert (len(data), sha(data)) == (item['bytes'], item['sha256'])
for item in safe['entries']:
    original = (FOLDER / item['raw_path']).read_bytes()
    candidate = (FOLDER / item['candidate_path']).read_bytes()
    assert candidate == original.replace(b'$HOME', b'$HOME')
    assert (len(original), sha(original)) == (item['raw']['bytes'], item['raw']['sha256'])
    assert (len(candidate), sha(candidate)) == (item['candidate']['bytes'], item['candidate']['sha256'])
for name, item in outer['files'].items():
    data = (FOLDER / name).read_bytes()
    assert (len(data), sha(data)) == (item['bytes'], item['sha256'])
before, after = load('inputs-before.json'), load('inputs-after.json')
assert before == after and before['head'] == HEAD and before['count'] == len(before['files']) == 1381
tree = {}
for row in subprocess.check_output(['git', 'ls-tree', '-r', '-z', HEAD], cwd=ROOT).split(b'\0'):
    if not row:
        continue
    metadata, name = row.split(b'\t', 1); mode, kind, oid = metadata.split()
    if name.startswith(b'progress/'):
        continue
    assert kind == b'blob'; tree[name.decode()] = (mode.decode(), oid.decode())
assert set(tree) == set(before['files'])
with subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as child:
    for name, item in before['files'].items():
        oid = item['git_blob']
        assert tree[name] == (item['git_mode'], oid) and item['exact_git_bytes']
        child.stdin.write((oid + '\n').encode()); child.stdin.flush()
        header = child.stdout.readline().strip().split()
        assert header[:2] == [oid.encode(), b'blob']
        data = child.stdout.read(int(header[2])); assert child.stdout.read(1) == b'\n'
        assert (len(data), sha(data)) == (item['bytes'], item['sha256'])
    child.stdin.close(); child.wait(); assert child.returncode == 0
mapping = load('mapping.json')
assert mapping['fixed_head'] == HEAD and mapping['exit_code'] == 0 and mapping['inputs_unchanged']
assert '--collect-only' in mapping['command'] and len(mapping['all_collected']) == 14
assert list(mapping['failed_selected'].values()) == ['test_missing_provider_owner_ca0', 'test_review_http_write_guards_9']
for name, item in before['private_inputs'].items():
    data = (FOLDER / name).read_bytes(); assert (len(data), sha(data)) == (item['bytes'], item['sha256'])
metadata = load('safe-metadata.json')
assert metadata['source_head'] == HEAD and metadata['association_receipt_sha256'] == sha((FOLDER / 'mapping.json').read_bytes())
assert len(metadata['cases']) == 2
for case in metadata['cases']:
    assert mapping['failed_selected'][case['nodeid']] == case['synthetic_basetemp_subdirectory']
    assert case['query_only'] and case['read_only_immutable_uri'] and case['database_and_directory_stat_unchanged']
    job = case['rows']['jobs'][0]
    assert job['status'] == 'running' and job['retry_count'] == 0 and job['has_lease_owner'] == 1
    assert job['error_code'] is None and job['nested_error_code'] is None
assert [v['rows']['jobs'][0]['revision'] for v in metadata['cases']] == [3, 2]
proof = load('allocation-proof.json')
original = BASE / 'm63-bootstrap-full-python-dcfda8c2-oct03/run.log'
data = original.read_bytes()
assert proof['original_full_source'] == HEAD
assert (len(data), sha(data)) == (proof['original_full_log']['bytes'], proof['original_full_log']['sha256'])
report = {
    'status': 'PASS_READBACK_OF_BOUNDED_METADATA_NOT_ERROR_RESOLUTION',
    'source': HEAD, 'engineering_inputs_git_verified': 1381,
    'raw_hash_verified': 10, 'explicit_candidates_verified': 11, 'outer_verified': 4,
    'observed': 'The two original errored fixtures persist running authoring r3 and import r2 with no selected terminal error code. Association established from source/collection/allocation evidence, not inferred from database content.',
    'cause': 'UNKNOWN; metadata cannot establish fixture-failure time, lease loss, UTC discrepancy or host causality.',
    'root_scope': 'Read exact metadata/scripts/manifests and fixed Git objects only; no database open/copy/hash or fixture/control/model execution. Fourteen collect-only cases are producer evidence, not root reruns.',
    'boundary': 'Original DCF complete Python gate remains FAIL:3683PASS1FAIL2setupERROR2physicalnumericENVSKIP. New184 complete run separate and pending; no lease/authorization weakening or historical result replacement.'
}
(OUT / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('package_helper', BASE / 'm62-v313-pushed-progress-sync-oct03/package.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
public = helper.package('M6.3-bootstrap-original-setup-errors-metadata', [
    ('metadata', FOLDER.name, [v['raw_path'] for v in safe['entries']] + list(outer['files']) + ['PUBLIC_OUTER_ALLOWLIST.json']),
    ('independent', OUT.name, ['verify_package.py', 'READBACK.json']),
], report.copy())
(OUT / 'PACKAGE_RECEIPT.json').write_text(json.dumps({'report': public}, indent=2) + '\n')
print(json.dumps({'readback': 'PASS', 'cause': 'UNKNOWN', 'original_complete_gate': 'FAIL', 'engineering_inputs': 1381}))
