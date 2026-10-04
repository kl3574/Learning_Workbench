"""Read only the explicit owner candidate allowlist and original sealing records."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

base = Path('$HOME/.cache/learning-workbench-acceptance/m63-artifact-p2-repair-evidence-oct04')
out = Path(__file__).parent
def sha(data):
    return hashlib.sha256(data).hexdigest()
def load(path):
    return json.loads(path.read_bytes())
allow_path = base/'publication-candidates/allowlist.json'
assert sha(allow_path.read_bytes()) == 'e9d2d811076cda735d0a8c3d1941147579e5379b1df7cd8320d5e707fe322762'
seal = load(base/'CANDIDATE_SEAL.json')
assert seal['allowlist_sha256'] == sha(allow_path.read_bytes())
assert seal['final_binding_sha256'] == sha((base/'FINAL_BINDING.json').read_bytes())
assert seal['report_sha256'] == sha((base/'REPORT.md').read_bytes())
assert (out/'RECOMPUTED_FULL_GIT_MANIFESTS.json').read_bytes() == (base/'FULL_GIT_MANIFESTS.json').read_bytes()
full = load(out/'RECOMPUTED_FULL_GIT_MANIFESTS.json')
assert len(full['verified_runs']) == 14 and full['current_complete_inputs'] == 1459
scanner_spec = importlib.util.spec_from_file_location('publication_scanner', Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02/scripts/check_publication.py'))
scanner = importlib.util.module_from_spec(scanner_spec)
scanner_spec.loader.exec_module(scanner)
allow = load(allow_path)
assert allow['candidate_count'] == seal['candidate_count'] == len(allow['files']) == 97
files = []
for item in allow['files']:
    path = item['path']
    assert not Path(path).is_absolute() and '..' not in Path(path).parts
    raw = (base/path).read_bytes()
    candidate = (base/'publication-candidates'/path).read_bytes()
    assert sha(raw) == item['raw_sha256'] and sha(candidate) == item['candidate_sha256']
    assert len(candidate) == item['bytes']
    assert candidate == raw.replace(b'$HOME', b'<LOCAL_HOME>')
    assert not scanner.inspect('progress/evidence/2026-10-04/M6.3-artifact512-repair/'+path, candidate), path
    if path.endswith('/run.log'):
        receipt = load(base/Path(path).parent/'receipt.json')
        assert receipt['exit_code'] == 0 and receipt['log_sha256'] == sha(raw)
    files.append({'path':path,'raw_sha256':sha(raw),'candidate_sha256':sha(candidate),'bytes':len(candidate)})
binding = load(base/'FINAL_BINDING.json')
for item in binding['files'] + binding['receipts']:
    assert sha((base/item['path']).read_bytes()) == item['sha256']
result = {'status':'ROOT_EXPLICIT_OWNER512_CANDIDATES_AND_ALL_RUNS_READBACK_PASS',
    'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'head':binding['fixed_sha'],'raw_allowlist_sha256':sha(allow_path.read_bytes()),
    'original_FULL_GIT_MANIFESTS_sha256':sha((base/'FULL_GIT_MANIFESTS.json').read_bytes()),
    'recomputed_FULL_GIT_MANIFESTS_byte_identical':True,'actual_recomputed_runs':14,
    'git_map_bindings':sum(x['count'] for x in full['verified_runs']),
    'verified_fixed_live_inputs':1459,'candidate_count':97,'files':files,'bounded_scan_findings':0,
    'boundary':'Pure immutable source/receipt/candidate readback, not new product test execution or canonical/wholeM6.3 acceptance. Recompute original audit was redirected to this private new pack; all owner seals unchanged. No failed raw log is a candidate; text home transformation is documentary.'}
assert not (out/'READBACK.json').exists()
(out/'READBACK.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='files'}))
