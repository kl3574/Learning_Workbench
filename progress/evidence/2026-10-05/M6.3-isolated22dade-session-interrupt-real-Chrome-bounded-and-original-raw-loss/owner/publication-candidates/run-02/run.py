"""Private source-bound build and native runner; no engineering output writes."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

os.umask(0o077)
base = Path(__file__).parent
assert not any((base / name).exists() for name in ('command.json', 'run-receipt.json', 'native.log', 'build.log')), 'Refuse output overwrite'
root = Path('$HOME/.cache/learning-workbench-acceptance/m63-session-interrupt-ui-oct05')
head = '22dade7996f13634202250ef5e1c05dc976214a5'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == head
assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True) == ''
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
        mode, kind, oid = meta.split(' ')
        payload = (root / name).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest() == oid
        files[name] = dict(mode=mode, type=kind, git_blob=oid, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
    assert len(files) == 1525
    return dict(head=head, count=len(files), files=files)
before = inputs()
(base / 'runner-before.json').write_text(json.dumps(before, indent=2) + '\n')
tmp = tempfile.mkdtemp(prefix='lwint22-', dir='$HOME/.cache')
os.chmod(tmp, 0o700)
env = dict(os.environ, TMPDIR=tmp, PYTHONDONTWRITEBYTECODE='1')
commands = [(['node', str(root / 'apps/web/node_modules/vite/bin/vite.js'), 'build', '--outDir', str(base / 'dist')], root / 'apps/web', 'build'),
            (['node', str(base / 'native.mjs')], root, 'native')]
record = dict(source_sha=head, TMPDIR=tmp, started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              harness={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [base / 'native.mjs', base / 'controlled_api.py', Path(__file__)]},
              commands=[dict(command=cmd, cwd=str(cwd), label=label) for cmd, cwd, label in commands])
(base / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
steps = []
for command, cwd, label in commands:
    started = time.monotonic()
    step = dict(command=command, cwd=str(cwd), started_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    with (base / (label + '.log')).open('wb') as log:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
    step.update(exit_code=result.returncode, finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                elapsed_seconds=time.monotonic() - started, log_sha256=hashlib.sha256((base / (label + '.log')).read_bytes()).hexdigest())
    steps.append(step)
    if result.returncode:
        break
after = inputs()
(base / 'runner-after.json').write_text(json.dumps(after, indent=2) + '\n')
assert before == after
if (base / 'dist').exists():
    assets = {str(path.relative_to(base / 'dist')): dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
              for path in sorted((base / 'dist').rglob('*')) if path.is_file()}
    (base / 'built-assets.json').write_text(json.dumps(assets, indent=2) + '\n')
record.update(steps=steps, exit_code=result.returncode, finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
(base / 'run-receipt.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2), flush=True)
raise SystemExit(result.returncode)
