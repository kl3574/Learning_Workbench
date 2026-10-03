"""Verify public integrity and optionally replay the explicit private transformations."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


PATTERNS = {
    'session_identity_complete': rb"SessionIdentity\(id='(?P<value>session_[0-9a-f]{32})(?=')",
    'session_identity_pytest_truncated': rb"SessionIdentity\(id='(?P<value>session_[0-9a-f]{11})(?=\.\.\.draft_revision=)",
    'csrf_identity_pytest_truncated': rb"SessionIdentity\(id='session_[0-9a-f]{32}', workspace_id='workspace_[0-9a-f]{31}\.\.\.srf_token='(?P<value>[0-9a-f]{64})(?=', expires_at=')",
}
REPLACEMENTS = {
    'session_identity_complete': b'<SYNTHETIC_SESSION_REDACTED>',
    'session_identity_pytest_truncated': b'<SYNTHETIC_SESSION_FRAGMENT_REDACTED>',
    'csrf_identity_pytest_truncated': b'<SYNTHETIC_CSRF_REDACTED>',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def spans(data):
    found = []
    for kind, pattern in PATTERNS.items():
        for match in re.finditer(pattern, data):
            start, end = match.span('value')
            found.append({'start': start, 'end': end, 'kind': kind})
    found.sort(key=lambda row: row['start'])
    assert all(a['end'] <= b['start'] for a, b in zip(found, found[1:]))
    return found


def transform(data, home, ci_home, expected_spans=None):
    # Every span is rediscovered from its exact field context AND value format.
    found = spans(data)
    if expected_spans is not None:
        assert found == expected_spans, 'redaction span/context mismatch'
    counts = {kind: 0 for kind in PATTERNS}
    for item in reversed(found):
        counts[item['kind']] += 1
        data = data[:item['start']] + REPLACEMENTS[item['kind']] + data[item['end']:]
    rules = [
        ('local_home_slash', (home.rstrip('/') + '/').encode(), b'<LOCAL_HOME>/'),
        ('local_home_bare', home.rstrip('/').encode(), b'<LOCAL_HOME>'),
        ('ci_home_slash', (ci_home.rstrip('/') + '/').encode(), b'<CI_HOME>/'),
        ('ci_home_bare', ci_home.rstrip('/').encode(), b'<CI_HOME>'),
        ('pytest_user_root', b'/tmp/pytest-of-' + Path(home).name.encode(), b'<PYTEST_ROOT>'),
    ]
    for name, old, new in rules:
        counts[name] = data.count(old)
        data = data.replace(old, new)
    return data, counts, found


def safe_path(base, relative):
    path = PurePosixPath(relative)
    assert not path.is_absolute() and '..' not in path.parts
    return base / relative


def checked(path, size, digest):
    raw = path.read_bytes()
    assert len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, str(path)
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-base', type=Path)
    parser.add_argument('--raw-home')
    parser.add_argument('--ci-home')
    args = parser.parse_args()
    if args.raw_base and (not args.raw_home or not args.ci_home):
        parser.error('--raw-home and --ci-home are required for raw replay')
    if args.raw_base:
        assert args.raw_home.rstrip('/') and args.ci_home.rstrip('/')
        assert args.raw_home.rstrip('/') != args.ci_home.rstrip('/')
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'manifest.json').read_bytes())
    aggregate = {'files': manifest['files'], 'generated_files': manifest['generated_files']}
    assert hashlib.sha256(canonical(aggregate)).hexdigest() == manifest['aggregate_sha256']
    expected = {'manifest.json'}
    aliases = set()
    for item in manifest['files']:
        alias = (item['raw_cache'], item['raw_path'])
        assert alias not in aliases
        aliases.add(alias)
        expected.add(item['public_path'])
        actual = checked(safe_path(root, item['public_path']), item['public_bytes'], item['public_sha256'])
        if args.raw_base:
            raw = checked(safe_path(args.raw_base, '/'.join(alias)), item['raw_bytes'], item['raw_sha256'])
            transformed, counts, _ = transform(raw, args.raw_home, args.ci_home, item['redaction_spans'])
            assert transformed == actual and counts == item['transformation_counts']
    for item in manifest['generated_files']:
        expected.add(item['path'])
        checked(safe_path(root, item['path']), item['bytes'], item['sha256'])
    actual_paths = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert actual_paths == expected, 'unexpected/missing public files'
    print(f'PASS: {len(aliases)} raw aliases; {len(expected)} public files; aggregate verified' +
          ('; raw hashes, field-context spans and transformations replayed' if args.raw_base else ''))


if __name__ == '__main__':
    main()
