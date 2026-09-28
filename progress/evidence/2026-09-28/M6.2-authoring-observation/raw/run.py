"""Capture exact inputs and original output for one authorized local diagnostic gate."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

BASE = Path(__file__).resolve().parent
WORK = BASE.parent / 'm62-authoring-observation-active'
ROOTS = ['AGENTS.md', 'PRODUCT_DESIGN.md', 'Makefile', 'pyproject.toml', 'uv.lock', '.python-version', '.node-version',
         'apps', 'services', 'packages', 'migrations', 'tests', 'scripts', 'docs/adr', '.github/workflows']


def snapshot():
    paths = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', *ROOTS], cwd=WORK).decode().split('\0')
    rows = []
    for relative in sorted(set(filter(None, paths))):
        path = WORK / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        target = BASE / 'source-by-sha256' / sha
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
        rows.append({'path': relative, 'bytes': len(data), 'sha256': sha,
                     'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()})
    return rows


def main():
    name, *command = sys.argv[1:]
    if command and command[0] == '--':
        command.pop(0)
    stage = BASE / name
    stage.mkdir(exist_ok=False)
    before = snapshot()
    (stage / 'inputs-before.json').write_text(json.dumps(before, indent=2) + '\n')
    started = datetime.now(timezone.utc).isoformat()
    with (stage / 'run.log').open('wb') as output:
        result = subprocess.run(command, cwd=WORK, stdout=output, stderr=subprocess.STDOUT)
    after = snapshot()
    (stage / 'inputs-after.json').write_text(json.dumps(after, indent=2) + '\n')
    receipt = {'command': command, 'cwd': str(WORK), 'started_at': started,
        'finished_at': datetime.now(timezone.utc).isoformat(), 'exit_code': result.returncode,
        'log_sha256': hashlib.sha256((stage / 'run.log').read_bytes()).hexdigest(),
        'inputs_before_sha256': hashlib.sha256((stage / 'inputs-before.json').read_bytes()).hexdigest(),
        'inputs_after_sha256': hashlib.sha256((stage / 'inputs-after.json').read_bytes()).hexdigest(),
        'input_count': len(before), 'inputs_unchanged': before == after,
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=WORK, text=True).strip(),
        'status': subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=WORK, text=True),
        'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (stage / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    raise SystemExit(result.returncode if before == after else 97)


if __name__ == '__main__':
    main()
