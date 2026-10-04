import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

B = Path('$HOME/.cache/learning-workbench-acceptance')
R = B / 'm62-public-safe-oct02'
O = Path(__file__).parent
ORIGINAL = '69029bc1ab355efdbb6e0fdb8a86204c59cea71a'
FINAL_DTO = '8da88ed890a25ee9ed6753fb6b4599625e449bf8'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=R)

def inputs():
    head = git('rev-parse', 'HEAD').decode().strip()
    result = {}
    for entry in git('ls-tree', '-rz', '--full-tree', head).split(b'\0'):
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        name = raw_name.decode()
        if name.startswith('progress/'):
            continue
        assert kind == b'blob'
        data = os.readlink(R / name).encode() if mode == b'120000' else (R / name).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == oid.decode()
        result[name] = {'git_blob': oid.decode(), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return {'head': head, 'files': result, 'count': len(result)}

assert not (O / 'receipt.json').exists()
assert git('rev-parse', 'HEAD').decode().strip() == ORIGINAL and not git('status', '--porcelain')
before = inputs()
(O / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
for label, commit in [('seam', '760af1e44c5447f60ba53248fbdd694ee25c774d'), ('revision-fix', FINAL_DTO)]:
    result = subprocess.run(['git', 'cherry-pick', commit], cwd=R, capture_output=True)
    (O / (label + '.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, 'Keep actual conflict/failure; no reset or overwrite'
after = inputs()
assert not git('status', '--porcelain')
changes = git('diff', '--name-only', ORIGINAL, after['head']).decode().splitlines()
bindings = json.loads((B / 'm63-turn-contract-dto-evidence-oct04/SOURCE_BINDINGS.json').read_text())
expected = sorted(path for path in bindings['changed_paths'] if path != 'tests/contract/test_api_projection.py')
assert changes == expected and len(changes) == 8
for name in changes:
    assert (R / name).read_bytes() == git('show', FINAL_DTO + ':' + name)
for name, facts in before['files'].items():
    if name not in changes:
        assert after['files'][name] == facts
assert before['count'] == 1387 and after['count'] == 1394
(O / 'after-integration.json').write_text(json.dumps(after, indent=2) + '\n')
helper_inputs = json.loads((B / 'm63-turn-contract-dto-evidence-oct04/fixed-8da88ed8/inputs-after.json').read_text())
exact_helper = []
for name, facts in helper_inputs['files'].items():
    if name != '.gitattributes':
        assert after['files'][name] == facts, name
        exact_helper.append(name)
assert len(exact_helper) == 1392
commands = [
    ('structural', ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/verify_spec.py']),
    ('ruff', ['uv', 'run', '--frozen', '--no-sync', 'ruff', 'check', '.']),
    ('mypy', ['uv', 'run', '--frozen', '--no-sync', 'mypy']),
    ('web-types', ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'typecheck']),
]
gates = []
for name, command in commands:
    start = time.monotonic()
    result = subprocess.run(command, cwd=R, capture_output=True)
    data = result.stdout + result.stderr
    (O / (name + '.log')).write_bytes(data)
    gates.append({'name': name, 'command': command, 'exit_code': result.returncode,
        'elapsed_seconds': time.monotonic() - start, 'log_sha256': hashlib.sha256(data).hexdigest()})
    print(name, result.returncode, flush=True)
finished = inputs()
assert after == finished and not git('status', '--porcelain')
(O / 'after-gates.json').write_text(json.dumps(finished, indent=2) + '\n')
receipt = {'status': 'FIXED_DTO_CANONICAL_INTEGRATED_SCOPED_STATIC_PASS' if all(g['exit_code'] == 0 for g in gates) else 'INTEGRATED_STATIC_GATE_FAIL',
    'head': after['head'], 'previous_head': ORIGINAL, 'fixed_dto_source': FINAL_DTO,
    'changed_paths': changes, 'complete_nonprogress_git_inputs': 1394,
    'before_after_gates_git_exact': True, 'helper_complete_common_inputs_byte_equal': 1392,
    'helper_difference': 'Only documentary .gitattributes differs; canonical extra historical approved proposal. All runtime/code/DTO/generated inputs exact helper8da.',
    'gates': gates, 'registered_operations': 116, 'declared_operations': 147,
    'boundary': 'Local reviewed DTO integration and structural/static checks; no new HTTP runtime integration yet, no model/CLI/tool/DB or whole M6.3 acceptance. Remote still690 until a separately audited actual push.'}
(O / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False))
assert all(g['exit_code'] == 0 for g in gates)
