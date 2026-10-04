import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

R = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-turn-interrupt-owner-oct04')
O = Path(__file__).parent
H = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
assert H.startswith('cc2cc675') and not (O / 'receipt.json').exists()
sha = lambda b: hashlib.sha256(b).hexdigest()

def inputs():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip() == H
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=R)
    values = {}
    for row in subprocess.check_output(['git', 'ls-tree', '-rz', H], cwd=R).split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        if name.startswith(b'progress/'):
            continue
        path, oid = name.decode(), meta.split()[2].decode()
        data = (R / path).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == oid
        values[path] = {'git_blob': oid, 'sha256': sha(data), 'bytes': len(data)}
    return {'head': H, 'count': len(values), 'files': values}

before = inputs()
(O / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
(O / 'tmp').mkdir(mode=0o700)
cmd = ['uv', 'run', '--frozen', '--no-sync', 'pytest', 'tests/integration/test_codex_turn_interrupt_http.py', '--tb=line', '--basetemp', str(O / 'basetemp')]
start = time.monotonic()
with (O / 'run.log').open('wb') as log:
    result = subprocess.run(cmd, cwd=R, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'TMPDIR': str(O / 'tmp')})
after = inputs()
assert after == before
(O / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
receipt = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'head': H, 'command': cmd, 'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - start, 'log_sha256': sha((O / 'run.log').read_bytes()), 'complete_nonprogress_inputs': before['count'], 'before_after_exact': True, 'scope': 'First actual tests for already specified interrupt route. Production parent fdd unchanged, only new test. No current source fix or fake handler success.', 'actual_external_requests': 0}
(O / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
raise SystemExit(result.returncode)
