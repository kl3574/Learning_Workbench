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

sha = lambda data: hashlib.sha256(data).hexdigest()
candidate_root = B / 'm63-codex-turn-ui-restore-evidence-oct04/publication-candidates'
allow = json.loads((candidate_root / 'allowlist.json').read_text())
records = []
for e in allow['allowlist']:
    relative = e['path']
    candidate = (candidate_root / relative).read_bytes()
    assert sha(candidate) == e['candidate_sha256'], relative
    assert not inspect('progress/' + relative, candidate), relative
    if e['transformation'] != 'new_fact_summary_only':
        raw_root = B / ('m63-codex-turn-ui-evidence-oct04' if relative.startswith('fixed-629003c8/') else 'm63-codex-turn-ui-restore-evidence-oct04')
        raw = (raw_root / relative).read_bytes()
        assert sha(raw) == e['raw_sha256'], relative
        assert len(candidate) == e['bytes'], relative
        assert raw.count(b'$HOME') == e['replacement_count'], relative
        expected = raw.replace(b'$HOME', b'<LOCAL_HOME>') if e['transformation'] == 'literal_home_prefix_only' else raw
        assert candidate == expected, relative
    records.append({'path': relative, 'sha256': sha(candidate), 'bytes': len(candidate), 'transformation': e['transformation']})
assert len(records) == 31

maps = []
for directory in ['m63-codex-turn-ui-evidence-oct04/fixed-629003c8', 'm63-codex-turn-ui-restore-evidence-oct04/fixed-db5a6bce']:
    p = B / directory
    before, after = [(p / name).read_bytes() for name in ['inputs-before.json', 'inputs-after.json']]
    assert before == after
    data = json.loads(before)
    assert data['all_match_git'] and data['status'] == '' and data['count'] == len(data['files'])
    expected = {}
    tree = subprocess.check_output(['git', 'ls-tree', '-rz', data['head']], cwd=R)
    for entry in tree.split(b'\0'):
        if not entry:
            continue
        meta, path = entry.split(b'\t', 1)
        if path.startswith(b'progress/'):
            continue
        expected[path.decode()] = meta.split()[2].decode()
    assert set(expected) == {e['path'] for e in data['files']}
    proc = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=R, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for e in data['files']:
        assert e['git_blob'] == e['actual_blob'] == expected[e['path']] and e['matches_git']
        proc.stdin.write((e['git_blob'] + '\n').encode())
        proc.stdin.flush()
        header = proc.stdout.readline().split()
        assert header[0].decode() == e['git_blob'] and header[1] == b'blob'
        blob = proc.stdout.read(int(header[2]))
        assert proc.stdout.read(1) == b'\n'
        assert sha(blob) == e['sha256']
    proc.stdin.close()
    assert proc.wait() == 0
    maps.append({'head': data['head'], 'count': data['count'], 'before_after_sha256': sha(before), 'complete_git_tree_and_all_blob_sha256_verified': True})

report = {
    'status': 'ROOT_RESTORE_P2_CLOSED_STATIC_CANDIDATES_READBACK_PASS_CANCEL_WIRE_P2_REMAINS_OPEN',
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'reviewer': 'root, one reviewer reports both Standards and Spec axes; no claim of two spawned reviewers',
    'Standards': {'additional_confirmed_findings': []},
    'Spec': {'restore_finding': 'CLOSED_STATIC: fresh actor/Policy, exact original durable/held baseline, fresh checks before independent branch persistence and protected delivery; original 5 FAIL evidence retained', 'independent_cancel_wire_finding': 'OPEN: actual Jobs cancel returns full JobSnapshot but existing client/command admits JobRef; author has actual 1 FAIL counterexample, separate from restore finding'},
    'source': 'db5a6bceaeadf099de9b3a9e6d6a7ce786071db2',
    'author_gates': '1176 Web /152 files, strict/build/spec exit0 and214 original owner tests PASS; root verified manifests and logs but did not rerun those commands',
    'candidate_allowlist_sha256': sha((candidate_root / 'allowlist.json').read_bytes()),
    'candidates': records,
    'git_maps': maps,
    'boundary': 'Read-only source/evidence verification, no source push, no actual external model/CLI, no whole UI/M6.3 or academic acceptance. Publication remains a separate explicit action.'
}
(O / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'candidates': len(records), 'git_map_counts': [m['count'] for m in maps], 'report_sha256': sha((O / 'READBACK.json').read_bytes())}))
