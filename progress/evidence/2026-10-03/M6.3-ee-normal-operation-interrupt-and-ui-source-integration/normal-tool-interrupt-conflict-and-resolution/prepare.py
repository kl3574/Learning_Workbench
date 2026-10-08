import datetime
import hashlib
import json
import subprocess
from pathlib import Path

B = Path('$HOME/.cache/learning-workbench-acceptance')
R = B / 'm62-public-safe-oct02'
O = Path(__file__).parent
H = '7f3bbc4b2a7c0dd80499ea8c1a8a3038c4d0e587'
BASE = 'fdd3a949fc9bc6edb2d136b912f3d8d1cdba4b81'
OWNER = '83d7b9164968e314261a3d12f5fb3fc75d2e8c6d'
sha = lambda b: hashlib.sha256(b).hexdigest()
git = lambda *args: subprocess.check_output(['git', *args], cwd=R)
assert git('rev-parse', 'HEAD').decode().strip() == H and not git('status', '--porcelain')
assert not (O / 'before.json').exists()
files = {}
for row in git('ls-tree', '-rz', H).split(b'\0'):
    if not row:
        continue
    meta, name = row.split(b'\t', 1)
    name = name.decode()
    if name.startswith('progress/'):
        continue
    raw = (R / name).read_bytes()
    oid = meta.split()[2].decode()
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == oid
    files[name] = {'git_blob': oid, 'sha256': sha(raw), 'bytes': len(raw)}
owner_paths = git('diff', '--name-only', BASE, OWNER).decode().splitlines()
assert len(owner_paths) == 15 and all(not name.startswith('progress/') for name in owner_paths)
overlap = [name for name in owner_paths if name in files and git('show', H + ':' + name) != git('show', BASE + ':' + name)]
(O / 'before.json').write_text(json.dumps({'head': H, 'count': len(files), 'files': files}, indent=2) + '\n')
command = ['git', 'merge', '--no-ff', '--no-commit', OWNER]
p = subprocess.run(command, cwd=R, capture_output=True)
(O / 'merge.stdout').write_bytes(p.stdout)
(O / 'merge.stderr').write_bytes(p.stderr)
conflicts = git('diff', '--name-only', '--diff-filter=U').decode().splitlines()
report = {'status': 'NORMAL_LOCAL_MERGE_PREPARED' if not conflicts else 'NORMAL_LOCAL_MERGE_CONFLICT_PRESERVED',
 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': command,
 'exit_code': p.returncode, 'before_head': H, 'owner_base': BASE, 'owner_head': OWNER,
 'owner_paths': owner_paths, 'original_overlap_paths': overlap, 'conflicts': conflicts,
 'complete_nonprogress_before': len(files), 'sourcepush': False,
 'boundary': 'Normal local no-commit merge only. Shared interruptv4/operationv5 history must be separately reviewed and tested before commit. No reset/stash/force/GitHubmerge/release/deploy.'}
(O / 'PREPARED.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
