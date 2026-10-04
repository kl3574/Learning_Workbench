"""Stage exact verified documentary paths; preserve original check outcomes."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

base = Path('$HOME/.cache/learning-workbench-acceptance')
root = base / 'm62-public-safe-oct02'
out = Path(__file__).parent
checkpoint = base / 'm63-412abe-progress-checkpoint-oct05'
plan = json.loads((checkpoint / 'installer-review-v2-PREPARED07/PLAN.json').read_text())
recovery = json.loads((checkpoint / 'ROLL_FORWARD_READBACK.json').read_text())
git = lambda *a: subprocess.check_output(['git', *a], cwd=root)
assert git('rev-parse', 'HEAD').decode().strip() == plan['expected_head']
assert not git('diff', '--cached', '--name-only')
paths = sorted({e['path'] for e in plan['packet_files']} | set(plan['originals']))
ignored = recovery['ignored_explicit_candidate']
assert len(ignored) == 1 and all(n in paths for n in ignored)
names = [n for n in paths if n not in ignored]
(out / 'pathspec.nul').write_bytes(b'\0'.join(n.encode() for n in names) + b'\0')
commands = [
    ['git', 'add', '--pathspec-from-file=' + str(out / 'pathspec.nul'), '--pathspec-file-nul'],
    ['git', 'add', '-f', '--', ignored[0]],
]
for i, command in enumerate(commands):
    process = subprocess.run(command, cwd=root, capture_output=True)
    (out / f'stage-{i}.stdout').write_bytes(process.stdout)
    (out / f'stage-{i}.stderr').write_bytes(process.stderr)
    assert process.returncode == 0
(out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
staged = set(git('diff', '--cached', '--name-only').decode().splitlines())
assert staged == set(paths) and len(paths) == 718
command = ['git', 'diff', '--cached', '--check']
process = subprocess.run(command, cwd=root, capture_output=True)
(out / 'original-diff-check.stdout').write_bytes(process.stdout)
(out / 'original-diff-check.stderr').write_bytes(process.stderr)
receipt = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'head': plan['expected_head'], 'exact_explicit_staged_paths': len(paths),
    'force_only_exact_approved_ignored_archive': ignored,
    'command': command, 'exit_code': process.returncode,
    'stdout_sha256': hashlib.sha256(process.stdout).hexdigest(),
    'stderr_sha256': hashlib.sha256(process.stderr).hexdigest(),
    'boundary': 'Actual original documentary diff check. No product test, sourcepush, ignore-rule expansion or original evidence mutation.'}
(out / 'original-diff-check-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
