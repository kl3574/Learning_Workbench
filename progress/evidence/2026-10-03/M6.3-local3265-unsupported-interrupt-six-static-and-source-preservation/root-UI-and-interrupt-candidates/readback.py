import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

B = Path('$HOME/.cache/learning-workbench-acceptance')
R = B / 'm62-public-safe-oct02'
O = Path(__file__).parent
sys.path.insert(0, str(R / 'scripts'))
from check_publication import inspect

sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_text())
records = []

def checked(path, data, digest, size=None):
    assert sha(data) == digest, path
    if size is not None:
        assert len(data) == size, path
    assert not inspect('progress/' + path, data), path
    return {'path': path, 'sha256': sha(data), 'bytes': len(data)}

def git_map(d):
    head = d.get('head', d.get('source_commit'))
    expected = {}
    tree = subprocess.check_output(['git', 'ls-tree', '-rz', head], cwd=R)
    for row in tree.split(b'\0'):
        if not row:
            continue
        meta, path = row.split(b'\t', 1)
        if not path.startswith(b'progress/'):
            expected[path.decode()] = meta.split()[2].decode()
    entries = d['files']
    if isinstance(entries, list):
        entries = {f['path']: f for f in entries}
    assert set(entries) == set(expected)
    assert len(expected) == d.get('count', len(expected))
    p = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=R,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for name, e in entries.items():
            assert e['git_blob'] == expected[name]
            p.stdin.write((e['git_blob'] + '\n').encode())
            p.stdin.flush()
            header = p.stdout.readline().split()
            blob = p.stdout.read(int(header[2]))
            assert p.stdout.read(1) == b'\n'
            assert sha(blob) == e['sha256'], name
            if 'matches_git' in e:
                assert e['matches_git'] and e['actual_blob'] == e['git_blob']
            if 'bytes' in e:
                assert len(blob) == e['bytes']
    finally:
        p.stdin.close()
        assert p.wait() == 0
    return {'head': head, 'complete_nonprogress_git_count': len(expected)}

U = B / 'm63-codex-turn-outbound-ui-evidence-oct04'
C = U / 'publication-candidates'
a = read(C / 'allowlist.json')
assert a['count'] == len(a['entries']) == 39
assert a['source_sha'] == '92c8836c5729c0a7a128a3a128d9e62c997da657'
for e in a['entries']:
    raw = (U / e['source']).read_bytes()
    candidate = (C / e['candidate']).read_bytes()
    assert sha(raw) == e['raw_sha256']
    assert candidate == raw.replace(b'$HOME', b'<LOCAL_HOME>')
    assert raw.count(b'$HOME') == e['replacement_count']
    records.append(checked('outbound-owner/' + e['candidate'], candidate,
                           e['candidate_sha256'], e['bytes']))
git_bindings = []
for fixed in ['43c6a8a1', '92c8836c']:
    before = U / ('fixed-' + fixed) / 'inputs-before.json'
    after = U / ('fixed-' + fixed) / 'inputs-after.json'
    assert before.read_bytes() == after.read_bytes()
    binding = git_map(read(before))
    assert binding['complete_nonprogress_git_count'] == 1443
    git_bindings.append(binding)

for folder in ['m63-outbound-ui-static-43c6-oct04',
               'm63-outbound-ui-static-92c8836-oct04']:
    P = B / folder
    safe, outer = read(P / 'SAFE_SHARE.json'), read(P / 'PUBLIC_OUTER_ALLOWLIST.json')
    assert len(safe['files']) == 8 and len(outer['files']) == 3
    for name, e in safe['files'].items():
        records.append(checked(folder + '/' + name, (P / name).read_bytes(),
                               e['sha256'], e['bytes']))
    for name, e in outer['files'].items():
        checked(folder + '/' + name, (P / name).read_bytes(), e['sha256'], e['bytes'])
    for line in (P / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert sha((P / name).read_bytes()) == digest
    binding = git_map(read(P / 'SOURCE_INPUTS.json'))
    assert binding['complete_nonprogress_git_count'] == 1443
    git_bindings.append(binding)

P = B / 'm63-interrupt-independent-static-79a3-oct04'
safe, outer = read(P / 'SAFE_SHARE.json'), read(P / 'PUBLIC_OUTER_ALLOWLIST.json')
assert len(safe['files']) == 3 and len(outer['files']) == 2
for e in safe['files']:
    raw = (P / e['path']).read_bytes()
    candidate = (P / 'safe-share' / e['path']).read_bytes()
    assert sha(raw) == e['raw_sha256'] and len(raw) == e['raw_bytes']
    assert candidate == raw.replace(b'$HOME', b'$HOME')
    records.append(checked('interrupt-peer/' + e['path'], candidate,
                           e['public_sha256'], e['public_bytes']))
for e in outer['files']:
    checked('interrupt-peer/' + e['path'], (P / e['path']).read_bytes(),
            e['sha256'], e['bytes'])

report = {'status': 'ROOT_EXPLICIT_CANDIDATES_AND_COMPLETE_GIT_READBACK_PASS',
          'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'outbound_owner_candidates': 39, 'outbound_peer_candidates_per_version': 8,
          'outbound_peer_outer_per_version': 3, 'interrupt_peer_candidates': 3,
          'interrupt_peer_outer': 2, 'complete_git_bindings': git_bindings,
          'records': records,
          'boundary': 'Read-only exact candidate/hash and original Git-blob verification only. No product tests, browser run, model/CLI or full M6.3 acceptance. Prefix-transformed archival scripts are not runnable-equivalence claims; no publication performed.'}
(O / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'candidate_count': len(records),
                  'git_bindings': git_bindings,
                  'receipt_sha256': sha((O / 'READBACK.json').read_bytes())}))
