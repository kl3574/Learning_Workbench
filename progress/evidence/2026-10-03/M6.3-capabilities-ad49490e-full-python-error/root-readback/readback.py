from pathlib import Path
import json
import hashlib
import subprocess
import datetime
import sys
import importlib.util

base = Path('$HOME/.cache/learning-workbench-acceptance')
root = base / 'm62-public-safe-oct02'
src = base / 'm63-capabilities-full-gates-ad49490e-oct03'
audit = Path(__file__).parent
assert not (audit / 'READBACK.json').exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
before = json.loads((src / 'python-before.json').read_text())
after = json.loads((src / 'python-after.json').read_text())
original = json.loads((src / 'python-receipt.json').read_text())
assert before == after and before['count'] == 1340 == len(before['tracked'])
assert original['inputs_unchanged'] and original['exit_code'] == 1
requests = ''.join(before['head'] + ':' + path + '\n' for path in before['tracked']).encode()
output = subprocess.check_output(['git', 'cat-file', '--batch'], input=requests, cwd=root)
position = 0
for path, expected in before['tracked'].items():
    end = output.index(b'\n', position)
    header = output[position:end].split()
    assert header[1] == b'blob'
    size = int(header[2])
    data = output[end + 1:end + 1 + size]
    position = end + size + 2
    assert sha(data) == expected['sha256'] and len(data) == expected['bytes'], path
assert position == len(output)
for path, expected in before['private'].items():
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = src / candidate
    data = candidate.read_bytes()
    assert sha(data) == expected['sha256'] and len(data) == expected['bytes'], path
raw = (src / 'python.log').read_bytes()
assert sha(raw) == original['log_sha256']
assert b'3633 passed, 2 skipped, 2 warnings, 1 error' in raw
assert b"assert 'running' == 'completed'" in raw
names = ['python-before.json', 'python-after.json', 'python-receipt.json', 'python.log']
sys.path.insert(0, str(root / 'scripts'))
from check_publication import inspect
rows = []
for name in names:
    data = (src / name).read_bytes()
    safe = data.replace(b'$HOME', b'$HOME').replace(b'$RUNNER_HOME', b'$RUNNER_HOME')
    assert not inspect('progress/' + name, safe), name
    rows.append({'source': name, 'raw_sha256': sha(data), 'candidate_sha256': sha(safe),
                 'transformation': 'exact home/runner prefixes only' if data != safe else 'none'})
receipt = {
    'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'head': before['head'], 'tracked_verified_exact_git': 1340, 'before_after_exact': True,
    'private_runner_verified': len(before['private']), 'exit_code': 1,
    'result': '3633 PASS /2 actual numeric ENVIRONMENT SKIP /2 existing warnings /1 setup ERROR',
    'failure': 'generated_group assessment fixture after worker.run_once returned true: authoring.read remains running; actual error_code None. Original tamper test body not reached; root cause not established.',
    'numeric': 'both original and restore physical calculator unavailable; no fallback',
    'log_sha256': sha(raw), 'duration_seconds': original['duration_seconds'],
    'pytest_reported_seconds': 2279.52,
    'boundary': 'independent readback only; no new tests or original evidence edits',
    'share': rows, 'readback_script_sha256': sha(Path(__file__).read_bytes()),
}
(audit / 'READBACK.json').write_text(json.dumps(receipt, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('pkg', base / 'm62-v313-pushed-progress-sync-oct03/package.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
package = module.package('M6.3-capabilities-ad49490e-full-python-error', [
    ('python', src.name, names),
    ('root-readback', audit.name, ['READBACK.json', 'READBACK_ATTEMPT01.json', 'readback.py']),
], receipt.copy())
verify = module.package('M6.3-session-bootstrap-v314-spec-structural', [
    ('verify', 'm63-session-bootstrap-spec-adoption-oct03', ['VERIFY.json', 'verify-fixed.log']),
], {'status': 'PASS_STRUCTURAL_ONLY', 'source_commit': 'b3f94b38c1f6f518bfca303cd87386fb6477669f',
    'scope': 'Sole v3.0.14 extract/DDL/fixtures/generation structural check; no bootstrap implementation or runtime/model acceptance.'})
state = module.read_state()
task = next(item for item in state['tasks'] if item['id'] == 'M6.3')
task['evidence_paths'] += [package, verify]
state['verification']['M6.3_mechanical_combination_v2']['python'] = receipt['result'] + ' /exit1'
state['verification']['M6.3_mechanical_combination_v2']['python_evidence'] = package
state['verification']['M6.3_spec_v314_adoption']['structural_check'] = 'PASS at fixed b3f94b38; runtime new slice NOT_RUN'
code = 'M63_AD494_FULL_PYTHON_FIXTURE_SETUP_ERROR'
assert not any(item['code'] == code for item in state['blockers'])
state['blockers'].append({'code': code, 'status': 'ACTUAL_FULL_GATE_ERROR_CAUSE_UNKNOWN_DIAGNOSIS_RUNNING',
                          'description': receipt['failure'] + ' Original fixed full gate exit1 preserved; no single-case or subset override.'})
task['blockers'].append(code)
task['verification'] += ' 追加终态：固定ad494完整Python3633PASS2ENVSKIP1setup ERROR，1340inputs逐Git及前后不变，原失败保留；v3.0.14获明确批准且结构自检通过，新的bootstrap实现进行中。'
module.save(state)
next_path = root / 'progress/M6.3-next.md'
next_path.write_text('# 固定ad494完整Python终态ERROR\n\n' + receipt['result'] + '，exit1，1340工程输入前后不变且同Git。生成组fixture未到completed，原因未知；不能称完整门禁成功。新v3.0.14合同已批准实施，与历史门禁分开。\n\n以下原时点保留。\n\n' + next_path.read_text())
print(json.dumps({'readback': sha((audit / 'READBACK.json').read_bytes()), 'package': package, 'structural': verify}))
