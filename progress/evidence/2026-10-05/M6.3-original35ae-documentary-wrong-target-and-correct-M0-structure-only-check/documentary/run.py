"""Bounded documentary validation, not a replacement full product gate."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

root = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
out = Path(__file__).parent
assert not (out / 'receipt.json').exists()
def inputs():
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).split(b'\0')
    return {name.decode(): hashlib.sha256((root / name.decode()).read_bytes()).hexdigest()
            for name in filter(None, names)}
before = inputs()
argv = ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/verify_spec.py']
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = subprocess.run(argv, cwd=root, capture_output=True)
(out / 'stdout').write_bytes(result.stdout)
(out / 'stderr').write_bytes(result.stderr)
after = inputs()
(out / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
(out / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
(out / 'receipt.json').write_text(json.dumps({
    'argv': argv, 'started_utc': start, 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'exit_code': result.returncode, 'tracked_before_after_unchanged': before == after,
    'tracked_count': len(before),
    'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
    'stderr_sha256': hashlib.sha256(result.stderr).hexdigest(),
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    'boundary': 'Only structural spec/progress validation after documentary edits; no product/fullPython/Web/native rerun and no real model. Before/after hashes bind current dirty progress, not exact Git HEAD.'}, indent=2) + '\n')
print(result.stdout.decode(), end='')
assert before == after
raise SystemExit(result.returncode)
