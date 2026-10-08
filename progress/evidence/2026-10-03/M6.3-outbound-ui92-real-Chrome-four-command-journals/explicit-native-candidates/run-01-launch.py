"""Bounded private invocation of the three root-read fixed native fixtures."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
base = Path(__file__).parent
out = base / 'run-01'
out.mkdir(mode=0o700)
root = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-outbound-native-owner-oct04')
expected = '92c8836c5729c0a7a128a3a128d9e62c997da657'
files = ['native.mjs', 'controlled_api.py', 'trusted_setup.py']
for name in files:
    (out / name).write_bytes((base / name).read_bytes())

def snapshot():
    records = []
    for row in subprocess.check_output(['git', 'ls-tree', '-rz', expected], cwd=root).split(b'\0'):
        if not row:
            continue
        metadata, raw_path = row.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        path = raw_path.decode()
        if path.startswith('progress/') or kind != 'blob':
            continue
        value = os.readlink(root / path).encode() if mode == '120000' else (root / path).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest()
        records.append({'path': path, 'git_blob': oid, 'actual_blob': actual, 'matches_git': actual == oid, 'sha256': hashlib.sha256(value).hexdigest()})
    return {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
            'status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True), 'count': len(records), 'files': records}

before = snapshot()
(out / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n')
assert before['head'] == expected and before['status'] == '' and all(v['matches_git'] for v in before['files'])
command = [str(root / '.toolchain/node-v24.21.0-linux-x64/bin/node'), str(out / 'native.mjs')]
env = dict(os.environ)
env['TMPDIR'] = (base / 'SHORT_TMPDIR.txt').read_text().strip()
env['PYTHONDONTWRITEBYTECODE'] = '1'
binding = {'command': command, 'cwd': str(root), 'TMPDIR': env['TMPDIR'], 'source_sha': expected,
           'harness': {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in files}}
(out / 'command.json').write_text(json.dumps(binding, indent=2) + '\n')
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
clock = time.monotonic()
with (out / 'run.log').open('wb') as log:
    result = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
after = snapshot()
(out / 'source-after.json').write_text(json.dumps(after, indent=2) + '\n')
receipt = {**binding, 'started_at': started, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - clock,
           'complete_nonprogress_inputs': before['count'], 'before_after_exact': before == after,
           'log_sha256': hashlib.sha256((out / 'run.log').read_bytes()).hexdigest(),
           'boundary': 'Real local Chrome and app HTTP. Explicit synthetic-only fixture, actual CLI/model/provider NOT_RUN.'}
(out / 'COMMAND_READBACK.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2), flush=True)
raise SystemExit(result.returncode if before == after else 99)
