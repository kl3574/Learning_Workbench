"""Read-only independent evidence verification; never runs product commands."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
RAW = BASE / 'm62-import-publication-ui-development-v1'
REPO = BASE / 'm62-import-publication-ui-active'
HEAD = 'fa71351e7d6b9358d4b0ef2f46184999f84e5e08'
EXPECTED = '8ed37ec82f0cb8f4ccf63ae546a732ce26bf42cd3e126388424cea5ea0bcff29'


def sha(value):
    return hashlib.sha256(value).hexdigest()


def git(*args, data=None):
    return subprocess.check_output(['git', '-C', str(REPO), *args], input=data)


manifest_bytes = (RAW / 'MANIFEST.json').read_bytes()
assert sha(manifest_bytes) == EXPECTED
members = json.loads(manifest_bytes)['members']
assert len(members) == 986
assert len({m['path'] for m in members}) == len(members)
assert {str(p.relative_to(RAW)) for p in RAW.rglob('*') if p.is_file()} == {m['path'] for m in members} | {'MANIFEST.json'}
for row in members:
    data = (RAW / row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
tree = {}
for raw in git('ls-tree', '-r', '-z', HEAD).split(b'\0'):
    if not raw:
        continue
    attrs, path = raw.split(b'\t')
    mode, kind, blob = attrs.decode().split()
    assert kind == 'blob'
    tree[path.decode()] = blob
objects = sorted(set(tree.values()))
payload = git('cat-file', '--batch', data=''.join(blob + '\n' for blob in objects).encode())
cursor = 0
blobs = {}
for wanted in objects:
    end = payload.index(b'\n', cursor)
    blob, kind, size = payload[cursor:end].decode().split()
    assert blob == wanted and kind == 'blob'
    size = int(size)
    data = payload[end + 1:end + 1 + size]
    assert len(data) == size and payload[end + 1 + size:end + 2 + size] == b'\n'
    assert hashlib.sha1(b'blob ' + str(size).encode() + b'\0' + data).hexdigest() == blob
    blobs[blob] = data
    cursor = end + 2 + size
assert cursor == len(payload)
for pins_name in ['source-pins.json', 'context-pins.json']:
    for row in json.loads((OUT / pins_name).read_text())['files']:
        data = blobs[tree[row['path']]]
        assert len(data) == row['bytes'] and sha(data) == row['sha256'] and tree[row['path']] == row['git_blob_sha1']
        if pins_name == 'source-pins.json':
            assert data == (OUT / 'source' / row['path']).read_bytes()
owner_bindings = json.loads((RAW / 'GIT_SOURCE_BINDINGS.json').read_text())
results = []
for stage in owner_bindings['stages']:
    name = stage['stage']
    receipt = json.loads((RAW / name / 'receipt.json').read_text())
    log = (RAW / name / 'run.log').read_bytes()
    before = (RAW / name / 'inputs-before.json').read_bytes()
    after = (RAW / name / 'inputs-after.json').read_bytes()
    assert before == after
    assert sha(log) == receipt['log_sha256'] == stage['log_sha256']
    assert sha(before) == receipt['inputs_before_sha256'] == stage['inputs_before_sha256']
    assert sha(after) == receipt['inputs_after_sha256'] == stage['inputs_after_sha256']
    inputs = json.loads(before)
    assert len(inputs) == receipt['input_count'] == stage['input_count']
    assert len({row['path'] for row in inputs}) == len(inputs)
    differences = []
    for row in inputs:
        data = (RAW / 'source-by-sha256' / row['sha256']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == row['git_blob']
        if row['path'] not in tree or data != blobs[tree[row['path']]]:
            differences.append(row['path'])
    assert len(inputs) - len(differences) == stage['actual_final_git_matches']
    assert set(differences) == set(stage['different_paths']) | set(stage['absent_final_paths'])
    assert receipt['exit_code'] == stage['exit_code']
    results.append({'stage': name, 'exit_code': receipt['exit_code'], 'log_sha256': sha(log),
                    'receipt_sha256': sha((RAW / name / 'receipt.json').read_bytes()),
                    'input_manifest_sha256': sha(before), 'input_count': len(inputs), 'inputs_unchanged': True,
                    'actual_final_git_matches': len(inputs) - len(differences), 'different_paths': differences})
red = {row['path']: row for row in json.loads((RAW / '10-late-basis-red/inputs-before.json').read_text())}
green = {row['path']: row for row in json.loads((RAW / '11-late-basis-green/inputs-before.json').read_text())}
changed = [path for path in red if red[path] != green[path]]
assert changed == ['apps/web/src/features/draftPublication/usePublication.ts']
path = changed[0]
old = (RAW / 'source-by-sha256' / red[path]['sha256']).read_text().splitlines(keepends=True)
new = (RAW / 'source-by-sha256' / green[path]['sha256']).read_text().splitlines(keepends=True)
(OUT / 'late-basis-red-green.diff').write_text(''.join(difflib.unified_diff(old, new, fromfile='stage10/usePublication.ts', tofile='stage11/usePublication.ts')))
native_paths = {row['path'] for row in json.loads((RAW / '18-native-publication/inputs-before.json').read_text())}
final_paths = {row['path'] for row in json.loads((RAW / '19-fixed-whole-web/inputs-before.json').read_text())}
assert final_paths - native_paths == {'docs/adr/0029-import-publication-ui-recovery.md'}
assert not native_paths - final_paths
assert sha((RAW / 'MANIFEST.json').read_bytes()) == EXPECTED
report = {'status': 'PASS', 'axis': 'Standards; source inspection and evidence read only', 'candidate': HEAD,
          'owner_manifest_sha256': EXPECTED, 'owner_members_verified': len(members),
          'changed_sources_verified': 17, 'context_sources_verified': 13, 'product_tests_executed_by_reviewer': False,
          'all_stage_cas_bytes_verified': True, 'stage_count': len(results),
          'full_engineering_tree_files': sum(not path.startswith('progress/') for path in tree),
          'execution_inventory_scope': 'Exact run.py ROOTS only, not all engineering files or external dependencies',
          'native_actual_inputs': len(native_paths), 'final_actual_inputs': len(final_paths),
          'final_added_after_native': sorted(final_paths - native_paths),
          'red_green_only_changed_path': changed, 'stages': results}
(OUT / 'EVIDENCE_VERIFICATION.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'stages'}, indent=2))
