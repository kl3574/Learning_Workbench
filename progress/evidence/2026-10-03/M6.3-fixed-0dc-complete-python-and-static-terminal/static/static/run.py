import datetime
import os
import hashlib
import json
import subprocess
import time
from pathlib import Path

R = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
O = Path(__file__).parent
H = '0dc454cd95e8ec82beec9e0921e53926204eec66'
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
(O/'tmp').mkdir(mode=0o700)
environment = dict(os.environ, TMPDIR=str(O/'tmp'))
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
receipt = {'status': 'LATEST_GRANT_STATIC_FULL_WEB_PASS' if all(g['exit_code']==0 for g in gates) else 'LATEST_GRANT_GATE_FAIL',
 'head':H,'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'complete_nonprogress_git_inputs':before['count'],'before_after_git_exact':True,'gates':gates,
 'environment_override':{'TMPDIR':str(O/'tmp')},
 'scope':'Latest canonical reviewed e399 permit owner +97 client binding + b0cf oldmethod test fix; complete repository static and fullWeb withstrict/build',
 'original_failures':'Both ff complete failures remainFAIL; sameoriginal7cases7PASS after explicitTMPDIR and test-onlymethod fix is separate. Grantexpiry1RED andnonobject3RED originalretained, staticmisreportwithdrawal didnotchange production.',
 'boundary':'Synthetic controlled proof is not actual CLI/model/resource enforcement or physical numeric acceptance. Production registry empty and0 actualexternalrequests; wholeM6.3/Broker/AC21/quality not complete.'}
(O/'GATES.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
assert all(g['exit_code']==0 for g in gates)
