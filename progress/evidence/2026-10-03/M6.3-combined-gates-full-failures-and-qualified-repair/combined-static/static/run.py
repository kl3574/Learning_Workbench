import datetime
import hashlib
import json
import subprocess
import time
from pathlib import Path

R = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
O = Path(__file__).parent
H = 'ff656a2fc360551f872bb0ff4ebe14d8240d82d3'
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
 ('ruff', ['uv','run','--frozen','--no-sync','ruff','check','.']),
 ('mypy', ['uv','run','--frozen','--no-sync','mypy']),
 ('generated', ['uv','run','--frozen','--no-sync','python','scripts/generate_contracts.py','--check']),
 ('spec', ['uv','run','--frozen','--no-sync','python','scripts/verify_spec.py']),
 ('full-web', ['bash','scripts/node.sh','npm','--prefix','apps/web','run','test']),
 ('strict', ['bash','scripts/node.sh','npm','--prefix','apps/web','run','lint']),
 ('build', ['bash','scripts/node.sh','npm','--prefix','apps/web','run','build']),
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
receipt = {'status': 'COMBINED_STATIC_AND_FULL_WEB_PASS' if all(g['exit_code'] == 0 for g in gates) else 'COMBINED_GATE_FAIL',
    'head': H, 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'complete_nonprogress_git_inputs': before['count'], 'before_after_git_exact': True,
    'gates': gates, 'prior_ui_original_red': 'Fixed9b12 original3FAIL/7PASS retained; final newtest has one explicit discriminator fixture guard only; initial missing pinned Node preflight NOT_RUN separate.',
    'scope': 'Current GET uses strict independent model and real revision/active slot/flags; original bootstrap ACK decoder/body/key/memory unchanged. No new prepare/execute/approval/manifest UI or API endpoints.',
    'boundary': 'Integrated fixed owner and client static/fullWeb gates only. Full Python separately running, native currentmetadata combination NOT_RUN here; zero actual Codex CLI/model/network requests, wholeM6.3 incomplete.'}
(O / 'GATES.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False))
assert all(g['exit_code'] == 0 for g in gates)
