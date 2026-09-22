from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m61-groups-active')
CACHE = Path(__file__).resolve().parent

def now():
    return datetime.now(UTC).isoformat()

def snapshot():
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    records = []
    for name in sorted(set(names)):
        path = ROOT / name
        if not name or name.startswith('progress/') or not path.is_file():
            continue
        data = path.read_bytes()
        stat = path.stat()
        records.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                        'mtime_ns': stat.st_mtime_ns, 'mode': stat.st_mode})
    return records

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

label, *command = sys.argv[1:]
run = CACHE / label
run.mkdir(exist_ok=False)
before = snapshot()
write(run / 'inputs-before.json', before)
for row in before:
    if row['path'] in {'tests/integration/test_authoring_group_provider.py', 'tests/integration/test_authoring_group_recovery.py'} or row['path'].startswith('services/api/app/application/authoring_group') or row['path'] == 'services/api/app/infrastructure/authoring_group_repository.py':
        target = run / 'source' / row['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / row['path']).read_bytes())
started = now()
start = time.monotonic()
with (run / 'output.log').open('wb') as log:
    result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
ended = now()
after = snapshot()
write(run / 'inputs-after.json', after)
left, right = ({row['path']: row for row in rows} for rows in (before, after))
changed = [name for name in sorted(set(left) | set(right)) if left.get(name) != right.get(name)]
log = (run / 'output.log').read_bytes()
receipt = {'command': command, 'cwd': str(ROOT), 'started_at': started, 'ended_at': ended,
           'duration_seconds': time.monotonic() - start, 'exit_code': result.returncode,
           'log_sha256': hashlib.sha256(log).hexdigest(), 'log_bytes': len(log),
           'source_snapshot_scope': 'all tracked and untracked non-ignored files except progress evidence',
           'before_count': len(before), 'after_count': len(after), 'input_changes': changed,
           'before_aggregate': hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
           'after_aggregate': hashlib.sha256(json.dumps(after, sort_keys=True).encode()).hexdigest(),
           'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
write(run / 'receipt.json', receipt)
print('Raw output retained at', run / 'output.log')
print(json.dumps(receipt, ensure_ascii=False))
sys.exit(result.returncode)
