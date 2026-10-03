"""Read-only independent binding audit for the fixed Draft edit service review."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import subprocess

BASE = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance')
RAW = BASE / 'm62-general-draft-service-development-v1'
REPO = BASE / 'm62-general-draft-service-active'
OUT = BASE / 'm62-general-draft-service-spec-independent-v1'
HEAD = '5c6d9959fee4ef7cf22fe2cca8e0f07fa524c18d'
BEFORE = 'a944ebfbdb835a731393977a606db5b473846e98'
SPEC = '2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d'


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def meta(raw: bytes) -> dict[str, object]:
    return {'bytes': len(raw), 'sha256': sha(raw)}


def git(*args: str, input: bytes | None = None) -> bytes:
    return subprocess.run(['git', *args], cwd=REPO, input=input, capture_output=True, check=True).stdout


def read_json(path: Path):
    return json.loads(path.read_bytes())


assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert git('rev-parse', BEFORE).decode().strip() == BEFORE
assert git('status', '--porcelain') == b''
assert sha((REPO / 'PRODUCT_DESIGN.md').read_bytes()) == SPEC
assert sha(Path('<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md').read_bytes()) == SPEC

manifest_raw = (RAW / 'PRIVATE_MANIFEST.json').read_bytes()
manifest = json.loads(manifest_raw)
assert manifest['format'] == 'sha256-private-evidence-manifest-v1'
members = manifest['members']
actual_paths = {str(p.relative_to(RAW)) for p in RAW.rglob('*') if p.is_file()}
assert actual_paths - {'PRIVATE_MANIFEST.json'} == set(members)
for name, recorded in members.items():
    rel = Path(name)
    assert not rel.is_absolute() and '..' not in rel.parts
    assert meta((RAW / rel).read_bytes()) == recorded, name

tree: dict[str, str] = {}
for line in git('ls-tree', '-r', '-z', HEAD).split(b'\0'):
    if line:
        header, path = line.split(b'\t', 1)
        mode, kind, oid = header.decode().split()
        name = path.decode()
        if not name.startswith('progress/'):
            assert kind == 'blob'
            tree[name] = oid
batch = git('cat-file', '--batch', input=('\n'.join(tree.values()) + '\n').encode())
stream = io.BytesIO(batch)
engineering: dict[str, dict[str, object]] = {}
for name, oid in tree.items():
    header = stream.readline().decode().split()
    assert header[:2] == [oid, 'blob']
    raw = stream.read(int(header[2]))
    assert stream.read(1) == b'\n'
    assert meta(raw) == meta((REPO / name).read_bytes()), name
    engineering[name] = meta(raw)
assert stream.read() == b'' and len(engineering) == 1051

pins = read_json(RAW / 'final-source-pins.json')
assert pins['candidate_commit'] == HEAD and pins['base_commit'] == BEFORE
assert pins['spec_sha256'] == SPEC and pins['engineering_input_count'] == len(engineering)
changed = git('diff', '--name-only', BEFORE, HEAD).decode().splitlines()
assert len(changed) == 21 and set(changed) == set(pins['paths'])
for name in changed:
    assert pins['paths'][name] == engineering[name] | {'git_blob': tree[name]}
assert (RAW / 'final-change.diff').read_bytes() == git('diff', '--binary', BEFORE, HEAD)

pool = RAW / 'source-pool'
pool_files = {p.name for p in pool.iterdir() if p.is_file()}
assert len(pool_files) == 1065
refs: set[str] = set()
ledger = read_json(RAW / 'run-ledger.json')
assert len(ledger) == 25
for row in ledger:
    stage = row['stage']
    folder = RAW / stage
    receipt = read_json(folder / 'receipt.json')
    log = (folder / 'run.log').read_bytes()
    before = read_json(folder / 'inputs-before.json')
    after = read_json(folder / 'inputs-after.json')
    assert row['receipt'] == stage + '/receipt.json'
    assert row['log'] == stage + '/run.log'
    assert row['receipt_metadata'] == meta((folder / 'receipt.json').read_bytes())
    assert row['log_metadata'] == meta(log)
    assert row['before'] == meta((folder / 'inputs-before.json').read_bytes())
    assert row['after'] == meta((folder / 'inputs-after.json').read_bytes())
    assert receipt['log_sha256'] == sha(log) and receipt['log_bytes'] == len(log)
    assert receipt['driver_sha256'] == sha((RAW / 'run.py').read_bytes())
    assert before == after and receipt['unchanged'] and not receipt['changed_paths']
    assert len(before) == len(after) == receipt['input_count_before'] == receipt['input_count_after'] == row['input_count']
    for name, detail in before.items():
        digest = detail['sha256']
        assert digest in pool_files and meta((pool / digest).read_bytes()) == detail, (stage, name)
        refs.add(digest)
    assert (before == engineering) == row['matches_final_engineering_git']
    assert row['changed_from_final'] == sorted(name for name in before.keys() | engineering.keys() if before.get(name) != engineering.get(name))
    assert row['exit_code'] == receipt['exit_code'] and row['actual_head'] == receipt['actual_head']
assert refs == pool_files

last = {r['stage']: r for r in ledger}
final = RAW / '25-final-related-restricted'
final_log = (final / 'run.log').read_text()
assert last['22-final-related']['exit_code'] == 1
assert 'KeyboardInterrupt' in (RAW / '22-final-related/run.log').read_text()
assert last['25-final-related-restricted']['exit_code'] == 0
assert '450 passed, 20 deselected, 2 warnings in 167.71s' in final_log
assert sum(' PASSED [' in line for line in final_log.splitlines()) == 450
new_tests = [line.split(' PASSED [')[0] for line in final_log.splitlines()
             if line.startswith('tests/integration/test_draft_edit') and ' PASSED [' in line]
assert len(new_tests) == 83
assert read_json(RAW / 'new-behavior-test-results.json')['nodeids'] == new_tests
assert last['23-final-mypy']['exit_code'] == 0
assert last['24-final-ruff']['exit_code'] == 0
assert 'Success: no issues found in 208 source files' in (RAW / '23-final-mypy/run.log').read_text()
assert 'All checks passed!' in (RAW / '24-final-ruff/run.log').read_text()

result = {
    'format': 'm62-draft-edit-spec-independent-source-audit-v1',
    'spec_sha256': SPEC,
    'base_commit': BEFORE,
    'candidate_commit': HEAD,
    'changed_git_paths': len(changed),
    'engineering_git_inputs': len(engineering),
    'raw_manifest_sha256': sha(manifest_raw),
    'raw_manifest_members': len(members),
    'raw_stages': len(ledger),
    'source_pool_blobs': len(refs),
    'final_related': '450 passed, 20 deselected, 2 warnings',
    'new_behavior_cases': len(new_tests),
    'final_mypy_source_files': 208,
    'final_ruff': 'PASS',
    'stage22': 'INTERRUPTED_NONZERO_TWO_CONTROLLED_LOOPBACK_FIXTURES',
    'source_validation': 'PASS',
    'product_test_rerun': 'NOT_RUN',
}
(OUT / 'VERIFY_RESULT.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print(json.dumps(result, sort_keys=True))
