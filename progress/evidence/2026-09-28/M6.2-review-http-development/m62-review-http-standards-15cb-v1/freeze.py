import ast
import hashlib
import json
import subprocess
from pathlib import Path

OUT = Path(__file__).parent
ROOT = OUT.parent / 'm62-review-http-active'
EVIDENCE = OUT.parent / 'm62-review-http-verification-v1'
BASE = 'ba8fa7245330cdf4cbbf5788091d8411fa229cad'
HEAD = '15cb60882751f32d2d6f5b14516dfe6611c40fcc'
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
def sha(data): return hashlib.sha256(data).hexdigest()
def write(name, data): (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
files = git('diff', '--name-only', BASE + '...' + HEAD).decode().splitlines()
assert len(files) == 10
pins = []
for name in files:
    data = git('show', HEAD + ':' + name)
    target = OUT / 'source' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    pins.append({'path': name, 'bytes': len(data), 'sha256': sha(data), 'git_blob': git('rev-parse', HEAD + ':' + name).decode().strip()})
write('source-pins.json', {'base': BASE, 'head': HEAD, 'diff_command': f'git diff {BASE}...{HEAD}', 'commits': git('log', '--format=%H %s', BASE + '..' + HEAD).decode().splitlines(), 'files': pins})

# Independent source comparisons, not runtime tests.
job_path = 'services/api/app/application/jobs.py'
def branches(commit):
    tree = ast.parse(git('show', commit + ':' + job_path))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'JobService')
    owner = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_owner')
    return {ast.unparse(n.test): ast.dump(n, include_attributes=False) for n in owner.body if isinstance(n, ast.If)}
old, new = branches(BASE), branches(HEAD)
assert all(new[k] == v for k, v in old.items())
assert len(new) == len(old) + 1
oldapi = json.loads(git('show', BASE + ':packages/contracts/generated/openapi.json'))
api = json.loads(git('show', HEAD + ':packages/contracts/generated/openapi.json'))
assert all(api['paths'][k] == v for k, v in oldapi['paths'].items())
assert all(api['components']['schemas'][k] == v for k, v in oldapi['components']['schemas'].items())
added_paths = sorted(set(api['paths']) - set(oldapi['paths']))
added_schemas = sorted(set(api['components']['schemas']) - set(oldapi['components']['schemas']))
assert added_paths == ['/api/v1/drafts/{id}/review', '/api/v1/reviews/{id}', '/api/v1/reviews/{id}/decision']
assert added_schemas == ['DraftCandidate', 'DraftReviewWrite', 'ReviewDecisionWrite', 'ReviewJobAck', 'StoredReviewReceipt']
coverage = json.loads(git('show', HEAD + ':packages/contracts/generated/runtime-route-coverage.json'))
assert coverage['product_acceptance'] == 'NOT_RUN'
write('static-diff-readback.json', {'scope': 'AST/JSON comparison of fixed committed source; no application/test execution', 'existing_job_owner_branches_identical': sorted(old), 'new_job_owner_branch': sorted(set(new) - set(old)), 'old_openapi_paths_unchanged': True, 'old_openapi_schemas_unchanged': True, 'new_paths': added_paths, 'new_schemas': added_schemas, 'product_acceptance': coverage['product_acceptance']})

tree = {}
for raw in git('ls-tree', '-rz', HEAD).split(b'\0'):
    if not raw:
        continue
    meta, path = raw.split(b'\t', 1)
    mode, kind, identifier = meta.decode().split()
    name = path.decode()
    if kind == 'blob' and not name.startswith('progress/'):
        tree[name] = (mode, identifier)
assert len(tree) == 989
keys = sorted(tree)
raw = git('cat-file', '--batch') if not keys else subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT, input=('\n'.join(tree[k][1] for k in keys) + '\n').encode())
offset = 0; actual = {}
for name in keys:
    end = raw.index(b'\n', offset)
    oid, kind, size = raw[offset:end].decode().split()
    size = int(size); body = raw[end + 1:end + 1 + size]; offset = end + 2 + size
    assert oid == tree[name][1] and kind == 'blob'
    actual[name] = {'sha256': sha(body), 'bytes': len(body), 'git_blob_sha1': oid, 'git_mode': tree[name][0]}
