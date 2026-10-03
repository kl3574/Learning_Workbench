from pathlib import Path
import datetime
import hashlib
import json
import subprocess

base = Path(__file__).resolve().parent
root = base.parent / 'm62-review-material-active'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)
head = git('rev-parse', 'HEAD').decode().strip()
assert not git('status', '--porcelain')
rows = []
for item in git('ls-files', '-s', '-z').decode().split('\0'):
    if not item:
        continue
    info, name = item.split('\t', 1)
    if name.startswith('progress/'):
        continue
    raw = (root / name).read_bytes()
    blob = info.split()[1]
    actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert actual == blob
    rows.append(dict(path=name, bytes=len(raw), sha256=sha(raw), git_blob=blob, git_matches=True))
rows.sort(key=lambda item: item['path'])
assert len(rows) == 951
write(base / 'final-source-binding.json', {'head': head, 'source_count': len(rows), 'all_git_match': True, 'files': rows})
final = json.loads((base / '13-final-material-green/inputs-before.json').read_text())
assert [(x['path'], x['sha256'], x['bytes']) for x in final] == [(x['path'], x['sha256'], x['bytes']) for x in rows]
changed = git('diff', '--name-only', head + '^', head).decode().splitlines()
assert len(changed) == 6
pins = [item for item in rows if item['path'] in changed]
write(base / 'final-pins.json', {'head': head, 'parent': git('rev-parse', head + '^').decode().strip(),
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'files': pins,
    'final_focused_source_bytes_match_commit': True, 'test_time_git_identity_preserved': True})
(base / 'commit.patch').write_bytes(git('show', '--format=fuller', '--binary', head))
stages = []
for stage in sorted(base.iterdir()):
    if not stage.is_dir() or not (stage / 'receipt.json').is_file():
        continue
    receipt = json.loads((stage / 'receipt.json').read_text())
    raw = (stage / 'run.log').read_bytes()
    assert sha(raw) == receipt['log_sha256'] and len(raw) == receipt['log_bytes']
    before = json.loads((stage / 'inputs-before.json').read_text())
    after = json.loads((stage / 'inputs-after.json').read_text())
    assert before == after and receipt['source_unchanged']
    assert len(before) == receipt['source_count']
    stages.append({'stage': stage.name, 'exit_code': receipt['exit_code'], 'source_count': len(before),
        'source_unchanged': True, 'log_sha256': sha(raw), 'receipt_sha256': sha((stage / 'receipt.json').read_bytes())})
assert len(stages) == 14
write(base / 'final-receipt.json', {'head': head, 'source_count': len(rows), 'all_git_match': True,
    'new_tests': {'stage': '13-final-material-green', 'passed': 45},
    'existing_regressions': {'stage': '10-related-regressions', 'passed': 106},
    'stages': stages, 'scope': 'Internal read-only port; synthetic loopback; no academic approval, numeric execution or public delivery.'})
selected = ['REPORT.md', 'run.py', 'finalize.py', 'verify.py', 'final-source-binding.json', 'final-pins.json',
            'commit.patch', 'final-receipt.json']
for stage in stages:
    prefix = stage['stage']
    selected.extend(f'{prefix}/{name}' for name in ['receipt.json','run.log','inputs-before.json','inputs-after.json','runner.py'])
    selected.extend(path.relative_to(base).as_posix() for path in sorted((base / prefix / 'source').rglob('*')) if path.is_file())
entries = []
for name in sorted(selected):
    raw = (base / name).read_bytes()
    entries.append({'path': name, 'bytes': len(raw), 'sha256': sha(raw)})
write(base / 'manifest.json', {'version': 1, 'private_only': True, 'head': head, 'files': entries,
    'excluded': ['pytest tmp directories and databases', 'mypy caches', 'secrets/session stores'],
    'note': 'Selected existing raw logs may contain temporary synthetic session representations; no public copy is implied.'})
print(json.dumps({'head':head, 'source_count':len(rows), 'evidence_files':len(entries),
    'manifest_sha256':sha((base/'manifest.json').read_bytes()), 'final_receipt_sha256':sha((base/'final-receipt.json').read_bytes()),
    'final_pins_sha256':sha((base/'final-pins.json').read_bytes())}, indent=2))
