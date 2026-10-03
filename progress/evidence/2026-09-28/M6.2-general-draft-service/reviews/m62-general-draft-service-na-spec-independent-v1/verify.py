"""Independent read-only audit of the fixed mathematical N/A repair evidence."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import subprocess

BASE = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance')
REPO = BASE / 'm62-general-draft-service-active'
RAW = BASE / 'm62-general-draft-service-na-repair-v1'
PRIOR = BASE / 'm62-general-draft-service-development-v1'
OUT = BASE / 'm62-general-draft-service-na-spec-independent-v1'
OLD = '5c6d9959fee4ef7cf22fe2cca8e0f07fa524c18d'
NEW = '2035fc9bf92f1c6b38725b2936898ad49adb4c16'
SPEC = '2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def item(data: bytes) -> dict[str, object]:
    return {'bytes': len(data), 'sha256': sha(data)}


def git(*args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(['git', *args], cwd=REPO, input=data, capture_output=True, check=True).stdout


def j(path: Path):
    return json.loads(path.read_bytes())


assert git('rev-parse', 'HEAD').decode().strip() == NEW
assert git('rev-parse', OLD).decode().strip() == OLD
assert git('status', '--porcelain') == b''
assert sha(Path('<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md').read_bytes()) == SPEC
prior_manifest = (PRIOR / 'PRIVATE_MANIFEST.json').read_bytes()
assert sha(prior_manifest) == 'd88f0e44e1703d8e8d27fdc4d01ee2e8d04d186562ece974269946c634d63e0f'
prior_members = j(PRIOR / 'PRIVATE_MANIFEST.json')['members']
assert len(prior_members) == 1180
for name, expected in prior_members.items():
    assert item((PRIOR / name).read_bytes()) == expected, name

manifest_raw = (RAW / 'PRIVATE_MANIFEST.json').read_bytes()
manifest = json.loads(manifest_raw)
assert manifest['format'] == 'sha256-private-evidence-manifest-v1'
members = manifest['members']
files = {str(p.relative_to(RAW)) for p in RAW.rglob('*') if p.is_file()}
assert files - {'PRIVATE_MANIFEST.json'} == set(members)
for name, expected in members.items():
    path = Path(name)
    assert not path.is_absolute() and '..' not in path.parts
    assert item((RAW / path).read_bytes()) == expected, name

tree = {}
for entry in git('ls-tree', '-r', '-z', NEW).split(b'\0'):
    if entry:
        header, name_raw = entry.split(b'\t', 1)
        mode, kind, oid = header.decode().split()
        name = name_raw.decode()
        if not name.startswith('progress/'):
            assert kind == 'blob'
            tree[name] = oid
stream = io.BytesIO(git('cat-file', '--batch', data=('\n'.join(tree.values()) + '\n').encode()))
engineering = {}
for name, oid in tree.items():
    header = stream.readline().decode().split()
    assert header[:2] == [oid, 'blob']
    data = stream.read(int(header[2]))
    assert stream.read(1) == b'\n'
    assert item(data) == item((REPO / name).read_bytes()), name
    engineering[name] = item(data)
assert stream.read() == b'' and len(engineering) == 1051

pins = j(RAW / 'final-source-pins.json')
assert pins['base_commit'] == OLD and pins['fixed_commit'] == NEW
assert pins['spec'] == item((REPO / 'PRODUCT_DESIGN.md').read_bytes())
assert pins['engineering_inputs'] == len(engineering)
changed = git('diff', '--name-only', OLD, NEW).decode().splitlines()
assert changed == ['services/api/app/application/review_service.py', 'tests/integration/test_draft_edit_integrity.py']
assert set(pins['paths']) == set(changed)
for name in changed:
    assert pins['paths'][name] == engineering[name] | {'git_blob': tree[name]}
assert (RAW / 'final-change.diff').read_bytes() == git('diff', '--binary', OLD, NEW)

pool = RAW / 'source-pool'
pool_names = {p.name for p in pool.iterdir() if p.is_file()}
assert len(pool_names) == 1034
references = set()
ledger = j(RAW / 'run-ledger.json')
assert len(ledger) == 5
maps = {}
for row in ledger:
    stage = row['stage']
    folder = RAW / stage
    receipt = j(folder / 'receipt.json')
    before = j(folder / 'inputs-before.json')
    after = j(folder / 'inputs-after.json')
    log = (folder / 'run.log').read_bytes()
    assert before == after and receipt['unchanged'] and not receipt['changed_paths']
    assert len(before) == len(after) == receipt['input_count_before'] == receipt['input_count_after'] == 1051
    assert receipt['log_sha256'] == sha(log) and receipt['log_bytes'] == len(log)
    assert receipt['driver_sha256'] == sha((RAW / 'run.py').read_bytes())
    assert row['exit_code'] == receipt['exit_code']
    assert row['actual_head'] == receipt['actual_head']
    for name, detail in before.items():
        digest = detail['sha256']
        assert digest in pool_names and item((pool / digest).read_bytes()) == detail, (stage, name)
        references.add(digest)
    maps[stage] = before
assert references == pool_names
red, green, related, ruff, mypy = [maps[row['stage']] for row in ledger]
assert green == related == ruff == mypy == engineering
assert [name for name in red if red[name] != green[name]] == ['services/api/app/application/review_service.py']
assert red['services/api/app/application/review_service.py'] == item(git('show', OLD + ':services/api/app/application/review_service.py'))
assert red['tests/integration/test_draft_edit_integrity.py'] == item(git('show', NEW + ':tests/integration/test_draft_edit_integrity.py'))
assert [row['exit_code'] for row in ledger] == [1, 0, 0, 0, 0]
assert [row['actual_head'] for row in ledger] == [OLD, OLD, NEW, NEW, NEW]

red_log = (RAW / '01-current-edit-na-red/run.log').read_text()
green_log = (RAW / '02-current-edit-na-green/run.log').read_text()
related_log = (RAW / '03-final-review-related/run.log').read_text()
assert 'test_edit_na_uses_current_body_while_retaining_exact_historical_formula_base' in red_log
assert 'MATHEMATICAL_REVIEW_REQUIRED' in red_log and '1 failed, 2 warnings' in red_log
assert '3 passed, 2 warnings' in green_log
assert '134 passed, 6 deselected, 2 warnings' in related_log
assert sum(' PASSED [' in line for line in related_log.splitlines()) == 134
assert 'All checks passed!' in (RAW / '04-final-ruff/run.log').read_text()
assert 'Success: no issues found in 208 source files' in (RAW / '05-final-mypy/run.log').read_text()
assert len(j(RAW / '04-final-ruff/receipt.json')['command']) - 2 == 2

result = {
    'format': 'm62-draft-edit-na-spec-independent-audit-v1',
    'old_commit': OLD,
    'fixed_commit': NEW,
    'spec_sha256': SPEC,
    'old_private_manifest_sha256': sha(prior_manifest),
    'old_private_members_checked': len(prior_members),
    'repair_private_manifest_sha256': sha(manifest_raw),
    'repair_private_members_checked': len(members),
    'engineering_git_inputs_checked': len(engineering),
    'repair_source_pool_blobs_checked': len(references),
    'repair_stages_checked': len(ledger),
    'changed_git_paths': changed,
    'red': '1 failed: historical TeX incorrectly rejected current prose N/A',
    'focused_green': '3 passed including both current-math counterexamples',
    'related_green': '134 passed, 6 deselected, 2 warnings',
    'mypy': '208 source files PASS',
    'ruff': '2 changed Python files PASS',
    'independent_product_test_rerun': 'NOT_RUN',
    'source_binding': 'PASS',
}
(OUT / 'VERIFY_RESULT.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print(json.dumps(result, sort_keys=True))
