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
CODE = '75b0ca5f83d809816b338c2d70cc5bfb9f1a3f83'
PREVIOUS = '88daa0a23dab0e69f7009b9af670671c45f90924'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def load(p):
    return json.loads(p.read_bytes())

def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() == CODE
receipts = {}
for gate in ['python', 'ruff', 'spec']:
    folder = HERE / gate
    r = load(folder / 'receipt.json')
    assert r['code_commit'] == CODE and r['exit_code'] == 0 and not r['timeout']
    assert r['source_count'] == 949 and r['source_unchanged']
    b, a = load(folder / 'inputs-before.json'), load(folder / 'inputs-after.json')
    assert b == a and all(x['git_matches'] for x in a)
    raw = (folder / 'test.log').read_bytes()
    assert len(raw) == r['log_bytes'] and sha(raw) == r['log_sha256']
    receipts[gate] = r

final = load(HERE / 'python/inputs-after.json')
native = load(BASE / 'm62-producer-parser-fixed-gates-v1/native/inputs-after.json')
old = {x['path']: x for x in native}
new = {x['path']: x for x in final}
assert old.keys() == new.keys()
changed = [p for p in new if new[p]['sha256'] != old[p]['sha256']]
assert sorted(changed) == ['tests/integration/test_evidence_independent_review.py',
                           'tests/integration/test_learning_evidence.py']
git_changed = subprocess.check_output(['git', 'diff', '--name-only', PREVIOUS, CODE], cwd=ROOT).decode().splitlines()
assert sorted(git_changed) == sorted(changed)
for row in final:
    b = subprocess.check_output(['git', 'show', CODE + ':' + row['path']], cwd=ROOT)
    assert len(b) == row['bytes'] and sha(b) == row['sha256']
write(HERE / 'inherited-gate-binding.json', {
    'code_commit': CODE, 'previous_gate_code_commit': PREVIOUS,
    'current_full_python_inputs': 949, 'each_final_source_verified_against_actual_git_blob': True,
    'native_and_mypy_source_change': changed, 'unchanged_engineering_files': 947,
    'scope': 'The only later changes are historical Python fixture tests. Native 12 PASS and mypy 180 PASS were actually run at the previous commit; all product/native/config inputs are unchanged. No native/mypy rerun at the final commit is claimed.',
    'final_inputs_sha256': sha((HERE / 'python/inputs-after.json').read_bytes()),
    'previous_native_inputs_sha256': sha((BASE / 'm62-producer-parser-fixed-gates-v1/native/inputs-after.json').read_bytes())})

spec = importlib.util.spec_from_file_location('evidence_transform', TEMPLATE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out = HERE / 'package'
out.mkdir(exist_ok=False)
files, generated, dedup = [], [], {}
names = ['run.py', 'runner-origin.json', 'inherited-gate-binding.json', 'package_final.py']
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
generated_file('README.md', f'''# M6.2 final fixed-source local gates

Code `{CODE}`; sole specification PRODUCT_DESIGN.md 3.0.7, SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`.

New complete Python run: `{result_line}`. Ruff and structural specification checks pass. Every run retains 949 before/after inputs matching the committed Git bytes; the final inventory was independently read from actual Git blobs during packaging. The one numeric-environment skip remains a skip, not an arithmetic success. The prior complete Python failure (3 FAIL / 2290 PASS / 1 environment SKIP) is preserved in its separate original gate package.

Only two historical fixture test files changed since `{PREVIOUS}`. The previous 12-case native gate and mypy 180-file check remain attributed to that commit. `inherited-gate-binding.json` documents 947 unchanged engineering inputs, including all product code, native tests and configuration; no new native or mypy execution is asserted. Full frontend/native suites, real DeepSeek platform E2E, sealed arithmetic success, human content approval and teaching effectiveness are not established by this package. Remote CI must be read separately for its exact head.

Run `python verify.py` for public integrity; optional `--raw-base`, `--raw-home`, `--ci-home` replay exact raw hashes and recorded literal path substitutions. Identical input manifests share one public payload through manifest aliases. This verifier checks retained bytes, not product functionality.
'''.encode())
write(out / 'manifest.json', {'intended_repository_path': 'progress/evidence/2026-09-22/M6.2-producer-final-gates',
      'files': files, 'generated_files': generated, 'excluded_raw': [],
      'scope': 'Explicit completed gate receipts, logs, source manifests and runner; no database, credential or runtime cache.',
      'transform_rules': 'Ordered local/CI home and pytest root replacements defined in verify.py with per-file counts.'})
print(json.dumps({'package': str(out), 'manifest_sha256': sha((out / 'manifest.json').read_bytes()),
                  'python_result': result_line, 'raw_aliases': len(files)}, indent=2))
