"""Private execution record; never imports production secrets or data."""

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m61-question-validation-extract-v1')
EVIDENCE = Path(__file__).resolve().parent
PYTHON = Path('<LOCAL_HOME>/Desktop/learning/Learning_Workbench/.venv/bin/python')
OWNED = [
    'services/api/app/application/question_solution_validation.py',
    'services/api/app/application/import_parse_package.py',
    'tests/unit/test_question_solution_validation.py',
]
COMMANDS = {
    'pure-and-package': [str(PYTHON), '-m', 'pytest', '-vv', 'tests/unit/test_question_solution_validation.py'],
    'import-regressions': [str(PYTHON), '-m', 'pytest', '-q',
        'tests/unit/test_import_parsing.py', 'tests/unit/test_import_budgets.py',
        'tests/contract/test_package_integrity.py',
        'tests/integration/test_import_repository.py', 'tests/integration/test_import_http.py',
        'tests/integration/test_document_imports.py'],
    'ruff': [str(PYTHON), '-m', 'ruff', 'check', *OWNED],
    'mypy': [str(PYTHON), '-m', 'mypy', *OWNED[:2]],
    'diff-check': ['git', 'diff', '--check'],
}


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def snapshot():
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = sorted({name for name in tracked if name and not name.startswith('progress/')} | set(OWNED))
    index = {}
    for line in subprocess.check_output(['git', 'ls-files', '--stage'], cwd=ROOT).decode().splitlines():
        entry, name = line.split('\t', 1)
        index[name] = entry.split()[1]
    rows = []
    for name in paths:
        path = ROOT / name
        data = path.read_bytes()
        git_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        rows.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(),
                     'size': len(data), 'mode': oct(path.stat().st_mode & 0o777),
                     'mtime_ns': path.stat().st_mtime_ns, 'git_blob': git_blob,
                     'index_blob': index.get(name), 'matches_index': git_blob == index.get(name)})
    content = [{k: row[k] for k in ('path', 'sha256', 'size', 'mode')} for row in rows]
    return {'observed_at': now(), 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'status': subprocess.check_output(['git', 'status', '--porcelain=v1', '-uall'], cwd=ROOT, text=True),
            'scope': 'All tracked repository files except progress/ plus all three owned paths; not a complete external environment closure.',
            'aggregate_sha256': hashlib.sha256(json.dumps(content, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'files': rows}


def main():
    label = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
    command = COMMANDS[sys.argv[1]]
    folder = EVIDENCE / 'runs' / label
    folder.mkdir(parents=True, exist_ok=False)
    if '-m' in command and 'pytest' in command:
        command = [*command, '--basetemp', str(folder/'pytest-temp')]
    environment = {'python': sys.version, 'executable': sys.executable,
                   'resolved_executable_sha256': hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
                   'packages': sorted((dist.metadata['Name'], dist.version) for dist in importlib.metadata.distributions())}
    write(folder/'environment.json', environment)
    before = snapshot()
    write(folder/'before.json', before)
    receipt = {'command': command, 'cwd': str(ROOT), 'started_at': now(), 'status': 'RUNNING',
               'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    write(folder/'receipt.json', receipt)
    start = time.monotonic()
    with (folder/'stdout.log').open('wb') as stdout, (folder/'stderr.log').open('wb') as stderr:
        completed = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, check=False)
    receipt.update(ended_at=now(), duration_seconds=time.monotonic()-start,
                   exit_code=completed.returncode, status='PASS' if completed.returncode == 0 else 'FAIL')
    after = snapshot()
    write(folder/'after.json', after)
    receipt.update(input_bytes_modes_unchanged=before['aggregate_sha256'] == after['aggregate_sha256'],
                   input_timestamps_unchanged=before['files'] == after['files'],
                   input_count=len(before['files']),
                   input_aggregate_sha256_before=before['aggregate_sha256'],
                   input_aggregate_sha256_after=after['aggregate_sha256'])
    receipt['logs'] = {name: hashlib.sha256((folder/name).read_bytes()).hexdigest()
                       for name in ['stdout.log', 'stderr.log']}
    write(folder/'receipt.json', receipt)
    print(json.dumps(receipt, indent=2))
    print((folder/'stdout.log').read_text())
    print((folder/'stderr.log').read_text())
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
