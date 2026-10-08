"""Reviewed observation/retention merge; preserve prior source and progress."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

base = Path('$HOME/.cache/learning-workbench-acceptance')
root = base / 'm62-public-safe-oct02'
out = Path(__file__).parent
before_head = '5d8bc7ef4f34bd08e6327053e874ed062a935ae8'
branch_base = '35aebd3039241abb3393300affd593f4826a4a0c'
candidate = '905eccdd667001ec8e545cb534d5282ef6949836'
sha = lambda data: hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git', *args], cwd=root)
def write(name, value): (out / name).write_text(json.dumps(value, indent=2) + '\n')
assert not (out / 'command.json').exists()
assert git('rev-parse', 'HEAD').decode().strip() == before_head
assert git('diff', '--cached', '--name-only') == b''
changed = git('diff', '--name-only', branch_base, candidate).decode().splitlines()
assert set(changed) == {'.github/workflows/ci.yml', 'tests/e2e/review.spec.ts'}
dirty = git('diff', '--name-only').decode().splitlines()
assert set(dirty) == {'progress/state.json', 'progress/CURRENT.md', 'progress/M6.3-next.md', 'progress/M6.3-bootstrap-acceptance.md'}
untracked = list(filter(None, git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')))
assert all(p.startswith('progress/evidence/2026-10-05/M6.3-') for p in untracked)
working = {p: (root / p).read_bytes() for p in dirty + untracked}
for p in dirty:
    target = out / 'before' / p
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(working[p])
def tree(head, progress):
    values = {}
    for entry in filter(None, git('ls-tree', '-rz', head).split(b'\0')):
        info, name = entry.split(b'\t', 1)
        mode, kind, blob = info.decode().split()
        name = name.decode()
        if name.startswith('progress/') == progress:
            values[name] = {'mode': mode, 'type': kind, 'git_blob': blob}
    return values
old_progress = tree(before_head, True)
old_source = tree(before_head, False)
new_source = tree(candidate, False)
expected_source = {**old_source, **{p: new_source[p] for p in changed}}
assert len(old_source) == len(expected_source) == 1525 and len(new_source) == 1524
for name, value in old_source.items():
    assert (root / name).read_bytes() == git('cat-file', 'blob', value['git_blob'])
for dirname, name, digest in [
    ('m63-review-history-timing-independent-oct05', 'REVIEW.md', '80a51a4f400c369902cdbb7fb39002744451b2875b045cd56e56175fd99add5c'),
    ('m63-review-history-workflow905-independent-oct05', 'REVIEW.md', 'cb2c1ea5663d6c0fa97cf046ef53cc66fd192e90aedc39cd8d4628e1d24685ce'),
]:
    assert sha((base / dirname / name).read_bytes()) == digest
write('before.json', {'head': before_head, 'engineering_inputs': old_source, 'progress_tree': old_progress,
    'dirty': dirty, 'untracked_count': len(untracked), 'working': {p: {'sha256': sha(v), 'bytes': len(v)} for p, v in working.items()}})
argv = ['git', 'merge', '--no-ff', candidate, '-m', 'test(M6.3): preserve bounded Review phase diagnostics']
write('command.json', {'argv': argv, 'cwd': str(root), 'before': before_head, 'candidate': candidate,
    'scope': 'Observation and exact CI failure artifact path only; original business/budget unchanged', 'source_push': False})
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
r = subprocess.run(argv, cwd=root, capture_output=True)
(out / 'stdout').write_bytes(r.stdout); (out / 'stderr').write_bytes(r.stderr)
assert r.returncode == 0
head = git('rev-parse', 'HEAD').decode().strip()
assert git('show', '-s', '--format=%P', head).decode().split() == [before_head, candidate]
assert tree(head, True) == old_progress and tree(head, False) == expected_source
assert all((root / p).read_bytes() == v for p, v in working.items())
assert all((root / p).read_bytes() == git('cat-file', 'blob', v['git_blob']) for p, v in expected_source.items())
write('READBACK.json', {'started_utc': start, 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'head': head, 'parents': [before_head, candidate], 'exit_code': r.returncode,
    'engineering_inputs': 1525, 'changed_paths': changed, '1523_other_source_inputs_preserved': True,
    'merged_review_and_workflow_bytes_exact_candidate': True, 'old_committed_progress_exact': True,
    'dirty_and_untracked_progress_bytes_preserved': len(working),
    'source_push': False, 'public_head': branch_base, 'new_combined_native': 'NOT_RUN',
    'qualification': '22dade full133 gate and c02 first1 gate remain original scope; 905 native/actualCIupload NOT_RUN, CI rootcause UNKNOWN, wholeM6.3 NOT_ACCEPTED'})
print(json.dumps({'head': head, 'preserved_progress': len(working), 'exit_code': r.returncode}))
