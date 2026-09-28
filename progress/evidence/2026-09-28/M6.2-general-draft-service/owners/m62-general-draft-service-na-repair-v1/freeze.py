"""Hash-bind a bounded review-applicability repair without rerunning tests."""
from pathlib import Path
import hashlib
import io
import json
import re
import subprocess

B = Path(__file__).resolve().parent
R = B.parent / 'm62-general-draft-service-active'
OLD = B.parent / 'm62-general-draft-service-development-v1'
BASE = '5c6d9959fee4ef7cf22fe2cca8e0f07fa524c18d'
HEAD = '2035fc9bf92f1c6b38725b2936898ad49adb4c16'
PRIOR = 'd88f0e44e1703d8e8d27fdc4d01ee2e8d04d186562ece974269946c634d63e0f'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': sha(raw)}


def write(name, value):
    (B / name).write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=R)


assert not (B / 'PRIVATE_MANIFEST.json').exists()
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert git('status', '--porcelain') == b''
assert meta(OLD / 'PRIVATE_MANIFEST.json')['sha256'] == PRIOR
old = json.loads((OLD / 'PRIVATE_MANIFEST.json').read_text())['members']
assert len(old) == 1180
for name, value in old.items():
    assert meta(OLD / name) == value, name
tree = {}
for line in git('ls-tree', '-r', '-z', HEAD).split(b'\0'):
    if not line:
        continue
    head, path = line.split(b'\t', 1)
    mode, kind, oid = head.decode().split()
    name = path.decode()
    if name.startswith('progress/'):
        continue
    assert kind == 'blob'
    tree[name] = oid
data = subprocess.run(['git', 'cat-file', '--batch'], cwd=R, capture_output=True, check=True,
    input=('\n'.join(tree.values()) + '\n').encode()).stdout
stream = io.BytesIO(data)
inputs = {}
for name, oid in tree.items():
    header = stream.readline().decode().split()
    assert header[:2] == [oid, 'blob']
    raw = stream.read(int(header[2]))
    assert stream.read(1) == b'\n'
    inputs[name] = {'bytes': len(raw), 'sha256': sha(raw)}
    assert meta(R / name) == inputs[name]
assert stream.read() == b'' and len(inputs) == 1051
changed = git('diff', '--name-only', BASE, HEAD).decode().splitlines()
assert changed == ['services/api/app/application/review_service.py', 'tests/integration/test_draft_edit_integrity.py']
write('final-source-pins.json', {'base_commit': BASE, 'fixed_commit': HEAD, 'engineering_inputs': len(inputs),
    'paths': {name: inputs[name] | {'git_blob': tree[name]} for name in changed},
    'spec': inputs['PRODUCT_DESIGN.md']})
(B / 'final-change.diff').write_bytes(git('diff', BASE, HEAD))
ledger = []
pool = B / 'source-pool'
references = set()
paths = sorted(B.glob('*/receipt.json'))
assert len(paths) == 5
for path in paths:
    stage = path.parent.name
    receipt = json.loads(path.read_text())
    before_path, after_path = path.parent / 'inputs-before.json', path.parent / 'inputs-after.json'
    before, after = json.loads(before_path.read_text()), json.loads(after_path.read_text())
    assert before == after and receipt['unchanged'] and not receipt['changed_paths']
    assert len(before) == receipt['input_count_before'] == receipt['input_count_after'] == 1051
    assert receipt['driver_sha256'] == sha((B / 'run.py').read_bytes())
    for name, value in before.items():
        assert meta(pool / value['sha256']) == value
        references.add(value['sha256'])
    log = path.parent / 'run.log'
    assert meta(log) == {'sha256': receipt['log_sha256'], 'bytes': receipt['log_bytes']}
    text = log.read_text()
    if stage.startswith(('03-', '04-', '05-')):
        assert before == inputs and receipt['actual_head'] == HEAD and receipt['exit_code'] == 0
    terminal = re.findall(r'[^\n]*(?:\d+ passed|\d+ failed|no issues found|All checks passed!)[^\n]*', text)[-1]
    ledger.append({'stage': stage, 'actual_head': receipt['actual_head'], 'exit_code': receipt['exit_code'],
        'input_count': len(before), 'source_unchanged': True, 'matches_final_git': before == inputs,
        'receipt': meta(path), 'log': meta(log), 'before': meta(before_path), 'after': meta(after_path), 'terminal': terminal})
