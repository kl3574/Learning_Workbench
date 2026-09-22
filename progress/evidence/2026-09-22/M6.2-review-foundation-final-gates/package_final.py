"""Package actual successful final gates only; prior failures have their own package."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE / 'm62-active'
TEMPLATE = BASE / 'm62-current-proof-packages-v1/verify-template.py'
CODE = '416b53261dafa0ddbdec3adf4ef2deab058b866b'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() == CODE
receipts = {}
for gate in ['python', 'ruff', 'mypy', 'spec']:
    folder = HERE / gate
    receipt = load(folder / 'receipt.json')
    assert receipt['code_commit'] == CODE and receipt['exit_code'] == 0 and not receipt['timeout']
    assert receipt['source_count'] == 960 and receipt['source_unchanged']
    before, after = load(folder / 'inputs-before.json'), load(folder / 'inputs-after.json')
    assert before == after and all(row['git_matches'] for row in after)
    raw = (folder / 'test.log').read_bytes()
    assert len(raw) == receipt['log_bytes'] and sha(raw) == receipt['log_sha256']
    receipts[gate] = receipt

binding = load(HERE / 'composition-binding.json')
assert binding['implementation_commit'] == CODE and binding['source_count'] == 960
assert binding['all_engineering_bytes_identical_to_declared_origins']
counts = {}
for row in load(HERE / 'python/inputs-after.json'):
    origin = binding['explicit_origins'].get(row['path'], binding['default_origin'])
    raw = subprocess.check_output(['git', 'show', CODE + ':' + row['path']], cwd=ROOT)
    original = subprocess.check_output(['git', 'show', origin + ':' + row['path']], cwd=ROOT)
    assert raw == original and len(raw) == row['bytes'] and sha(raw) == row['sha256']
    counts[origin] = counts.get(origin, 0) + 1
assert counts == binding['origin_counts']

spec = importlib.util.spec_from_file_location('evidence_transform', TEMPLATE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
out = HERE / 'package'
out.mkdir(exist_ok=False)
files, generated, dedup = [], [], {}
names = ['run.py', 'runner-origin.json', 'composition-binding.json', 'package_final.py']
names += [gate + '/' + leaf for gate in receipts for leaf in ['receipt.json', 'test.log', 'inputs-before.json', 'inputs-after.json']]
for name in names:
    raw = (HERE / name).read_bytes()
    raw.decode('utf-8')
    data, transforms = module.transform(raw, str(Path.home()), '<CI_HOME>')
    digest = sha(raw)
    public = dedup.get(digest, name)
    if digest not in dedup:
        target = out / public
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        dedup[digest] = public
    files.append({'raw_cache': HERE.name, 'raw_path': name, 'raw_bytes': len(raw), 'raw_sha256': digest,
        'public_path': public, 'public_bytes': len(data), 'public_sha256': sha(data),
        'transformed': raw != data, 'transformation_counts': transforms})

def generated_file(name, raw):
    (out / name).write_bytes(raw)
    generated.append({'path': name, 'bytes': len(raw), 'sha256': sha(raw)})

generated_file('verify.py', TEMPLATE.read_bytes())
result_line = (HERE / 'python/test.log').read_text().strip().splitlines()[-1]
generated_file('README.md', f'''# M6.2 review foundation: final composed local gates

Fixed code `{CODE}`. Sole specification PRODUCT_DESIGN.md 3.0.7, SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`.

Actual complete Python result: `{result_line}`. Ruff, mypy and structural specification checks passed. All four runs preserve 960 engineering inputs before/after and match actual Git blobs. The composition binding compares every final source blob with its stated origin: the numeric foundation, the independently reviewed Jobs adapter, the reviewed Tutor cancellation test repair, or the root-authored ADR. This is a fresh combined Python gate, not a sum of earlier focused results.

The earlier acb full gate failed (2376 passed, one Tutor lease assertion failed, one numeric environment skip). Its original failure is preserved in M6.2-review-numeric-initial-gates. The real controlled renewal reproduction, unchanged strong assertions moved into the cancellation transaction, original Node setup failure and final 116 Tutor regressions are separately retained. Seven real Review adapter boundary failures and their repairs are in M6.2-review-job-lifecycle. None of these later successes rewrite old GitHub browser failures or establish their unique cause.

Implemented scope: frozen owner-backed numeric observations, strict review intent, and isolated internal Jobs lifecycle. Quality storage/worker/report/HTTP, human decisions and publication are not implemented by this slice. No new frontend or native suite is claimed. Numeric environment skip is not arithmetic success; production DeepSeek Agent, real Codex and independent teaching effectiveness remain NOT_RUN. Current CI needs its own exact-head readback.

The verifier checks these retained public bytes, optionally replaying all literal path substitutions against private raw hashes. It does not execute the application or authenticate a human review.
'''.encode())
write(out / 'manifest.json', {'intended_repository_path': 'progress/evidence/2026-09-22/M6.2-review-foundation-final-gates',
    'files': files, 'generated_files': generated, 'excluded_raw': [],
    'scope': 'Completed fixed-source gate receipts, logs, source inventories, runner and exact source composition; no database or credential.',
    'transform_rules': 'Ordered literal local/CI home and pytest root replacements, with exact per-file counts in the manifest.'})
print(json.dumps({'manifest_sha256': sha((out / 'manifest.json').read_bytes()),
    'raw_aliases': len(files), 'python_result': result_line}, indent=2))
