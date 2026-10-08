import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

root = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-turn-execution-ui-owner-oct04')
evidence = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-turn-outbound-ui-evidence-oct04/fixed-43c6a8a1')
expected = '43c6a8a157f483cdb829f97a1f77ba060801c330'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)

def snapshot():
    entries = []
    for entry in git('ls-tree', '-rz', expected).split(b'\0'):
        if not entry:
            continue
        metadata, raw_path = entry.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        path = raw_path.decode()
        if path.startswith('progress/') or kind != 'blob':
            continue
        file = root / path
        content = os.readlink(file).encode() if mode == '120000' else file.read_bytes()
        actual_blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        entries.append({'path': path, 'sha256': hashlib.sha256(content).hexdigest(), 'git_blob': blob, 'actual_blob': actual_blob, 'matches_git': actual_blob == blob})
    return {'head': git('rev-parse', 'HEAD').decode().strip(), 'status': git('status', '--porcelain').decode(), 'count': len(entries), 'all_match_git': all(item['matches_git'] for item in entries), 'files': entries}

before = snapshot()
(evidence / 'inputs-before.json').write_text(json.dumps(before, indent=2) + '\n')
assert before['head'] == expected and before['status'] == '' and before['all_match_git']
node = str(root / '.toolchain/node-v24.21.0-linux-x64/bin/node')
npm = str(root / '.toolchain/node-v24.21.0-linux-x64/bin/npm')
env = dict(os.environ)
env['PATH'] = str(root / '.toolchain/node-v24.21.0-linux-x64/bin') + os.pathsep + env['PATH']
env['TMPDIR'] = str(evidence / 'tmp')
env['PYTHONDONTWRITEBYTECODE'] = '1'
commands = [
    ('web', [node, 'apps/web/node_modules/vitest/vitest.mjs', 'run', '--root', 'apps/web'], root),
    ('strict', [node, 'apps/web/node_modules/typescript/bin/tsc', '--project', 'apps/web/tsconfig.json', '--noEmit', '--noUnusedLocals', '--noUnusedParameters'], root),
    ('build', [npm, 'run', 'build'], root / 'apps/web'),
    ('spec', ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/verify_spec.py'], root),
    ('original-contract-owner', ['uv', 'run', '--frozen', '--no-sync', 'pytest', '-q', '--basetemp', str(evidence / 'pytest-temp'), 'tests/contract/test_codex_turn_dto.py', 'tests/contract/test_codex_bootstrap_dto.py', 'tests/integration/test_codex_turn_preparation_http.py', 'tests/integration/test_codex_turn_lifecycle.py', 'tests/integration/test_codex_turn_review_boundaries.py', 'tests/integration/test_codex_bootstrap_legacy.py'], root),
]
commands.append(('outbound-owner', ['uv', 'run', '--frozen', '--no-sync', 'pytest', '-q', '--basetemp', str(evidence / 'pytest-outbound-temp'), 'tests/integration/test_codex_turn_consent_http.py', 'tests/integration/test_codex_turn_dispatch_http.py', 'tests/unit/test_provider_codex_profile.py', 'tests/unit/test_provider_codex_execution.py'], root))
results = []
for name, command, cwd in commands:
    print('START', name, flush=True)
    (evidence / (name + '.command.json')).write_text(json.dumps({'argv': command, 'cwd': str(cwd), 'TMPDIR': env['TMPDIR'], 'source_sha': expected}, indent=2) + '\n')
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    started = time.monotonic()
    with (evidence / (name + '.log')).open('w') as output:
        completed = subprocess.run(command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, check=False)
    result = {'name': name, 'exit_code': completed.returncode, 'elapsed_seconds': round(time.monotonic() - started, 3), 'started_at': started_at, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'log_sha256': hashlib.sha256((evidence / (name + '.log')).read_bytes()).hexdigest()}
    results.append(result)
    (evidence / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print('END', result, flush=True)
after = snapshot()
(evidence / 'inputs-after.json').write_text(json.dumps(after, indent=2) + '\n')
summary = {'source_sha': expected, 'spec_sha256': hashlib.sha256((root / 'PRODUCT_DESIGN.md').read_bytes()).hexdigest(), 'all_nonprogress_tracked_count': before['count'], 'before_all_match_git': before['all_match_git'], 'after_all_match_git': after['all_match_git'], 'inputs_unchanged': before == after, 'results': results, 'real_browser': 'NOT_RUN', 'real_provider': 'NOT_RUN', 'real_codex': 'NOT_RUN', 'overall_M6_3': 'NOT_RUN'}
(evidence / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2), flush=True)
raise SystemExit(0 if all(item['exit_code'] == 0 for item in results) and before == after else 1)
