import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

BASE = Path('$HOME/.cache/learning-workbench-acceptance')
ROOT = BASE / 'm62-public-safe-oct02'
OUT = Path(__file__).parent
sha = lambda data: hashlib.sha256(data).hexdigest()
names = ('m63-bootstrap-native-a2d9-oct03', 'm63-bootstrap-initial-read-fix-oct03',
         'm63-bootstrap-native-a480-oct03', 'm63-bootstrap-read-boundary-test-oct03')
groups = []
counts = {}
for name in names:
    folder = BASE / name
    raw = json.loads((folder / 'RAW_MANIFEST.json').read_text())
    safe = json.loads((folder / 'SAFE_SHARE.json').read_text())
    assert raw['count'] == len(raw['files']) == safe['count'] == len(safe['files'])
    by_name = {item['path']: item for item in safe['files']}
    assert len(by_name) == raw['count']
    for item in raw['files']:
        path = item['path']
        assert '..' not in Path(path).parts and not Path(path).is_absolute()
        data = (folder / path).read_bytes()
        assert sha(data) == item['sha256'] and len(data) == item['bytes']
        candidate_directory = 'public-candidates' if name in names[:2] else 'safe-share'
        candidate = (folder / candidate_directory / path).read_bytes()
        entry = by_name[path]
        assert entry['raw_sha256'] == sha(data) and entry['raw_bytes'] == len(data)
        assert candidate == data.replace(b'$HOME', b'$HOME')
        assert sha(candidate) == entry['public_sha256'] and len(candidate) == entry['public_bytes']
    counts[name] = raw['count']
    groups.append((name, name, [item['path'] for item in raw['files']] + ['RAW_MANIFEST.json', 'SAFE_SHARE.json', 'SAFE_SCAN.json']))

source_maps = {}
cache = {}
with subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as child:
    for name in (names[0], names[2], names[3]):
        folder = BASE / name
        before = json.loads((folder / 'before.json').read_text())
        after = json.loads((folder / 'after.json').read_text())
        assert before['head'] == after['head'] and before['files'] == after['files']
        assert before['all_exact_git'] and after['all_exact_git'] and before['status'] == after['status'] == ''
        assert after.get('count_all_tracked', after.get('tracked_count')) == 17161
        assert after.get('count_nonprogress', after.get('nonprogress_count')) == 1376
        assert before['count_all_tracked'] == len(before['files']) == 17161
        assert before['count_nonprogress'] == sum(not x['path'].startswith('progress/') for x in before['files']) == 1376
        tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', before['head']], cwd=ROOT).split(b'\0')
        tree_by_path = {}
        for item in filter(None, tree):
            metadata, path = item.split(b'\t', 1)
            mode, kind, oid = metadata.split()
            assert kind == b'blob'
            tree_by_path[path.decode()] = (mode.decode(), oid.decode())
        assert set(tree_by_path) == {x['path'] for x in before['files']}
        for item in before['files']:
            path = item['path']; oid = item['git_blob_sha1']
            assert tree_by_path[path] == (item['mode'], oid) and item['exact_git']
            if oid not in cache:
                child.stdin.write((oid + '\n').encode()); child.stdin.flush()
                header = child.stdout.readline().strip().split()
                assert header[0].decode() == oid and header[1] == b'blob'
                data = child.stdout.read(int(header[2])); assert child.stdout.read(1) == b'\n'
                cache[oid] = (len(data), sha(data))
            assert cache[oid] == (item['bytes'], item['sha256']), path
        source_maps[name] = {'head': before['head'], 'tracked': 17161, 'nonprogress': 1376, 'exact_git_and_before_after': True}
    child.stdin.close(); child.wait(); assert child.returncode == 0

