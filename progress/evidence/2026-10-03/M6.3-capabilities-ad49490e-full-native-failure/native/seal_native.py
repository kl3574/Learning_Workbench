from pathlib import Path
import json
import hashlib
import datetime
import sys
import re

evidence = Path(__file__).parent
root = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
sys.path.insert(0, str(root / 'scripts'))
from check_publication import inspect
sha = lambda data: hashlib.sha256(data).hexdigest()
names = ['capture.py', 'finish.py', 'native-full/run.log', 'native-full/before.json', 'native-full/after.json',
         'native-full/receipt.json', 'native-full/runner.json', 'native-output-preservation.json', 'root-terminal-readback.json']
failure = 'native-full/artifacts/import-admission-real-inde-c8d41-res-only-explicit-admission/'
names += [failure + 'error-context.md', failure + 'test-failed-1.png']
preserved = json.loads((evidence / 'native-output-preservation.json').read_text())
names += ['changed-tracked-ui/' + row['path'] for row in preserved['expected_generated_ui_outputs']]
selected = {}
for filename in ['codex-capabilities-actual.json', 'codex-capabilities-1440.png', 'codex-capabilities-390.png',
                 'single-publication-actual.json', 'restore-numeric-actual.json']:
    matches = list((evidence / 'native-full/artifacts').rglob(filename))
    assert len(matches) == 1, (filename, len(matches))
    selected[filename] = matches[0].relative_to(evidence).as_posix()
names += list(selected.values())
receipt = json.loads((evidence / 'native-full/receipt.json').read_text())
assert receipt['head'] == 'ad49490e78c21174349595da8090c6c2b445bce9' and receipt['exit_code'] == 1
log = (evidence / 'native-full/run.log').read_text()
assert re.search(r'^\s*1 failed\s*$', log, re.M) and re.search(r'^\s*126 passed \(17\.4m\)', log, re.M)
actual = json.loads((evidence / selected['codex-capabilities-actual.json']).read_text())
assert actual['first'] == actual['second'] and actual['first']['status'] == 200
assert actual['first']['capabilities']['available'] and not actual['first']['capabilities']['authorized']
assert actual['first']['capabilities']['capabilities'] == {'approvals': False, 'interrupt': False, 'artifacts': False}
report = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'head': receipt['head'],
    'status': 'FULL_NATIVE_FAIL_126_PASS_1_FAIL', 'worker_count': 1, 'retries': 0, 'runner_reported_duration': '17.4m',
    'original_failure': 'import-admission.spec.ts:65; RestartRuntime.authenticateOnly five-second saved-heading assertion. Screenshot shows unauthenticated401branch; original bootstrap HTTP response was not retained, cause UNKNOWN.',
    'input_count': 1340, 'expected_generated_ui_outputs_archived_restored': 5, 'other_inputs_unchanged': 1335,
    'codex_control_read': 'PASS actual200 available=true authorized=false, threeflagsfalse;2APIprocesses/sameDB/jobsunchanged',
    'selected_artifacts': selected, 'boundary': 'Whole suite remains FAIL; passing Codex case is not suite acceptance. Extended independent review was automatically interrupted; no broad probe resumed. No model/thread/turn/tool call from Codex test, no sourcepush/release.'}
(evidence / 'REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
names += ['REPORT.json', 'seal_native.py']
rows = []
for name in names:
    raw = (evidence / name).read_bytes()
    public = raw.replace(b'$HOME', b'$HOME')
    findings = inspect('progress/evidence/M6.3/full-native/' + name, public)
    assert not findings, (name, findings)
    rows.append({'source': name, 'raw_sha256': sha(raw), 'published_sha256': sha(public),
                 'bytes': len(raw), 'transformation': 'exact $HOME to $HOME only' if raw != public else 'none'})
(evidence / 'MANIFEST.json').write_text(json.dumps({'scope': 'Only explicit completed full-gate source/evidence and selected synthetic artifact hashes; all runtimeDB/browserprofile/globalcredentials and unselected artifacts excluded.', 'entries': rows}, indent=2) + '\n')
(evidence / 'SAFE_SHARE.json').write_text(json.dumps({'explicit_names': names + ['MANIFEST.json'], 'status': report['status'], 'boundary': report['boundary']}, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'selected': len(names), 'report_sha256': sha((evidence / 'REPORT.json').read_bytes())}))
