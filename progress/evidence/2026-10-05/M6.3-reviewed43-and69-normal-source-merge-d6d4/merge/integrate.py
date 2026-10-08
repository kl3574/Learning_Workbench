"""Normal reviewed local source merge, preserving progress and documentary attributes."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

base = Path('$HOME/.cache/learning-workbench-acceptance')
root = base / 'm62-public-safe-oct02'
out = Path(__file__).parent
before_head = '7bbbbb0e6f1ff23c5ed2e5956f9dd68963f8ff46'
candidate = 'd69de81045ff6c9ff2f345643f0fd412e2d108fb'
source_base = '412abe09c519104d9dbd2b360eed3ff4f897f829'
sha = lambda b: hashlib.sha256(b).hexdigest()
git = lambda *a: subprocess.check_output(['git', *a], cwd=root)

def snapshot(head):
    files, progress = {}, {}
    for row in git('ls-tree', '-rz', head).split(b'\0'):
        if not row:
            continue
        meta, n = row.split(b'\t', 1)
        n = n.decode(); mode, kind, oid = meta.decode().split()
        if n.startswith('progress/'):
            progress[n] = {'mode': mode, 'type': kind, 'git_blob': oid}
            continue
        data = git('cat-file', 'blob', oid)
        files[n] = {'mode': mode, 'type': kind, 'git_blob': oid, 'sha256': sha(data), 'bytes': len(data)}
    return {'head': head, 'count': len(files), 'files': files, 'progress_git': progress}

assert git('rev-parse', 'HEAD').decode().strip() == before_head and not git('status', '--porcelain')
assert sha((root / 'PRODUCT_DESIGN.md').read_bytes()) == 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
before, source = snapshot(before_head), snapshot(candidate)
delta = git('diff', '--name-only', source_base, candidate).decode().splitlines()
assert len(delta) == 12 and all(n.startswith(('apps/web/', 'tests/e2e/')) for n in delta)
assert before['count'] == 1512 and source['count'] == 1522
expected = dict(before['files'])
for n in delta:
    expected[n] = source['files'][n]
assert set(expected) == set(source['files'])
assert all(v == source['files'][n] for n, v in expected.items() if n != '.gitattributes')
(out / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
command = ['git', 'merge', '--no-ff', candidate, '-m', 'Merge reviewed GenericApproval UI and bounded Review route lifecycle fix']
(out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
q = subprocess.run(command, cwd=root, capture_output=True)
(out / 'stdout.log').write_bytes(q.stdout); (out / 'stderr.log').write_bytes(q.stderr)
assert q.returncode == 0, q.returncode
head = git('rev-parse', 'HEAD').decode().strip(); after = snapshot(head)
assert after['files'] == expected and after['progress_git'] == before['progress_git']
assert git('rev-list', '--parents', '-n', '1', head).decode().split() == [head, before_head, candidate]
assert not git('status', '--porcelain')
for n, v in after['files'].items():
    assert sha((root / n).read_bytes()) == v['sha256']
(out / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
result = {'status': 'NORMAL_REVIEWED_SOURCE_MERGE_EXACT_PROGRESS_PRESERVED',
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'head': head, 'parents': [before_head, candidate], 'merge_exit_code': q.returncode,
    'source_base': source_base, 'candidate': candidate, 'delta_paths': delta, 'inputs': after['count'],
    'all12_candidate_paths_exact': True, 'all_progress_mode_type_blob_preserved': True,
    'candidate_input_continuity': '1521/1522 exact d69; sole .gitattributes documentary exception preserves5 original archived warning paths. No runtime code/profile/DTO/spec/dependency drift.',
    'review_limits': 'Generic43 P2 CLOSED_STATIC/zero new findings. D69 lifecycle source zero new findings, client JSON/React completion coverage remains OPEN_EVIDENCE.3subset not whole native/client late acceptance. New client observer is separate work. Complete native d69 RUNNING in isolated fixed tree, not called PASS.',
    'new_product_tests_executed': False, 'sourcepush': False, 'whole_M6_3_accepted': False}
(out / 'SOURCE_FUSION.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
