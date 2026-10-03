"""Verify all public bytes; optionally replay exact recorded raw byte spans."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe(base, relative):
    name = PurePosixPath(relative)
    assert not name.is_absolute() and '..' not in name.parts
    return base / relative


def checked(path, size, digest):
    raw = path.read_bytes()
    assert len(raw) == size and sha(raw) == digest, str(path)
    return raw


def replay(raw, spans):
    parts, end = [], 0
    for item in spans:
        assert end <= item['start'] < item['end'] <= len(raw)
        old = raw[item['start']:item['end']]
        assert sha(old) == item['raw_span_sha256']
        parts.extend([raw[end:item['start']], item['replacement'].encode()])
        end = item['end']
    return b''.join([*parts, raw[end:]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-base', type=Path)
    parser.add_argument('--git-repo', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'manifest.json').read_bytes())
    expected = {'manifest.json'}
    raw_paths = {}
    for item in manifest['files']:
        expected.add(item['public_path'])
        actual = checked(safe(root, item['public_path']), item['public_bytes'], item['public_sha256'])
        raw_paths.setdefault(item['raw_cache'], set()).add(item['raw_path'])
        if args.raw_base:
            raw = checked(safe(args.raw_base, item['raw_cache'] + '/' + item['raw_path']),
                          item['raw_bytes'], item['raw_sha256'])
            assert replay(raw, item['spans']) == actual
    for item in manifest['generated_files']:
        expected.add(item['path'])
        checked(safe(root, item['path']), item['bytes'], item['sha256'])
    for item in manifest['excluded_raw']:
        raw_paths.setdefault(item['raw_cache'], set()).add(item['raw_path'])
        if args.raw_base:
            checked(safe(args.raw_base, item['raw_cache'] + '/' + item['raw_path']),
                    item['raw_bytes'], item['raw_sha256'])
    assert expected == {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    sources = json.loads((root / 'engineering-source-map.json').read_bytes())
    final = sources['final_engineering_inputs']
    mappings = {(r['raw_cache'], r['raw_path']): r for r in manifest['files']}
    cache = 'm62-publication-service-development-v1'
    for stage, delta in sources['stages'].items():
        reconstructed = {k: v for k, v in final.items() if k not in delta['absent_from_stage']}
        for path, row in delta['overrides'].items():
            mapping = mappings[(cache, row['raw_path'])]
            assert row['public_path'] == mapping['public_path']
            assert row['sha256'] == mapping['raw_sha256'] and row['bytes'] == mapping['raw_bytes']
            reconstructed[path] = {'bytes': row['bytes'], 'sha256': row['sha256']}
        for side in ('before', 'after'):
            mapping = mappings[(cache, stage + '/inputs-' + side + '.json')]
            assert reconstructed == json.loads(safe(root, mapping['public_path']).read_bytes())
    if args.git_repo:
        commit = sources['fixed_final_commit']
        for path, row in final.items():
            raw = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=args.git_repo)
            assert row == {'bytes': len(raw), 'sha256': sha(raw)}
    if args.raw_base:
        for cache, expected_paths in raw_paths.items():
            folder = safe(args.raw_base, cache)
            assert expected_paths == {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    print(f"PASS: {len(manifest['files'])} raw mappings, {len(expected)} public files, "
          f"{len(manifest['excluded_raw'])} explicitly excluded raw files; "
          + ('all raw spans and inventory replayed' if args.raw_base else 'public hashes verified'))
    print(f"PASS: all {len(sources['stages'])} complete stage input sets reconstructed from final Git plus exact source deltas"
          + (f"; {len(final)} actual Git inputs verified" if args.git_repo else ''))


if __name__ == '__main__':
    main()
