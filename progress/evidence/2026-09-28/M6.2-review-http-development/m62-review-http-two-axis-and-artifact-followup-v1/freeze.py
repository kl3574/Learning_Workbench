import hashlib
import json
import subprocess
from pathlib import Path

OUT = Path(__file__).parent
ROOT = OUT.parent / 'm62-review-http-active'
EVIDENCE = OUT.parent / 'm62-review-http-verification-v1'
STD = OUT.parent / 'm62-review-http-standards-15cb-v1'
SPEC = OUT.parent / 'm62-review-http-spec-15cb-v1'
HEAD = '82ca2052de914bf8ea53cb36a9b8be2c9b64c7bf'
RED = '06c54ed19a0f2cc9125cb6c3fbb75059bf69241f'
def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
def write(name, value): (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

verified = []
for folder, name, expected in [(STD, 'manifest.json', '727659659e781797e79ba447f12652deeb9cda7ecd2a5b62841ffea106ef49b0'), (SPEC, 'MANIFEST.json', 'd0ce4787875592b83aafb0ddf548fd7316da6ba8fe5312595442cca525cda636')]:
    raw = (folder / name).read_bytes(); assert sha(raw) == expected
    value = json.loads(raw); members = value['files'] if isinstance(value, dict) else value
    for item in members:
        data = (folder / item['path']).read_bytes()
        assert len(data) == item['bytes'] and sha(data) == item['sha256']
    verified.append({'path': str(folder), 'manifest': name, 'sha256': sha(raw), 'members_verified': len(members)})
write('axis-evidence-index.json', verified)
standards = (STD / 'STANDARDS.md').read_text().removeprefix('# Standards\n')
spec = (SPEC / 'REPORT.md').read_text().split('\n', 1)[1]
(OUT / 'HTTP_TWO_AXIS.md').write_text('# Fixed HTTP review: ba8fa72...15cb608\n\n## Standards\n' + standards + '\n## Spec\n' + spec + '\nStandards: 0 findings; worst issue: none. Spec: 0 findings; worst issue: none.\n')

base = git('rev-parse', RED + '^').decode().strip()
changed = git('diff', '--name-only', base, HEAD).decode().splitlines()
assert changed == ['tests/integration/test_artifact_owners.py']
for label, commit in [('before', base), ('red', RED), ('green', HEAD)]:
    target = OUT / 'source' / (label + '-test_artifact_owners.py')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(git('show', commit + ':' + changed[0]))
write('followup-source-pins.json', {'base': base, 'red': RED, 'green': HEAD, 'changed_paths': changed, 'production_changes': [], 'diff': git('diff', base, HEAD, '--', changed[0]).decode()})
checks = []
for stage in ['related-final', 'warning-artifact-guard-red', 'warning-artifact-guard-green']:
    folder = EVIDENCE / stage
    receipt = json.loads((folder / 'receipt.json').read_text())
    head = receipt['code_commit']
    before = json.loads((folder / 'inputs-before.json').read_text())
    after = json.loads((folder / 'inputs-after.json').read_text())
    assert before == after and len(before) == receipt['source_count'] == 990
    tree = {}
    for raw in git('ls-tree', '-rz', head).split(b'\0'):
        if not raw: continue
        meta, name = raw.split(b'\t', 1); mode, kind, oid = meta.decode().split(); name = name.decode()
        if kind == 'blob' and not name.startswith('progress/'): tree[name] = (mode, oid)
    assert len(tree) == len(before) and set(tree) == {v['path'] for v in before}
    keys = sorted(tree)
    raw = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT, input=('\n'.join(tree[k][1] for k in keys) + '\n').encode())
    offset = 0; actual = {}
    for name in keys:
        end = raw.index(b'\n', offset); oid, kind, size = raw[offset:end].decode().split(); size = int(size)
        body = raw[end+1:end+1+size]; offset = end+2+size
        assert oid == tree[name][1] and kind == 'blob'
        actual[name] = {'sha256': sha(body), 'bytes': len(body), 'git_blob_sha1': oid, 'git_mode': tree[name][0]}
    assert actual == {v['path']: {k: v[k] for k in ['sha256', 'bytes', 'git_blob_sha1', 'git_mode']} for v in before}
    logs = [p for p in folder.glob('*.log') if sha(p.read_bytes()) == receipt['log_sha256']]; assert len(logs) == 1
    log = logs[0].read_bytes(); assert len(log) == receipt['log_bytes']
    target = OUT / 'author-evidence' / stage; target.mkdir(parents=True, exist_ok=True)
    for name in ['receipt.json', 'inputs-before.json', 'inputs-after.json', logs[0].name]: (target / name).write_bytes((folder / name).read_bytes())
    checks.append({'stage': stage, 'head': head, 'source_count': len(actual), 'before_after_independently_verified_git': True, 'exit_code': receipt['exit_code'], 'log_sha256': sha(log), 'log_tail': log.decode().splitlines()[-4:]})
write('followup-evidence-verification.json', {'scope': 'Read-only source and author evidence verification; reviewer did not run tests', 'runs': checks})
(OUT / 'ARTIFACT_TEST_FOLLOWUP.md').write_text('''# Bounded test repair review

No blocking finding in the fixed06c54ed19a0f2cc9125cb6c3fbb75059bf69241f →82ca2052de914bf8ea53cb36a9b8be2c9b64c7bf repair. Only tests/integration/test_artifact_owners.py changes; production code is identical across the probe/repair commits.

The original c2c5ee8 gate is264PASS with **3warnings**, including a real PytestUnhandledThreadExceptionWarning from learning-tutor-worker. Its traceback reaches the test's shared Database.connect monkeypatch. It must not be reported as a clean2dependency-warning pass.

The added concurrent database.workspace_id probe produces an actual deterministic test RED at06c54ed:1FAIL/4warnings. The original shared factory patch rejects that real second-thread read, and the log also records two background-worker exceptions. At82ca205, Database(database.settings) creates a separate connection-factory object for the exact same SQLite path; the checked ImportService alone owns it. Database.__init__ only sets settings/path. Patching that object's connect no longer replaces the application workers' shared factory.

The test still holds the caller's existing transaction with PRAGMA query_only=ON, passes that exact connection to the real owner, compares exact returned bytes/descriptor, and verifies unchanged database dump. A new explicit assertion proves the owner factory itself really rejects connect; a concurrent real app-factory read must succeed. This preserves the old guard while adding its missing isolation boundary, without mocking the owner, weakening assertions, muting warnings or changing timeouts. Relevant requirement: PRODUCT_DESIGN.md:349 and R-29; no contract or migration change.

The same focused case at82ca205 is1PASS/2dependency warnings. All three runs'990 complete engineering inputs independently match their fixed Git blobs before/after, and full raw logs/receipts remain copied privately. The reviewer did not rerun tests. The264-case suite was not repeated on82ca205 here; root's upcoming complete combined gate remains separate evidence. Real provider and human approval NOT_RUN.
''')
members = [{'path': p.relative_to(OUT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'manifest.json']
write('manifest.json', {'http_head': '15cb60882751f32d2d6f5b14516dfe6611c40fcc', 'test_repair_head': HEAD, 'files': members})
print(json.dumps({'files': len(members), 'manifest_sha256': sha((OUT / 'manifest.json').read_bytes())}))
