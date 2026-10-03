from pathlib import Path
import hashlib
import json
import subprocess

BASE = Path(__file__).resolve().parent
WORK = BASE.parent / 'm62-authoring-observation-active'
START = 'ce42bf8cae734e49166a1472184fd9c3fa875bc7'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=WORK)


def save(path, value):
    (BASE / path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


head = git('rev-parse', 'HEAD').decode().strip()
assert head == '8b6629205a72593ab835e2c61a20b6e1eac7061e'
assert not git('status', '--porcelain')
paths = git('diff', '--name-only', START, head).decode().splitlines()
source = []
for path in paths:
    data = git('show', f'{head}:{path}')
    assert data == (WORK / path).read_bytes()
    target = BASE / 'fixed-source' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    source.append({'path': path, 'bytes': len(data), 'sha256': sha(data),
                   'git_blob': git('rev-parse', f'{head}:{path}').decode().strip()})
save('source-pins.json', {'base': START, 'head': head, 'files': source})
(BASE / 'change.patch').write_bytes(git('diff', '--binary', START, head))

stages = []
for stage in sorted(BASE.glob('[0-9][0-9]-*')):
    if not stage.is_dir():
        continue
    receipt = json.loads((stage / 'receipt.json').read_text())
    before = json.loads((stage / 'inputs-before.json').read_text())
    after = json.loads((stage / 'inputs-after.json').read_text())
    assert before == after and receipt['inputs_unchanged']
    assert sha((stage / 'run.log').read_bytes()) == receipt['log_sha256']
    assert sha((stage / 'inputs-before.json').read_bytes()) == receipt['inputs_before_sha256']
    assert sha((stage / 'inputs-after.json').read_bytes()) == receipt['inputs_after_sha256']
    matches, differences = [], []
    for item in before:
        raw = (BASE / 'source-by-sha256' / item['sha256']).read_bytes()
        assert len(raw) == item['bytes'] and sha(raw) == item['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['git_blob']
        current = git('show', f"{head}:{item['path']}")
        (matches if raw == current else differences).append(item['path'])
    stages.append({'stage': stage.name, 'exit_code': receipt['exit_code'],
                   'log_sha256': receipt['log_sha256'], 'inputs': len(before),
                   'all_original_bytes_retained': True, 'inputs_unchanged': True,
                   'candidate_exact_matches': len(matches), 'candidate_differences': differences})
save('GIT_SOURCE_BINDINGS.json', {'head': head, 'scope': 'Explicit engineering roots in run.py, not all Git files or all external runtime inputs.', 'stages': stages})
auxiliary = ['run.py', 'controlled-playwright.config.ts', 'native-tsconfig.json', 'native-tsconfig-with-types.json', 'playwright-type-bridge.d.ts']
save('invocation-files.json', [{'path': path, 'bytes': (BASE / path).stat().st_size, 'sha256': sha((BASE / path).read_bytes())} for path in auxiliary])
original = BASE.parent / 'm62-review-http-507-ci-v1'
original_paths = ['logs/pull_request-browser-108758811037.log', 'FAILURE_REPORT.md', 'failure-source-pins.json',
                  'failure-artifacts/members/authoring-groups-native-pr-d6a94-rs-after-permission-changes/error-context.md',
                  'failure-artifacts/members/authoring-groups-native-pr-d6a94-rs-after-permission-changes/test-failed-1.png']
save('original-red-bindings.json', {'cache': original.name, 'checkout': 'f74cd7a8f81a8b51abf06ae12fb62a51da3bb99d', 'cause': 'UNKNOWN',
     'files': [{'path': path, 'bytes': (original / path).stat().st_size, 'sha256': sha((original / path).read_bytes())} for path in original_paths]})
print(json.dumps({'head': head, 'source_count': len(source), 'stages': stages}, indent=2))
