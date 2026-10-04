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
commands = [('full-python', ['uv','run','--frozen','--no-sync','pytest','--tb=line','--basetemp','$HOME/.cache/learning-workbench-acceptance/m63-combined-preparation-gates-oct04/python-fixed-02/basetemp'])]
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
receipt = {'status': 'COMBINED_FULL_PYTHON_FIXED_BASETEMP_PASS' if all(g['exit_code'] == 0 for g in gates) else 'COMBINED_GATE_FAIL',
    'head': H, 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'complete_nonprogress_git_inputs': before['count'], 'before_after_git_exact': True,
    'gates': gates, 'prior_full_python_failure': 'Originalsame-source440FAIL/1568ERROR/1939PASS/1skip withErrno122quotaretained; this full rerun only changes dedicated basetemp.',
    'prior_ui_original_red': 'Fixed9b12 original3FAIL/7PASS retained; final newtest has one explicit discriminator fixture guard only; initial missing pinned Node preflight NOT_RUN separate.',
    'scope': 'Complete repository pytest on integrated preparation/control and currentclient source; no collection subset claimed as full.',
    'boundary': 'Complete pytest test suite; actual numeric environment skips, if present, remain blockers. Controlled peers do not prove actual external model/CLI turn or wholeM6.3/quality/release.'}
(O / 'GATES.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False))
assert all(g['exit_code'] == 0 for g in gates)
