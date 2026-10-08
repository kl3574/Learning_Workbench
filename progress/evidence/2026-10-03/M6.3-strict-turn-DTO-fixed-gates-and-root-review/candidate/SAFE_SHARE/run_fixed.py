"""Fixed DTO-only gates with complete non-progress tracked input binding."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

ROOT = Path('$HOME/.cache/learning-workbench-acceptance/m63-turn-contract-dto-oct04')
EVIDENCE = Path(__file__).resolve().parent
HEAD = '760af1e44c5447f60ba53248fbdd694ee25c774d'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def stamp():
    return datetime.now(timezone.utc).isoformat()

def write(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def inputs():
    assert git('rev-parse', 'HEAD').decode().strip() == HEAD
    entries = {}
    for item in git('ls-tree', '-rz', '--full-tree', HEAD).split(b'\0'):
        if not item:
            continue
        meta, raw_name = item.split(b'\t', 1)
        mode, kind, object_id = meta.decode().split()
        name = raw_name.decode()
        if name.startswith('progress/'):
            continue
        assert kind == 'blob', name
        path = ROOT / name
        data = os.readlink(path).encode() if mode == '120000' else path.read_bytes()
        actual_git = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert actual_git == object_id, name
        entries[name] = {'git_blob': object_id, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return {'head': HEAD, 'scope': 'all tracked nonprogress files; only progress/ excluded; dependency links are untracked read-only reuse',
            'count': len(entries), 'files': entries}

(EVIDENCE / 'tmp').mkdir(exist_ok=True)
env = dict(os.environ, TMPDIR=str(EVIDENCE / 'tmp'), PYTHONDONTWRITEBYTECODE='1')
write('inputs-before.json', before := inputs())
runner = Path(__file__).read_bytes()
write('runner-source.json', {'name': 'run_fixed.py', 'sha256': hashlib.sha256(runner).hexdigest(), 'bytes': len(runner)})
commands = [
    ('01-focused', ['uv', 'run', '--frozen', '--no-sync', 'pytest',
        'tests/contract/test_codex_turn_dto.py', 'tests/contract/test_codex_bootstrap_dto.py',
        'tests/contract/test_provider_dto.py', 'tests/contract/test_models.py',
        'tests/contract/test_generated_transport.py', 'tests/contract/test_api_projection.py',
        'tests/contract/test_provider_binding.py', '--tb=short', '-q',
        '--basetemp', str(EVIDENCE / 'private-basetemp'), '-o', 'cache_dir=' + str(EVIDENCE / 'private-cache')]),
    ('02-ruff', ['uv', 'run', '--frozen', '--no-sync', 'ruff', 'check', '.']),
    ('03-mypy', ['uv', 'run', '--frozen', '--no-sync', 'mypy']),
    ('04-verify-spec', ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/verify_spec.py']),
    ('05-web-strict', ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'lint']),
    ('06-contract-strict', ['bash', 'scripts/node.sh', 'apps/web/node_modules/.bin/tsc', '--noEmit', '--strict',
        '--skipLibCheck', '--module', 'esnext', '--moduleResolution', 'bundler', '--target', 'es2023',
        '--lib', 'es2023,dom', 'tests/contract/codex_turn_types.ts']),
    ('07-node-version', ['bash', 'scripts/node.sh', 'node', '--version']),
]
results = []
for name, command in commands:
    start, started = time.monotonic(), stamp()
    with (EVIDENCE / (name + '.log')).open('wb') as log:
        process = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
    entry = {'name': name, 'command': command, 'started_at': started, 'finished_at': stamp(),
             'duration_seconds': time.monotonic() - start, 'exit_code': process.returncode}
    results.append(entry)
    write('gate-results.json', {'head': HEAD, 'terminal': False, 'gates': results})
    print(name, process.returncode, flush=True)
write('inputs-after.json', after := inputs())
assert before == after
write('gate-results.json', {'head': HEAD, 'terminal': True, 'gates': results,
                          'all_pass': all(row['exit_code'] == 0 for row in results),
                          'engineering_inputs_unchanged': True, 'input_count': before['count'],
                          'working_tree_status': git('status', '--porcelain').decode()})
print('terminal', before['count'], all(row['exit_code'] == 0 for row in results), flush=True)
