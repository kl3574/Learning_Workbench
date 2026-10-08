import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

BASE = Path('$HOME/.cache/learning-workbench-acceptance')
ROOT = BASE / 'm62-public-safe-oct02'
FOLDER = BASE / 'm63-bootstrap-full-native-bd3b-evidence-oct03'
OUT = Path(__file__).parent
HEAD = 'bd3b9375b41cf9a726260e7497a7302f11c3db04'
sha = lambda data: hashlib.sha256(data).hexdigest()
load = lambda name: json.loads((FOLDER / name).read_text())
raw = load('RAW_MANIFEST.json')
safe = load('SAFE_SHARE.json')
artifacts = load('ARTIFACT_MANIFEST.json')
assert raw['count'] == len(raw['files']) == 230
assert artifacts['count'] == len(artifacts['files']) == 217
assert safe['count'] == len(safe['files']) == 23 and safe['only_explicit_candidates']
raw_by_name = {v['path']: v for v in raw['files']}
assert len(raw_by_name) == 230
for item in raw['files']:
    name = item['path']
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    data = (FOLDER / name).read_bytes()
    assert (len(data), sha(data)) == (item['bytes'], item['sha256']), name
for item in artifacts['files']:
    assert item == raw_by_name[item['path']]
for item in safe['files']:
    data = (FOLDER / item['path']).read_bytes()
    candidate = (FOLDER / 'safe-share' / item['path']).read_bytes()
    assert candidate == data.replace(b'$HOME', b'$HOME')
    assert (len(data), sha(data)) == (item['raw_bytes'], item['raw_sha256'])
    assert (len(candidate), sha(candidate)) == (item['public_bytes'], item['public_sha256'])

before, after = load('before.json'), load('after.json')
assert before == after
assert before['head'] == HEAD and before['status'] == '' and before['all_exact_git']
assert before['count_all_tracked'] == len(before['files']) == 17628
assert before['count_nonprogress'] == sum(not v['path'].startswith('progress/') for v in before['files']) == 1381
tree = {}
for row in subprocess.check_output(['git', 'ls-tree', '-r', '-z', HEAD], cwd=ROOT).split(b'\0'):
    if not row:
        continue
    metadata, path = row.split(b'\t', 1)
    mode, kind, oid = metadata.split()
    assert kind == b'blob'
    tree[path.decode()] = (mode.decode(), oid.decode())
assert set(tree) == {v['path'] for v in before['files']}
cache = {}
with subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as child:
    for item in before['files']:
        oid = item['git_blob_sha1']
        assert tree[item['path']] == (item['mode'], oid) and item['exact_git']
        if oid not in cache:
            child.stdin.write((oid + '\n').encode()); child.stdin.flush()
            header = child.stdout.readline().strip().split()
            assert header[:2] == [oid.encode(), b'blob']
            data = child.stdout.read(int(header[2])); assert child.stdout.read(1) == b'\n'
            cache[oid] = (len(data), sha(data))
        assert cache[oid] == (item['bytes'], item['sha256'])
    child.stdin.close(); child.wait(); assert child.returncode == 0

receipt = load('receipt.json')
assert receipt['head'] == HEAD and receipt['exit_code'] == 0
assert receipt['command'] == ['apps/web/node_modules/.bin/playwright', 'test', '--config', 'tests/e2e/playwright.config.ts', '--workers=1', '--retries=0']
assert b'128 passed (18.1m)' in (FOLDER / 'run.log').read_bytes()
summary = load('RUN_SUMMARY.json')
assert summary['head'] == HEAD and (summary['passed'], summary['failed'], summary['skipped']) == (128, 0, 0)
assert summary['workers'] == 1 and summary['retries'] == 0 and summary['case_filter'] is None
for block in [summary['bootstrap'], *summary['physical_numeric'].values()]:
    assert sha((FOLDER / block['source']).read_bytes()) == block['raw_sha256']
