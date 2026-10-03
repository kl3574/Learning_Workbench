"""Freeze only bounded evidence, excluding all runtime databases and tool caches."""
from pathlib import Path
import hashlib
import json

BASE = Path(__file__).resolve().parent
names = {'setup.json', 'run.py', 'verify.py', 'make_manifest.py', 'REPORT.md', 'verification.json',
         'verification-before-large-revision.json', 'source-final-pins.json',
         'source-before-large-revision-pins.json', 'post-owner-focused.diff',
         'commit-receipt.json', 'final-change.patch', 'independent-review.json', 'independent-review.md', 'final-inputs.json'}
files = []
selected = [BASE / name for name in names if (BASE / name).is_file()]
for directory in BASE.iterdir():
    head = directory.name
    if directory.is_dir() and (head in {'source-final', 'source-before-large-revision'}
                              or (len(head) > 3 and head[:2].isdigit() and head[2] == '-')):
        selected.extend(path for path in directory.rglob('*') if path.is_file())
for path in sorted(selected):
    if not path.is_file():
        continue
    relative = path.relative_to(BASE)
    head = relative.parts[0]
    allowed = (str(relative) in names or head in {'source-final', 'source-before-large-revision'}
               or (len(head) > 3 and head[:2].isdigit() and head[2] == '-'))
    if allowed:
        data = path.read_bytes()
        files.append({'path': str(relative), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
assert all(not row['path'].startswith(('tmp/', 'tool-cache/')) for row in files)
assert not any(Path(row['path']).suffix in {'.sqlite3', '.db', '.zip'} for row in files)
aggregate = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
manifest = {'version': 'm62-catalog-wiring-private-evidence-v1', 'scope': '17 bounded development commands; not full gates',
            'base_head': '2ab067b9d832c0aa64699a9a56e879d2ab6c6ac5', 'files': files,
            'aggregate_sha256': aggregate, 'excluded': ['tmp runtime data', 'tool-cache', 'any database/profile/ZIP'],
            'raw_logs_are_private': True}
raw = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
with (BASE / 'manifest.json').open('xb') as output:
    output.write(raw)
print(json.dumps({'files': len(files), 'bytes': sum(row['bytes'] for row in files),
                  'aggregate_sha256': aggregate, 'manifest_sha256': hashlib.sha256(raw).hexdigest()}, indent=2))
