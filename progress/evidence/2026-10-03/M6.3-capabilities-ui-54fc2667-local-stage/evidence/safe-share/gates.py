import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

root = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-capabilities-ui-oct03')
out = Path(__file__).parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def inputs():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    result = {}
    for path in paths:
        if path and not path.startswith('progress/'):
            data = (root / path).read_bytes()
            git = subprocess.check_output(['git', 'show', head + ':' + path], cwd=root)
            assert git == data, path
            result[path] = {'sha256': sha(data), 'bytes': len(data)}
    return {'head': head, 'tracked': result, 'count': len(result), 'runner_sha256': sha(Path(__file__).read_bytes())}

commands = {
    'focused': ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'test', '--', 'src/features/codex', 'src/features/authoring/AuthoringPanel.test.tsx', 'src/features/authoring/AuthoringPanelLifecycle.test.tsx', 'src/features/authoring/AuthoringShellAdmission.test.tsx'],
    'strict': ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'lint'],
    'native-types': ['bash', 'scripts/node.sh', './apps/web/node_modules/.bin/tsc', '--noEmit', '-p', 'tests/e2e/tsconfig.json'],
    'native': ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'test:e2e', '--', 'codex-capabilities.spec.ts', '--workers=1', '--retries=0'],
}
name = sys.argv[1]
command = commands[name]
assert not (out / (name + '-receipt.json')).exists()
before = inputs()
(out / (name + '-before.json')).write_text(json.dumps(before, indent=2) + '\n')
env = os.environ.copy()
env['TMPDIR'] = '<LOCAL_HOME>/.cache/lw-codex-ui'
Path(env['TMPDIR']).mkdir(exist_ok=True)
env['LEARNING_E2E_OUTPUT_DIR'] = str(out / (name + '-artifacts'))
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
stamp = time.monotonic()
with (out / (name + '.log')).open('wb') as log:
    result = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
after = inputs()
(out / (name + '-after.json')).write_text(json.dumps(after, indent=2) + '\n')
receipt = {'head': before['head'], 'command': command, 'started_at': started, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'duration_seconds': round(time.monotonic() - stamp, 3), 'exit_code': result.returncode, 'input_count': before['count'],
           'inputs_unchanged': before == after, 'log_sha256': sha((out / (name + '.log')).read_bytes()),
           'scope': 'All tracked nonprogress Git bytes and actual private runner; excludes progress, ignored tools/runtime/caches. No model turn by this gate.'}
(out / (name + '-receipt.json')).write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt), flush=True)
print((out / (name + '.log')).read_text()[-2500:])
assert before == after
sys.exit(result.returncode)
