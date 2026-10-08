"""Record fixed source, terminal command and private original logs for bounded local gates."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

SOURCE = Path('$HOME/.cache/learning-workbench-acceptance/m71-codex-backup-synthetic-owner-oct05')
ROOT = Path(__file__).resolve().parent
UV = shutil.which('uv')
if UV is None:
    raise RuntimeError('uv unavailable before any test launch')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=SOURCE)


def snapshot():
    entries = []
    # Track engineering inputs only; never read old evidence or any runtime data.
    for name in git('ls-files', '-z').decode().split('\0'):
        if not name or name.startswith('progress/'):
            continue
        path = SOURCE / name
        raw = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
        entries.append({'path': name, 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                        'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()})
    return {'source_commit': git('rev-parse', 'HEAD').decode().strip(), 'entries': entries}


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def main():
    name, gate = sys.argv[1:3]
    target = ROOT / name
    target.mkdir(mode=0o700)
    (target / 'tmp').mkdir(mode=0o700)
    if gate == 'focused':
        command = [UV, 'run', '--frozen', '--no-sync', 'pytest', '-q',
                   'tests/integration/test_backup_codex_turn_history.py', '--basetemp', str(target / 'data')]
    elif gate == 'related':
        command = [UV, 'run', '--frozen', '--no-sync', 'pytest', '-q',
                   'tests/integration/test_backup_codex_turn_history.py',
                   'tests/integration/test_backup_codex_control_history.py',
                   'tests/integration/test_backup_session_history.py', 'tests/integration/test_backup_owner_history.py',
                   'tests/unit/test_backup_command.py', 'tests/unit/test_session_backup.py',
                   '--basetemp', str(target / 'data')]
    elif gate == 'ruff':
        command = [UV, 'run', '--frozen', '--no-sync', 'ruff', 'check',
                   'tests/integration/test_backup_codex_turn_history.py']
    elif gate == 'diff':
        command = ['git', 'diff', '--check', 'd6d4d9b98316d7f3790eb60e5d1bb4aca67450d1..HEAD']
    else:
        raise ValueError('Unknown bounded gate')
    before = snapshot()
    write(target / 'before.json', before)
    env = {'PATH': str(Path(UV).parent) + ':/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
           'UV_OFFLINE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1',
           'TMPDIR': str(target / 'tmp')}
    write(target / 'command.json', {'argv': command, 'cwd': str(SOURCE), 'env': env, 'gate': gate,
                                   'source_commit': before['source_commit']})
    start = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    with (target / 'run.log').open('wb') as log:
        result = subprocess.run(command, cwd=SOURCE, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    after = snapshot()
    write(target / 'after.json', after)
    receipt = {'source_commit': before['source_commit'], 'start_utc': start,
               'end_utc': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': time.monotonic() - clock,
               'exit_code': result.returncode, 'status': 'PASS' if result.returncode == 0 else 'FAIL',
               'engineering_inputs': len(before['entries']), 'source_inputs_unchanged': before == after,
               'original_log_sha256': hashlib.sha256((target / 'run.log').read_bytes()).hexdigest(),
               'scope': 'bounded synthetic backup tests or related local gate; no M7 restore acceptance',
               'external_model_requests': 0, 'approval_import_new_owner_coverage': 'NOT_RUN',
               'workspace_restore_preview_commit': 'NOT_RUN', 'full_platform_gate': 'NOT_RUN'}
    write(target / 'receipt.json', receipt)
    print(json.dumps(receipt, sort_keys=True))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
