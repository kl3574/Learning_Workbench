import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-active')
CACHE = ROOT.parent
OUT = pathlib.Path(__file__).parent


def git(*args, data=None):
    return subprocess.run(['git', *args], cwd=ROOT, input=data, capture_output=True, check=True).stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


check = json.loads((OUT / 'CHECK.json').read_bytes())
assert git('rev-parse', 'HEAD').decode().strip() == check['head']
assert git('show', ':.gitattributes') == (OUT / 'gitattributes.before').read_bytes()
results = []
for path, warnings in check['files'].items():
    assert path.startswith('progress/evidence/2026-09-28/')
    data = git('show', ':' + path)
    assert data == (ROOT / path).read_bytes()
    parts = pathlib.PurePosixPath(path).parts
    package = pathlib.PurePosixPath(*parts[:4])
    rel = pathlib.PurePosixPath(*parts[4:]).as_posix()
    manifest_data = git('show', ':' + str(package / 'manifest.json'))
    assert manifest_data == (ROOT / package / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_data)
    mappings = []
    for item in manifest.get('files', []):
        if item['public_path'] == rel:
            mappings.append((item['raw_cache'], item))
    for item in manifest.get('included_raw', []):
        if item['public_path'] == rel:
            mappings.append((manifest['original_cache_name'], item))
    for group in manifest.get('additional_sources', []):
        for item in group.get('included_raw', []):
            if item['public_path'] == rel:
                mappings.append((group['cache'], item))
    assert mappings
    verified = []
    for raw_cache, item in mappings:
        raw = (CACHE / raw_cache / item['raw_path']).read_bytes()
        assert len(raw) == item['raw_bytes'] and sha(raw) == item['raw_sha256']
        assert len(data) == item['public_bytes'] and sha(data) == item['public_sha256']
        if path.endswith('supervisor.stdout'):
            assert raw.count(b'<LOCAL_HOME>/') == 2
            assert raw.replace(b'<LOCAL_HOME>/', b'<LOCAL_HOME>/') == data
            assert item['transformation_counts'] == {
                'local_home_slash': 2, 'local_home_bare': 0,
                'ci_home_slash': 0, 'ci_home_bare': 0, 'pytest_user_root': 0,
            }
            assert raw.endswith(b'\n\n') and data.endswith(b'\n\n')
        else:
            assert raw == data
        verified.append({'raw_cache': raw_cache, 'raw_path': item['raw_path'],
                         'raw_sha256': sha(raw), 'raw_bytes': len(raw)})
    lines = data.splitlines(keepends=True)
    if path.endswith(('.patch', '.diff')):
        hunks = set()
        old_remaining = new_remaining = 0
        for number, line in enumerate(lines, 1):
            match = re.match(rb'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if match:
                assert old_remaining == new_remaining == 0
                old_remaining = int(match[2] or b'1')
                new_remaining = int(match[4] or b'1')
            elif old_remaining or new_remaining:
                if line.startswith(b' '):
                    hunks.add(number)
                    old_remaining -= 1
                    new_remaining -= 1
                elif line.startswith(b'-'):
                    old_remaining -= 1
                elif line.startswith(b'+'):
                    new_remaining -= 1
                else:
                    assert line.startswith(b'\\ No newline at end of file')
                assert old_remaining >= 0 and new_remaining >= 0
        assert old_remaining == new_remaining == 0
        assert all(w['line'] in hunks and lines[w['line'] - 1] == b' \n' for w in warnings)
        parsed = git('apply', '--numstat', '-', data=data)
        (OUT / (str(len(results)) + '-patch-numstat.txt')).write_bytes(parsed)
        kind = 'unified-diff unchanged-empty-line context markers'
    else:
        assert len(warnings) == 1 and lines[warnings[0]['line'] - 1] == b'\n'
        assert warnings[0]['line'] == len(lines)
        kind = 'captured stdout original final blank line'
    results.append({'path': path, 'bytes': len(data), 'sha256': sha(data),
                    'manifest_sha256': sha(manifest_data), 'kind': kind,
                    'warnings': warnings, 'originals': verified})

paths = git('diff', '--cached', '--name-only', '-z').decode().split('\0')
paths = [p for p in paths if p]
assert len(paths) == 683
non_evidence = [p for p in paths if not p.startswith('progress/evidence/')]
assert non_evidence == ['progress/CURRENT.md', 'progress/M6.2-next.md', 'progress/state.json']
subset = subprocess.run(['git', 'diff', '--cached', '--check', '--', *non_evidence],
                        cwd=ROOT, capture_output=True)
assert subset.returncode == 0 and not subset.stdout and not subset.stderr
result = {'head': check['head'], 'status': 'PASS', 'staged_path_count': len(paths),
          'warning_file_count': len(results), 'warning_count': sum(len(x['warnings']) for x in results),
          'original_mapping_count': sum(len(x['originals']) for x in results),
          'source_or_progress_warning_count': 0,
          'non_evidence_check_exit': subset.returncode, 'files': results,
          'scope': 'Read-only staged bytes, six exact warning files and their original mappings; no product tests or index/source changes.'}
(OUT / 'VERIFY.json').write_text(json.dumps(result, indent=2) + '\n')
(OUT / 'suggested-exact-attributes.txt').write_text(''.join(x['path'] + ' -whitespace\n' for x in results))
print(json.dumps({k: v for k, v in result.items() if k != 'files'}, indent=2))