actual_path = 'native-output/codex-bootstrap-actual-loc-ae767-ent-metadata-across-restart/codex-bootstrap-actual.json'
actual = json.loads((BASE / names[2] / actual_path).read_text())
assert actual['real_thread'] == 'PASS' and actual['actor_preserved'] and actual['database_identity_unchanged']
assert actual['api_processes'] == 2 and actual['page_errors'] == []
assert actual['decline_session_posts'] == 0 and actual['decline_registered_instances'] == {'sessions': 0, 'permits': 0, 'finished': 0}
assert actual['create_posts_before_explicit_replay'] == 1
assert actual['registrations_before_restart'] == actual['registrations_after_restart_and_replay'] == {'sessions': 1, 'permits': 1, 'finished': 1}
assert actual['session_current']['status'] == 'ready' and actual['session_current']['revision'] == 2
assert actual['session_current']['active_turn_id'] is None and not any(actual['session_current']['capabilities'].values())
assert len(actual['original_replays']) == 5
for entry in actual['original_replays']:
    assert entry['equal_ack_bytes'] and entry['original_status'] == entry['replay_status']
    assert entry['original_ack_sha256'] == entry['replay_ack_sha256']
for view in actual['viewport_bounds'].values():
    assert view['scroll'] <= view['client'] + 1 and view['inner_scroll'] <= view['inner_client'] + 1
    assert view['left'] >= 0 and view['right'] <= view['viewport'] and view['document'] <= view['viewport']

native = json.loads((BASE / names[2] / '01-native.json').read_text())
assert native['head'] == source_maps[names[2]]['head'] == 'a48033ff9fe4beb78e5458b9806d7933d9faff66'
assert native['exit_code'] == 0
final = json.loads((BASE / names[3] / '02-full-web.json').read_text())
assert final['head'] == source_maps[names[3]]['head'] == 'f321c6f9574451c2e4d75f3be40cd9427e7bd4f5'
assert final['exit_code'] == 0
changes = subprocess.check_output(['git', 'diff', '--name-only', 'a48033ff', 'f321c6f9'], cwd=ROOT, text=True).splitlines()
assert changes == ['apps/web/src/features/authoring/AuthoringBootstrap.test.tsx']
for path in ('tests/e2e/codex-bootstrap.spec.ts', 'apps/web/src/features/codex/useBootstrap.ts'):
    assert subprocess.check_output(['git', 'show', 'a48033ff:' + path], cwd=ROOT) == subprocess.check_output(['git', 'show', 'f321c6f9:' + path], cwd=ROOT)
report = {'status': 'PASS_SCOPED_WEB_NATIVE_INDEPENDENT_READBACK', 'explicit_original_and_candidate_files': counts,
          'source_maps': source_maps, 'actual_native': 'a480 one new case PASS; ready/r2, two API OS processes, same DB, five original ACK byte-equal replays, counts stay1; no independent CLI process count from this browser layer',
          'final_web': 'f321 complete1038 PASS/145files plus strict/build849 PASS; test-only readiness wait, production/native unchanged froma480',
          'preserved': 'Originala2d9 newnative FAIL before prepare/real thread NOT_RUN; separately controlled same-symptom RED/GREEN; a480 fullWeb1037PASS1FAIL asynchronous button-readiness assertion; no historical gate upgraded',
          'root_review': 'Root read native/helper/delta source and viewed synthetic original failure,390 and1440 screenshots. No raw thread/Broker/transport secrets in explicit candidates. Exact file maps match before/after; a480 after metadata uses differently named counts and adds captured_utc, preserved as-is.',
          'boundary': 'Readback, not new browser/model/control execution. Formal full128-case canonicalbd3b native running separately. Complete PythonDCF has setupERROR markers; whole M6.3/AC21/Broker unaccepted. No source push/merge/release/deploy.'}
(OUT / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('package_helper', BASE / 'm62-v313-pushed-progress-sync-oct03/package.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
groups.append(('independent', OUT.name, ['verify_package.py', 'READBACK.json', 'verify_package.attempt01.py', 'READBACK_ATTEMPT01.json', 'verify_package.attempt02.py', 'READBACK_ATTEMPT02.json']))
public_report = helper.package('M6.3-bootstrap-web-and-native-actual-readback', groups, report.copy())
(OUT / 'PACKAGE_RECEIPT.json').write_text(json.dumps({'report': public_report}, indent=2) + '\n')
print(json.dumps({'source_maps_verified': len(source_maps), 'all_raw_and_exact_home_candidates': sum(counts.values()), 'native_readback': 'PASS', 'whole_stage': 'INCOMPLETE'}))
