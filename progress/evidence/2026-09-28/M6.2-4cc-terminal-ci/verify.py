"""Offline verification of public hashes, exact raw spans, logs and archive members."""
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path, PurePosixPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe(base, name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts
    return base / name


def checked(path, row, prefix=''):
    raw = path.read_bytes()
    assert len(raw) == row[prefix + 'bytes'] and sha(raw) == row[prefix + 'sha256'], str(path)
    return raw


def replay(raw, spans):
    out, cursor = bytearray(), 0
    for span in spans:
        offset, length = span['raw_offset'], span['raw_length']
        assert cursor <= offset < offset + length <= len(raw)
        assert sha(raw[offset:offset + length]) == span['raw_sha256']
        out.extend(raw[cursor:offset])
        assert len(out) == span['public_offset']
        out.extend(span['replacement'].encode())
        cursor = offset + length
    out.extend(raw[cursor:])
    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-base', type=Path, help='Parent of the original named evidence cache')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'manifest.json').read_bytes())
    expected = {'manifest.json'}
    public, included, originals = {}, {}, {}
    for row in manifest['included_raw']:
        expected.add(row['public_path'])
        data = checked(safe(root, row['public_path']), row, 'public_')
        public[row['raw_path']] = data
        included[row['raw_path']] = row
        end = 0
        for span in row['spans']:
            offset = span['public_offset']
            replacement = span['replacement'].encode()
            assert end <= offset and data[offset:offset + len(replacement)] == replacement
            end = offset + len(replacement)
        if args.raw_base:
            raw = checked(safe(args.raw_base, manifest['original_cache_name'] + '/' + row['raw_path']), row, 'raw_')
            assert replay(raw, row['spans']) == data
            originals[row['raw_path']] = raw
    for row in manifest['generated']:
        expected.add(row['path'])
        checked(safe(root, row['path']), row)
    assert expected == {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    excluded = {row['raw_path']: row for row in manifest['excluded_raw']}
    assert not set(excluded) & set(included)
    if args.raw_base:
        raw_root = args.raw_base / manifest['original_cache_name']
        for name, row in excluded.items():
            originals[name] = checked(safe(raw_root, name), row, 'raw_')
        assert set(originals) == {p.relative_to(raw_root).as_posix() for p in raw_root.rglob('*') if p.is_file()}
        original_manifest = json.loads(originals['MANIFEST.json'])
        assert sha(originals['MANIFEST.json']) == manifest['original_manifest_sha256']
        for row in original_manifest['files']:
            assert len(originals[row['path']]) == row['bytes'] and sha(originals[row['path']]) == row['sha256']
        assert len(original_manifest['files']) == 168
    evidence = json.loads(public['FINAL_JOB_EVIDENCE.json'])
    assert len(evidence['jobs']) == 12
    expected_tree = '7014f0f0abfe5f692141415752403922624e10f9'
    assert evidence['actual_tree'] == expected_tree
    for event, commit_name, run_id in [('push', 'push', 36386011041), ('pull_request', 'pr', 36386016520)]:
        expected_checkout = evidence['head'] if event == 'push' else evidence['pr_actual_checkout']
        commit = json.loads(public['browser-diagnosis/' + commit_name + '-checkout-commit.json'])
        assert commit['sha'] == expected_checkout and commit['tree']['sha'] == expected_tree
        run = json.loads(public['terminal/' + event + '-run.json'])
        assert run['id'] == run_id and run['event'] == event and run['head_sha'] == evidence['head']
        assert run['status'] == 'completed' and run['conclusion'] == 'failure' and run['run_attempt'] == 1
        actual_jobs = json.loads(public['terminal/' + event + '-jobs.json'])['jobs']
        assert len(actual_jobs) == 6 and all(job['status'] == 'completed' for job in actual_jobs)
        assert [(job['name'], job['conclusion']) for job in actual_jobs if job['conclusion'] != 'success'] == [('browser', 'failure')]
        assert {job['id'] for job in actual_jobs} == {job['id'] for job in evidence['jobs'] if job['event'] == event}
    apt, job_failures = 0, 0
    ansi = re.compile(r'\x1b\[[0-9;]*m')
    for job in evidence['jobs']:
        row = included[job['log_path']]
        assert row['raw_sha256'] == job['log_sha256']
        lines = [ansi.sub('', line) for line in public[job['log_path']].decode().splitlines()]
        checkout = job['checkout']
        assert checkout['sha'] in lines[checkout['line'] - 1]
        assert checkout['sha'] == {'push': evidence['head'], 'pull_request': evidence['pr_actual_checkout']}[job['event']]
        assert all(span['reason'] == 'exact filesystem path alias' for span in row['spans'])
        if job['installed_packages']:
            assert job['apt_step'] == 'success' and len(job['installed_packages']) == 4
            for name, value in job['installed_packages'].items():
                assert name in lines[value['line'] - 1] and value['version'] in lines[value['line'] - 1]
            apt += 1
        job_failures += job['conclusion'] == 'failure'
        expectations = {'backend': ['731 passed'], 'integration': ['1570 passed, 1 skipped',
            'BLOCKED_ENVIRONMENT: real sealed runtime did not execute the calculator; original FAIL retained'],
            'frontend': ['538 passed (538)', '91 passed (91)'], 'spec-contracts': ['604 passed'],
            'security-publication': ['PASS: scanned 12983'], 'browser': ['106 passed (', '1 failed', 'Timeout: 5000ms']}
        for fragment in expectations[job['name']]:
            assert any(fragment in line for line in lines)
    assert apt == 6 and job_failures == 2
    members = 0
    for artifact in evidence['artifacts']:
        archive_path = 'artifacts/' + artifact['event'] + '-' + str(artifact['id']) + '.zip'
        assert archive_path in excluded and excluded[archive_path]['raw_sha256'] == artifact['sha256']
        assert artifact['server_digest'] == 'sha256:' + artifact['sha256']
        archive = zipfile.ZipFile(io.BytesIO(originals[archive_path])) if args.raw_base else None
        if archive:
            assert {item.filename for item in archive.infolist() if not item.is_dir()} == {row['path'] for row in artifact['members']}
        try:
            for item in artifact['members']:
                name = 'extracted/' + Path(archive_path).stem + '/' + item['path']
                assert included[name]['raw_sha256'] == item['sha256'] and included[name]['raw_bytes'] == item['bytes']
                if archive:
                    assert archive.read(item['path']) == originals[name]
                if 'tutor-explicit' in item['path'] and item['path'].endswith('/tutor-completion-diagnostic.json'):
                    diagnostic = json.loads(public[name])
                    assert diagnostic['assertion']['verdict'] == 'failed'
                    assert diagnostic['assertion']['original_expect_timeout_ms'] == 5000
                    records = diagnostic['mechanism']['frozen_browser_records']
                    applied = [row for row in records if row['stage'] == 'event_applied'][-1]
                    assert applied['seq'] == 4 and applied['delivered_ms'] < diagnostic['assertion']['frozen_at_ms']
                    assert any(row.get('event') == 'answer_delta' and row['stage'] == 'validated_event_yield' for row in records)
                    assert not any(row.get('event') == 'completed' for row in records)
                members += 1
        finally:
            if archive:
                archive.close()
    assert members == 16
    print(json.dumps({'public_files': len(expected), 'included_raw': len(included), 'excluded_raw': len(excluded),
        'complete_logs': 12, 'failed_jobs': job_failures, 'exact_apt_installations': apt, 'archive_members_included': members,
        'private_replay': bool(args.raw_base), 'archive_containers_private': 2, 'network_requests': 0, 'product_tests': 0}, indent=2))


if __name__ == '__main__':
    main()
