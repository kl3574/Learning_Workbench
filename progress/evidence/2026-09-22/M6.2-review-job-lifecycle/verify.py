"""Verify public bytes and optionally replay parameterized private path substitutions."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def transform(data, raw_home, ci_home):
    rules = [
        ('local_home_slash', (raw_home.rstrip('/') + '/').encode(), b'<LOCAL_HOME>/'),
        ('local_home_bare', raw_home.rstrip('/').encode(), b'<LOCAL_HOME>'),
        ('ci_home_slash', (ci_home.rstrip('/') + '/').encode(), b'<CI_HOME>/'),
        ('ci_home_bare', ci_home.rstrip('/').encode(), b'<CI_HOME>'),
        ('pytest_user_root', b'/tmp/pytest-of-' + Path(raw_home).name.encode(), b'<PYTEST_ROOT>'),
    ]
    counts = {}
    for name, old, new in rules:
        counts[name] = data.count(old)
        data = data.replace(old, new)
    return data, counts


def safe_path(base, relative):
    path = PurePosixPath(relative)
    assert not path.is_absolute() and '..' not in path.parts and path.parts
    result = base / relative
    assert result.resolve().is_relative_to(base.resolve())
    return result


def checked(path, size, digest):
    data = path.read_bytes()
    assert len(data) == size and hashlib.sha256(data).hexdigest() == digest, str(path)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-base', type=Path)
    parser.add_argument('--raw-home')
    parser.add_argument('--ci-home')
    args = parser.parse_args()
    if args.raw_base and (not args.raw_home or not args.ci_home):
        parser.error('--raw-home and --ci-home are required for raw replay')
    if args.raw_base:
        assert Path(args.raw_home).is_absolute() and Path(args.ci_home).is_absolute()
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
            transformed, counts = transform(raw, args.raw_home, args.ci_home)
            assert transformed == actual and counts == item['transformation_counts']
            assert item['transformed'] == (raw != actual)
    for item in manifest['generated_files']:
        assert item['path'] not in expected
        expected.add(item['path'])
        checked(safe_path(root, item['path']), item['bytes'], item['sha256'])
    actual_paths = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert actual_paths == expected, 'unexpected/missing public files'
    print(f'PASS: {len(aliases)} raw aliases; {len(expected)} public files; aggregate verified' +
          ('; raw hashes and every ordered path transformation replayed' if args.raw_base else ''))


if __name__ == '__main__':
    main()
