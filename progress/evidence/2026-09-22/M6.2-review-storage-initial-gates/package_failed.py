from pathlib import Path
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
OUT = HERE / 'failed-package'
OUT.mkdir(exist_ok=False)
TEMPLATE = HERE.parent / 'm62-current-proof-packages-v1/verify-template.py'
spec = importlib.util.spec_from_file_location('transform', TEMPLATE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sha = lambda data: hashlib.sha256(data).hexdigest()
names = ['run.py', 'runner-origin.json', 'composition-binding.json', 'package_failed.py']
for gate in ['python','ruff','mypy','spec']:
    receipt = json.loads((HERE / gate / 'receipt.json').read_bytes())
    assert receipt['code_commit'] == '72e4e64ce0e97b444146fe237efee9f199da16dc'
    assert receipt['exit_code'] == (1 if gate == 'python' else 0)
    assert receipt['source_count'] == 964 and receipt['source_unchanged']
    assert receipt['all_source_matches_git_before'] and receipt['all_source_matches_git_after']
    assert (HERE / gate / 'inputs-before.json').read_bytes() == (HERE / gate / 'inputs-after.json').read_bytes()
    log = (HERE / gate / 'test.log').read_bytes()
    assert sha(log) == receipt['log_sha256'] and len(log) == receipt['log_bytes']
    names += [gate + '/' + name for name in ['receipt.json','test.log','inputs-before.json','inputs-after.json']]
files, generated, dedup = [], [], {}
for name in names:
    raw = (HERE / name).read_bytes()
    data, transformations = module.transform(raw, str(Path.home()), '<CI_HOME>')
    original_hash = sha(raw)
    public = dedup.get(original_hash, name)
    if original_hash not in dedup:
        p = OUT / public
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        dedup[original_hash] = public
    files.append({'raw_cache':HERE.name,'raw_path':name,'raw_bytes':len(raw),'raw_sha256':original_hash,
        'public_path':public,'public_bytes':len(data),'public_sha256':sha(data),'transformed':raw!=data,
        'transformation_counts':transformations})
for name, data in {
    'verify.py':TEMPLATE.read_bytes(),
    'README.md':b'''# Original combined storage gate failure

Fixed code 72e4e64ce0e97b444146fe237efee9f199da16dc, 964 engineering inputs unchanged and Git-matched.
Actual whole Python: 2519 passed, 1 failed, 1 numeric-environment skipped, 2 warnings, 698.43s.
The original failure is test_content_store.py:232: process-wide file-descriptor count changed from15 to14.
No descriptor identity trace exists for that original schedule; do not infer which resource closed or a unique cause.
Ruff, mypy186 and specification checks passed. All four raw receipts/logs/inventories and the source composition are retained.

A separate actual unrelated descriptor closure reproduced the original assertion. Its later isolated-process test repair
and negative leak/foreign-close/same-count-replacement controls are separate evidence, not a rewrite of this FAIL.
No native, vendor, numeric execution, human approval or Quality workflow success is established by this package.
The verifier checks public integrity or replays exact path substitutions against original raw hashes; it does not rerun tests.
''',
}.items():
    (OUT/name).write_bytes(data)
    generated.append({'path':name,'bytes':len(data),'sha256':sha(data)})
manifest={'intended_repository_path':'progress/evidence/2026-09-22/M6.2-review-storage-initial-gates',
    'files':files,'generated_files':generated,'excluded_raw':[],
    'scope':'Original whole Python FAIL and successful static gates; no failed result omitted.',
    'transform_rules':'Ordered literal home/CI-home/pytest directory substitutions only; exact counts retained.'}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'raw_aliases':len(files),'public_files':len(dedup)+len(generated)+1,'manifest_sha256':sha((OUT/'manifest.json').read_bytes())}))
