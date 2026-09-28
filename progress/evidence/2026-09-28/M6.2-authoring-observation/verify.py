"""Verify the public package; optionally replay every private original and Git binding.

No network, model call, product test, file write or Git mutation is performed.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath


def require(condition, description):
    if not condition:
        raise ValueError(description)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe(base, relative):
    require(isinstance(relative, str), 'Non-string evidence path')
    path = PurePosixPath(relative)
    require(not path.is_absolute() and '..' not in path.parts and relative == path.as_posix(), 'Unsafe evidence path')
    target = base / relative
    require(not target.is_symlink() and target.resolve().is_relative_to(base.resolve()), 'Evidence path escapes its root')
    return target


def checked(path, length, digest):
    data = path.read_bytes()
    require(len(data) == length and sha(data) == digest, 'Evidence bytes/hash mismatch: ' + path.name)
    return data


def replay(raw, spans, prefix):
    cursor, result = 0, bytearray()
    for span in spans:
        start, length = span['raw_offset'], span['raw_length']
        require(cursor <= start <= len(raw) - length, 'Overlapping/outside raw span')
        require(raw[start:start + length] == prefix and sha(prefix) == span['raw_sha256'], 'Exact raw alias mismatch')
        result.extend(raw[cursor:start])
        require(len(result) == span['public_offset'], 'Wrong public span offset')
        result.extend(span['replacement'].encode())
        cursor = start + length
    result.extend(raw[cursor:])
    return bytes(result)


def check_public_spans(actual, item, policy):
    raw_cursor, public_cursor = 0, 0
    for span in item['spans']:
        start, length, destination = span['raw_offset'], span['raw_length'], span['public_offset']
        require(all(type(value) is int and value >= 0 for value in [start, length, destination]), 'Invalid span numbers')
        require(start >= raw_cursor and start + length <= item['raw_bytes'], 'Invalid raw span order')
        require(length == policy['raw_length'] and span['raw_sha256'] == policy['raw_sha256'], 'Unapproved span value')
        require(span['replacement'] == policy['replacement'], 'Unapproved replacement')
        require(destination == public_cursor + start - raw_cursor, 'Unexpected unmodified span length')
        replacement = span['replacement'].encode()
        require(actual[destination:destination + len(replacement)] == replacement, 'Missing public alias')
        raw_cursor, public_cursor = start + length, destination + len(replacement)
    require(len(actual) == public_cursor + item['raw_bytes'] - raw_cursor, 'Final unchanged span length mismatch')
    if not item['spans']:
        require(item['raw_bytes'] == item['public_bytes'] and item['raw_sha256'] == item['public_sha256'], 'Undeclared byte change')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-base', type=Path)
    parser.add_argument('--local-home')
    parser.add_argument('--source-repo', type=Path)
    parser.add_argument('--additional-raw', action='append', default=[], metavar='NAME=PATH')
    args = parser.parse_args()
    if (args.raw_base or args.additional_raw) and not args.local_home:
        parser.error('--local-home is required for exact private replay')
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'manifest.json').read_bytes())
    additional_bases = {}
    for value in args.additional_raw:
        name, separator, path = value.partition('=')
        require(separator and name not in additional_bases, 'Invalid/repeated additional raw root')
        additional_bases[name] = Path(path)
    additional_names = {group['name'] for group in manifest['additional_sources']}
    require(set(additional_bases) <= additional_names, 'Unknown additional raw root')
    if args.raw_base:
        require(set(additional_bases) == additional_names, 'Strict replay requires every additional raw root')
    prefix = (args.local_home.rstrip('/') + '/').encode() if args.local_home else None
    policy = manifest['transform']
    require(policy['replacement'] == '<LOCAL_HOME>/', 'Unexpected alias')
    if prefix:
        require(len(prefix) == policy['raw_length'] and sha(prefix) == policy['raw_sha256'], 'Wrong private home alias')
    expected, inventory, public_data, raw_data = {'manifest.json'}, {}, {}, {}
    for item in manifest['included_raw']:
        relative = item['raw_path']
        require(relative not in inventory and item['public_path'] not in expected, 'Repeated mapping')
        inventory[relative] = item; expected.add(item['public_path'])
        actual = checked(safe(root, item['public_path']), item['public_bytes'], item['public_sha256'])
        public_data[relative] = actual
        check_public_spans(actual, item, policy)
        if args.raw_base:
            original = checked(safe(args.raw_base, relative), item['raw_bytes'], item['raw_sha256'])
            raw_data[relative] = original
            require(replay(original, item['spans'], prefix) == actual, 'Replay differs from public file')
            require(original.count(prefix) == len(item['spans']), 'Undeclared private prefix occurrence')
    for item in manifest['excluded_raw']:
        require(item['raw_path'] not in inventory and item['reason'], 'Repeated/unexplained exclusion')
        inventory[item['raw_path']] = item
        if args.raw_base:
            raw_data[item['raw_path']] = checked(safe(args.raw_base, item['raw_path']), item['raw_bytes'], item['raw_sha256'])
    require(len(inventory) == manifest['raw_member_count'], 'Wrong raw member count')
    original_manifest = json.loads(public_data['MANIFEST.json'])
    require(sha(public_data['MANIFEST.json']) == manifest['original_manifest_sha256'], 'Original manifest was changed')
    original_members = {item['path']: item for item in original_manifest['members']}
    require(len(original_members) == original_manifest['count'] == 904, 'Original member list mismatch')
    require(set(inventory) == set(original_members) | {'MANIFEST.json'}, 'Original inventory is not fully accounted')
    for relative, item in original_members.items():
        require((inventory[relative]['raw_bytes'], inventory[relative]['raw_sha256']) == (item['bytes'], item['sha256']), 'Original member metadata changed')
    if args.raw_base:
        actual_raw = {p.relative_to(args.raw_base).as_posix() for p in args.raw_base.rglob('*') if p.is_file()}
        require(actual_raw == set(inventory), 'Private inventory changed')
    for item in manifest['generated']:
        require(item['path'] not in expected, 'Repeated generated file')
        expected.add(item['path']); checked(safe(root, item['path']), item['bytes'], item['sha256'])
    additional_replayed = []
    for group in manifest['additional_sources']:
        account, data_by_raw = {}, {}
        base = additional_bases.get(group['name'])
        for item in group['included_raw']:
            require(item['raw_path'] not in account, 'Repeated review member')
            account[item['raw_path']] = item
            expected.add(item['public_path'])
            data = checked(safe(root, item['public_path']), item['public_bytes'], item['public_sha256'])
            check_public_spans(data, item, policy)
            data_by_raw[item['raw_path']] = data
            if base:
                original = checked(safe(base, item['raw_path']), item['raw_bytes'], item['raw_sha256'])
                require(replay(original, item['spans'], prefix) == data, 'Review replay differs')
                require(original.count(prefix) == len(item['spans']), 'Undeclared review path occurrence')
        for item in group['excluded_raw']:
            require(item['raw_path'] not in account and item['reason'], 'Unexplained review exclusion')
            account[item['raw_path']] = item
            if base:
                checked(safe(base, item['raw_path']), item['raw_bytes'], item['raw_sha256'])
        require(len(account) == group['raw_member_count'], 'Review inventory count mismatch')
        review_manifest = data_by_raw[group['manifest_path']]
        require(sha(review_manifest) == group['manifest_sha256'], 'Review manifest changed')
        rows = json.loads(review_manifest)['members']
        require({item['path'] for item in rows} | {group['manifest_path']} == set(account), 'Review inventory incomplete')
        for row in rows:
            require((row['bytes'], row['sha256']) == (account[row['path']]['raw_bytes'], account[row['path']]['raw_sha256']), 'Review inventory metadata mismatch')
        if base:
            require({p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()} == set(account), 'Review raw inventory changed')
            additional_replayed.append(group['name'])
    actual_files = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    require(actual_files == expected, 'Public member inventory changed')

    source = json.loads(public_data['source-pins.json'])
    bindings = json.loads(public_data['GIT_SOURCE_BINDINGS.json'])
    require(source['head'] == bindings['head'] == manifest['candidate'], 'Candidate mismatch')
    require(len(source['files']) == 9, 'Wrong fixed source scope')
    for row in source['files']:
        data = public_data['fixed-source/' + row['path']]
        require(len(data) == row['bytes'] and sha(data) == row['sha256'], 'Fixed source mismatch')
        require(hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == row['git_blob'], 'Fixed Git blob mismatch')
    git_blobs = None
    if args.source_repo:
        tree = subprocess.check_output(['git', 'ls-tree', '-rz', '--full-tree', source['head']], cwd=args.source_repo)
        git_blobs = {}
        for record in tree.split(b'\0'):
            if record:
                meta, name = record.split(b'\t', 1)
                git_blobs[name.decode()] = meta.split()[2].decode()
        for row in source['files']:
            require(git_blobs.get(row['path']) == row['git_blob'], 'Repository fixed source differs')
    require(len(bindings['stages']) == 10, 'Missing actual stage')
    coverage = []
    for stage in bindings['stages']:
        name = stage['stage']
        receipt = json.loads(public_data[name + '/receipt.json'])
        before, after = public_data[name + '/inputs-before.json'], public_data[name + '/inputs-after.json']
        require(before == after, 'Stage engineering input changed during execution')
        require(sha(before) == receipt['inputs_before_sha256'] and sha(after) == receipt['inputs_after_sha256'], 'Stage input hash differs')
        require(inventory[name + '/run.log']['raw_sha256'] == receipt['log_sha256'] == stage['log_sha256'], 'Raw log binding mismatch')
        require(receipt['exit_code'] == stage['exit_code'] and receipt['inputs_unchanged'] is True, 'Original verdict changed')
        rows = json.loads(before)
        require(len(rows) == stage['inputs'] == receipt['input_count'], 'Wrong stage coverage')
        matches, differences = [], []
        for row in rows:
            cas = inventory['source-by-sha256/' + row['sha256']]
            require((cas['raw_bytes'], cas['raw_sha256']) == (row['bytes'], row['sha256']), 'Missing original source bytes')
            if args.raw_base:
                data = raw_data['source-by-sha256/' + row['sha256']]
                require(hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == row['git_blob'], 'Source input blob mismatch')
            if git_blobs is not None:
                (matches if git_blobs.get(row['path']) == row['git_blob'] else differences).append(row['path'])
        if git_blobs is not None:
            require(len(matches) == stage['candidate_exact_matches'] and differences == stage['candidate_differences'], 'Candidate coverage claim changed')
        if name.startswith('05-'):
            require(stage['inputs'] == 827 and stage['candidate_exact_matches'] == 825 and stage['candidate_differences'] == ['apps/web/src/features/authoring/useAuthoringObservation.test.tsx', 'docs/adr/0020-authoring-candidate-and-numeric-check.md'], 'Native scope overclaimed')
        if int(name[:2]) >= 6:
            require(stage['inputs'] == stage['candidate_exact_matches'] == 827 and not stage['candidate_differences'], 'Final scope mismatch')
        coverage.append({'stage': name, 'exit_code': receipt['exit_code'], 'candidate_matches': stage['candidate_exact_matches'], 'inputs': stage['inputs']})
    print(json.dumps({'status': 'PASS', 'candidate': manifest['candidate'], 'public_files': len(expected),
        'included_raw': len(manifest['included_raw']), 'excluded_raw': len(manifest['excluded_raw']),
        'exact_spans': sum(len(item['spans']) for item in manifest['included_raw']) + sum(len(item['spans']) for group in manifest['additional_sources'] for item in group['included_raw']),
        'raw_replay': args.raw_base is not None, 'git_binding_verified': git_blobs is not None,
        'additional_raw_replayed': additional_replayed,
        'stage_coverage': coverage, 'scope': 'Evidence hashes, exact byte substitutions, all raw originals and declared source coverage; no product tests executed.'}, indent=2))


if __name__ == '__main__':
    main()
