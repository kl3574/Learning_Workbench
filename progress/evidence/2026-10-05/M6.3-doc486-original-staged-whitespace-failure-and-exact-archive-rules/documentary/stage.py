"""Stage only the four managed progress files and seventeen named packets."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

base = Path('$HOME/.cache/learning-workbench-acceptance')
root = base / 'm62-public-safe-oct02'
out = Path(__file__).parent
assert not (out / 'READBACK.json').exists()
sha = lambda b: hashlib.sha256(b).hexdigest()
def run(label, argv):
    assert not (out / (label + '-command.json')).exists()
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out / (label + '-command.json')).write_text(json.dumps({'argv': argv, 'cwd': str(root), 'started_utc': start}, indent=2) + '\n')
    result = subprocess.run(argv, cwd=root, capture_output=True)
    (out / (label + '.stdout')).write_bytes(result.stdout)
    (out / (label + '.stderr')).write_bytes(result.stderr)
    (out / (label + '-receipt.json')).write_text(json.dumps({'exit_code': result.returncode,
        'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'stdout_sha256': sha(result.stdout), 'stderr_sha256': sha(result.stderr)}, indent=2) + '\n')
    return result
assert run('head', ['git','rev-parse','HEAD']).stdout.decode().strip() == '4869393654446c1dfcb0da97b9dca5fa7429b36f'
assert run('index-before', ['git','diff','--cached','--name-only','-z']).stdout == b''
selected = ['progress/state.json', 'progress/CURRENT.md', 'progress/M6.3-next.md', 'progress/M6.3-bootstrap-acceptance.md']
for folder, filename in [
    ('m63-public35ae-actual-evidence-archive-oct05','READBACK.json'),
    ('m63-interrupt-and-backup-root-archive-oct05','ROOT_READBACK.json'),
    ('m63-5d8-terminal-ci-and-interrupt-final-archive-oct05','READBACK.json'),
    ('m63-review-observer-and-terminal-sync-archive-oct05','READBACK.json'),
    ('m63-final486-combined-and-documentary-archive-oct05','READBACK.json')]:
    metadata = json.loads((base / folder / filename).read_text())
    selected.extend(str(Path(p).parent) for p in metadata['evidence_paths'])
assert len(selected) == 21 and len(set(selected)) == 21
files = {}
for name in selected:
    p = root / name
    if p.is_file(): files[name] = sha(p.read_bytes())
    else:
        assert p.is_dir() and (p / 'manifest.json').is_file()
        for f in p.rglob('*'):
            if f.is_file(): files[str(f.relative_to(root))] = sha(f.read_bytes())
(out / 'SELECTION.json').write_text(json.dumps({'paths': selected, 'files': files}, indent=2) + '\n')
result = run('stage', ['git', 'add', '--', *selected])
assert result.returncode == 0
staged = run('index-after', ['git','diff','--cached','--name-only','-z']).stdout.decode().split('\0')
staged = {p for p in staged if p}
missing = sorted(set(files) - staged)
assert not (staged - set(files))
# A known repository ignore may omit an explicitly reviewed archived script.
if missing:
    (out / 'EXPLICIT_IGNORED_SELECTION.json').write_text(json.dumps({'paths': missing}, indent=2) + '\n')
    ignored = run('selected-ignore', ['git','check-ignore','--',*missing])
    assert ignored.returncode == 0 and set(ignored.stdout.decode().splitlines()) == set(missing)
    assert run('explicit-force-selected', ['git','add','-f','--',*missing]).returncode == 0
for p, expected in files.items():
    assert sha(subprocess.check_output(['git','show',':'+p],cwd=root)) == expected
check = run('original-staged-diff', ['git','diff','--cached','--check'])
(out / 'READBACK.json').write_text(json.dumps({'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'head':'4869393654446c1dfcb0da97b9dca5fa7429b36f', 'selected_files':len(files),
    'original_staged_diff_exit_code':check.returncode, 'source_push':False},indent=2)+'\n')
print(json.dumps({'selected_files':len(files),'original_staged_diff_exit_code':check.returncode}))
print(check.stdout.decode())