checks = []
for stage in ['related', 'ruff', 'mypy', 'spec']:
    folder = EVIDENCE / stage
    receipt = json.loads((folder / 'receipt.json').read_text())
    assert receipt['code_commit'] == HEAD and receipt['exit_code'] == 0 and receipt['source_count'] == len(tree)
    before = json.loads((folder / 'inputs-before.json').read_text())
    after = json.loads((folder / 'inputs-after.json').read_text())
    assert before == after and len(before) == len(tree)
    observed = {item['path']: {k: item[k] for k in ['sha256', 'bytes', 'git_blob_sha1', 'git_mode']} for item in before}
    assert observed == actual
    logs = [p for p in folder.glob('*.log') if sha(p.read_bytes()) == receipt['log_sha256']]
    assert len(logs) == 1
    log = logs[0].read_bytes(); assert len(log) == receipt['log_bytes']
    target = OUT / 'author-evidence' / stage
    target.mkdir(parents=True, exist_ok=True)
    for name in ['receipt.json', 'inputs-before.json', 'inputs-after.json', logs[0].name]:
        (target / name).write_bytes((folder / name).read_bytes())
    checks.append({'stage': stage, 'code_commit': HEAD, 'source_count_independently_verified': len(tree), 'complete_git_inventory_matches_before_after': True, 'log_sha256': sha(log), 'log_bytes': len(log), 'exit_code': receipt['exit_code'], 'log_tail': log.decode().splitlines()[-3:]})
write('evidence-verification.json', {'scope': 'Author run receipts/logs plus every recorded source independently checked against fixed Git blobs; reviewer ran no tests', 'stages': checks})
(OUT / 'STANDARDS.md').write_text('''# Standards

No blocking Standards finding in `ba8fa724...15cb6088` (10 files, four commits). Sole documented authority is PRODUCT_DESIGN.md; AGENTS.md points only to it. Tool-enforced lint/type rules were not re-reviewed as manual findings.

The added HTTP adapter delegates commands and reads to Quality application ports; it does not access another module's tables (spec:349). Production composition binds real import/single/group candidate owners, existing numeric-history owners, the real ReviewWorker and explicit `(profile, job kind)` artifact readers. Startup and shutdown register the new worker symmetrically without substituting a placeholder.

`jobs.py:94–95,133–145` adds only explicit injected ReviewService dispatch. Independent AST comparison confirms every previous owner branch is unchanged, including version-sensitive single/group Authoring and numeric routing, Grading, Import, Retrieval, Tutor and missing-job handling. Unknown kinds retain their prior unavailable result. Original safe-control delegation is preserved for existing consumers.

`import_http.py:37–41` permits the composed Jobs/Artifacts services while preserving the standalone defaults. Registered import readers remain present beside the exact Quality report reader; download adds no-store/Cookie variance and retains the actual owner download. The report route does not turn routing metadata into permission.

The fixed generated OpenAPI JSON adds exactly three paths and five DTO schemas; every prior path and schema is unchanged as parsed JSON. Typed client/coverage follow the same three operations, with product_acceptance still NOT_RUN (spec:964–966, R-29). Synthetic tests explicitly preserve mathematical/source/pedagogy NOT_RUN and do not claim human approval. No actionable baseline smell outweighs these explicit boundaries.

Read-only evidence verification: author related gate172PASS/2dependency warnings, RuffPASS, mypy195PASS and specPASS; all four stages'989 before/after engineering inputs independently match every fixed Git blob and log hashes. Reviewer did not rerun tests. This review covers this fixed HTTP slice, not later privacy/workflow increments or full product acceptance.
''')
members = [{'path': p.relative_to(OUT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'manifest.json']
write('manifest.json', {'head': HEAD, 'files': members})
print(json.dumps({'head': HEAD, 'files': len(members), 'manifest_sha256': sha((OUT / 'manifest.json').read_bytes())}))
