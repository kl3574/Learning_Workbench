"""Package completed fixed-source gates only; never infer success from a live log."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE / 'm62-active'
TEMPLATE = BASE / 'm62-current-proof-packages-v1/verify-template.py'
CODE = 'e100f1b2ce02ccd0af85e2596b53ba2a24da9cda'
REVIEWED_CANDIDATE = '93130a93be4b6097be8a4aafd23bbf139ba142fb'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def load(p):
    return json.loads(p.read_bytes())

def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() == CODE
receipts = {}
for gate in ['python', 'ruff', 'mypy', 'spec']:
    folder = HERE / gate
    r = load(folder / 'receipt.json')
    assert r['code_commit'] == CODE and r['exit_code'] == 0 and not r['timeout']
    assert r['source_count'] == 951 and r['source_unchanged']
    b, a = load(folder / 'inputs-before.json'), load(folder / 'inputs-after.json')
    assert b == a and all(x['git_matches'] for x in a)
    raw = (folder / 'test.log').read_bytes()
    assert len(raw) == r['log_bytes'] and sha(raw) == r['log_sha256']
    receipts[gate] = r

final = load(HERE / 'python/inputs-after.json')
for row in final:
    raw = subprocess.check_output(['git', 'show', CODE + ':' + row['path']], cwd=ROOT)
    reviewed = subprocess.check_output(['git', 'show', REVIEWED_CANDIDATE + ':' + row['path']], cwd=ROOT)
    assert raw == reviewed and len(raw) == row['bytes'] and sha(raw) == row['sha256']
assert load(HERE / 'integration-binding.json')['all_engineering_bytes_identical']

spec = importlib.util.spec_from_file_location('evidence_transform', TEMPLATE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out = HERE / 'package'
out.mkdir(exist_ok=False)
files, generated, dedup = [], [], {}
names = ['run.py', 'runner-origin.json', 'integration-binding.json', 'package_final.py']
names += [gate + '/' + name for gate in receipts for name in ['receipt.json', 'test.log', 'inputs-before.json', 'inputs-after.json']]
for name in names:
    raw = (HERE / name).read_bytes()
    raw.decode('utf-8')
    data, counts = mod.transform(raw, str(Path.home()), '<CI_HOME>')
    digest = sha(raw)
    public = dedup.get(digest, name)
    if digest not in dedup:
        target = out / public
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        dedup[digest] = public
    files.append({'raw_cache': HERE.name, 'raw_path': name, 'raw_bytes': len(raw), 'raw_sha256': digest,
                  'public_path': public, 'public_bytes': len(data), 'public_sha256': sha(data),
                  'transformed': raw != data, 'transformation_counts': counts})

def generated_file(name, raw):
    (out / name).write_bytes(raw)
    generated.append({'path': name, 'bytes': len(raw), 'sha256': sha(raw)})

generated_file('verify.py', TEMPLATE.read_bytes())
result_line = (HERE / 'python/test.log').read_text().strip().splitlines()[-1]
generated_file('README.md', f'''# M6.2 complete review material: fixed-source local gates

Code `{CODE}`. Sole specification PRODUCT_DESIGN.md 3.0.7, SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`.

New complete Python result: `{result_line}`. Ruff, product mypy and structural specification checks pass. All four runs preserve 951 before/after input entries matching actual Git blobs; packaging also compares every engineering blob with the independently reviewed candidate `{REVIEWED_CANDIDATE}`. Prior development failures, including the original logging-privacy defect and inadequate first repr test, are retained in the separate material development package.

This adds internal read-only owner materials. There is no new review HTTP/UI, review Job/decision, human approval or publication here. The numeric-environment skip is not arithmetic success. No new frontend or native suite, vendor service, actual successful sealed calculator, Codex or teaching-effectiveness test is claimed. The older 88daa0a native evidence belongs to that earlier source; this package does not inherit its verdict for changed product source. CI needs its own exact-head readback.

Run `python verify.py` for the selected public payloads; optional raw-base/raw-home/ci-home replay literal recorded path substitutions and raw SHA bindings. Identical source inventories share a public payload through manifest aliases. The verifier checks retained bytes, not current application functionality.
'''.encode())
write(out / 'manifest.json', {'intended_repository_path': 'progress/evidence/2026-09-22/M6.2-review-material-fixed-gates',
      'files': files, 'generated_files': generated, 'excluded_raw': [],
      'scope': 'Explicit completed gate receipts, logs, source manifests and runner; no database, credential or runtime cache.',
      'transform_rules': 'Ordered local/CI home and pytest root replacements defined in verify.py with per-file counts.'})
print(json.dumps({'package': str(out), 'manifest_sha256': sha((out / 'manifest.json').read_bytes()),
                  'python_result': result_line, 'raw_aliases': len(files)}, indent=2))