assert references == {path.name for path in pool.iterdir()}
write('run-ledger.json', ledger)
write('VERIFY.json', {'fixed_commit': HEAD, 'base_commit': BASE, 'actual_final_git_inputs_checked': len(inputs),
    'changed_source_paths_checked': len(changed), 'all_stage_logs_receipts_before_after_checked': len(paths),
    'all_source_pool_blobs_checked': len(references), 'all_sources_unchanged_during_runs': True,
    'prior_package_manifest_sha256': PRIOR, 'prior_package_all_members_unchanged': len(old),
    'stage01': 'actual decision rejected plain current edit due to historical TeX; 1 RED',
    'stage02': '3 PASS including both current-formula counterexamples',
    'stages03_to05': 'Actual final Git inputs and successful exits', 'source_tree_clean': True})
related = ledger[2]['terminal']
report = f'''# Edit Review mathematical applicability repair

Fixed `{HEAD}` relative to `{BASE}`; two files,58 insertions/2 deletions, clean owner tree. Sole normative source is PRODUCT_DESIGN.md §20.3 (line997), SHA256 `{inputs['PRODUCT_DESIGN.md']['sha256']}`. No spec, DTO, migration, HTTP, main, remote or prior package change.

Independent Spec review found a real defect: mathematical N/A applicability scanned the complete EditReviewMaterial, including its frozen old base body. Deleting a formula from the reviewed candidate still left the old formula in provenance and caused an incorrect409. Stage01 uses actual Content r1 with TeX equation*, a later published Content r2, exact-r1 Draft create, plain-body PATCH, actual Review job/worker/machine receipt and an explicit synthetic human reason. On the old implementation the actual decision call returns MATHEMATICAL_REVIEW_REQUIRED (1FAIL). The failure is not a setup failure.

Only the EditReviewMaterial branch now supplies its exact record.payload to the existing math-signal checker. Import/single/group keep their previous dump and checker. Owner/material/history validation still checks the complete base, parent chain and physical old bytes. This selects the candidate belonging to the Review, not the newest editable head. It does not automatically classify or approve N/A.

Stage02 has3PASS: the new historical-TeX/current-prose positive case and both existing current-formula counterexamples. The positive preserves the explicit original reason, current actor and exact candidate; source verdict remains synthetic REJECTED. Machine math/source/pedagogy stay NOT_RUN, and the machine report remains NOT_RUN after the human N/A. A later Draft r3 containing mathematics does not change the old r2 decision or its command ACK. Corrupting the physical r1 base then rejects Draft create replay, Review read, original decision ACK and original Review create ACK with no repair writes.

Fixed-source final related gate: **{related}** in four integration files. Controlled-generation fixtures are explicitly deselected. Final Ruff on the two changed Python files passes; final mypy208 source files passes. This is a bounded repair gate, not a rerun of the earlier450-case set, a full suite, HTTP or M6.2 acceptance. The earlier5c6d995 results retain their original source identity and must not be relabeled as tested2035fc9.

No Provider fixture, external vendor, key, numeric executor or real human approval was used in this repair run. All content/actors/decisions are synthetic, with real local owner/SQLite/worker operations. The earlier stage22 selection error remains in its immutable prior package and is not erased by this repair.

All five commands, actual exits, complete logs, before/after1051 source inputs and source bytes are retained. Final03/04/05 inputs each match actual Git2035fc9; stage02 has identical engineering bytes before the commit while its actual HEAD remains recorded as5c6d995. The old1180-member package was independently rehashed by this freeze script and remains byte-identical. Runtime databases/blobs and virtual environments are excluded; no missing runtime is synthesized. Independent review of this repair remains pending.
'''
(B / 'REPORT.md').write_text(report)
write('TASK_RECEIPT.json', {'task': 'Fix edit Review N/A applicability to exact reviewed payload', 'fixed_commit': HEAD,
    'base_commit': BASE, 'status': 'REPAIRED_PENDING_INDEPENDENT_REVIEW', 'red': '01-current-edit-na-red: 1 failed at actual decision',
    'green': '02-current-edit-na-green: 3 passed', 'final_related': related,
    'ruff': 'PASS: 2 changed Python files', 'mypy': 'PASS: 208 source files',
    'real_provider_numeric_human_approval': 'NOT_RUN', 'controlled_provider_fixtures_in_this_repair': 'NOT_RUN',
    'http_full_suite_m62_acceptance': 'NOT_RUN', 'prior_package': {'manifest_sha256': PRIOR, 'members_unchanged': len(old)},
    'next': 'Independent root review and separate HTTP integration'})
members = {str(path.relative_to(B)): meta(path) for path in sorted(B.rglob('*')) if path.is_file()}
write('PRIVATE_MANIFEST.json', {'format': 'sha256-private-evidence-manifest-v1', 'members': members})
print(json.dumps({'members': len(members), 'manifest': meta(B / 'PRIVATE_MANIFEST.json'),
    'report': meta(B / 'REPORT.md'), 'receipt': meta(B / 'TASK_RECEIPT.json'), 'verification': meta(B / 'VERIFY.json')}))
