from pathlib import Path
import datetime, hashlib, json, os, subprocess

BASE = Path(__file__).resolve().parent
TREE = BASE.parent / 'm62-block-compare-integration-active'
MAIN = BASE.parent / 'm62-active'
FIXED = '84a07e23bb05e18119f215fd5e1532bbd095d53b'
BASELINE = 'a944ebfbdb835a731393977a606db5b473846e98'
OWNER = '05aa1af2fd000654b0d7b62e5eae32998c81d43f'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args, root=TREE):
    return subprocess.check_output(['git', '--no-optional-locks', *args], cwd=root)

def dump(name, value):
    path = BASE / name
    serialized = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if path.exists():
        assert path.read_text() == serialized
    else:
        path.write_text(serialized)

def tree(commit):
    result = {}
    for entry in git('ls-tree', '-rz', commit).split(b'\0'):
        if entry:
            metadata, path = entry.split(b'\t', 1)
            mode, kind, blob = metadata.decode().split()
            assert kind == 'blob'
            result[path.decode()] = {'mode': mode, 'blob': blob}
    return result

assert git('rev-parse', 'HEAD').decode().strip() == FIXED
assert git('status', '--porcelain') == b''
expected = tree(BASELINE)
owner = tree(OWNER)
changes = git('diff', '--name-only', BASELINE, FIXED).decode().splitlines()
assert changes == git('diff', '--name-only', '833f0a84168638ba5ce421c70cd2f20a71e45e48', OWNER).decode().splitlines()
assert len(changes) == 12
for name in changes:
    expected[name] = owner[name]
actual = tree(FIXED)
assert expected == actual
engine = {name: row for name, row in actual.items() if not name.startswith('progress/')}
verified = []
contents = {}
for name, item in sorted(engine.items()):
    raw = git('cat-file', 'blob', item['blob'])
    path = TREE / name
    disk = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
    assert disk == raw
    contents[name] = raw
    verified.append({'path': name, 'sha256': sha(raw), 'bytes': len(raw), 'git_blob_sha1': item['blob'], 'git_mode': item['mode']})
dump('final-source-pins.json', {'source': FIXED, 'input_scope': 'All tracked files excluding progress/; includes docs/ui and tracks Git symlink bytes when present.', 'count': len(verified), 'files': verified})
ledger = []
for name in ['web', 'web-lint', 'web-build', 'spec']:
    stage = BASE / name
    before = json.loads((stage / 'inputs-before.json').read_text())
    after = json.loads((stage / 'inputs-after.json').read_text())
    receipt = json.loads((stage / 'receipt.json').read_text())
    log = (stage / 'test.log').read_bytes()
    assert before == after and len(before) == len(engine)
    assert receipt['code_commit'] == receipt['head_after'] == FIXED
    assert receipt['source_count'] == len(engine) and receipt['source_unchanged']
    assert receipt['exit_code'] == 0 and not receipt['timeout']
    assert receipt['log_sha256'] == sha(log) and receipt['log_bytes'] == len(log)
    assert receipt['runner_sha256'] == sha((BASE / 'run.py').read_bytes())
    assert {row['path'] for row in before} == set(engine)
    for row in before:
        name_in_source = row['path']
        raw = contents[name_in_source]
        assert row['git_matches']
        assert row['git_blob_sha1'] == engine[name_in_source]['blob']
        assert row['git_mode'] == engine[name_in_source]['mode']
        assert row['sha256'] == sha(raw) and row['bytes'] == len(raw)
    ledger.append({'stage': name, **receipt, 'actual_git_verification': 'Every listed input read from actual fixed Git blob and compared to recorded bytes/hash and current worktree.'})
dump('run-ledger.json', ledger)
index = Path(git('rev-parse', '--git-path', 'index', root=MAIN).decode().strip())
main_state = {'head': git('rev-parse', 'HEAD', root=MAIN).decode().strip(), 'index_sha256': sha(index.read_bytes()), 'status': git('status', '--porcelain', root=MAIN).decode()}
prior_main = json.loads((BASE / 'protected-main-before.json').read_text())
assert main_state['head'] == prior_main['head'] and main_state['index_sha256'] == prior_main['index_sha256']
assert all(line[3:].startswith('progress/') for line in main_state['status'].splitlines())
dump('protected-main-after-gates.json', main_state)
backend_delta = git('diff', '--name-only', '62118f823b03da6bc4c34ba335f736e20ea31df6', FIXED, '--', 'services', 'packages', 'migrations', 'tests/unit', 'tests/integration', 'tests/contracts', 'pyproject.toml', 'uv.lock').decode().splitlines()
assert not backend_delta
dump('VERIFY.json', {'verified_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source': FIXED, 'baseline': BASELINE, 'comparison_owner': OWNER,
                     'exact_full_tree_composition': True, 'comparison_paths': changes, 'engineering_count': len(engine), 'complete_stage_count': len(ledger),
                     'all_stage_before_after_and_actual_git_equal': True, 'final_worktree_clean': True, 'main_head_index_unchanged': True, 'main_status_unchanged': main_state['status'] == prior_main['status'], 'observed_main_progress_changes': main_state['status'].splitlines(),
                     'backend_path_delta_vs_621': backend_delta, 'backend_paths_checked': ['services', 'packages', 'migrations', 'tests/unit', 'tests/integration', 'tests/contracts', 'pyproject.toml', 'uv.lock'],
                     'backend_gate_this_run': 'NOT_RUN', 'native_gate_this_run': 'NOT_RUN', 'remote_action': 'NONE'})
rows = []
for path in sorted(BASE.rglob('*')):
    if path.is_file() and path.name != 'MANIFEST.json':
        raw = path.read_bytes()
        rows.append({'path': path.relative_to(BASE).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)})
dump('MANIFEST.json', {'members': rows})
print(json.dumps({'source': FIXED, 'engineering_count': len(engine), 'members': len(rows), 'manifest_sha256': sha((BASE / 'MANIFEST.json').read_bytes())}, indent=2))
