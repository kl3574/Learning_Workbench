import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

R = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
O = Path(__file__).parent / sys.argv[1]
assert sys.argv[1] in ['static', 'python']
O.mkdir(mode=0o700, exist_ok=False)
H = '79acabc2566318f9ea099da067abd7e9c4f010a2'
sha = lambda b: hashlib.sha256(b).hexdigest()
def inputs():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip() == H
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=R)
    files = {}
    for row in subprocess.check_output(['git', 'ls-tree', '-rz', H], cwd=R).split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        name = name.decode()
        if name.startswith('progress/'):
            continue
        data, oid = (R / name).read_bytes(), meta.split()[2].decode()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == oid
        files[name] = {'git_blob': oid, 'sha256': sha(data), 'bytes': len(data)}
    assert len(files) == 1465
    return {'head': H, 'count': len(files), 'files': files}
before = inputs()
(O / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
(O / 'tmp').mkdir(mode=0o700)
env = dict(os.environ, TMPDIR=str(O / 'tmp'))
if sys.argv[1] == 'python':
    commands = [('full-python', ['uv', 'run', '--frozen', '--no-sync', 'pytest', '--tb=line', '--basetemp', str(O / 'basetemp')])]
else:
    commands = [('ruff', ['uv', 'run', '--frozen', '--no-sync', 'ruff', 'check', '.']),
     ('mypy', ['uv', 'run', '--frozen', '--no-sync', 'mypy']),
     ('generated', ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/generate_contracts.py', '--check']),
     ('spec', ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/verify_spec.py']),
     ('full-web', ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'test']),
     ('strict', ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'lint']),
     ('build', ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'build'])]
gates = []
started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
(O / 'RUNNING.json').write_text(json.dumps({'status': 'RUNNING', 'head': H,
 'started_at': started_at, 'complete_nonprogress_git_inputs': 1465,
 'commands': commands, 'runner_sha256': sha(Path(__file__).read_bytes()),
 'boundary': 'Fixed-source execution in progress, no terminal result yet; canonicalHEAD/progress frozen.'}, indent=2) + '\n')
for name, command in commands:
    started = time.monotonic()
    with (O / (name + '.log')).open('wb') as log:
        p = subprocess.run(command, cwd=R, stdout=log, stderr=subprocess.STDOUT, env=env)
    gates.append({'name': name, 'command': command, 'exit_code': p.returncode,
        'elapsed_seconds': time.monotonic() - started, 'log_sha256': sha((O / (name + '.log')).read_bytes())})
    print(name, p.returncode, flush=True)
after = inputs()
(O / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
assert before == after
report = {'status': 'FIXED79AC_COMPLETE_' + sys.argv[1].upper() + '_PASS' if all(g['exit_code'] == 0 for g in gates) else 'FIXED79AC_COMPLETE_COMBINATION_GATE_FAIL',
 'head': H, 'started_at': started_at,
 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'complete_nonprogress_git_inputs': 1465, 'before_after_git_exact': True,
 'gates': gates, 'environment_override': {'TMPDIR': str(O / 'tmp')},
 'scope': 'Actual complete current fixed repository commands after reviewed unsupported approvals, independent interruptv4, opt-in memory operationv5 with83dclosure, outboundUI92, and6127mixed HTTP test. Includes allactual archival attributes/docs/ui/scripts/Git inputs.',
 'originals': 'All old complete/localcounterexampleFAIL, source-drift run, oraclecorrections, nativeoriginalwrapperFAIL, andarchivewhitespacecheckFAIL retained separately; no retrospective cause claim or borrowing of old29e/isolatedslice gates.',
 'boundary': 'Productionfullinputproof/executor andoperationregistry unavailable/empty; actualCLI/DeepSeek/remoteprovider/hosttoolsNOT_RUN. PhysicalnumericENVblocked, nofallback. FullM6.3/AC21/manifestImport/materialquality/Broker/wholeplatform acceptance incomplete even if these checks pass.'}
(O / 'GATES.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False))
assert all(g['exit_code'] == 0 for g in gates)
