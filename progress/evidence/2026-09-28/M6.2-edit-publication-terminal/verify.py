"""Offline public/source verification and optional exact private raw replay."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe(base, name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts
    return base / name


def checked(path, row, prefix=''):
    raw = path.read_bytes()
    assert len(raw) == row[prefix + 'bytes'] and sha(raw) == row[prefix + 'sha256'], str(path)
    return raw


def replay(raw, spans):
    chunks, end = [], 0
    for span in spans:
        assert end <= span['start'] < span['end'] <= len(raw)
        assert sha(raw[span['start']:span['end']]) == span['raw_span_sha256']
        chunks.extend([raw[end:span['start']], span['replacement'].encode()])
        end = span['end']
    return b''.join([*chunks, raw[end:]])


def serialize(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git-repo', type=Path)
    parser.add_argument('--raw-base', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'manifest.json').read_bytes())
    expected = {'manifest.json'}
    for row in manifest['public_files']:
        expected.add(row['path']); checked(safe(root, row['path']), row)
    assert expected == {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    sm = json.loads((root / 'source-map.json').read_bytes())
    im = json.loads((root / 'input-map.json').read_bytes())
    sources = {}
    git_sources = 0
    for digest, row in sm['sources'].items():
        if row['method'] == 'public-git':
            if not args.git_repo:
                continue
            raw = subprocess.check_output(['git', 'show', sm['public_base'] + ':' + row['path']], cwd=args.git_repo)
            git_sources += 1
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            assert blob == row['git_blob']
        else:
            raw = checked(safe(root, row['path']), row)
        assert sha(raw) == digest and len(raw) == row['bytes']
        sources[digest] = raw
    inputs = {}
    for digest, delta in im['snapshots'].items():
        value = {p: v for p, v in im['baseline'].items() if p not in delta['absent']}
        value.update(delta['overrides'])
        raw = serialize(value); assert sha(raw) == digest
        for info in value.values():
            assert sm['sources'][info['sha256']]['bytes'] == info['bytes']
        inputs[digest] = raw
    mapped, covered = {}, {}
    for row in manifest['raw_mappings']:
        cache, name = row['raw_cache'], row['raw_path']
        covered.setdefault(cache, set()).add(name)
        if row['method'] == 'file':
            raw = checked(safe(root, row['public_path']), row, 'public_')
        elif row['method'] == 'input':
            raw = inputs[row['raw_sha256']]
        else:
            assert row['method'] == 'source'
            raw = sources.get(row['raw_sha256'])
        mapped[(cache, name)] = raw
        if args.raw_base:
            original = checked(safe(args.raw_base, cache + '/' + name), row, 'raw_')
            assert raw is not None, '--git-repo is required for full replay'
            assert replay(original, row.get('spans', [])) == raw
    if args.raw_base:
        for cache, row in manifest['raw_manifests'].items():
            original = checked(safe(args.raw_base, cache + '/' + row['path']), row)
            members = json.loads(original)['members']
            names = set(members) if isinstance(members, dict) else {item['path'] for item in members}
            assert covered[cache] == names | {row['path']}
    commits = {}
    actual_commits = []
    for head, delta in sm['commit_overrides'].items():
        value = {p: v for p, v in sm['public_base_inputs'].items() if p not in delta['absent']}
        value.update(delta['overrides']); commits[head] = value
        if args.git_repo:
            tree = subprocess.check_output(['git', 'ls-tree', '-rz', head], cwd=args.git_repo)
            rows = {}
            for entry in tree.split(b'\0'):
                if not entry:
                    continue
                meta, name = entry.split(b'\t', 1); path = name.decode()
                if path.startswith('progress/'):
                    continue
                blob = meta.decode().split()[2]
                assert path in value
                content = sources[value[path]['sha256']]
                assert hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest() == blob
                rows[path] = value[path]
            assert rows == value
            actual_commits.append(head)
    stages = json.loads((root / 'stage-bindings.json').read_bytes())
    for stage in stages:
        cache, name = stage['cache'], stage['stage']
        before = mapped[(cache, name + '/inputs-before.json')]
        after = mapped[(cache, name + '/inputs-after.json')]
        receipt = json.loads(mapped[(cache, name + '/receipt.json')])
        assert before == after and receipt['unchanged']
        value = json.loads(before)
        assert len(value) == receipt['input_count_before'] == receipt['input_count_after']
        assert receipt['actual_head'] == stage['actual_head'] and receipt['exit_code'] == stage['exit_code']
        assert stage['log_sha256'] == receipt['log_sha256']
        driver = next(row for row in manifest['raw_mappings'] if row['raw_cache'] == cache and row['raw_path'] == 'run.py')
        assert driver['raw_sha256'] == receipt['driver_sha256']
        raw_log = next(row for row in manifest['raw_mappings'] if row['raw_cache'] == cache and row['raw_path'] == name + '/run.log')
        assert raw_log['raw_sha256'] == receipt['log_sha256'] and raw_log['raw_bytes'] == receipt['log_bytes']
        assert stage['matching_fixed_commit_bytes'] == [head for head, data in commits.items() if data == value]
    print(json.dumps({'public_files': len(expected), 'raw_mappings': len(manifest['raw_mappings']),
        'source_pool': len(sm['sources']), 'public_git_sources_verified': git_sources,
        'input_snapshots_reconstructed': len(inputs), 'stages_verified': len(stages),
        'actual_git_commits_verified': actual_commits, 'private_replay': bool(args.raw_base),
        'excluded_log_lines': 0, 'network_requests': 0, 'product_tests': 0}, indent=2))


if __name__ == '__main__':
    main()
