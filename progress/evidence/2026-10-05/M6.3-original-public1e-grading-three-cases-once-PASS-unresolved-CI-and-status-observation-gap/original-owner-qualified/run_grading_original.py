"""One original grading run after exact list; offline local setup, no retry/remote API.

The entire evidence directory is private until an explicit finite candidate list is prepared.
No unknown listeners are inspected or killed. No raw credentials are inherited or printed.
"""

import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time

ROOT = Path('~/.cache/learning-workbench-acceptance/m63-grading-public1e-diagnosis-oct05')
EVIDENCE = Path(__file__).resolve().parent
BASE = '1e7ad7a8656c0dc8373d4181fa3002f385ed1847'
ARCHIVE = Path('~/.cache/learning-workbench-acceptance/m62-public-safe-oct02/.toolchain/node-v24.21.0-linux-x64.tar.xz')
ARCHIVE_SHA = 'fd8e59d5a511510f6a298afb548f18c7d2b1be404d8b4a27d94fbe49f56cb2d6'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path, value):
    assert not path.exists(), f'Preserve every original output: {path}'
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def manifest():
    head = git('rev-parse', 'HEAD').decode().strip()
    rows = git('ls-tree', '-rz', '--full-tree', 'HEAD').split(b'\0')
    selected = []
    for row in rows:
        if not row:
            continue
        header, raw_path = row.split(b'\t', 1)
        mode, kind, blob = header.decode().split()
        name = raw_path.decode()
        if name.startswith('progress/'):
            continue
        assert kind == 'blob', (name, kind)
        path = ROOT / name
        data = os.readlink(path).encode() if mode == '120000' else path.read_bytes()
        live_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        selected.append({'path': name, 'git_mode': mode, 'git_type': kind, 'git_blob': blob,
                         'size': len(data), 'sha256': sha(data), 'live_git_blob': live_blob,
                         'live_equals_fixed_git': live_blob == blob})
    return {'readback_utc': utc(), 'head': head, 'selection': 'All tracked Git blobs except progress/**; includes docs/ui, spec and configuration',
            'count': len(selected), 'all_live_equals_fixed_git': all(x['live_equals_fixed_git'] for x in selected), 'files': selected}


assert git('rev-parse', 'HEAD').decode().strip() == BASE
assert git('status', '--porcelain', '--untracked-files=no') == b''
original = manifest()
assert original['all_live_equals_fixed_git'] and original['count'] == 1541
write(EVIDENCE / 'ORIGINAL_GIT_INPUTS.json', original)
archive_bytes = ARCHIVE.read_bytes()
assert sha(archive_bytes) == ARCHIVE_SHA
short_root = Path(tempfile.mkdtemp(prefix='lwg-', dir='~/.cache'))
short_root.chmod(0o700)
for name in ['tmp', 'pw', 'output', 'data']:
    (short_root / name).mkdir(mode=0o700)
node_parent = ROOT / '.toolchain'
node_parent.mkdir(exist_ok=True)
local_archive = node_parent / ARCHIVE.name
assert not local_archive.exists()
local_archive.write_bytes(archive_bytes)
with tarfile.open(local_archive) as source:
    source.extractall(node_parent, filter='data')
node_bin = node_parent / 'node-v24.21.0-linux-x64/bin'
env = {'PATH': str(node_bin) + os.pathsep + os.environ['PATH'], 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
       'UV_OFFLINE': '1', 'npm_config_offline': 'true', 'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD': '1',
       'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(short_root / 'tmp'), 'PWTEST_CACHE_DIR': str(short_root / 'pw'),
       'LEARNING_E2E_OUTPUT_DIR': str(short_root / 'output'), 'LEARNING_E2E_DATA_DIR': str(short_root / 'data')}
write(EVIDENCE / 'ENVIRONMENT_BOUNDARY.json', {'source': BASE, 'created_utc': utc(), 'owned_private_root': str(short_root),
      'root_mode': oct(short_root.stat().st_mode & 0o777), 'explicit_env': env,
      'no_other_parent_environment_forwarded': True, 'original_node_archive': {'path': str(ARCHIVE), 'size': len(archive_bytes), 'sha256': ARCHIVE_SHA},
      'local_archive': {'path': str(local_archive), 'size': len(archive_bytes), 'sha256': sha(local_archive.read_bytes())},
      'original_product_timeout_ms': 30000, 'original_retry': 0, 'original_workers': 1,
      'credential_provider_model_environment_not_supplied': True,
      'new_remote_API_or_model_request': False, 'unknown_listener_scan_or_kill': False})


def stage(name, argv):
    directory = EVIDENCE / name
    directory.mkdir()
    before = manifest()
    write(directory / 'before.json', before)
    command = {'argv': argv, 'cwd': str(ROOT), 'started_utc': utc(), 'explicit_env': env,
               'runner_sha256': sha(Path(__file__).read_bytes()), 'fixed_source_head': BASE,
               'original_timeout_ms': 30000, 'original_retry': 0, 'original_workers': 1}
    write(directory / 'command.json', command)
    start = time.monotonic()
    with (directory / 'run.log').open('wb') as log:
        completed = subprocess.run(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
    after = manifest()
    write(directory / 'after.json', after)
    raw = (directory / 'run.log').read_bytes()
    changed = [a['path'] for a, b in zip(before['files'], after['files']) if a != b]
    receipt = {'exit_code': completed.returncode, 'ended_utc': utc(), 'elapsed_seconds': time.monotonic() - start,
               'run_log_size': len(raw), 'run_log_sha256': sha(raw), 'head_before': before['head'], 'head_after': after['head'],
               'selected_input_count_before': before['count'], 'selected_input_count_after': after['count'],
               'complete_before_after_files_exact': before['files'] == after['files'], 'changed_tracked_inputs': changed,
               'after_live_equals_fixed_git': after['all_live_equals_fixed_git'], 'raw_log_public_admission': False}
    write(directory / 'receipt.json', receipt)
    print(json.dumps({'stage': name, **receipt}), flush=True)
    return completed.returncode, raw


setup_code, _ = stage('setup-01', ['make', 'setup'])
if setup_code:
    write(EVIDENCE / 'STOP.json', {'reason': 'Original locked offline setup failed; no list/business run or retry', 'business': 'NOT_RUN'})
    raise SystemExit(setup_code)
selector = 'grading[.]spec[.]ts$'
list_code, raw_list = stage('original-list-01', ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'test:e2e', '--', selector, '--list'])
list_text = raw_list.decode(errors='strict')
if list_code or not re.search(r'Total: 3 tests in 1 file', list_text):
    write(EVIDENCE / 'STOP.json', {'reason': 'Original exact selector list not confirmed as three tests/one file', 'business': 'NOT_RUN', 'list_exit': list_code})
    raise SystemExit(list_code or 1)
code, log = stage('original-three-cases-01', ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'test:e2e', '--', selector])
write(EVIDENCE / 'ORIGINAL_RUN_TERMINAL.json', {'source': BASE, 'business_run_count': 1, 'run_exit_code': code,
      'original_list_three_cases': True, 'old_public_CI_failure_preserved': True, 'old_failure_cause': 'UNKNOWN',
      'business_log_sha256': sha(log), 'product_source_or_timeout_or_retries_changed': False,
      'no_repeat_until_pass': True, 'private_runtime_root': str(short_root)})
raise SystemExit(code)
