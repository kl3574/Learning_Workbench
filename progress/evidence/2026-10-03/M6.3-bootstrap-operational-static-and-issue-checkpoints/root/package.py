import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

BASE = Path('$HOME/.cache/learning-workbench-acceptance')
ROOT = BASE / 'm62-public-safe-oct02'
OUT = Path(__file__).parent
sha = lambda b: hashlib.sha256(b).hexdigest()
load = lambda folder, name: json.loads((BASE / folder / name).read_text())
static = 'm63-bootstrap-canonical-static-7b0e-oct03'
audit = 'm63-bootstrap-publication-preaudit-7b0e-oct03'
sync = 'm63-bootstrap-actual-issue32-sync-oct03'
admission = 'm63-bootstrap-backend-root-final-readback-oct03'
head = '7b0ee3ae7d94a0d069b873133e69b5aaf3a18c89'
before, after = load(static, 'before.json'), load(static, 'after.json')
assert before == after and before['head'] == head and len(before['files']) == 1381
assert before['private_runner_sha256'] == sha((BASE / static / 'run.py').read_bytes())
receipt = load(static, 'receipt.json')
assert receipt['head'] == head and receipt['input_count'] == 1381 and receipt['inputs_unchanged'] and receipt['all_git_match']
for name, result in receipt['results'].items():
    assert result['exit_code'] == 0 and result['log_sha256'] == sha((BASE / static / (name + '.log')).read_bytes())
preaudit = load(audit, 'receipt.json')
inputs = load(audit, 'inputs.json')
assert preaudit['head'] == head and preaudit['findings'] == [] and not preaudit['sourcepush']
assert sum(k.startswith('tree:') for k in inputs) == preaudit['current_tree_files'] == 17628
assert sum(k.startswith('outgoing:') for k in inputs) == preaudit['outgoing_blobs'] == 815
cache = {}
with subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as child:
    def facts(oid):
        if oid not in cache:
            child.stdin.write((oid + '\n').encode()); child.stdin.flush()
            header = child.stdout.readline().strip().split(); assert header[:2] == [oid.encode(), b'blob']
            data = child.stdout.read(int(header[2])); assert child.stdout.read(1) == b'\n'
            cache[oid] = (len(data), sha(data))
        return cache[oid]
    tree = {}
    for row in subprocess.check_output(['git', 'ls-tree', '-r', '-z', head], cwd=ROOT).split(b'\0'):
        if not row:
            continue
        metadata, path = row.split(b'\t', 1); mode, kind, oid = metadata.split()
        assert kind == b'blob'; tree[path.decode()] = oid.decode()
    assert {k[5:] for k in inputs if k.startswith('tree:')} == set(tree)
    for name, item in inputs.items():
        oid = tree[name[5:]] if name.startswith('tree:') else name[9:]
        if name.startswith('tree:'):
            assert item['object'] == oid
        assert facts(oid) == (item['bytes'], item['sha256'])
    assert {name for name in tree if not name.startswith('progress/')} == set(before['files'])
    for name, item in before['files'].items():
        assert tree[name] == item['git_blob'] and facts(item['git_blob']) == (item['bytes'], item['sha256'])
    child.stdin.close(); child.wait(); assert child.returncode == 0
issue = load(sync, 'readback.json')
assert issue['body_sha256'] == sha((BASE / sync / 'issue-body.md').read_bytes())
assert issue['metadata_and_outside_block_unchanged'] and issue['state'] == 'open' and not issue['sourcepush']
whitespace = load(admission, 'staged-whitespace-original.json')
assert whitespace['exit_code'] == 2 and whitespace['check_replay_bytes_match_initial_log']
attrs = subprocess.check_output(['git', 'show', 'd0d3a842:.gitattributes'], cwd=ROOT)
(OUT / 'adopted-exact-path.gitattributes').write_bytes(attrs)
for name, digest in whitespace['files'].items():
    assert sha((ROOT / name).read_bytes()) == digest and (name + ' -whitespace').encode() in attrs
report = {
    'status': 'PASS_INDEPENDENT_OPERATIONAL_READBACK', 'static_head': head,
    'static': 'Ruff/mypy250/structural80 actualPASS;1381 Git inputs unchanged, runner and logs bound.',
    'historical_preaudit': 'Exact7b currenttree17628 and815 outgoing blobs hash-read. Findings0 is bounded scanner result, not arbitrary-prose provenance guarantee. Additional commits still require fresh audit.',
    'historical_issue_sync': issue,
    'immutable_patch_admission': 'Original stagedwhitespaceexit2 retained for exactly two immutable evidence patches; hashes unchanged and exact-path attributes adopted in d0. Subsequent stagedcheckPASS and181-file scannerPASS observed in tool478905; not reconstructed log files or product tests.',
    'boundary': 'Evidence readback/package only. No new tests/runtime/model or sourcepush/merge/release/deploy. Complete184PythonRUNNING and all historicalFAIL remain separate.'
}
(OUT / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
groups = [
    ('static', static, ['run.py', 'before.json', 'after.json', 'receipt.json', 'ruff.log', 'mypy.log', 'structural.log']),
    ('preaudit', audit, ['audit.py', 'inputs.json', 'receipt.json']),
    ('issue-sync', sync, ['sync.py', 'issue-body.md', 'readback.json']),
    ('immutable-admission', admission, ['staged-whitespace-original.log', 'staged-whitespace-original.json']),
    ('root', OUT.name, ['package.py', 'READBACK.json', 'adopted-exact-path.gitattributes']),
    ('progress-updater', 'm63-bootstrap-gate-progress-oct04', ['update_progress.py']),
]
spec = importlib.util.spec_from_file_location('package_helper', BASE / 'm62-v313-pushed-progress-sync-oct03/package.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
public = helper.package('M6.3-bootstrap-operational-static-and-issue-checkpoints', groups, report.copy())
(OUT / 'PACKAGE_RECEIPT.json').write_text(json.dumps({'report': public}, indent=2) + '\n')
print(json.dumps({'static_readback': 'PASS', 'historical_preaudit': 'PASS', 'issue_sync': 'body-only verified', 'future_publication': 'pending fresh delta audit'}))
