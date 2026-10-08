import datetime
import hashlib
import json
import subprocess
import time
from pathlib import Path

R = Path('$HOME/.cache/learning-workbench-acceptance/m63-current-session-client-oct04')
O = Path(__file__).parent
H = '763e536e7a3e4d914157a34279e91416f7a6a3cd'
assert not (O / 'GATES.json').exists()

def inputs():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip() == H
    files = {}
    for row in subprocess.check_output(['git', 'ls-tree', '-rz', H], cwd=R).split(b'\0'):
        if not row:
            continue
        metadata, raw_name = row.split(b'\t', 1)
        name = raw_name.decode()
        if name.startswith('progress/'):
            continue
        oid = metadata.split()[2].decode()
        data = (R / name).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == oid
        files[name] = {'git_blob': oid, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return {'head': H, 'count': len(files), 'files': files}

assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=R)
before = inputs()
(O / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
commands = [
    ('full-web', ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'test']),
    ('strict', ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'lint']),
    ('build', ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'build']),
]
gates = []
for name, command in commands:
    start = time.monotonic()
    with (O / (name + '.log')).open('wb') as log:
        result = subprocess.run(command, cwd=R, stdout=log, stderr=subprocess.STDOUT)
    gates.append({'name': name, 'command': command, 'exit_code': result.returncode,
        'elapsed_seconds': time.monotonic() - start,
        'log_sha256': hashlib.sha256((O / (name + '.log')).read_bytes()).hexdigest()})
    print(name, result.returncode, flush=True)
after = inputs()
assert before == after and not subprocess.check_output(['git', 'status', '--porcelain'], cwd=R)
(O / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
receipt = {'status': 'FIXED_CURRENT_SESSION_CLIENT_SCOPED_PASS' if all(g['exit_code'] == 0 for g in gates) else 'CURRENT_SESSION_CLIENT_GATE_FAIL',
    'head': H, 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'complete_nonprogress_git_inputs': before['count'], 'before_after_git_exact': True,
    'gates': gates, 'original_red': 'Fixed9b12 same test bytes3FAIL/7PASS retained; initial missing pinned Node preflight NOT_RUN separate.',
    'scope': 'Current GET uses strict independent model and real revision/active slot/flags; original bootstrap ACK decoder/body/key/memory unchanged. No new prepare/execute/approval/manifest UI or API endpoints.',
    'boundary': 'Synthetic Web behavior plus full Web/strict/build gates only; real HTTP/native combination NOT_RUN here. No CLI/model/network execution or whole M6.3 acceptance.'}
(O / 'GATES.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False))
assert all(g['exit_code'] == 0 for g in gates)
