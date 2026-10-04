"""One fixed-source UI check, exact complete engineering inputs before/after."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path('${HOME}/.cache/learning-workbench-acceptance/m63-session-interrupt-ui-oct05')
out = Path(__file__).parent / sys.argv[1]
expected = sys.argv[2]
argv = sys.argv[3:]
assert argv and not out.exists()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == expected
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=root)
out.mkdir()
def snapshot():
    values = {}
    for raw in filter(None, subprocess.check_output(['git', 'ls-tree', '-r', '-z', expected], cwd=root).split(b'\0')):
        info, name = raw.split(b'\t', 1)
        mode, kind, blob = info.decode().split()
        name = name.decode()
        if name.startswith('progress/'):
            continue
        data = (root / name).read_bytes()
        bound = subprocess.check_output(['git', 'show', expected + ':' + name], cwd=root)
        values[name] = {'mode': mode, 'type': kind, 'git_blob': blob, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'git_exact': data == bound}
    return values
before = snapshot()
(out / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
clock = time.monotonic()
temporary = out / 'private-temporary'
temporary.mkdir()
environment = {**os.environ, 'TMPDIR': str(temporary)}
with (out / 'run.log').open('wb') as log:
    result = subprocess.run(argv, cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT)
elapsed = time.monotonic() - clock
after = snapshot()
(out / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
receipt = {'head': expected, 'argv': argv, 'started_utc': start, 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'elapsed_seconds': elapsed, 'exit_code': result.returncode, 'inputs': len(before),
           'before_after_git_exact': before == after and all(v['git_exact'] for v in before.values()) and all(v['git_exact'] for v in after.values()),
           'log_sha256': hashlib.sha256((out / 'run.log').read_bytes()).hexdigest(),
           'explicit_environment_delta': {'TMPDIR': str(temporary)},
           'actual_external_model_calls': 'NOT_PERFORMED_BY_THIS_UI_COMMAND',
           'boundary': 'Synthetic UI/component wire only, not physical App Server/wholeM6.3 or original public35ae CI.'}
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
assert receipt['before_after_git_exact']
raise SystemExit(result.returncode)
