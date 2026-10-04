"""Read-only audit of exact finished receipts, Git objects and current owner inputs."""
import hashlib
import json
from pathlib import Path
import subprocess

base = Path(__file__).parent
root = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-artifact-ui-owner-oct04')
names = ['migration-red-01', 'migration-green-01', 'delivery-red-01', 'delivery-red-02', 'delivery-green-01',
         'fixed-boundaries-01', 'static-ruff-01', 'static-mypy-01', 'static-generated-01', 'static-spec-01',
         'static-typescript-01', 'static-diff-01', 'fixed-focused-01', 'fixed-related-01']
sha = lambda raw: hashlib.sha256(raw).hexdigest()
receipts = {name: json.loads((base/name/'receipt.json').read_text()) for name in names}
heads = sorted({r['source_sha'] for r in receipts.values()})
trees = {}
for head in heads:
    tree = []
    for row in subprocess.check_output(['git', 'ls-tree', '-rz', head], cwd=root).split(b'\0'):
        if not row: continue
        meta, path = row.split(b'\t', 1)
        mode, kind, oid = meta.decode().split(); path = path.decode()
        if path.startswith('progress/'): continue
        assert kind == 'blob'
        tree.append({'path': path, 'mode': mode, 'type': kind, 'git_blob': oid})
    trees[head] = tree
objects = sorted({r['git_blob'] for tree in trees.values() for r in tree})
data = subprocess.check_output(['git', 'cat-file', '--batch'], input=('\n'.join(objects)+'\n').encode(), cwd=root)
position, blobs = 0, {}
for oid in objects:
    end = data.index(b'\n', position)
    actual, kind, size = data[position:end].decode().split(); size = int(size)
    assert actual == oid and kind == 'blob'
    raw = data[end+1:end+1+size]
    assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest() == oid
    blobs[oid] = {'size': size, 'sha256': sha(raw)}
    position = end+1+size+1
assert position == len(data)
for tree in trees.values():
    for row in tree: row.update(blobs[row['git_blob']])
verified = []
for name, receipt in receipts.items():
    head = receipt['source_sha']
    assert sha((base/name/'run.log').read_bytes()) == receipt['log_sha256']
    assert sha((base/'run.py').read_bytes()) == receipt['runner_sha256']
    assert sha((base/name/'test_codex_artifact_repair_boundaries.py').read_bytes()) == receipt['test_sha256']
    a = json.loads((base/name/'source-before.json').read_text())
    b = json.loads((base/name/'source-after.json').read_text())
    assert a == b and a['head'] == head and a['status'] == ''
    assert a['count'] == len(trees[head]) == receipt['complete_nonprogress_inputs']
    assert len(a['files']) == a['count']
    for actual, expected in zip(a['files'], trees[head], strict=True):
        assert actual['path'] == expected['path']
        assert actual['git_blob'] == actual['actual_blob'] == expected['git_blob']
        assert actual['matches_git'] and actual['sha256'] == expected['sha256']
    verified.append({'run': name, 'head': head, 'count': a['count'], 'exit_code': receipt['exit_code'],
        'before_sha256': sha((base/name/'source-before.json').read_bytes()),
        'after_sha256': sha((base/name/'source-after.json').read_bytes()),
        'receipt_sha256': sha((base/name/'receipt.json').read_bytes())})
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
assert head == '51205a75c401911d98d54a42387fbaa43583da7f'
assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=root) == b''
for row in trees[head]:
    assert row['mode'] == '100644' or row['mode'] == '100755'
    assert sha((root/row['path']).read_bytes()) == row['sha256']
result = {'source': str(root), 'head': head, 'verified_runs': verified, 'unique_git_objects': len(objects),
    'current_complete_inputs': len(trees[head]), 'trees': trees,
    'qualifications': 'Supplementary complete mode/type/blob/size/SHA maps; original before/after files are retained unchanged.'}
(base/'FULL_GIT_MANIFESTS.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'head':head,'runs':len(verified),'unique_git_objects':len(objects),
    'current_complete_inputs':len(trees[head]),'sha256':sha((base/'FULL_GIT_MANIFESTS.json').read_bytes())}))
