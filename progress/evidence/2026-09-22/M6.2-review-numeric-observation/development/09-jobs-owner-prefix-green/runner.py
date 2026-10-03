"""Bounded checks with tracked and untracked source bytes and real Git identities."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent / 'm62-review-numeric-observation-active'
PYTHON = '<LOCAL_HOME>/Desktop/learning/Learning_Workbench/.venv/bin/python'
os.umask(0o077)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def snapshot():
    tracked = {}
    for entry in subprocess.check_output(['git', 'ls-files', '-s', '-z'], cwd=ROOT).decode().split('\0'):
        if entry:
            meta, name = entry.split('\t', 1)
            tracked[name] = meta.split()[1]
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    rows = []
    for name in sorted(set(tracked) | set(untracked)):
        if not name or name.startswith('progress/'):
            continue
        path = ROOT / name
        if path.is_file():
            raw = path.read_bytes()
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            rows.append({'path': name, 'bytes': len(raw), 'sha256': sha(raw), 'git_blob': tracked.get(name),
                         'git_matches': blob == tracked[name] if name in tracked else None})
    return rows

out = BASE / sys.argv[1]
out.mkdir(mode=0o700, exist_ok=False)
(out / 'tmp').mkdir()
mode = sys.argv[2]
command = [PYTHON, '-m', mode, *sys.argv[3:]]
if mode == 'pytest':
    command += ['-p', 'no:cacheprovider']
before = snapshot()
write(out / 'inputs-before.json', before)
for name in ['services/api/app/application/review_numeric_models.py', 'services/api/app/application/review_numeric.py', 'services/api/app/application/authoring_numeric_service.py', 'services/api/app/application/authoring_group_numeric_service.py', 'services/api/app/infrastructure/authoring_numeric_repository.py', 'services/api/app/infrastructure/authoring_group_numeric_repository.py', 'tests/integration/test_review_numeric_observations.py', 'services/api/app/infrastructure/authoring_job_repository.py']:
    dest = out / 'source' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if (ROOT / name).exists():
        shutil.copyfile(ROOT / name, dest)
shutil.copyfile(__file__, out / 'runner.py')
env = {**os.environ, 'TMPDIR': str(out / 'tmp'), 'PYTHONDONTWRITEBYTECODE': '1'}
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
clock = time.monotonic()
with (out / 'run.log').open('wb') as log:
    try:
        code = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                              timeout=300, check=False).returncode
    except subprocess.TimeoutExpired:
        code = 124
finished = datetime.datetime.now(datetime.timezone.utc).isoformat()
after = snapshot()
write(out / 'inputs-after.json', after)
raw = (out / 'run.log').read_bytes()
receipt = {'command': command, 'cwd_alias': 'm62-review-numeric-observation-active', 'started_at': started, 'finished_at': finished,
           'elapsed_seconds': time.monotonic() - clock, 'exit_code': code, 'runner_timeout_seconds': 300,
           'source_count': len(before), 'source_unchanged': before == after,
           'log_sha256': sha(raw), 'log_bytes': len(raw),
           'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
           'runner_sha256': sha(Path(__file__).read_bytes()),
           'scope': 'Only declared command; private synthetic data/processes, no shared listening ports or vendor calls. Untracked sources have null Git identity.'}
write(out / 'receipt.json', receipt)
print(json.dumps(receipt, indent=2), flush=True)
