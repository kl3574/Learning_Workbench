"""Read-only replay of this private evidence package; never imports archived code."""
from pathlib import Path
import hashlib
import json

BASE = Path(__file__).resolve().parent

def digest(data):
    return hashlib.sha256(data).hexdigest()

manifest = json.loads((BASE / 'manifest.json').read_text())
for item in manifest['files']:
    path = Path(item['path'])
    assert not path.is_absolute() and '..' not in path.parts
    data = (BASE / path).read_bytes()
    assert len(data) == item['bytes'] and digest(data) == item['sha256'], path
rows = manifest['files']
assert len({row['path'] for row in rows}) == len(rows)
encoded = json.dumps(rows, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
assert digest(encoded) == manifest['aggregate_sha256']
for stage in sorted(BASE.glob('[0-9][0-9]-*')):
    receipt = json.loads((stage / 'receipt.json').read_text())
    data = (stage / 'output.log').read_bytes()
    assert len(data) == receipt['log_bytes'] and digest(data) == receipt['log_sha256']
    before = json.loads((stage / 'inputs-before.json').read_text())
    after = json.loads((stage / 'inputs-after.json').read_text())
    assert before == after and receipt['source_unchanged']
    by_path = {row['path']: row for row in before}
    assert len(by_path) == receipt['source_count']
    for path in (stage / 'source').rglob('*'):
        if path.is_file():
            item = by_path[str(path.relative_to(stage / 'source'))]
            data = path.read_bytes()
            assert len(data) == item['bytes'] and digest(data) == item['sha256']
for row in json.loads((BASE / 'source-final-pins.json').read_text()):
    data = (BASE / 'source-final' / row['path']).read_bytes()
    assert len(data) == row['bytes'] and digest(data) == row['sha256']
print(f"PASS: {len(rows)} manifest files; 17 original run receipts and stable source maps; 7 final source files")
