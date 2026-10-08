"""Fixed combined Review gate: exclusive --list, then exactly one original run."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

os.umask(0o077)
ROOT = Path('$HOME/.cache/learning-workbench-acceptance/m63-review-combined-486939-oct05')
BASE = Path(__file__).resolve().parent
HEAD = '4869393654446c1dfcb0da97b9dca5fa7429b36f'
MODE = sys.argv[1]
assert MODE in ('list', 'native')
STAGE = BASE / ('static-list-02' if MODE == 'list' else 'native-run-02')
STAGE.mkdir(mode=0o700)
for name in ('command.json', 'output.log', 'run-receipt.json', 'failure.json', 'receipt.json', 'before.json', 'after.json'):
    assert not (STAGE / name).exists()

def digest(value):
    return hashlib.sha256(value).hexdigest()

def save(name, value):
    with (STAGE / name).open('x') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')

def inputs():
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT)
    assert git('rev-parse', 'HEAD').decode().strip() == HEAD
    assert git('status', '--porcelain') == b''
    assert git('rev-parse', '--abbrev-ref', 'HEAD').decode().strip() == 'HEAD'
    files = {}
    for row in git('ls-tree', '-rz', HEAD).split(b'\0'):
        if not row:
            continue
        meta, name = row.decode().split('\t')
        if name.startswith('progress/'):
            continue
        mode, kind, oid = meta.split()
        value = (ROOT / name).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest() == oid, name
        files[name] = dict(mode=mode, type=kind, git_blob=oid, bytes=len(value), sha256=digest(value))
    assert len(files) == 1525
    assert files['PRODUCT_DESIGN.md']['sha256'] == 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
    return dict(head=HEAD, count=len(files), files=files)

before = inputs()
save('before.json', before)
if MODE == 'native':
    listed = json.loads((BASE / 'static-list-02/run-receipt.json').read_text())
    assert listed['exit_code'] == 0 and listed['selected_tests'] == 2
    assert listed['source'] == HEAD and listed['runner_sha256'] == digest(Path(__file__).read_bytes())
    assert listed['log_sha256'] == digest((BASE / 'static-list-02/output.log').read_bytes())

tmp = Path(tempfile.mkdtemp(prefix='lwr486-', dir='$HOME/.cache'))
os.chmod(tmp, 0o700)
environment = dict(TMPDIR=str(tmp), LEARNING_E2E_DATA_DIR=str(tmp / 'data'),
                   LEARNING_E2E_OUTPUT_DIR=str(STAGE / 'results'), PYTHONDONTWRITEBYTECODE='1')
command = ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'test:e2e', '--', 'tests/e2e/review.spec.ts']
if MODE == 'list':
    command.append('--list')
record = dict(source=HEAD, cwd=str(ROOT), command=command, environment=environment,
              started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              absolute_runner=str(Path(__file__).resolve()), runner_sha256=digest(Path(__file__).read_bytes()),
              input_binding_sha256=digest((BASE / 'SOURCE_BINDINGS.json').read_bytes()),
              observation_source_sha256=before['files']['tests/e2e/review.spec.ts']['sha256'],
              config_sha256=before['files']['tests/e2e/playwright.config.ts']['sha256'],
              qualification='New fixed combined source; two original Review cases once, 30000ms/workers1/defaultretry0 unchanged. No CI rerun or whole-suite claim. No screenshot or business JSON readback.')
save('command.json', record)
start = time.monotonic()
with (STAGE / 'output.log').open('xb') as output:
    result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, **environment), stdout=output, stderr=subprocess.STDOUT)
record.update(exit_code=result.returncode, finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              elapsed_seconds=time.monotonic() - start, log_sha256=digest((STAGE / 'output.log').read_bytes()))
try:
    after = inputs()
    save('after.json', after)
    record['source_before_after_exact'] = before == after
    assert before == after
    if MODE == 'list':
        log = (STAGE / 'output.log').read_text()
        selections = re.findall(r'^\s+review\.spec\.ts:\d+:\d+ › .+$', log, re.MULTILINE)
        assert len(selections) == 2 and 'Total: 2 tests in 1 file' in log
        assert ':36:1 › real history ' in selections[0]
        assert 'a delayed old review response ' in selections[1]
        record['selected_tests'] = len(selections)
except BaseException as error:
    save('failure.json', dict(kind=type(error).__name__, command_exit=result.returncode, qualification='Wrapper verification failed; original command/log preserved.'))
    save('run-receipt.json', record)
    raise
save('run-receipt.json', record)
print(json.dumps(record, indent=2), flush=True)
raise SystemExit(result.returncode)
