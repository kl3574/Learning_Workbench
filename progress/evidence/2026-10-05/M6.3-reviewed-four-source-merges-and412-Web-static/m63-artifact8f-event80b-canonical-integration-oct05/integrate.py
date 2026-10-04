"""Ordinary reviewed local merges; full immutable source delta checks."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

base = Path('$HOME/.cache/learning-workbench-acceptance')
root = base / 'm62-public-safe-oct02'
out = Path(__file__).parent
initial = '937848134230c967d068183b6365ced0b320cc1e'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def snapshot(head):
    files = {}
    for row in git('ls-tree', '-rz', head).split(b'\0'):
        if not row:
            continue
        meta, path = row.split(b'\t', 1)
        path = path.decode()
        if path.startswith('progress/'):
            continue
        mode, kind, oid = meta.decode().split()
        data = git('cat-file', 'blob', oid)
        files[path] = {'mode': mode, 'type': kind, 'git_blob': oid,
                       'sha256': sha(data), 'bytes': len(data)}
    return {'head': head, 'count': len(files), 'files': files}


assert git('rev-parse', 'HEAD').decode().strip() == initial
assert not git('status', '--porcelain')
assert not (out / 'before.json').exists()
before = snapshot(initial)
(out / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
expected = dict(before['files'])
results = []
for label, candidate, candidate_base, count in [
    ('artifact-ui', '8f2c884510aef987b80ae62a018c33c83d89388c',
     '4353a05570afd9f2378c904b5594998de21bc474', 15),
    ('event-ui', '80b405a9c859c47bff0d9b74465f1e7370268218',
     '4353a05570afd9f2378c904b5594998de21bc474', 7),
]:
    delta = git('diff', '--name-only', candidate_base, candidate).decode().splitlines()
    assert len(delta) == count
    source = snapshot(candidate)
    for path in delta:
        assert path not in {p for item in results for p in item['delta_paths']}
        expected[path] = source['files'][path]
    previous = git('rev-parse', 'HEAD').decode().strip()
    command = ['git', 'merge', '--no-ff', candidate, '-m',
               'Merge independently reviewed Codex ' + label]
    (out / (label + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
    process = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out / (label + '-stdout.log')).write_bytes(process.stdout)
    (out / (label + '-stderr.log')).write_bytes(process.stderr)
    assert process.returncode == 0, (label, process.returncode)
    merged = git('rev-parse', 'HEAD').decode().strip()
    after = snapshot(merged)
    assert after['files'] == expected
    assert git('rev-list', '--parents', '-n', '1', merged).decode().split() == [merged, previous, candidate]
    assert not git('status', '--porcelain')
    for path, item in after['files'].items():
        assert sha((root / path).read_bytes()) == item['sha256']
    (out / (label + '-after.json')).write_text(json.dumps(after, indent=2) + '\n')
    results.append({'stage': label, 'previous_head': previous, 'source': candidate,
                    'source_base': candidate_base, 'merged_head': merged,
                    'merge_exit_code': process.returncode, 'delta_paths': delta,
                    'complete_source_exact': True, 'inputs': after['count']})
result = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'status': 'NORMAL_TWO_MERGES_COMPLETE_REVIEWED_SOURCE_EXACT',
          'before_head': initial, 'head': merged, 'records': results,
          'original_nonoverlap_unchanged': 1490, 'complete_nonprogress_inputs': len(expected),
          'new_product_tests_executed': False, 'source_pushed': False,
          'whole_M6_3_accepted': False}
(out / 'SOURCE_FUSION.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
