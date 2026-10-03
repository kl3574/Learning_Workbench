"""Independent read-only hash/source replay; no product commands are executed."""
from pathlib import Path
import hashlib
import json
import subprocess

OUT = Path(__file__).parent
OWNER = OUT.parent / 'm62-review-import-close-diagnosis-v1'
TREE = OUT.parent / 'm62-review-import-close-active'
BASE = 'a944ebfbdb835a731393977a606db5b473846e98'
HEAD = '36b501cf8da071909fbb5628b7354de70d5d1825'
PATH = 'apps/web/src/features/draftReview/ReviewImportShell.test.tsx'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=TREE)


manifest_bytes = (OWNER / 'PRIVATE_MANIFEST.json').read_bytes()
manifest = json.loads(manifest_bytes)
expected = {'PRIVATE_MANIFEST.json'}
for row in manifest['files']:
    data = (OWNER / row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    expected.add(row['path'])
assert expected == {p.relative_to(OWNER).as_posix() for p in OWNER.rglob('*') if p.is_file()}
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert git('status', '--porcelain') == b''
assert git('diff', '--name-only', BASE, HEAD).decode().splitlines() == [PATH]
assert git('diff', BASE, HEAD) == (OWNER / 'final.diff').read_bytes() == (OUT / 'reviewed.diff').read_bytes()
assert git('show', BASE + ':' + PATH) == (OWNER / 'original-test.tsx').read_bytes()
assert (OWNER / 'ci-push-frontend.log').read_bytes() == (OUT.parent / 'm62-publication-a944-ci-v1/logs/push-frontend-108791498320.log').read_bytes()

trees = {}
for head in (BASE, HEAD):
    trees[head] = {}
    for item in git('ls-tree', '-rz', head).split(b'\0'):
        if item:
            meta, path = item.split(b'\t', 1)
            trees[head][path.decode()] = meta.decode().split()[2]
ledger = json.loads((OWNER / 'run-ledger.json').read_bytes())
snapshots = {stage['stage']: json.loads((OWNER / stage['stage'] / 'inputs-before.json').read_bytes()) for stage in ledger}
object_ids = sorted({row['git_blob'] for snap in snapshots.values() for row in snap['files'] if row.get('git_blob')})
raw_stream = subprocess.run(['git', 'cat-file', '--batch'], cwd=TREE,
                            input=('\n'.join(object_ids) + '\n').encode(), capture_output=True, check=True).stdout
objects = {}
offset = 0
for object_id in object_ids:
    end = raw_stream.index(b'\n', offset)
    actual, kind, size = raw_stream[offset:end].split()
    assert actual.decode() == object_id and kind == b'blob'
    offset = end + 1
    raw = raw_stream[offset:offset + int(size)]
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == object_id
    objects[object_id] = (len(raw), sha(raw))
    offset += int(size) + 1
assert offset == len(raw_stream)
stages = []
for stage in ledger:
    name = stage['stage']
    folder = OWNER / name
    receipt_raw = (folder / 'receipt.json').read_bytes()
    receipt = json.loads(receipt_raw)
    snap = snapshots[name]
    assert snap == json.loads((folder / 'inputs-after.json').read_bytes())
    assert receipt['head'] == snap['head']
    assert receipt['source_count'] == len(snap['files'])
    assert receipt['log_sha256'] == sha((folder / 'test.log').read_bytes())
    assert receipt['runner_sha256'] == sha((OWNER / 'run.py').read_bytes())
    assert stage['receipt_sha256'] == sha(receipt_raw)
    assert stage['inputs_before_sha256'] == sha((folder / 'inputs-before.json').read_bytes())
    assert stage['inputs_after_sha256'] == sha((folder / 'inputs-after.json').read_bytes())
    assert all(stage[key] == value for key, value in receipt.items())
    mismatches = []
    for row in snap['files']:
        assert not row.get('absent')
        raw = (OWNER / 'source-pool' / row['sha256']).read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
        blob = trees[snap['head']].get(row['path'])
        assert blob == row['git_blob']
        matched = blob is not None and objects[blob] == (row['bytes'], row['sha256'])
        assert matched == row['git_matches']
        if not matched:
            mismatches.append(row['path'])
    assert mismatches == stage['actual_git_source_mismatches']
    if name.startswith(('01-', '07-', '08-')):
        assert not mismatches
    stages.append({'stage': name, 'head': snap['head'], 'inputs': len(snap['files']),
                   'git_matches': len(snap['files']) - len(mismatches),
                   'mismatches': mismatches, 'exit_code': receipt['exit_code'],
                   'log_sha256': receipt['log_sha256']})

pins = json.loads((OWNER / 'final-source-pins.json').read_bytes())
for row in pins['sources']:
    data = git('show', HEAD + ':' + row['path'])
    assert row['git_blob'] == trees[HEAD][row['path']]
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
    assert data == (OWNER / 'final-source' / row['path']).read_bytes()
    copy = OUT / 'source' / row['path']
    copy.parent.mkdir(parents=True, exist_ok=True)
    if copy.exists():
        assert copy.read_bytes() == data
    else:
        copy.write_bytes(data)
for stage_name, original_file in [
    ('02-publication-ledger-red', 'probe-publication-ledger-source.tsx'),
    ('03-publication-ledger-enabled-control', 'probe-enabled-click-source.tsx'),
]:
    row = next(item for item in snapshots[stage_name]['files'] if item['path'].endswith('/ReviewImportShell.diagnostic.test.tsx'))
    assert row['sha256'] == sha((OWNER / original_file).read_bytes())
stage06 = next(item for item in snapshots['06-dirty-shell-guard']['files'] if item['path'] == PATH)
assert stage06['sha256'] == sha(git('show', HEAD + ':' + PATH))
result = {'status': 'PASS', 'base': BASE, 'head': HEAD,
          'owner_manifest_sha256': sha(manifest_bytes), 'owner_members_verified': len(manifest['files']),
          'actual_git_blob_count': len(objects), 'source_copies_verified': len(pins['sources']),
          'stages': stages, 'ci_original_byte_exact': True,
          'controlled_probe_sources_match_actual_stage_inputs': True,
          'stage06_test_bytes_equal_fixed_final': True,
          'product_tests_run': False, 'network_requests': 0, 'owner_or_tree_mutations': False}
(OUT / 'VERIFY.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
