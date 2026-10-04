"""Pure readback after actual installer post-check failure; no canonical writes."""
import datetime
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
p = Path(__file__).parent
root = p.parent / 'm62-public-safe-oct02'
review = p / 'installer-review-v2-PREPARED07'
execution = p / 'installer-execution-v2-PREPARED07'
sha = lambda b: hashlib.sha256(b).hexdigest()
git = lambda *args: subprocess.check_output(['git', *args], cwd=root)
plan = json.loads((review / 'PLAN.json').read_text())
assert sha((review / 'PLAN.json').read_bytes()) == '507c4a49a5c3f5d189b669141372b397f27e232767b04213b848d2920ed19750'
assert (execution / 'PARTIAL_FAILURE.json').exists()
assert git('rev-parse', 'HEAD').decode().strip() == plan['expected_head']
assert not git('diff', '--cached', '--name-only')
for n, item in plan['originals'].items():
    assert sha((execution / 'before' / n).read_bytes()) == item['sha256']
    assert (execution / 'before' / n).read_bytes() == (review / 'before' / n).read_bytes()
for item in plan['packet_files']:
    assert sha((root / item['path']).read_bytes()) == item['sha256']
    assert (root / item['path']).stat().st_size == item['bytes']
proposed = json.loads((review / 'proposed/progress/state.json').read_text())
current = json.loads((root / 'progress/state.json').read_text())
proposed.pop('updated_at'); current.pop('updated_at')
assert current == proposed
for n in ['progress/M6.3-next.md', 'progress/M6.3-bootstrap-acceptance.md']:
    assert (root / n).read_bytes() == (review / 'proposed' / n).read_bytes()
    assert (root / n).read_bytes().endswith((review / 'before' / n).read_bytes())
shadow = p / 'rollforward-render-check'
shadow.mkdir()
spec = importlib.util.spec_from_file_location('actual_progress_render', root / 'scripts/progress.py')
api = importlib.util.module_from_spec(spec); spec.loader.exec_module(api)
api.STATE = shadow / 'state.json'
actual = json.loads((root / 'progress/state.json').read_text())
api.render(actual)
assert (shadow / 'CURRENT.md').read_bytes() == (root / 'progress/CURRENT.md').read_bytes()
expected = {e['path'] for e in plan['packet_files']}
untracked = set(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
assert not (untracked - expected)
missing = expected - untracked
assert len(missing) == 1
ignore = git('check-ignore', '-v', '--stdin') if False else subprocess.check_output(
    ['git', 'check-ignore', '-v', '--stdin'], input=('\n'.join(sorted(missing)) + '\n').encode(), cwd=root).decode()
assert 'imports/' in ignore
assert next(iter(missing)).endswith('/source/apps/web/src/features/imports/ImportWorkflow.tsx')
assert set(git('diff', '--name-only').decode().splitlines()) == set(plan['originals'])
inputs = 0
for row in git('ls-tree', '-rz', plan['expected_head']).split(b'\0'):
    if not row:
        continue
    meta, name = row.split(b'\t', 1)
    name = name.decode()
    if name.startswith('progress/'):
        continue
    mode, kind, oid = meta.decode().split()
    data = (root / name).read_bytes()
    assert kind == 'blob' and hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == oid
    inputs += 1
assert inputs == 1512
result = {'status': 'PURE_POST_FAILURE_ROLLFORWARD_READBACK_PASS_WRITES_COMPLETE_UNSTAGED',
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'head': plan['expected_head'], 'packet_count': plan['packet_count'], 'verified_files': len(expected),
    'complete_nonprogress_inputs_exact': inputs, 'four_progress_semantics_exact': True,
    'old_history_and_original_backups_exact': True, 'original_installer_exit_code': 1,
    'original_failure': 'Final nonignored untracked equality omitted exactly one explicit approved archive source path due to imports/ ignore rule. All714 copies and4 progress writes already completed.',
    'ignored_explicit_candidate': sorted(missing), 'actual_ignore_rule': ignore,
    'proposed_recovery': 'Stage the explicitly admitted ignored ImportWorkflow source archive path with force only for that exact path; no ignore-rule change, recopy, reset or rollback.',
    'original_partial_failure_sha256': sha((execution / 'PARTIAL_FAILURE.json').read_bytes()),
    'new_product_tests_executed': False, 'source_pushed': False,
}
(p / 'ROLL_FORWARD_READBACK.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': result['status'], 'files': len(expected), 'readback_sha256': sha((p / 'ROLL_FORWARD_READBACK.json').read_bytes())}))
