"""Read-only source/evidence check. Never execute product commands or read runtime data."""
from pathlib import Path
import difflib
import hashlib
import json
import os
import subprocess

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
RAW = BASE / 'm62-block-version-compare-development-v1'
REPO = BASE / 'm62-block-version-compare-active'
FINAL = '05aa1af2fd000654b0d7b62e5eae32998c81d43f'
PRODUCT = 'b20f4aa9110829cf096bcae21e980e95b358a048'
MANIFEST = '84546ac78a9a90e5b40898e37bcd8bbd03c5785c26addad332babaa2758a767b'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args, data=None):
    return subprocess.check_output(['git', '-C', str(REPO), *args], input=data)


def git_tree(commit):
    result = {}
    for item in git('ls-tree', '-r', '-z', commit).split(b'\0'):
        if not item:
            continue
        header, path = item.split(b'\t')
        mode, kind, blob = header.decode().split()
        assert kind == 'blob'
        result[path.decode()] = blob
    return result


manifest_bytes = (RAW / 'PRIVATE_MANIFEST.json').read_bytes()
assert sha(manifest_bytes) == MANIFEST
manifest = json.loads(manifest_bytes)
assert manifest['excluded_directories'] == ['native-data', 'native-final-data']
members = manifest['members']
assert len(members) == len({row['path'] for row in members}) == 1076
names = set()
for root, dirs, files in os.walk(RAW):
    if Path(root) == RAW:
        dirs[:] = [name for name in dirs if name not in manifest['excluded_directories']]
    names.update(str((Path(root) / name).relative_to(RAW)) for name in files)
assert names == {row['path'] for row in members} | {'PRIVATE_MANIFEST.json'}
for row in members:
    assert not any(row['path'].startswith(excluded + '/') for excluded in manifest['excluded_directories'])
    data = (RAW / row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
ledger = json.loads((RAW / 'run-ledger.json').read_text())
trees = {head: git_tree(head) for head in {stage['head'] for stage in ledger} | {FINAL}}
objects = sorted({blob for tree in trees.values() for blob in tree.values()})
payload = git('cat-file', '--batch', data=''.join(blob + '\n' for blob in objects).encode())
offset = 0
blobs = {}
for wanted in objects:
    end = payload.index(b'\n', offset)
    blob, kind, size = payload[offset:end].decode().split()
    size = int(size)
    assert blob == wanted and kind == 'blob'
    data = payload[end + 1:end + 1 + size]
    assert len(data) == size and payload[end + 1 + size:end + 2 + size] == b'\n'
    assert hashlib.sha1(b'blob ' + str(size).encode() + b'\0' + data).hexdigest() == blob
    blobs[blob] = data
    offset = end + 2 + size
assert offset == len(payload)
for file in ['source-pins.json', 'context-pins.json']:
    for row in json.loads((OUT / file).read_text())['files']:
        blob = trees[FINAL][row['path']]
        data = blobs[blob]
        assert blob == row['git_blob_sha1'] and sha(data) == row['sha256'] and len(data) == row['bytes']
        if file == 'source-pins.json':
            assert data == (OUT / 'source' / row['path']).read_bytes()
stages = []
snapshots = {}
for declared in ledger:
    name = declared['stage']
    receipt = json.loads((RAW / name / 'receipt.json').read_text())
    log = (RAW / name / 'run.log').read_bytes()
    before = (RAW / name / 'inputs-before.json').read_bytes()
    after = (RAW / name / 'inputs-after.json').read_bytes()
    assert before == after
    assert sha(before) == declared['inputs_sha256']
    assert sha(log) == declared['log_sha256'] == receipt['log_sha256']
    for key in receipt:
        assert receipt[key] == declared[key]
    inventory = json.loads(before)
    assert inventory['head'] == receipt['head']
    rows = inventory['files']
    assert len(rows) == len({row['path'] for row in rows}) == declared['input_count']
    tree = trees[receipt['head']]
    matched, changed, absent = [], [], []
    for row in rows:
        raw = (RAW / 'source-pool' / row['sha256']).read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
        blob = tree.get(row['path'])
        assert row['git_blob'] == blob
        equal = blob is not None and blobs[blob] == raw
        assert row['git_matches'] is equal
        (matched if equal else changed if blob else absent).append(row['path'])
    assert len(matched) == declared['actual_git_matches']
    assert len(changed) == declared['development_changed']
    assert len(absent) == declared['development_absent']
    snapshots[name] = {row['path']: row for row in rows}
    stages.append({'stage': name, 'actual_head': receipt['head'], 'exit_code': receipt['exit_code'],
                   'log_sha256': sha(log), 'receipt_sha256': sha((RAW / name / 'receipt.json').read_bytes()),
                   'inputs_sha256': sha(before), 'input_count': len(rows), 'inputs_unchanged': True,
                   'actual_git_matches': len(matched), 'development_changed': changed, 'development_absent': absent})
pool = list((RAW / 'source-pool').iterdir())
assert len(pool) == 958 and all(p.is_file() and sha(p.read_bytes()) == p.name for p in pool)
repairs = []
for old, new in [('04-integrity-red', '05-integrity-green'), ('11-role-change-red', '12-role-change-green'), ('13-current-policy-red', '14-current-policy-green')]:
    a, b = snapshots[old], snapshots[new]
    paths = sorted(path for path in set(a) | set(b) if a.get(path, {}).get('sha256') != b.get(path, {}).get('sha256'))
    texts = []
    for path in paths:
        left = (RAW / 'source-pool' / a[path]['sha256']).read_text().splitlines(keepends=True) if path in a else []
        right = (RAW / 'source-pool' / b[path]['sha256']).read_text().splitlines(keepends=True) if path in b else []
        texts.extend(difflib.unified_diff(left, right, fromfile=old + '/' + path, tofile=new + '/' + path))
    name = f'{old}-to-{new}.diff'
    (OUT / name).write_text(''.join(texts))
    repairs.append({'before': old, 'after': new, 'changed_paths': paths, 'diff': name})
delta = git('diff', PRODUCT, FINAL)
assert delta == (RAW / 'native-locator-only.diff').read_bytes()
assert git('diff', '--name-only', PRODUCT, FINAL).decode().splitlines() == ['tests/e2e/block-version-compare.spec.ts']
(OUT / 'native-locator-only.diff').write_bytes(delta)
assert all(stage['input_count'] == stage['actual_git_matches'] == 952 for stage in stages[16:])
summary = {'status': 'PASS', 'axis': 'Standards independent read-only verification', 'candidate': FINAL,
           'product_commit': PRODUCT, 'owner_manifest_sha256': MANIFEST, 'owner_members_verified': len(members),
           'source_pool_bytes_verified': len(pool), 'stage_count': len(stages), 'all_before_after_equal': True,
           'fixed_stage_inputs': 952, 'actual_stage_heads_preserved': True, 'changed_sources_verified': 12,
           'context_pins_verified': 17, 'runtime_directories_not_read': manifest['excluded_directories'],
           'native_locator_only_delta_verified': True, 'product_tests_executed_by_reviewer': False,
           'repairs': repairs, 'stages': stages}
(OUT / 'EVIDENCE_VERIFICATION.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
assert sha((RAW / 'PRIVATE_MANIFEST.json').read_bytes()) == MANIFEST
print(json.dumps({key: value for key, value in summary.items() if key not in ['repairs', 'stages']}, indent=2))
