"""Verify exact public/raw evidence and optional fixed Git source composition."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe(root, name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts
    return root / name


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-base', type=Path)
    parser.add_argument('--git-repo', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'manifest.json').read_bytes())
    expected = {'manifest.json'}
    for row in manifest['public_files']:
        expected.add(row['path'])
        checked(safe(root, row['path']), row)
    assert expected == {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    raw_files = {}
    for row in manifest['raw_mappings']:
        derived = checked(safe(root, row['public_path']), row, 'public_')
        raw_files[row['raw_path']] = (derived, row)
        if args.raw_base:
            raw = checked(safe(args.raw_base, row['raw_cache'] + '/' + row['raw_path']), row, 'raw_')
            assert replay(raw, row['spans']) == derived
    if args.raw_base:
        info = manifest['raw_manifest']
        raw = checked(safe(args.raw_base, manifest['raw_cache'] + '/' + info['path']), info)
        assert set(raw_files) == {row['path'] for row in json.loads(raw)['members']} | {info['path']}

    composition = json.loads((root / 'source-composition.json').read_bytes())
    inventories = []
    for stage in composition['stages']:
        before = json.loads(raw_files[stage + '/inputs-before.json'][0])
        after = json.loads(raw_files[stage + '/inputs-after.json'][0])
        receipt = json.loads(raw_files[stage + '/receipt.json'][0])
        assert before == after and len(before) == receipt['source_count'] == 1051
        assert receipt['code_commit'] == receipt['head_after'] == composition['tested_source']
        assert receipt['source_unchanged'] and receipt['all_source_matches_git_before'] and receipt['all_source_matches_git_after']
        assert receipt['log_sha256'] == raw_files[stage + '/test.log'][1]['raw_sha256']
        assert receipt['log_bytes'] == raw_files[stage + '/test.log'][1]['raw_bytes']
        assert receipt['exit_code'] == 0 and not receipt['timeout']
        assert all(row['git_matches'] is True for row in before)
        inventories.append(before)
    assert all(value == inventories[0] for value in inventories)
    pins = json.loads(raw_files['final-source-pins.json'][0])
    assert pins['source'] == composition['tested_source'] and pins['count'] == 1051
    assert pins['files'] == [{key: value for key, value in row.items() if key != 'git_matches'} for row in inventories[0]]
    overrides = {row['path']: row for row in composition['included_overrides']}
    assert len(overrides) == 12
    git_sources = 0
    tree = {}
    if args.git_repo:
        for entry in subprocess.check_output(['git', 'ls-tree', '-rz', composition['known_public_base']], cwd=args.git_repo).split(b'\0'):
            if entry:
                meta, name = entry.split(b'\t', 1)
                mode, kind, blob = meta.decode().split()
                assert kind == 'blob'
                tree[name.decode()] = (mode, blob)
    for row in inventories[0]:
        if row['path'] in overrides:
            item = overrides[row['path']]
            raw = checked(safe(root, item['public_path']), item)
            assert item['git_mode'] == row['git_mode']
        else:
            if not args.git_repo:
                continue
            mode, blob = tree[row['path']]
            assert (mode, blob) == (row['git_mode'], row['git_blob_sha1'])
            raw = subprocess.check_output(['git', 'cat-file', 'blob', blob], cwd=args.git_repo)
            git_sources += 1
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_blob_sha1']
    print(json.dumps({'public_files': len(expected), 'raw_mappings': len(manifest['raw_mappings']),
        'private_replay': bool(args.raw_base), 'fixed_source': composition['tested_source'],
        'stages': len(inventories), 'engineering_inputs_per_stage': 1051, 'included_source_overrides': len(overrides),
        'known_public_git_sources_verified': git_sources, 'excluded_log_lines': 0}, indent=2))


if __name__ == '__main__':
    main()
