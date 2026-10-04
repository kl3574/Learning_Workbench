import hashlib
import json
import subprocess
from pathlib import Path

BASE = Path('$HOME/.cache/learning-workbench-acceptance')
PRODUCER = BASE / 'm63-local-session-bootstrap-evidence-oct03'
ROOT = BASE / 'm62-public-safe-oct02'
OUT = Path(__file__).parent
HEAD = 'df0bc6188745cf96aed4b68e52737dab492758d4'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def verify_item(name, expected):
    assert '..' not in Path(name).parts and not Path(name).is_absolute()
    data = (PRODUCER / name).read_bytes()
    assert sha(data) == expected['sha256'] and len(data) == expected['bytes'], name
    return data

raw = json.loads((PRODUCER / 'RAW_MANIFEST.json').read_text())
assert raw['source_head'] == HEAD and len(raw['files']) == 642
for name, item in raw['files'].items():
    verify_item(name, item)
safe = json.loads((PRODUCER / 'SAFE_SHARE.json').read_text())
assert safe['source_head'] == HEAD and safe['only_explicit_entries_authorized']
assert safe['count'] == len(safe['entries']) == 140
for entry in safe['entries']:
    original = verify_item(entry['raw_path'], entry['raw'])
    candidate = verify_item(entry['candidate_path'], entry['candidate'])
    assert candidate == original.replace(b'$HOME', b'$HOME'), entry['raw_path']
outer = json.loads((PRODUCER / 'PUBLIC_OUTER_ALLOWLIST.json').read_text())
assert len(outer['entries']) == 4
for entry in outer['entries']:
    original = verify_item(entry['raw_path'], {'sha256': entry['raw_sha256'], 'bytes': entry['raw_bytes']})
    candidate = verify_item(entry['candidate_path'], {'sha256': entry['candidate_sha256'], 'bytes': entry['candidate_bytes']})
    assert candidate == original.replace(b'$HOME', b'$HOME')

runner_sha = sha((PRODUCER / 'run_stage.py').read_bytes())
stages = ('48-final-focused', '49-final-ruff', '50-final-mypy', '51-final-verify')
inputs = None
gate_results = {}
for name in stages:
    directory = PRODUCER / 'stages' / name
    before = json.loads((directory / 'before.json').read_text())
    after = json.loads((directory / 'after.json').read_text())
    result = json.loads((directory / 'result.json').read_text())
    assert before == after and before['head'] == result['head'] == HEAD
    assert before['runner_sha256'] == runner_sha
    assert result['exit_code'] == 0 and result['inputs_unchanged'] and result['all_match_git']
    assert len(before['files']) == result['input_count'] == 1365
    if inputs is None:
        inputs = before['files']
    assert before['files'] == inputs
    gate_results[name] = {'exit_code': 0, 'runner_seconds': result['seconds'], 'log_sha256': sha((directory / 'raw.log').read_bytes())}

tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', HEAD], cwd=ROOT, text=True).splitlines()
assert set(inputs) == {path for path in tracked if not path.startswith('progress/')}
names = sorted(inputs)
batch = ''.join(HEAD + ':' + name + '\n' for name in names)
data = subprocess.check_output(['git', 'cat-file', '--batch'], input=batch.encode(), cwd=ROOT)
offset = 0
for name in names:
    end = data.index(b'\n', offset)
    object_sha, kind, length = data[offset:end].split()
    assert kind == b'blob'
    length = int(length)
    blob = data[end + 1:end + 1 + length]
    item = inputs[name]
    assert len(blob) == item['bytes'] and sha(blob) == item['sha256'] and item['matches_git'], name
    assert object_sha.decode() == item['git_blob'], name
    offset = end + 2 + length
assert offset == len(data)

legacy = json.loads((PRODUCER / 'legacy-actual-47.json').read_text())
assert legacy['source_head'] == HEAD and legacy['status'] == 'PASS'
assert legacy['runner_sha256'] == sha((PRODUCER / 'legacy_actual_47.py').read_bytes())
assert {i['original_stage'] for i in legacy['instances']} == {32, 33, 34}
for instance in legacy['instances']:
    assert instance['session']['status'] == 'unknown' and instance['eight_owner_tables_unchanged']
    assert instance['preparation']['status'] == 'consumed' and instance['preparation']['validity'] == 'closed'

report = {
    'status': 'PASS_SCOPED_FINAL_BACKEND_EVIDENCE_READBACK',
    'backend_head': HEAD,
    'production_last_change': '04500f20fd9727d9b15da081e820bbd81a780fad',
    'raw_manifest_files': 642, 'explicit_safe_candidates': 140, 'explicit_outer_candidates': 4,
    'nonprogress_inputs': 1365, 'all_before_after_and_git_match': True,
    'producer_runner_sha256': runner_sha, 'gates': gate_results,
    'focused_cases': 264, 'old_actual_unknown_instances_retained': [32, 33, 34],
    'boundaries': 'Readback only, not a rerun of control or test gates. Exact home-only candidate transformation verified. Full Python/native and combined source gates pending. Original ERROR/FAIL/WIP limitations and unknowns retained. No private DB, key, archive, profile or raw protocol response admitted.'
}
(OUT / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k != 'gates'}, ensure_ascii=False))
