import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

root = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-native-formal-29e-owner-oct04')
evidence = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-native-formal-29e864a6-03-oct04')
expected = '29e864a6157f3bb23c6ced5d1a2f34f77bf3b875'
os.umask(0o077)

def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)

def snapshot():
    files = []
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
        files.append({'path': path, 'sha256': hashlib.sha256(content).hexdigest(), 'git_blob': blob, 'actual_blob': actual_blob, 'matches_git': actual_blob == blob})
    return {'head': git('rev-parse', 'HEAD').decode().strip(), 'status': git('status', '--porcelain').decode(), 'count': len(files), 'all_match_git': all(item['matches_git'] for item in files), 'files': files}

def write(name, value):
    (evidence / name).write_text(json.dumps(value, indent=2) + '\n')

generated = ['docs/ui/m1-after-390-directory.png', 'docs/ui/m1-after-390-agent.png', 'docs/ui/m1-after-390-long-formula.png', 'docs/ui/m1-session-three-way-conflict.png', 'docs/ui/m1-after-200-percent-native.png', 'docs/ui/m1-native-zoom-metrics.json']
for name in generated:
    (evidence / 'generated-before' / Path(name).name).write_bytes((root / name).read_bytes())
before = snapshot()
write('inputs-before.json', before)
assert before['head'] == expected and before['status'] == '' and before['count'] == 1433 and before['all_match_git']
command = ['make', 'test-e2e']
overrides = {'TMPDIR': '<LOCAL_HOME>/.cache/lwn29tmp-6619a647', 'LEARNING_E2E_DATA_DIR': str(evidence / 'data'), 'LEARNING_E2E_OUTPUT_DIR': str(evidence / 'results'), 'PYTHONDONTWRITEBYTECODE': '1'}
env = {**os.environ, **overrides}
write('command.json', {'argv': command, 'cwd': str(root), 'source_sha': expected, 'environment_overrides': overrides, 'existing_suite_config': 'tests/e2e/playwright.config.ts', 'changed_test_or_budget': False})
started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
started = time.monotonic()
print('START', started_utc, command, flush=True)
with (evidence / 'native.log').open('wb') as output:
    result = subprocess.run(command, cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT, check=False)
elapsed = time.monotonic() - started
finished_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
after = snapshot()
write('inputs-after.json', after)
for name in generated:
    (evidence / 'generated-after' / Path(name).name).write_bytes((root / name).read_bytes())
old = {v['path']: v for v in before['files']}
changes = [v['path'] for v in after['files'] if v != old[v['path']]]
source_unchanged = all(v == old[v['path']] for v in after['files'] if v['path'] not in generated) and set(changes).issubset(set(generated)) and after['head'] == expected
write('generated-output-changes.json', {'generated_paths': generated, 'actual_changed_paths': changes, 'other_1427_inputs_unchanged': source_unchanged, 'before': [v for v in before['files'] if v['path'] in generated], 'after': [v for v in after['files'] if v['path'] in generated]})
receipt = {'source_sha': expected, 'spec_sha256': hashlib.sha256((root / 'PRODUCT_DESIGN.md').read_bytes()).hexdigest(), 'argv': command, 'started_utc': started_utc, 'finished_utc': finished_utc, 'elapsed_seconds': round(elapsed, 3), 'exit_code': result.returncode, 'inputs_count': before['count'], 'before_all_match_git': before['all_match_git'], 'after_all_match_git': after['all_match_git'], 'inputs_unchanged': before == after, 'other_1427_inputs_unchanged': source_unchanged, 'actual_generated_output_changes': changes, 'native_log_sha256': hashlib.sha256((evidence / 'native.log').read_bytes()).hexdigest(), 'actual_remote_provider': 'NOT_RUN', 'actual_codex_cli_model': 'NOT_RUN', 'overall_M6_3': 'NOT_RUN', 'publication': 'PRIVATE_UNREVIEWED'}
write('receipt.json', receipt)
print(json.dumps(receipt, indent=2), flush=True)
raise SystemExit(0 if result.returncode == 0 and source_unchanged else 1)
