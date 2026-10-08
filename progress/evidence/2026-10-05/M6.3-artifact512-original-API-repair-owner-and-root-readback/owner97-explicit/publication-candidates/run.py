"""Fixed-source bounded regression invocation; preserves every original log."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.umask(0o077)
root = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-artifact-ui-owner-oct04')
base = Path(__file__).parent
name, *command = sys.argv[1:]
out = base / name
out.mkdir(mode=0o700)
expected = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()

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
        data = os.readlink(root / path).encode() if mode == '120000' else (root / path).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        records.append({'path': path, 'git_blob': oid, 'actual_blob': actual,
                        'matches_git': actual == oid, 'sha256': hashlib.sha256(data).hexdigest()})
    return {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
            'status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True),
            'count': len(records), 'files': records}

before = snapshot()
(out / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n')
assert before['status'] == '' and all(item['matches_git'] for item in before['files'])
source = root / 'tests/integration/test_codex_artifact_repair_boundaries.py'
(out / source.name).write_bytes(source.read_bytes())
env = dict(os.environ)
env['TMPDIR'] = str(base / 'tmp')
env['PYTHONDONTWRITEBYTECODE'] = '1'
binding = {'source_sha': expected, 'command': command, 'cwd': str(root), 'TMPDIR': env['TMPDIR'],
           'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'test_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
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
           'boundary': 'Actual local HTTP/owners with explicit synthetic memory peer; no CLI/remote model/tool process.'}
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2), flush=True)
raise SystemExit(result.returncode if before == after else 99)
