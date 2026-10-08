import datetime
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

B = Path('$HOME/.cache/learning-workbench-acceptance')
R = B / 'm62-public-safe-oct02'
O = Path(__file__).parent
sys.path.insert(0, str(R / 'scripts'))
from check_publication import inspect
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_text())
assert not (O / 'READBACK.json').exists()
N = B / 'm63-outbound-ui-native-92c8836c-oct04'
binding = read(N / 'FINAL_BINDING.json')
for name, e in binding['raw_files'].items():
    raw = (N / name).read_bytes()
    assert sha(raw) == e['sha256'] and len(raw) == e['bytes']
for name, digest in binding['private_harness_hashes_only'].items():
    assert sha((N / name).read_bytes()) == digest
    assert (N / name).read_bytes() == (N / 'run-01' / name).read_bytes()
a = read(N / 'publication-candidates/allowlist.json')
assert a['count'] == len(a['files']) == 24
for e in a['files']:
    raw = (N / e['source']).read_bytes()
    candidate = (N / 'publication-candidates' / e['candidate']).read_bytes()
    assert sha(raw) == e['raw_sha256'] and len(raw) == e['raw_bytes']
    expected = raw if e['source'].endswith('.png') else raw.replace(b'$HOME', b'<LOCAL_HOME>')
    assert candidate == expected and sha(candidate) == e['candidate_sha256']
    assert len(candidate) == e['candidate_bytes'] and not inspect('progress/' + e['candidate'], candidate)

def git_map(d):
    head = d.get('head', d.get('source_commit'))
    fs = d['files']
    if isinstance(fs, list):
        fs = {e['path']: e for e in fs}
    tree = {}
    for row in subprocess.check_output(['git', 'ls-tree', '-rz', head], cwd=R).split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        if not name.startswith(b'progress/'):
            tree[name.decode()] = meta.split()[2].decode()
    assert set(tree) == set(fs) and len(tree) == d.get('count', len(tree))
    p = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=R, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for name, e in fs.items():
        assert e['git_blob'] == tree[name]
        p.stdin.write((tree[name] + '\n').encode())
        p.stdin.flush()
        header = p.stdout.readline().split()
        blob = p.stdout.read(int(header[2]))
        assert p.stdout.read(1) == b'\n' and sha(blob) == e['sha256']
        if 'bytes' in e:
            assert len(blob) == e['bytes']
        if 'matches_git' in e:
            assert e['matches_git'] and e['actual_blob'] == tree[name]
    p.stdin.close()
    assert p.wait() == 0
    return {'head': head, 'complete_nonprogress_git_count': len(tree)}

maps = []
for name in ['before.json', 'source-before.json']:
    after = name.replace('before', 'after')
    assert (N / 'run-01' / name).read_bytes() == (N / 'run-01' / after).read_bytes()
    item = git_map(read(N / 'run-01' / name))
    assert item['head'] == binding['source_sha'] and item['complete_nonprogress_git_count'] == 1443
    maps.append(item)
receipt = read(N / 'run-01/receipt.json')
assert receipt['synthetic_model_requests'] == 1 and receipt['before_after_git_exact']
assert binding['exit_code'] == 0
assert sorted(w['kind'] for w in receipt['writes']) == ['grant', 'preview', 'revoke', 'start']
assert all(w['durable_complete_ack'] and w['refresh_automatic_posts'] == 0 and w['explicit_posts'] == 2 for w in receipt['writes'])

P = B / 'm63-operation-closure-fix-evidence-oct04'
command = ['python3', str(P / 'VERIFY.py'), str(P), str(B / 'm63-operation-closure-fix-oct04')]
started = time.monotonic()
p = subprocess.run(command, capture_output=True)
(O / 'operation-verifier.stdout').write_bytes(p.stdout)
(O / 'operation-verifier.stderr').write_bytes(p.stderr)
v = {'command': command, 'exit_code': p.returncode, 'elapsed_seconds': time.monotonic() - started,
     'stdout_sha256': sha(p.stdout), 'stderr_sha256': sha(p.stderr)}
(O / 'operation-verifier.json').write_text(json.dumps(v, indent=2) + '\n')
assert p.returncode == 0
assert sha(p.stdout) == '122c870334c79dc919a1d24e76e072deb78f39a3ea7211e90a6ba5367603d45e'

peer_records = []
for folder in ['m63-operation-closure-static-3120-oct04', 'm63-operation-closure-static-83d7-oct04']:
    P = B / folder
    for manifest_name, count in [('SAFE_SHARE.json', 8), ('PUBLIC_OUTER_ALLOWLIST.json', 3)]:
        manifest = read(P / manifest_name)
        assert len(manifest['files']) == count
        for name, e in manifest['files'].items():
            raw = (P / name).read_bytes()
            assert sha(raw) == e['sha256'] and len(raw) == e['bytes']
            assert not inspect('progress/' + name, raw)
    for line in (P / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert sha((P / name).read_bytes()) == digest
    peer_records.append(git_map(read(P / 'SOURCE_INPUTS.json')))
report = {'status': 'ROOT_FINAL_NATIVE_CANDIDATES_GIT_AND_OPERATION_ORIGINAL_VERIFIER_PASS',
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'native_candidates': 24, 'native_complete_git_maps': maps,
    'native_original_harness_read': 'Root privately read all three files before run01 and hash-checked unchanged after; harnesses not public candidates',
    'native_images': 'Root independently viewed all6 original1440/390PNG: actualfailed+complete response and Unicode/hash visible; default1440/learner390 only longJSON sections, no single-frame complete-state claim. Geometry assertions bound to successful original harness.',
    'native_model_boundary': 'Actual default modelCount0 and exactly1 controlled memory transport plus statically reviewed no-remote fixture. actual_external_requests=0 field is a harness declaration, not browser/OS full-traffic measurement. No actual CLI/DeepSeek/remote model acceptance.',
    'operation_verifier': v, 'operation_peer_complete_git_maps': peer_records,
    'operation_scope': 'Root read83d final production dependency delta and actual defining-global/compiled model path; peer originalP2 CLOSED_STATIC. Actual226PASS/55overlap/final sixstatic belong to owner, root runs pure read-only original evidence/Git verifier only.',
    'boundary': 'No source mutation or remote publication; no new root product tests/model/CLI/system probes. Whole M6.3, physicalBroker/numeric/academic acceptance incomplete. Transformed archival scripts are not runnable-equivalence claims.'}
(O / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'native_candidates': 24,
                  'operation_verifier_exit': p.returncode, 'peer_git_bindings': peer_records,
                  'receipt_sha256': sha((O / 'READBACK.json').read_bytes())}))
