"""Normal local merge of reviewed source; preserve every preexisting progress byte."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

base_dir = Path('$HOME/.cache/learning-workbench-acceptance')
root = base_dir / 'm62-public-safe-oct02'
out = Path(__file__).parent
expected = '35aebd3039241abb3393300affd593f4826a4a0c'
candidate = '22dade7996f13634202250ef5e1c05dc976214a5'
assert not (out / 'command.json').exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git', *args], cwd=root)
def dump(name, data): (out / name).write_text(json.dumps(data, indent=2) + '\n')
assert git('rev-parse', 'HEAD').decode().strip() == expected
assert git('diff', '--cached', '--name-only') == b''
changed = git('diff', '--name-only', expected, candidate).decode().splitlines()
assert len(changed) == 8 and all(p.startswith('apps/web/src/features/codex/') for p in changed)
dirty = git('diff', '--name-only').decode().splitlines()
assert sorted(dirty) == sorted(['progress/state.json', 'progress/CURRENT.md', 'progress/M6.3-next.md', 'progress/M6.3-bootstrap-acceptance.md'])
untracked = list(filter(None, git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')))
assert all(p.startswith('progress/evidence/2026-10-05/M6.3-') for p in untracked)
owned_existing = {p: (root / p).read_bytes() for p in dirty + untracked}
for name in dirty:
    file = out / 'before' / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(owned_existing[name])
def tree(head, progress):
    values = {}
    for row in filter(None, git('ls-tree', '-rz', head).split(b'\0')):
        info, name = row.split(b'\t', 1)
        mode, kind, blob = info.decode().split()
        name = name.decode()
        if name.startswith('progress/') != progress:
            continue
        values[name] = {'mode': mode, 'type': kind, 'git_blob': blob}
    return values
before_progress = tree(expected, True)
before_source = tree(expected, False)
candidate_source = tree(candidate, False)
assert len(before_source) == 1524 and len(candidate_source) == 1525
assert all(before_source[p] == candidate_source[p] for p in before_source if p not in changed)
for name, entry in before_source.items():
    assert (root / name).read_bytes() == git('cat-file', 'blob', entry['git_blob'])
peer = base_dir / 'm63-session-interrupt-ui-independent-review-oct05'
assert sha((peer / 'FINAL_REVIEW.md').read_bytes()) == '0b48eca0fea2fbaef8b79d239f6879eef2970b773ba11a793c504d43022ffd63'
assert sha((peer / 'FINAL_READBACK.json').read_bytes()) == '4d7e3103eef1f6985e09a6282137f59d10378dad2b3dcdc1118ca7970d073a05'
native = json.loads((base_dir / 'm63-native-formal-22dade-oct05/receipt.json').read_text())
assert native['source_sha'] == candidate and native['exit_code'] == native['wrapper_exit_code'] == 0
assert native['actual_suite_summary'] == ['\n  133 passed (20.4m)']
dump('before.json', {'head': expected, 'dirty': dirty, 'untracked_count': len(untracked),
    'preserved_working_files': {p: {'sha256': sha(v), 'bytes': len(v)} for p, v in owned_existing.items()},
    'progress_tree': before_progress, 'engineering_inputs': before_source})
argv = ['git', 'merge', '--no-ff', candidate, '-m', 'feat(M6.3): expose durable session interrupt control']
dump('command.json', {'argv': argv, 'cwd': str(root), 'expected_before': expected,
    'candidate': candidate, 'source_review': 'INDEPENDENT_TWO_AXES_ZERO_NEW',
    'full_native': 'ACTUAL133PASS_FOR_EXACT_CANDIDATE', 'remote_merge_push': False})
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = subprocess.run(argv, cwd=root, capture_output=True)
(out / 'stdout').write_bytes(result.stdout)
(out / 'stderr').write_bytes(result.stderr)
assert result.returncode == 0
merged = git('rev-parse', 'HEAD').decode().strip()
assert git('show', '-s', '--format=%P', merged).decode().split() == [expected, candidate]
assert tree(merged, True) == before_progress and tree(merged, False) == candidate_source
assert all((root / name).read_bytes() == data for name, data in owned_existing.items())
for name, entry in candidate_source.items():
    assert (root / name).read_bytes() == git('cat-file', 'blob', entry['git_blob'])
dump('READBACK.json', {'started_utc': start, 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'NORMAL_LOCAL_MERGE_EXACT_REVIEWED_CANDIDATE_ALL_PROGRESS_PRESERVED',
    'exit_code': result.returncode, 'head': merged, 'parents': [expected, candidate], 'source_paths': changed,
    'engineering_inputs': 1525, 'all_engineering_git_blobs_exact_candidate': True,
    'unchanged_old_nonoverlap_inputs': 1517, 'old_progress_git_tree_exact': True,
    'dirty_and_untracked_progress_bytes_preserved': len(owned_existing),
    'public_source_still': expected, 'M6_3': 'NOT_ACCEPTED', 'M7': 'NOT_ACCEPTED',
    'source_push_github_merge_release_deploy_model_calls': False})
print(json.dumps({'head': merged, 'exit_code': result.returncode, 'preserved_progress_files': len(owned_existing), 'source_inputs': 1525}))
