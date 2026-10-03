"""Read-only, offline verification of independently reviewed Tutor evidence."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).parent
ROOT = OUT.parent / 'm62-tutor-ci-observation-active'
RAW = OUT.parent / 'm62-tutor-ci-observation-development-v1'
HEAD = 'ab11b811867bb1c30166491279ada5ae20934886'
BASE = '416b53261dafa0ddbdec3adf4ef2deab058b866b'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def h(raw):
    return hashlib.sha256(raw).hexdigest()

def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': h(raw)}

def read(path):
    return json.loads(path.read_text())

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert git('status', '--porcelain') == b''
binding = read(RAW / 'git-input-binding.json')
raw_index = read(RAW / 'raw-index.json')
raw_verified = []
for item in raw_index['files']:
    path = RAW / item['path']
    assert path.resolve().is_relative_to(RAW.resolve())
    fact = pin(path)
    assert fact['bytes'] == item['bytes'] and fact['sha256'] == item['sha256'], item['path']
    raw_verified.append(item)

tree = {}
for line in git('ls-tree', '-rz', HEAD).split(b'\0'):
    if not line:
        continue
    meta, path_bytes = line.split(b'\t', 1)
    mode, kind, blob = meta.decode().split(' ')
    path = path_bytes.decode()
    if kind == 'blob' and not path.startswith('progress/'):
        raw = git('cat-file', 'blob', blob)
        tree[path] = {'bytes': len(raw), 'sha256': h(raw), 'git_blob': blob}
assert len(tree) == 965
assert tree == binding['files']
working = {name: {'bytes': len((ROOT/name).read_bytes()), 'sha256': h((ROOT/name).read_bytes())} for name in tree}
manifest_tree = {name: {k:v for k,v in value.items() if k != 'git_blob'} for name,value in tree.items()}
assert working == manifest_tree
changed = git('diff', '--name-only', BASE, HEAD).decode().splitlines()
assert sorted(changed) == sorted(binding['changed_paths']) and len(changed) == 14
source_pins = []
for name in changed:
    raw = git('show', f'{HEAD}:{name}')
    path = OUT / 'source' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    source_pins.append({'path': name, **tree[name], 'reviewed_full_file_or_full_diff_and_surrounding_source': True})

unchanged = []
for name in [*binding['unchanged_pins'], '.github/workflows/ci.yml', 'packages/contracts/generated/api-client.ts']:
    assert git('show', f'{HEAD}:{name}') == git('show', f'{BASE}:{name}'), name
    unchanged.append({'path': name, **tree[name]})
stage31 = read(RAW / '31-original-tutor/inputs-before.json')
production_comparison = []
for name in binding['production_paths']:
    assert stage31[name] == manifest_tree[name]
    snapshot = RAW / '31-original-tutor/source' / name
    assert snapshot.read_bytes() == git('show', f'{HEAD}:{name}')
    production_comparison.append({'path': name, **manifest_tree[name]})

fixed = []
for check in binding['checks']:
    stage = check['stage']
    before = read(RAW / stage / 'inputs-before.json')
    after = read(RAW / stage / 'inputs-after.json')
    assert before == after == manifest_tree, stage
    r = read(RAW / stage / 'receipt.json')
    log = pin(RAW / stage / 'run.log')
    assert r['exit_code'] == 0 and r['unchanged'] and not r['changed_paths']
    assert r['input_count_before'] == r['input_count_after'] == len(manifest_tree)
    assert log['bytes'] == r['log_bytes'] and log['sha256'] == r['log_sha256']
    assert r['driver_sha256'] == h((RAW / 'run.py').read_bytes())
    fixed.append({'stage': stage, 'receipt': pin(RAW/stage/'receipt.json'), 'command': r['command'], 'exit_code': r['exit_code'], 'log': log, 'source_count': len(before), 'source_matches_actual_git': True})

historical = []
for path in sorted(RAW.glob('[0-9][0-9]-*/receipt.json')):
    r = read(path)
    log = pin(path.parent / 'run.log')
    assert log['sha256'] == r['log_sha256'] and log['bytes'] == r['log_bytes']
    before, after = [read(path.parent / f'inputs-{side}.json') for side in ('before', 'after')]
    assert r['unchanged'] == (before == after)
    for source in (path.parent / 'source').rglob('*'):
        if source.is_file():
            name = str(source.relative_to(path.parent/'source'))
            fact = pin(source)
            assert {k:fact[k] for k in ('bytes','sha256')} == before[name]
    historical.append({'stage': path.parent.name, 'exit_code': r['exit_code'], 'log_sha256': log['sha256'], 'receipt_sha256': h(path.read_bytes()), 'source_count': len(before), 'source_stable': before == after, 'copied_source_matches_manifest': True})
assert len(historical) == 44

artifact = next((RAW/'31-original-tutor/artifacts').rglob('tutor-completion-diagnostic.json'))
data = read(artifact)
freeze = data['assertion']['frozen_at_ms']
browser = data['mechanism']['frozen_browser_records']
dom = data['mechanism']['frozen_dom_projections']
events = data['frozen_observation']['events']
assert data['assertion']['verdict'] == 'passed' and data['assertion']['original_expect_timeout_ms'] == 5000
assert data['mechanism']['post_assertion_api'] == {'state': 'failed'}
assert all(row['delivered_ms'] <= freeze for row in browser + dom)
assert all(row['elapsed_ms'] <= freeze for row in events)
assert data['post_assertion']['started_ms'] >= freeze
correlations = []
for row in dom:
    found = [item for item in browser if f"{item['epoch']}:{item['ordinal']}" == row['token']]
    matched = len(found) == 1 and found[0]['stage'] in ('snapshot_accepted','event_applied') and all(found[0].get(key) == row[key] for key in ('run','seq','revision','status'))
    assert row['matched_source'] == matched and matched
    # Only compare two browser-clock timestamps, not their Node receipt clocks.
    assert found[0]['source_ms'] <= row['source_ms']
    correlations.append({'dom_ordinal': row['ordinal'], 'source_ordinal': found[0]['ordinal'], 'stage': found[0]['stage'], 'status': row['status'], 'seq': row['seq'], 'revision': row['revision'], 'source_match_independently_recomputed': matched, 'node_delivery_precedes_assertion_freeze': True})
assert len(browser) == 33 and len(dom) == 10 and len(events) == 248
assert any(row['status'] == 'completed' and row['seq'] == 6 and row['revision'] == 6 for row in dom)

save('source-pins.json', {'base': BASE, 'head': HEAD, 'changed': source_pins, 'unchanged': unchanged, 'original_native_stage_31_production_bytes_equal_final': production_comparison, 'all_965_current_engineering_inputs_actual_git': tree})
save('evidence-verification.json', {'verified_at': datetime.now(timezone.utc).isoformat(), 'mode': 'independent offline source and existing evidence review; tests not rerun', 'raw_index': pin(RAW/'raw-index.json'), 'raw_index_entries_verified': len(raw_verified), 'all_stage_receipts': historical, 'seven_final_fixed_stages': fixed, 'original_native': {'artifact': pin(artifact), 'browser_records': len(browser), 'dom_projections': len(dom), 'node_events': len(events), 'assertion': data['assertion'], 'source_dom_correlations': correlations, 'post_assertion_api': data['mechanism']['post_assertion_api'], 'post_assertion_browser_state': data['mechanism']['post_assertion_browser']['state'], 'later_read_not_deadline_evidence': True}, 'auxiliary_inputs': [pin(RAW/name) for name in ('run.py', 'run-driver-v1.py', 'native-tsconfig.json', 'playwright-types.d.ts', 'TASK_RECEIPT.json', 'REPORT.md', 'git-input-binding.json')]})
assert git('status', '--porcelain') == b''
print(json.dumps({'head': HEAD, 'source_count': len(tree), 'changed_files': len(changed), 'raw_index_verified': len(raw_verified), 'stages': len(historical), 'fixed_stages': len(fixed), 'recomputed_dom_correlations': len(correlations), 'artifact_sha256': h(artifact.read_bytes())}))
