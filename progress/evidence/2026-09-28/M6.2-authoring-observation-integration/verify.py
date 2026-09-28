"""Verify public bytes and optionally replay the explicit private raw bindings."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def transform(data, home, ci_home):
    rules = [
        ("local_home_slash", (home.rstrip('/') + '/').encode(), b'<LOCAL_HOME>/'),
        ("local_home_bare", home.rstrip('/').encode(), b'<LOCAL_HOME>'),
        ("ci_home_slash", (ci_home.rstrip('/') + '/').encode(), b'<CI_HOME>/'),
        ("ci_home_bare", ci_home.rstrip('/').encode(), b'<CI_HOME>'),
        ("pytest_user_root", b'/tmp/pytest-of-' + Path(home).name.encode(), b'<PYTEST_ROOT>'),
    ]
    counts = {}
    for name, old, new in rules:
        counts[name] = data.count(old)
        data = data.replace(old, new)
    return data, counts


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
    expected = {'manifest.json'}
    for item in manifest['files']:
        expected.add(item['public_path'])
        actual = checked(safe_path(root, item['public_path']), item['public_bytes'], item['public_sha256'])
        if args.raw_base:
            raw = checked(safe_path(args.raw_base, item['raw_cache'] + '/' + item['raw_path']),
                          item['raw_bytes'], item['raw_sha256'])
            transformed, counts = transform(raw, args.raw_home, args.ci_home)
            assert transformed == actual and counts == item['transformation_counts']
    for item in manifest['generated_files']:
        expected.add(item['path'])
        checked(safe_path(root, item['path']), item['bytes'], item['sha256'])
    if args.raw_base:
        for item in manifest.get('excluded_raw', []):
            checked(safe_path(args.raw_base, item['raw_cache'] + '/' + item['raw_path']),
                    item['raw_bytes'], item['raw_sha256'])
    actual_paths = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert actual_paths == expected, (sorted(actual_paths - expected), sorted(expected - actual_paths))
    print(f"PASS: {len(manifest['files'])} raw aliases, {len(expected)} public files" +
          ('; all raw bytes and transformations replayed' if args.raw_base else ''))


if __name__ == '__main__':
    main()
