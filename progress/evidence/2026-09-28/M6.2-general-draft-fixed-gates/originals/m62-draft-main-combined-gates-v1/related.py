"""Freeze exact local HTTP slice inputs and command output; not a product gate itself."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

root = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-draft-combined-active')
cache = Path(__file__).resolve().parent
commands = {
    '02-focused-final': ['.venv/bin/python', '-m', 'pytest', 'tests/integration/test_draft_edit_http.py', '-q'],
    '03-related': ['.venv/bin/python', '-m', 'pytest', 'tests/integration/test_draft_edit_http.py',
                   'tests/integration/test_draft_edits.py', 'tests/integration/test_draft_edit_boundaries.py',
                   'tests/integration/test_draft_edit_integrity.py', 'tests/integration/test_review_http.py',
                   'tests/integration/test_draft_publication_http.py', 'tests/contract/test_api_projection.py',
                   'tests/contract/test_draft_edit_projection.py', '-q'],
    '03b-related-final': ['.venv/bin/python', '-m', 'pytest', 'tests/integration/test_draft_edit_http.py',
                   'tests/integration/test_draft_edits.py', 'tests/integration/test_draft_edit_boundaries.py',
                   'tests/integration/test_draft_edit_integrity.py', 'tests/integration/test_review_http.py',
                   'tests/integration/test_draft_publication_http.py', 'tests/contract/test_api_projection.py',
                   'tests/contract/test_draft_edit_projection.py', '-q'],
    '04-ruff': ['.venv/bin/python', '-m', 'ruff', 'check', 'services/api/app/draft_dto.py',
                'services/api/app/interfaces/draft_http.py', 'services/api/app/main.py',
                'scripts/schema_types.py', 'tests/integration/test_draft_edit_http.py',
                'tests/contract/test_draft_edit_projection.py', 'tests/contract/test_api_projection.py'],
    '04b-ruff-final': ['.venv/bin/python', '-m', 'ruff', 'check', 'services/api/app/draft_dto.py',
                'services/api/app/interfaces/draft_http.py', 'services/api/app/main.py',
                'scripts/schema_types.py', 'tests/integration/test_draft_edit_http.py',
                'tests/contract/test_draft_edit_projection.py', 'tests/contract/test_api_projection.py'],
    '10-contract-focused': ['.venv/bin/python', '-m', 'pytest', 'tests/contract/test_api_projection.py',
                'tests/contract/test_draft_edit_projection.py', '-q'],
    '05-mypy': ['.venv/bin/python', '-m', 'mypy', 'services/api/app'],
    '06-spec': ['.venv/bin/python', 'scripts/verify_spec.py'],
    '07-generated': ['.venv/bin/python', 'scripts/generate_contracts.py', '--check'],
    '08-web-lint': ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'lint'],
    '09-web-build': ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'build'],
}
name = sys.argv[1]
command = commands[name]
stage = cache / name
stage.mkdir(exist_ok=False)


def write(path: str, value: object) -> None:
    (stage / path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=root)


def inputs() -> list[dict]:
    tracked: dict[str, tuple[str, str]] = {}
    for item in git('ls-files', '--stage', '-z').split(b'\0'):
        if not item:
            continue
        metadata, path = item.split(b'\t', 1)
        mode, blob, stage_number = metadata.decode().split()
        assert stage_number == '0'
        tracked[path.decode()] = (mode, blob)
    others = [path.decode() for path in git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if path]
    rows = []
    for name in sorted(set(tracked) | set(others)):
        if name.startswith('progress/'):
            continue
        path = root / name
        payload = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
        mode, committed = tracked.get(name, ('100644', None))
        rows.append({'path': name, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
                     'git_mode': mode, 'actual_blob': blob, 'indexed_blob': committed,
                     'git_matches': committed == blob})
    return rows


start_head = git('rev-parse', 'HEAD').decode().strip()
before = inputs()
write('inputs-before.json', {'head': start_head, 'files': before})
started = datetime.now(timezone.utc).isoformat()
begin = time.monotonic()
timed_out = False
with (stage / 'test.log').open('wb') as output:
    process = subprocess.Popen(command, cwd=root, stdout=output, stderr=subprocess.STDOUT,
                               start_new_session=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    try:
        exit_code = process.wait(timeout=1500)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        exit_code = process.returncode
finished = datetime.now(timezone.utc).isoformat()
after = inputs()
write('inputs-after.json', {'head': git('rev-parse', 'HEAD').decode().strip(), 'files': after})
log = (stage / 'test.log').read_bytes()
receipt = {'command': command, 'cwd': str(root), 'head': start_head,
           'start': started, 'finish': finished, 'seconds': time.monotonic() - begin,
           'pid': process.pid, 'exit_code': exit_code, 'timeout': timed_out,
           'input_count': len(before), 'inputs_unchanged': before == after,
           'log_sha256': hashlib.sha256(log).hexdigest(), 'log_bytes': len(log),
           'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
write('receipt.json', receipt)
print(json.dumps(receipt, indent=2))
print(log.decode(errors='replace')[-3500:])
sys.exit(0 if exit_code == 0 and not timed_out and before == after else 1)
