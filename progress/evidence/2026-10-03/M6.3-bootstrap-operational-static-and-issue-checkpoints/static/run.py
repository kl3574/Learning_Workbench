import datetime
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
OUT = Path(__file__).parent
HEAD = '7b0ee3ae7d94a0d069b873133e69b5aaf3a18c89'
sha = lambda data: hashlib.sha256(data).hexdigest()
assert not (OUT / 'before.json').exists()
def inputs():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    names = sorted(name for name in names if name and not name.startswith('progress/'))
    data = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT, input=''.join(HEAD + ':' + name + '\n' for name in names).encode())
    offset = 0
    result = {}
    for name in names:
        end = data.index(b'\n', offset)
        blob_sha, kind, length = data[offset:end].split()
        assert kind == b'blob'
        length = int(length)
        original = data[end + 1:end + 1 + length]
        current = (ROOT / name).read_bytes()
        assert current == original, name
        result[name] = {'bytes': length, 'sha256': sha(current), 'git_blob': blob_sha.decode()}
        offset = end + 2 + length
    assert offset == len(data)
    return {'head': HEAD, 'private_runner_sha256': sha(Path(__file__).read_bytes()), 'files': result}
before = inputs()
(OUT / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
commands = [
    ('ruff', ['uv', 'run', '--frozen', '--no-sync', 'ruff', 'check', '.']),
    ('mypy', ['uv', 'run', '--frozen', '--no-sync', 'mypy']),
    ('structural', ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/verify_spec.py']),
]
results = {}
for label, command in commands:
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tick = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, capture_output=True)
    log = result.stdout + result.stderr
    (OUT / (label + '.log')).write_bytes(log)
    results[label] = {'command': command, 'exit_code': result.returncode, 'start_utc': start,
                     'seconds': time.monotonic() - tick, 'log_sha256': sha(log)}
after = inputs()
(OUT / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
receipt = {'head': HEAD, 'input_count': len(before['files']), 'all_git_match': True,
           'inputs_unchanged': before == after, 'results': results,
           'scope': 'Canonical integrated source static gates. No runtime/control/model/native rerun; original failed complete gates remain unchanged.'}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
raise SystemExit(0 if before == after and all(r['exit_code'] == 0 for r in results.values()) else 1)
