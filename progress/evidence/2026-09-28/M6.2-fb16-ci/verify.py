"""Verify complete public transcripts and optionally replay exact private raw spans."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe(base, relative):
    path = PurePosixPath(relative)
    assert not path.is_absolute() and '..' not in path.parts
    return base / relative


def checked(path, size, digest):
    data = path.read_bytes()
    assert len(data) == size and sha(data) == digest, str(path)
    return data


def replay(raw, spans, prefix):
    cursor, result = 0, bytearray()
    for span in spans:
        start, length = span['raw_offset'], span['raw_length']
        assert cursor <= start and raw[start:start + length] == prefix
        assert sha(prefix) == span['raw_sha256']
        result.extend(raw[cursor:start])
        assert len(result) == span['public_offset']
        result.extend(span['replacement'].encode())
        cursor = start + length
    result.extend(raw[cursor:])
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-base', type=Path)
    parser.add_argument('--ci-home')
    args = parser.parse_args()
    if args.raw_base and not args.ci_home:
        parser.error('--ci-home is required for exact raw replay')
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'manifest.json').read_bytes())
    expected = {'manifest.json'}
    raw_accounted = set()
    for item in manifest['included_raw']:
        expected.add(item['public_path'])
        assert item['raw_path'] not in raw_accounted
        raw_accounted.add(item['raw_path'])
        actual = checked(safe(root, item['public_path']), item['public_bytes'], item['public_sha256'])
        for span in item['spans']:
            replacement = span['replacement'].encode()
            assert actual[span['public_offset']:span['public_offset'] + len(replacement)] == replacement
        if args.raw_base:
            original = checked(safe(args.raw_base, item['raw_path']), item['raw_bytes'], item['raw_sha256'])
            result = replay(original, item['spans'], (args.ci_home.rstrip('/') + '/').encode())
            assert result == actual
            if item['spans']:
                assert original.count((args.ci_home.rstrip('/') + '/').encode()) == len(item['spans'])
    for item in manifest['excluded_raw']:
        assert item['raw_path'] not in raw_accounted and item['reason']
        raw_accounted.add(item['raw_path'])
        if args.raw_base:
            checked(safe(args.raw_base, item['raw_path']), item['raw_bytes'], item['raw_sha256'])
    assert len(raw_accounted) == manifest['raw_member_count']
    if args.raw_base:
        actual_raw = {p.relative_to(args.raw_base).as_posix() for p in args.raw_base.rglob('*') if p.is_file()}
        assert actual_raw == raw_accounted
    for item in manifest['generated']:
        expected.add(item['path'])
        checked(safe(root, item['path']), item['bytes'], item['sha256'])
    actual_files = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert actual_files == expected
    print(json.dumps({'status': 'PASS', 'public_files': len(expected), 'included_raw': len(manifest['included_raw']),
        'excluded_raw': len(manifest['excluded_raw']), 'exact_replacement_spans': sum(len(x['spans']) for x in manifest['included_raw']),
        'raw_replay': args.raw_base is not None, 'scope': 'bytes, exact spans, and complete raw inventory; no product tests rerun'}))


if __name__ == '__main__':
    main()