actual = load(summary['bootstrap']['source'])
assert actual['real_thread'] == 'PASS' and actual['actor_preserved'] and actual['database_identity_unchanged']
assert actual['api_processes'] == 2 and actual['page_errors'] == []
assert actual['create_posts_before_explicit_replay'] == 1
assert actual['decline_session_posts'] == 0 and actual['decline_registered_instances'] == {'sessions': 0, 'permits': 0, 'finished': 0}
assert actual['registrations_before_restart'] == actual['registrations_after_restart_and_replay'] == {'sessions': 1, 'permits': 1, 'finished': 1}
assert actual['session_current']['status'] == 'ready' and actual['session_current']['revision'] == 2
assert actual['session_current']['active_turn_id'] is None and not any(actual['session_current']['capabilities'].values())
assert len(actual['original_replays']) == 5
for item in actual['original_replays']:
    assert item['equal_ack_bytes'] and item['original_status'] == item['replay_status']
    assert item['original_ack_sha256'] == item['replay_ack_sha256']
for item in actual['viewport_bounds'].values():
    assert item['scroll'] <= item['client'] + 1 and item['inner_scroll'] <= item['inner_client'] + 1
    assert item['left'] >= 0 and item['right'] <= item['viewport'] and item['document'] <= item['viewport']
for item in summary['physical_numeric'].values():
    assert (item['job_status'], item['outcome'], item['verdict']) == ('failed', 'environment_unavailable', 'BLOCKED')
assert summary['physical_numeric']['restore']['publication_http_status'] == 409
for item in load('ui-source-equality.json'):
    assert item['equals_f321']
    assert subprocess.check_output(['git', 'show', HEAD + ':' + item['path']], cwd=ROOT) == subprocess.check_output(['git', 'show', 'f321c6f9:' + item['path']], cwd=ROOT)
report = {
    'status': 'PASS_INDEPENDENT_READBACK_OF_COMPLETE_NATIVE',
    'source_head': HEAD, 'tracked_git_inputs': 17628, 'engineering_inputs': 1381,
    'raw_files_hash_verified': 230, 'explicit_candidates_hash_verified': 23,
    'formal_native': {'pass': 128, 'fail': 0, 'skip': 0, 'exit_code': 0, 'workers': 1, 'retries': 0, 'filter': None},
    'actual_bootstrap': 'ready/r2; all three capabilities false; two API OS processes and same DB; five original ACK replays byte-identical; persisted session/permit/finish counts1/1/1. Browser evidence does not independently count OS CLI starts.',
    'numeric': 'Authoring and Restore environment_unavailable/BLOCKED; Jobs failed; Restore publication409. These remain physical execution BLOCKED.',
    'root_visual_review': 'Viewed the two explicit 1440/390 bootstrap screenshots; synthetic identifiers and product metadata, no upstream thread ID or private Broker path. Geometry assertions verified.',
    'boundary': 'Independent evidence readback only, no new execution. Prior failed gates unchanged. Complete PythonDCF remains FAIL; new184 run separate and pending. Complete M6.3/AC21 remains unaccepted; no source push/merge/release/deploy.'
}
(OUT / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('package_helper', BASE / 'm62-v313-pushed-progress-sync-oct03/package.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
public = helper.package('M6.3-bootstrap-complete-native-bd3b', [
    ('native', FOLDER.name, [v['path'] for v in safe['files']] + ['RAW_MANIFEST.json', 'SAFE_SHARE.json', 'SAFE_SCAN.json']),
    ('independent', OUT.name, ['verify_package.py', 'READBACK.json']),
], report.copy())
(OUT / 'PACKAGE_RECEIPT.json').write_text(json.dumps({'report': public}, indent=2) + '\n')
print(json.dumps({'readback': 'PASS', 'formal_native': '128PASS', 'raw': 230, 'explicit': 23, 'tracked': 17628, 'physical_numeric': 'BLOCKED'}))
