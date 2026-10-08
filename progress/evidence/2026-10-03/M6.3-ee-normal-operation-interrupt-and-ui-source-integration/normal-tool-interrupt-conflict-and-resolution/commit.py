import ast
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

B = Path('$HOME/.cache/learning-workbench-acceptance')
R = B / 'm62-public-safe-oct02'
O = Path(__file__).parent
read = lambda p: json.loads(p.read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()
git = lambda *args: subprocess.check_output(['git', *args], cwd=R)
prepared = read(O / 'PREPARED.json')
H, OWNER = prepared['before_head'], prepared['owner_head']
assert git('rev-parse', 'HEAD').decode().strip() == H
assert git('rev-parse', 'MERGE_HEAD').decode().strip() == OWNER
source = 'services/api/app/infrastructure/codex_turn_repository.py'
raw = (R / source).read_bytes()
assert b'<<<<<<<' not in raw and b'>>>>>>>' not in raw
assert all(word in raw for word in [b'codex-turn-event-v1', b'codex-turn-event-v2', b'codex-turn-event-v3', b'codex-turn-event-v4', b'codex-turn-event-v5'])
def method_bytes(data, method):
    lines = data.splitlines(keepends=True)
    tree = ast.parse(data)
    item = next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == method)
    return b''.join(lines[item.lineno - 1:item.end_lineno])
for name in ['_interrupt', 'cancelled_control', 'cancel_requested_control', 'replay']:
    assert method_bytes(raw, name) == method_bytes(git('show', H + ':' + source), name)
turn = 'services/api/app/application/codex_turn.py'
prior = git('show', H + ':' + turn)
expected = prior.replace(b'self.approvals.control(approvals[item.id],turn)',
                        b'self.approvals.control(approvals[item.id],turn,conn,approvals,history)')
assert expected != prior and expected == (R / turn).read_bytes()
for name in prepared['owner_paths']:
    if name not in prepared['original_overlap_paths']:
        assert (R / name).read_bytes() == git('show', OWNER + ':' + name), name
before = read(O / 'before.json')
for name, e in before['files'].items():
    if name not in prepared['owner_paths']:
        assert sha((R / name).read_bytes()) == e['sha256'], name
subprocess.run(['git', 'add', '--', source], cwd=R, check=True)
assert not git('diff', '--name-only', '--diff-filter=U')
for index, command in enumerate([['git', 'diff', '--cached', '--check'],
    ['uv', 'run', '--frozen', '--no-sync', 'ruff', 'check', '.'],
    ['uv', 'run', '--frozen', '--no-sync', 'mypy']]):
    p = subprocess.run(command, cwd=R, capture_output=True)
    (O / f'precommit-{index}.stdout').write_bytes(p.stdout)
    (O / f'precommit-{index}.stderr').write_bytes(p.stderr)
    assert p.returncode == 0
command = ['git', 'commit', '-m', 'feat(M6.3): integrate reviewed single operation and retain interrupt history']
p = subprocess.run(command, cwd=R, capture_output=True)
(O / 'commit.stdout').write_bytes(p.stdout)
(O / 'commit.stderr').write_bytes(p.stderr)
assert p.returncode == 0
head = git('rev-parse', 'HEAD').decode().strip()
assert not git('status', '--porcelain')
files = {}
for row in git('ls-tree', '-rz', head).split(b'\0'):
    if not row:
        continue
    meta, name = row.split(b'\t', 1)
    name = name.decode()
    if name.startswith('progress/'):
        continue
    data = (R / name).read_bytes()
    oid = meta.split()[2].decode()
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == oid
    files[name] = {'git_blob': oid, 'sha256': sha(data), 'bytes': len(data)}
(O / 'after.json').write_text(json.dumps({'head': head, 'count': len(files), 'files': files}, indent=2) + '\n')
report = {'status': 'NORMAL_LOCAL_OPERATION_INTERRUPT_MERGE_WITH_EXPLICIT_BOTH_VERSIONS_PRESERVED',
 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'before_head': H, 'owner_head': OWNER, 'head': head,
 'complete_nonprogress_before': before['count'], 'complete_nonprogress_after': len(files),
 'original_conflict': 'git no-commit merge exit1 in one shared repository, originalstdout/stderr preserved',
 'resolution': 'Retain both original InterruptEventEnvelopev4 and OperationControlEnvelopev5 imports/type unions/strict decoder/append dispatch, retainingv1/v2/v3; no immutable oldmodel changes',
 'original_interrupt_methods_exact': ['_interrupt', 'cancelled_control', 'cancel_requested_control', 'replay'],
 'original_turn_all_bytes_except_approval_control_arguments_exact': True,
 'all_other13_owner_paths_exact': True, 'all_preexisting_nonoverlap_byte_exact': True,
 'precommit': 'diffcheck/Ruff/mypy actualexit0; combined product gates not run yet',
 'sourcepush': False, 'boundary': 'Actual normal local merge commit only. Whole combined tests/native and independent resolution review pending; owner226PASS and old29e gates do not imply new complete acceptance. No force/reset/stash/GitHubmerge/release/deploy or actual model/host tools.'}
(O / 'READBACK.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
