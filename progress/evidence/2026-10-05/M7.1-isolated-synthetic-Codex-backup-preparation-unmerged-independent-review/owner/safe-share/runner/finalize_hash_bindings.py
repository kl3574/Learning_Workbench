"""Append documentary Git SHA-256 verification; never change source or execution evidence."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = Path.home() / '.cache/learning-workbench-acceptance/m71-codex-backup-synthetic-owner-oct05'
SAFE = ROOT / 'safe-share'
previous = ROOT / 'SAFE_SHARE.json'
manifest = json.loads(previous.read_bytes())
objects = {}
maps = []
bindings = 0
for gate in ('01-original-focused', '02-fixed-focused', '03-related-backups', '04-ruff', '05-diff-check'):
    for phase in ('before', 'after'):
        path = ROOT / gate / (phase + '.json')
        raw = path.read_bytes()
        data = json.loads(raw)
        maps.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(),
                     'source_commit': data['source_commit'], 'entry_count': len(data['entries'])})
        for entry in data['entries']:
            expected = (entry['size'], entry['sha256'])
            assert objects.setdefault(entry['git_blob'], expected) == expected
            bindings += 1
names = list(objects)
result = subprocess.run(['git', 'cat-file', '--batch'], cwd=SOURCE,
                        input=('\n'.join(names) + '\n').encode(), capture_output=True, check=True)
offset = 0
for name in names:
    newline = result.stdout.index(b'\n', offset)
    header = result.stdout[offset:newline].decode().split()
    assert header[0] == name and header[1] == 'blob'
    size = int(header[2])
    start = newline + 1
    raw = result.stdout[start:start + size]
    assert (size, hashlib.sha256(raw).hexdigest()) == objects[name]
    assert result.stdout[start + size:start + size + 1] == b'\n'
    offset = start + size + 1
assert offset == len(result.stdout)
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE).decode().strip() == manifest['fixed_source']
assert not subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=SOURCE)
readback = {'format': 'append-only-documentary-git-sha256-binding-v1',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'source_commit': manifest['fixed_source'], 'source_clean': True,
            'map_count': len(maps), 'exact_git_size_sha256_entry_bindings': bindings,
            'distinct_checked_git_blobs': len(objects), 'maps': maps,
            'original_allowlist_sha256': hashlib.sha256(previous.read_bytes()).hexdigest(),
            'original_run_source_and_failure_evidence_changed': False,
            'original_readback_candidate_count_semantics':
                '53 files before READBACK.json itself; original SAFE_SHARE.json lists 54; final allowlist adds two documentary files',
            'additional_tests_or_runtime_execution': 'NOT_RUN',
            'background_lifespan_worker_convergence': 'NOT_RUN'}
additions = [
    ('SHA256_BINDINGS.json', (json.dumps(readback, sort_keys=True, indent=2) + '\n').encode()),
    ('runner/finalize_hash_bindings.py', Path(__file__).read_bytes()),
]
for name, raw in additions:
    path = SAFE / name
    assert not path.exists()
    path.write_bytes(raw)
    manifest['entries'].append({'path': name, 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                               'original_sha256': hashlib.sha256(raw).hexdigest(), 'transformation': 'none',
                               'origin': 'new append-only documentary final Git SHA-256 binding'})
final = ROOT / 'SAFE_SHARE_FINAL.json'
assert not final.exists()
manifest['created_at'] = datetime.now(timezone.utc).isoformat()
manifest['prior_manifest_preserved_sha256'] = hashlib.sha256(previous.read_bytes()).hexdigest()
manifest['candidate_count'] = len(manifest['entries'])
final.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
for entry in manifest['entries']:
    raw = (SAFE / entry['path']).read_bytes()
    assert len(raw) == entry['size'] and hashlib.sha256(raw).hexdigest() == entry['sha256']
print(json.dumps({'candidate_count': len(manifest['entries']),
                  'safe_final_manifest_sha256': hashlib.sha256(final.read_bytes()).hexdigest(),
                  'sha256_bindings_sha256': hashlib.sha256((SAFE / 'SHA256_BINDINGS.json').read_bytes()).hexdigest(),
                  'exact_git_size_sha256_entry_bindings': bindings, 'distinct_git_blobs': len(objects)}, sort_keys=True))
