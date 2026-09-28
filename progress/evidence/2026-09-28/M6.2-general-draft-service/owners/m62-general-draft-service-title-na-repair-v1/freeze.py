"""Freeze the title-applicability repair and verify every retained source byte."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import io
import json
import re
import subprocess

B = Path(__file__).resolve().parent
R = B.parent / 'm62-general-draft-service-active'
PRIOR = B.parent / 'm62-general-draft-service-na-repair-v1'
BASE = '2035fc9bf92f1c6b38725b2936898ad49adb4c16'
HEAD = 'ca788866bb37aae0e783d63c2d36e7bd31994b2f'
PRIOR_SHA = 'd7fa8d2285852b287d77dce5983df279bd551e105878790690f1ceb9ff6efe81'
STAGES = ('01-title-na-red', '02-title-na-green', '03-related-review', '04-ruff', '05-mypy')


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def meta(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': sha(raw)}


def write(name: str, value: object) -> None:
    (B / name).write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + '\n')


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=R)


assert not (B / 'PRIVATE_MANIFEST.json').exists()
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert git('status', '--porcelain') == b''
assert meta(PRIOR / 'PRIVATE_MANIFEST.json')['sha256'] == PRIOR_SHA
prior = json.loads((PRIOR / 'PRIVATE_MANIFEST.json').read_text())['members']
assert len(prior) == 1063
for name, expected in prior.items():
    assert meta(PRIOR / name) == expected, name

tree: dict[str, str] = {}
for line in git('ls-tree', '-r', '-z', HEAD).split(b'\0'):
    if not line:
        continue
    header, path = line.split(b'\t', 1)
    mode, kind, oid = header.decode().split()
    name = path.decode()
    if name.startswith('progress/'):
        continue
    assert kind == 'blob' and mode in {'100644', '100755'}
    tree[name] = oid
batch = subprocess.run(['git', 'cat-file', '--batch'], cwd=R, capture_output=True, check=True,
    input=('\n'.join(tree.values()) + '\n').encode()).stdout
stream = io.BytesIO(batch)
final_inputs: dict[str, dict[str, object]] = {}
for name, oid in tree.items():
    header = stream.readline().decode().split()
    assert header[:2] == [oid, 'blob']
    raw = stream.read(int(header[2]))
    assert stream.read(1) == b'\n'
    final_inputs[name] = {'bytes': len(raw), 'sha256': sha(raw)}
    assert meta(R / name) == final_inputs[name], name
assert stream.read() == b'' and len(final_inputs) == 1051
changed = git('diff', '--name-only', BASE, HEAD).decode().splitlines()
assert changed == ['services/api/app/application/review_service.py', 'tests/integration/test_draft_edit_integrity.py']
write('final-source-pins.json', {'base_commit': BASE, 'fixed_commit': HEAD, 'engineering_inputs': len(final_inputs),
    'paths': {name: final_inputs[name] | {'git_blob': tree[name]} for name in changed},
    'spec': final_inputs['PRODUCT_DESIGN.md']})
diff = git('diff', '--binary', BASE, HEAD)
assert not re.search(rb'sk-[A-Za-z0-9]{20,}', diff)
(B / 'final-change.diff').write_bytes(diff)

ledger = []
pool = B / 'source-pool'
references = set()
for stage in STAGES:
    target = B / stage
    receipt_path = target / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    before_path, after_path = target / 'inputs-before.json', target / 'inputs-after.json'
    before, after = json.loads(before_path.read_text()), json.loads(after_path.read_text())
    assert before == after and receipt['unchanged'] and not receipt['changed_paths']
    assert len(before) == receipt['input_count_before'] == receipt['input_count_after'] == 1051
    assert receipt['driver_sha256'] == sha((B / 'run.py').read_bytes())
    assert receipt['actual_head'] == BASE
    for name, expected in before.items():
        assert meta(pool / expected['sha256']) == expected, name
        references.add(expected['sha256'])
    log_path = target / 'run.log'
    assert meta(log_path) == {'sha256': receipt['log_sha256'], 'bytes': receipt['log_bytes']}
    log = log_path.read_text()
    if stage == STAGES[0]:
        assert receipt['exit_code'] == 1 and '2 failed, 2 warnings' in log and 'DID NOT RAISE ApiError' in log
        assert before != final_inputs
    else:
        assert receipt['exit_code'] == 0 and before == final_inputs
    if stage == STAGES[1]:
        assert '5 passed, 2 warnings' in log
    elif stage == STAGES[2]:
        assert '136 passed, 6 deselected, 2 warnings' in log
    elif stage == STAGES[3]:
        assert 'All checks passed!' in log
    elif stage == STAGES[4]:
        assert 'Success: no issues found in 208 source files' in log
    terminal = re.findall(r'[^\n]*(?:\d+ passed|\d+ failed|no issues found|All checks passed!)[^\n]*', log)[-1]
    ledger.append({'stage': stage, 'actual_head': receipt['actual_head'], 'exit_code': receipt['exit_code'],
        'input_count': len(before), 'source_unchanged_during_run': True, 'inputs_match_fixed_git': before == final_inputs,
        'receipt': meta(receipt_path), 'log': meta(log_path), 'before': meta(before_path),
        'after': meta(after_path), 'terminal': terminal})
assert references == {path.name for path in pool.iterdir() if path.is_file()}
write('run-ledger.json', ledger)
write('VERIFY.json', {'base_commit': BASE, 'fixed_commit': HEAD, 'engineering_inputs_checked': len(final_inputs),
    'changed_source_paths_checked': changed, 'raw_stages_checked': len(STAGES),
    'source_pool_blobs_checked': len(references), 'all_sources_unchanged_during_runs': True,
    'green_and_later_inputs_match_actual_fixed_git': True, 'prior_package_manifest_sha256': PRIOR_SHA,
    'prior_package_members_unchanged': len(prior), 'worktree_clean': True})
report = f'''# Edited Draft title mathematical N/A repair

Fixed `{HEAD}` relative to `{BASE}`; only Review applicability and its integration test changed. The sole normative source is PRODUCT_DESIGN.md §20.3, SHA256 `{final_inputs['PRODUCT_DESIGN.md']['sha256']}`. No main, remote, Provider, numeric executor or real human approval was touched.

The real local Edit Draft/SQLite/Review worker path accepted explicit mathematical NOT_APPLICABLE when the current title contained `$x^2$` or `\\(x=1\\)` and the body was plain. Stage01 is the exact RED: two decision calls failed to raise MATHEMATICAL_REVIEW_REQUIRED. Its complete stdout, source input map and raw source bytes are retained. The behavior was a bypass at the decision boundary, not a setup error.

The existing signal scanner now includes `title` only for `EditReviewMaterial`, and that material still supplies only its current record.payload. It does not scan the historical frozen base for applicability. Complete original base/history authentication remains unchanged. Import, single and group applicability logic is unchanged. A signal blocks N/A; lack of a signal grants no automatic classification or approval.

Stage02 targeted behavior is **5 passed, 2 warnings**: both title formula forms, existing current-body formula counterexamples, and a nonmath current title/body with historical math in both the frozen base title and body. That positive case preserves exact original base bytes, explicit human reason, candidate identity, NOT_RUN machine report and historical replay; corrupting the old physical base still rejects read/replay. The decisions are explicitly synthetic, not real human reviews.

Stage03 related gate is **136 passed, 6 deselected, 2 warnings** in four integration files. The two deselected generated-owner fixture tests intentionally avoid controlled Provider activity; neither is claimed as passing. Stage04 Ruff on both changed files passed; stage05 mypy on 208 source files passed. Full suite, HTTP/UI, real Provider, real math/source approval and M6.2 acceptance were not run here.

All five commands, complete logs, actual exit codes, actual precommit HEAD and unchanged before/after 1051 engineering inputs are retained. Green and later inputs match the actual final Git tree byte-for-byte; RED has the old implementation. The previous 1063-member repair package was rehashed and remains untouched. Runtime databases and virtual environment are not part of this package. Independent review of this increment remains pending.
'''
(B / 'REPORT.md').write_text(report)
write('TASK_RECEIPT.json', {'task': 'Reject mathematical N/A when edited Draft current title contains formula',
    'base_commit': BASE, 'fixed_commit': HEAD, 'status': 'REPAIRED_PENDING_INDEPENDENT_REVIEW',
    'red': '2 real decision failures, not setup errors', 'targeted_green': '5 passed, 2 warnings',
    'related': '136 passed, 6 deselected, 2 warnings', 'ruff': 'PASS: two changed Python files',
    'mypy': 'PASS: 208 source files', 'real_provider_numeric_human_approval': 'NOT_RUN',
    'http_ui_full_suite_m62_acceptance': 'NOT_RUN', 'prior_package': {'manifest_sha256': PRIOR_SHA, 'members_unchanged': len(prior)},
    'next': 'Independent Spec/Standards review; cherry into HTTP integration then run exact-commit gates'})
members = {str(path.relative_to(B)): meta(path) for path in sorted(B.rglob('*')) if path.is_file()}
write('PRIVATE_MANIFEST.json', {'format': 'sha256-private-evidence-manifest-v1',
    'created_at': datetime.now(timezone.utc).isoformat(), 'members': members})
print(json.dumps({'members': len(members), 'manifest': meta(B / 'PRIVATE_MANIFEST.json'),
    'report': meta(B / 'REPORT.md'), 'verification': meta(B / 'VERIFY.json')}))
