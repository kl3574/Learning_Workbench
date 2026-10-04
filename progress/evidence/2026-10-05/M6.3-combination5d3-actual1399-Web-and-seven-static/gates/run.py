"""Fixed complete Git-input binding for ordinary HTTP and static gates only."""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

root = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
out = Path(__file__).parent / sys.argv[1]
command = sys.argv[2:]
assert command and not out.exists()
out.mkdir()
def sha(b):
    return hashlib.sha256(b).hexdigest()
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)
head = git('rev-parse', 'HEAD').decode().strip()
assert head == '5d3aa2032d148c668dd10a2e46b74b21e3203fb0'
assert not git('status', '--porcelain')
def snapshot():
    entries = {}
    for record in git('ls-tree', '-r', '-z', head).split(b'\0'):
        if not record:
            continue
        meta, name = record.split(b'\t', 1)
        name = name.decode()
        if name.startswith('progress/'):
            continue
        mode, kind, oid = meta.split()
        assert kind == b'blob'
        data = (root / name).read_bytes()
        assert data == git('show', head + ':' + name), name
        entries[name] = {'git_blob': oid.decode(), 'git_mode': mode.decode(), 'git_type': kind.decode(), 'sha256': sha(data), 'bytes': len(data)}
    return {'head': head, 'count': len(entries), 'files': entries}
before = snapshot()
assert before['count'] == 1524
(out / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
(out / 'command.json').write_text(json.dumps({'command': command, 'cwd': str(root)}, indent=2) + '\n')
tmp = out / 'tmp'
tmp.mkdir(mode=0o700)
env = {**os.environ, 'TMPDIR': str(tmp)}
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
tick = time.monotonic()
with (out / 'run.log').open('wb') as log:
    process = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, env=env)
elapsed = time.monotonic() - tick
after = snapshot()
(out / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
assert before == after and git('rev-parse', 'HEAD').decode().strip() == head and not git('status', '--porcelain')
receipt = {'status': 'PASS' if process.returncode == 0 else 'ORIGINAL_GATE_FAIL_RETAINED',
           'head': head, 'command': command, 'started_at': start,
           'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'exit_code': process.returncode, 'elapsed_seconds': elapsed,
           'complete_nonprogress_git_inputs': before['count'], 'before_after_git_exact': True,
           'log_sha256': sha((out / 'run.log').read_bytes()),
           'boundary': 'Actual ordinary Web/static command at reviewed combination5d3. Three test-only22eb paths exact,1522/1524 candidate inputs exact; README and exact archivalattributes documentary exceptions. Original412 full132P1F/480focused1P1F/oldwronginvocationFAILs remain. New specificJSON/synchronouschain gap independently closedat22 only, no allReacteffect guarantee. Rootisolated22 fullnative is separateRUNNING, not borrowed d69full133PASS. No actual provider/CLI/hosttool or wholeM6_3/AC21 acceptance. Complete Git maps bound each command.'}
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
raise SystemExit(process.returncode)
