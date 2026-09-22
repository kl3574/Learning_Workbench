"""Replay selected private evidence hashes without reading databases or secrets."""
from pathlib import Path
import hashlib
import json

base = Path(__file__).resolve().parent
manifest = json.loads((base / 'manifest.json').read_text())
for entry in manifest['files']:
    path = (base / entry['path']).resolve()
    assert path.is_relative_to(base)
    raw = path.read_bytes()
    assert len(raw) == entry['bytes']
    assert hashlib.sha256(raw).hexdigest() == entry['sha256']
receipt = json.loads((base / 'final-receipt.json').read_text())
for stage in receipt['stages']:
    directory = base / stage['stage']
    actual = json.loads((directory / 'receipt.json').read_text())
    raw = (directory / 'run.log').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == actual['log_sha256'] == stage['log_sha256']
    before = json.loads((directory / 'inputs-before.json').read_text())
    after = json.loads((directory / 'inputs-after.json').read_text())
    assert before == after and actual['source_unchanged'] and len(before) == stage['source_count']
binding = json.loads((base / 'final-source-binding.json').read_text())
final = json.loads((base / '09-jobs-owner-prefix-green/inputs-before.json').read_text())
assert binding['all_git_match'] and binding['source_count'] == len(binding['files']) == 954
assert [(x['path'], x['bytes'], x['sha256']) for x in final] == [(x['path'], x['bytes'], x['sha256']) for x in binding['files']]
print(f"PASS: {len(manifest['files'])} selected private evidence files; {len(receipt['stages'])} original runs; final 954 source bindings.")
