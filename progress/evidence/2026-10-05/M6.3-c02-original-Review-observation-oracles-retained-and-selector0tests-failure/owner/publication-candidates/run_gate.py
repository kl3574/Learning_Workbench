"""Each stage owns a new directory; never overwrites prior dynamic evidence."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.umask(0o077)
base = Path(__file__).parent
root = Path('$HOME/.cache/learning-workbench-acceptance/m63-review-history-timing-oct05')
stage = base / sys.argv[1]
command = sys.argv[2:]
assert command
stage.mkdir(mode=0o700)
def inputs():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    files = {}
    for row in subprocess.check_output(['git', 'ls-tree', '-rz', head], cwd=root).split(b'\0'):
        if not row:
            continue
        meta, name = row.decode().split('\t')
        if name.startswith('progress/'):
            continue
        mode, kind, oid = meta.split()
        value = (root / name).read_bytes()
        files[name] = dict(mode=mode, type=kind, git_blob=oid, bytes=len(value), sha256=hashlib.sha256(value).hexdigest())
    return dict(head=head, status=subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True), count=len(files), files=files)
def save(name, data):
    with (stage / name).open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
before = inputs()
save('before.json', before)
record = dict(source=before['head'], command=command, cwd=str(root), started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
save('command.json', record)
started = time.monotonic()
with (stage / 'output.log').open('xb') as f:
    result = subprocess.run(command, cwd=root, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), stdout=f, stderr=subprocess.STDOUT)
after = inputs()
save('after.json', after)
record.update(exit_code=result.returncode, finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - started,
              inputs_equal=before == after, log_sha256=hashlib.sha256((stage / 'output.log').read_bytes()).hexdigest())
save('receipt.json', record)
print(json.dumps(record, indent=2), flush=True)
assert before == after
raise SystemExit(result.returncode)
