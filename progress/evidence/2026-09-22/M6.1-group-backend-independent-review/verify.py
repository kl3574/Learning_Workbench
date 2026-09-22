"""Verify this bounded public review package; optional exact private-origin replay.

This script only reads the public package and explicitly mapped original files.
It never opens the excluded private database, executes the probe, or accesses a network.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(value):
    p = Path(value)
    if p.is_absolute() or not p.parts or any(x in {'.', '..'} for x in p.parts):
        raise ValueError('unsafe package-relative path')
    return p


def read(root, name):
    path = root / relative(name)
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('unexpected nonregular or escaping file')
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-base', type=Path)
    parser.add_argument('--raw-home', help='Original HOME prefix, required with --raw-base')
    args = parser.parse_args()
    if (args.raw_base is None) != (args.raw_home is None):
        parser.error('--raw-base and --raw-home are required together')
    root = Path(__file__).resolve().parent
    manifest = json.loads(read(root, 'manifest.json'))
    if manifest['version'] != 'bounded-backend-review-public-v1':
        raise ValueError('unexpected manifest version')
    entries = manifest['files']
    all_files = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('symlink not allowed')
    if all_files != set(entries) | {'manifest.json'}:
        raise ValueError('unlisted, missing or unexpected file')
    for name, entry in entries.items():
        data = read(root, name)
        if len(data) != entry['bytes'] or digest(data) != entry['sha256']:
            raise ValueError('public size/hash mismatch: ' + name)
        if 'probe-data' in Path(name).parts or Path(name).suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.zip', '.har'}:
            raise ValueError('excluded private state in package')
        text = data.decode('utf-8')
        if re.search(r'/home/[A-Za-z0-9_.-]+', text):
            raise ValueError('unconverted local HOME prefix: ' + name)
    aggregate = digest(''.join(f'{entries[p]["sha256"]}  {p}\n' for p in sorted(entries)).encode())
    if aggregate != manifest['payload_aggregate_sha256']:
        raise ValueError('aggregate hash mismatch')
    origins = json.loads(read(root, 'raw-origin-map.json'))
    if origins['sensitive_value_redactions'] != [] or origins['home_marker'] != '<HOME>':
        raise ValueError('unexpected transformation policy')
    mapping = origins['files']
    if len({m['public_path'] for m in mapping}) != len(mapping):
        raise ValueError('duplicate raw mapping')
    if set(m['public_path'] for m in mapping) != set(entries) - set(manifest['generated_payload_files']):
        raise ValueError('raw-origin coverage mismatch')
    before = json.loads(read(root, 'inputs-before.json'))
    after = json.loads(read(root, 'inputs-after.json'))
    if len(before['files']) != 32 or before['files'] != after['files']:
        raise ValueError('32-file before/after claim is not exact')
    if before['head'] != after['head'] or after['declared_before_after_changed_files']:
        raise ValueError('declared source/HEAD changed')
    end_only = after['additional_read_dependency_files_end_snapshot_only']
    if len(end_only) != 12:
        raise ValueError('unexpected end-only input count')
    lookup = {m['public_path']: m for m in mapping}
    for prefix, values in [('source-before', before['files']), ('source-end-only', end_only)]:
        for name, expected in values.items():
            if lookup[f'{prefix}/{name}']['raw_sha256'] != expected:
                raise ValueError('source fingerprint does not bind original snapshot')
    counts = 0
    for item in mapping:
        public = read(root, item['public_path'])
        if item['public_sha256'] != digest(public) or item['public_bytes'] != len(public):
            raise ValueError('mapped public fingerprint mismatch')
        counts += item['home_substitutions']
        if args.raw_base is not None:
            raw = read(args.raw_base, item['raw_relative_path'])
            if digest(raw) != item['raw_sha256'] or len(raw) != item['raw_bytes']:
                raise ValueError('original raw fingerprint mismatch')
            count = raw.count(args.raw_home.encode())
            if count != item['home_substitutions'] or raw.replace(args.raw_home.encode(), b'<HOME>') != public:
                raise ValueError('original-to-public HOME transformation mismatch')
    if counts != origins['total_home_substitutions']:
        raise ValueError('transformation count mismatch')
    original_manifest = json.loads(read(root, 'original-review-manifest.json'))
    for name, entry in original_manifest['files'].items():
        original = lookup[name]
        if entry['sha256'] != original['raw_sha256'] or entry['bytes'] != original['raw_bytes']:
            raise ValueError('original review receipt mismatch')
    result = json.loads(read(root, 'probe-result.json'))
    if not (result['after_draft_read']['code'] == 'PROVIDER_INTEGRITY_INVALID'
            and result['after_numeric_preview']['accepted']
            and result['after_numeric_approval']['accepted']
            and result['after_worker_original_access_guard_and_begin']['admitted']
            and result['calculator_executed'] is False):
        raise ValueError('reproduction claim differs from saved result')
    print(json.dumps({'verified': True, 'mode': 'public+exact-raw' if args.raw_base else 'public-only',
        'files_including_manifest': len(all_files), 'bytes_including_manifest': sum((root/p).stat().st_size for p in all_files),
        'payload_aggregate_sha256': aggregate, 'manifest_sha256': digest(read(root, 'manifest.json')),
        'declared_stable_files': 32, 'end_only_snapshots': 12, 'original_bindings': len(mapping),
        'home_substitutions': counts, 'sensitive_value_redactions': 0,
        'excluded_private_state_opened': False}, indent=2))


if __name__ == '__main__':
    main()
