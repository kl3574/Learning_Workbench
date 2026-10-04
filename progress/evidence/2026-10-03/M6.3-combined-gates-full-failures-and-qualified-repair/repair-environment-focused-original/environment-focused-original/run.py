import datetime
import os
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
(O/'tmp').mkdir(mode=0o700)
environment = dict(os.environ, TMPDIR=str(O/'tmp'))
commands = [('focused-original', ['uv', 'run', '--frozen', '--no-sync', 'pytest', 'tests/integration/test_import_parser_exit_race.py', 'tests/integration/test_provider_dispatch.py::test_real_sqlite_writer_lock_does_not_block_event_loop_or_cancel_preflight', 'tests/security/test_local_boundary.py::test_payload_budget_and_unimplemented_routes', 'tests/unit/test_provider_protocol.py::test_near_resource_limits_do_not_block_event_loop_heartbeat', '--tb=line', '--basetemp', '$HOME/.cache/learning-workbench-acceptance/m63-full-python-repair-oct04/environment-focused-original/basetemp'])]
gates = []
for name, command in commands:
    start = time.monotonic()
    with (O / (name + '.log')).open('wb') as log:
        result = subprocess.run(command, cwd=R, stdout=log, stderr=subprocess.STDOUT, env=environment)
    gates.append({'name': name, 'command': command, 'exit_code': result.returncode,
        'elapsed_seconds': time.monotonic() - start,
        'log_sha256': hashlib.sha256((O / (name + '.log')).read_bytes()).hexdigest()})
    print(name, result.returncode, flush=True)
after = inputs()
assert before == after and not subprocess.check_output(['git', 'status', '--porcelain'], cwd=R)
(O / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
receipt = {'status': 'FOCUSED_ORIGINAL_PASS' if all(g['exit_code'] == 0 for g in gates) else 'FOCUSED_ORIGINAL_FAIL',
 'head':H, 'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'complete_nonprogress_git_inputs':before['count'], 'before_after_git_exact':True, 'gates':gates,
 'environment_override':{'TMPDIR':str(O/'tmp')},
 'scope':'The seven failed cases on unchanged ff source; only dedicated TMPDIR and basetemp change. No production or test modifications; not a complete gate.',
 'prior':'Both original complete failures retained; three exit120 causes not classified solely by inference.',
 'boundary':'Ordinary existing application regressions only. No new low-level probes, no provider transmission and no physical numeric or whole milestone claim.'}
(O/'GATES.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
assert all(g['exit_code']==0 for g in gates)
