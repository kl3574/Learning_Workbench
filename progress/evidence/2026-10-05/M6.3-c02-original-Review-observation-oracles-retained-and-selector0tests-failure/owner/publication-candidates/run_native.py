"""Exactly one original-budget first Review case. No rerun or server reuse."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

os.umask(0o077)
root = Path('$HOME/.cache/learning-workbench-acceptance/m63-review-history-timing-oct05')
base = Path(__file__).parent
head = 'c02e9e5c73d7da5e8e1617731fbefdf94f44f0e8'
stage = base / 'native-run-01'
stage.mkdir(mode=0o700)
for name in ('command.json', 'output.log', 'run-receipt.json', 'failure.json', 'receipt.json', 'before.json', 'after.json'):
    assert not (stage / name).exists()
def inputs():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == head
    assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True) == ''
    files = {}
    for row in subprocess.check_output(['git', 'ls-tree', '-rz', head], cwd=root).split(b'\0'):
        if not row:
            continue
        meta, name = row.decode().split('\t')
        if name.startswith('progress/'):
            continue
        mode, kind, oid = meta.split()
        value = (root / name).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest() == oid
        files[name] = dict(mode=mode, type=kind, git_blob=oid, bytes=len(value), sha256=hashlib.sha256(value).hexdigest())
    assert len(files) == 1524
    return dict(head=head, count=len(files), files=files)
def save(name, value):
    with (stage / name).open('x') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')
before = inputs()
save('before.json', before)
tmp = tempfile.mkdtemp(prefix='lwrh35-', dir='$HOME/.cache')
os.chmod(tmp, 0o700)
environment = dict(TMPDIR=tmp, LEARNING_E2E_DATA_DIR=str(Path(tmp) / 'data'),
                   LEARNING_E2E_OUTPUT_DIR=str(stage / 'results'), PYTHONDONTWRITEBYTECODE='1')
command = ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'test:e2e', '--', 'review.spec.ts', '--grep',
           '^real history and exact material review preserve original submitted text, null scores and a selected old revision after reload$']
record = dict(source=head, cwd=str(root), command=command, environment=environment,
              started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              observation_source_sha256=before['files']['tests/e2e/review.spec.ts']['sha256'],
              qualification='One local diagnostic; original30000ms/workers1/retries unchanged. Static route/status only; root cause UNKNOWN. No CI rerun.')
save('command.json', record)
start = time.monotonic()
with (stage / 'output.log').open('xb') as output:
    result = subprocess.run(command, cwd=root, env=dict(os.environ, **environment), stdout=output, stderr=subprocess.STDOUT)
finished = datetime.datetime.now(datetime.timezone.utc).isoformat()
elapsed = time.monotonic() - start
after = inputs()
save('after.json', after)
record.update(exit_code=result.returncode, finished_at=finished, elapsed_seconds=elapsed,
              source_before_after_exact=before == after, log_sha256=hashlib.sha256((stage / 'output.log').read_bytes()).hexdigest())
save('run-receipt.json', record)
print(json.dumps(record, indent=2), flush=True)
assert before == after
raise SystemExit(result.returncode)
