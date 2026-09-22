#!/usr/bin/env python3
"""Verify declared public artifacts; optionally replay transformations from local raw aliases."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform(data, rules, raw_home=None):
    value = data.decode('utf-8')
    counts = []
    for rule in rules:
        if rule['kind'] == 'parameter':
            if rule['parameter'] != 'raw_home' or raw_home is None:
                raise ValueError('Raw replay requires the explicit --raw-home parameter')
            count = value.count(raw_home)
            value = value.replace(raw_home, rule['replace'])
        elif rule['kind'] == 'literal':
            count = value.count(rule['find'])
            value = value.replace(rule['find'], rule['replace'])
        else:
            value, count = re.subn(rule['pattern'], rule['replace'], value)
        if count:
            counts.append({'rule': rule['id'], 'count': count})
    return value.encode('utf-8'), counts


def scan(path, data):
    assert path.suffix.lower() not in {'.db', '.sqlite', '.sqlite3', '.zip', '.har'}, path
    assert not any(part.lower() in {'pytest-temp', 'secrets', 'sessions', 'profile', 'storageState'.lower(), 'mypy-cache', 'pytest-cache', '__pycache__'} for part in path.parts), path
    assert b'\x00' not in data, path
    text = data.decode('utf-8')
    for name, pattern in [
        ('csrf_value', r'(?:csrf_token|srf_token)\s*[=:]\s*[\x27\x22][0-9a-f]{64}[\x27\x22]'),
        ('session_id', r'session_[0-9a-f]{32}'),
        ('bearer_value', r'Bearer\s+[A-Za-z0-9_-]{24,}'),
        ('vendor_key', r'sk-[A-Za-z0-9]{24,}'),
        ('private_key', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        ('home_directory', r'/home/[A-Za-z0-9_.-]+(?:/|\b)'),
    ]:
        assert not re.search(pattern, text), f'{path}: {name}'


def verify(public, raw_base=None, raw_home=None):
    if raw_base is not None and raw_home is None:
        raise ValueError('Raw replay requires explicit --raw-base and --raw-home')
    if raw_home is not None:
        if raw_base is None or not Path(raw_home).is_absolute() or raw_home == '/' or raw_home.endswith('/') or any(character in raw_home for character in ('\n', '\r', '\x00')):
            raise ValueError('Provide one exact absolute --raw-home prefix without a trailing slash alongside --raw-base')
    manifest = json.loads((public / 'manifest.json').read_text())
    entries = {row['raw_alias']: row for row in manifest['files']}
    assert len(entries) == len(manifest['files'])
    destinations = set()
    replayed = 0
    for row in entries.values():
        destination = Path(row['public_path'])
        assert not destination.is_absolute() and '..' not in destination.parts
        data = (public / destination).read_bytes()
        assert len(data) == row['public_bytes'] and sha(data) == row['public_sha256'], row['raw_alias']
        scan(destination, data)
        destinations.add(str(destination))
        if raw_base:
            stage, rel = row['raw_alias'].split('/', 1)
            raw = (raw_base / manifest['raw_roots'][stage] / rel).read_bytes()
            assert len(raw) == row['raw_bytes'] and sha(raw) == row['raw_sha256'], row['raw_alias']
            reproduced, counts = transform(raw, manifest['transform_rules'], raw_home)
            assert reproduced == data and counts == row['transformations'], row['raw_alias']
            replayed += 1
    def read_alias(alias):
        return json.loads((public / entries[alias]['public_path']).read_text())
    runs = []
    for alias in sorted(entries):
        if not alias.endswith('/receipt.json') or '/runtime-evidence/' in alias:
            continue
        prefix = alias.removesuffix('receipt.json')
        if prefix + 'inputs-before.json' not in entries:
            continue
        receipt = read_alias(alias)
        before, after = (read_alias(prefix + f'inputs-{side}.json') for side in ('before', 'after'))
        left, right = ({row['path']: row for row in rows} for rows in (before, after))
        changed = [name for name in sorted(set(left) | set(right)) if left.get(name) != right.get(name)]
        assert len(before) == receipt['before_count'] and len(after) == receipt['after_count'], alias
        assert changed == receipt['input_changes'], alias
        raw_log = entries[prefix + 'output.log']
        assert receipt['log_sha256'] == raw_log['raw_sha256'] and receipt['log_bytes'] == raw_log['raw_bytes'], alias
        runs.append({'alias': alias, 'exit_code': receipt['exit_code'], 'before_count': len(before), 'after_count': len(after), 'input_changes': changed})
    runtime = read_alias('group-numeric/runtime-evidence/receipt.json')
    end = read_alias('group-numeric/runtime-evidence/end.json')
    start = read_alias('group-numeric/runtime-evidence/start.json')
    assert runtime['verdict'] == end['result']['verdict'] == 'BLOCKED'
    assert runtime['outcome'] == end['result']['outcome'] == 'environment_unavailable'
    assert runtime['exit_code'] == end['result']['exit_code'] == 1
    assert runtime['started_at'] == start['actual_started_at'] == end['result']['started_at']
    for item in runtime['files']:
        row = entries['group-numeric/runtime-evidence/' + item['path']]
        assert item['sha256'] == row['raw_sha256'] and item['bytes'] == row['raw_bytes']
    assert base64.b64decode(end['stderr_base64']) == b'bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted\n'
    for row in manifest['generated_files']:
        data = (public / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    allowed = destinations | {item['path'] for item in manifest['generated_files']} | {'manifest.json'}
    actual = {str(p.relative_to(public)) for p in public.rglob('*') if p.is_file()}
    assert actual == allowed, {'unexpected': sorted(actual-allowed), 'missing': sorted(allowed-actual)}
    for name in sorted(actual):
        data = (public / name).read_bytes()
        scan(Path(name), data)
        if raw_home is not None:
            assert raw_home.encode('utf-8') not in data, f'{name}: supplied private prefix remains'
    return {'status': 'PASS', 'raw_aliases': len(entries), 'unique_payload_files': len(destinations), 'raw_replays': replayed,
            'scanner': 'PASS: all payload files checked for forbidden extensions/directories, binary NUL, raw HOME, session IDs, CSRF values, bearer/vendor tokens and private keys',
            'runtime_verdict': 'BLOCKED/environment_unavailable', 'runs': runs}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('public', nargs='?', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--raw-base', type=Path)
    parser.add_argument('--raw-home', help='Exact private prefix required only with --raw-base; never inferred or recorded')
    args = parser.parse_args()
    print(json.dumps(verify(args.public, args.raw_base, args.raw_home), indent=2))
