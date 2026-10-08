import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

BASE = Path('$HOME/.cache/learning-workbench-acceptance')
ROOT = BASE / 'm62-public-safe-oct02'
OUT = Path(__file__).parent
sha = lambda b: hashlib.sha256(b).hexdigest()
groups = []
counts = {}
for name in ('m63-legacy-review-backup-test-evidence-oct04', 'm71-backup-legacy-test-static-review-1843556e-oct04', 'm63-legacy-review-backup-test-independent-readback-oct04'):
    folder = BASE / name
    raw = json.loads((folder / 'RAW_MANIFEST.json').read_text())
    safe = json.loads((folder / 'SAFE_SHARE.json').read_text())
    items = raw['files'].items() if isinstance(raw['files'], dict) else [(v['path'], v) for v in raw['files']]
    for path, item in items:
        data = (folder / path).read_bytes()
        assert (len(data), sha(data)) == (item['bytes'], item['sha256'])
    if 'entries' in safe:
        names = [v['raw_path'] for v in safe['entries']]
        for item in safe['entries']:
            original = (folder / item['raw_path']).read_bytes()
            candidate = (folder / item['candidate_path']).read_bytes()
            assert candidate == original.replace(b'$HOME', b'$HOME')
            assert (len(original), sha(original)) == (item['raw']['bytes'], item['raw']['sha256'])
            assert (len(candidate), sha(candidate)) == (item['candidate']['bytes'], item['candidate']['sha256'])
        outer = json.loads((folder / 'PUBLIC_OUTER_ALLOWLIST.json').read_text())
        for path, item in outer['files'].items():
            data = (folder / path).read_bytes(); assert (len(data), sha(data)) == (item['bytes'], item['sha256'])
        names += list(outer['files']) + ['PUBLIC_OUTER_ALLOWLIST.json']
    else:
        names = [v['path'] for v in safe['files']]
        for item in safe['files']:
            original = (folder / item['path']).read_bytes()
            candidate = (folder / 'safe-share' / item['path']).read_bytes()
            assert candidate == original.replace(b'$HOME', b'$HOME')
            assert (len(original), sha(original)) == (item['raw_bytes'], item['raw_sha256'])
            assert (len(candidate), sha(candidate)) == (item['public_bytes'], item['public_sha256'])
        names += ['RAW_MANIFEST.json', 'SAFE_SHARE.json', 'SAFE_SCAN.json']
    counts[name] = safe['count']
    groups.append((name, name, names))
static = BASE / 'm71-backup-legacy-test-static-review-1843556e-oct04'
bindings = json.loads((static / 'SOURCE.json').read_text())
head = '1843556e1c01b48e60082969e78d2a82b3848b45'
assert bindings['reviewed_head'] == head and bindings['canonical_matches_fixed_commit']
for item in bindings['files']:
    data = subprocess.check_output(['git', 'show', head + ':' + item['path']], cwd=ROOT)
    assert (len(data), sha(data)) == (item['bytes'], item['sha256'])
    assert (static / 'source' / item['path']).read_bytes() == data
original = json.loads((BASE / 'm63-legacy-review-backup-test-independent-readback-oct04/READBACK.json').read_text())
rerun = json.loads((OUT / 'ROOT_RERUN_READBACK.json').read_text())
assert original['result'] == rerun['result'] == 'PASS'
assert [{k:v for k,v in x.items() if k != 'readback_utc'} for x in (original, rerun)][0] == [{k:v for k,v in x.items() if k != 'readback_utc'} for x in (original, rerun)][1]
report = {
    'status': 'PASS_BACKUP_TEST_CORRECTION_AND_INDEPENDENT_READBACK',
    'canonical_test_correction': head, 'source_test_only': 'b51de327fe74cdc476a52e061fe2e044072d2267',
    'stages': 'Original fixedbd3 singleRED1FAIL; revisedb51 single1PASS included in seven-file65PASS; RuffPASS. Wrongcommit preflightNOT_RUN retained. Four stages each1381 Git-exact unchanged engineering inputs independently verified.',
    'static_review': 'No blocker. Preserves immutable reviews/receipt/actor IDs; invalidates authentication and clears mutable commands. Source eleven reviewed files independently bound to184.',
    'safe_candidates': counts,
    'root_rerun': 'Root read and reexecuted static verifier only. Timestamped output separately retained; original sealed JSON restored exact from raw-identical candidate, all original manifest bytes reverified.',
    'boundary': 'No production/native/timeout or lease change. SQL fixture is synthetic history, not actual login/human review. Complete M7 acceptance NOT_RUN; originalDCF completePythonFAIL1F2E2ENVskip unchanged; twoE causeUNKNOWN; new184 full gate separate and pending.'
}
(OUT / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
groups.append(('root', OUT.name, ['package.py', 'READBACK.json', 'ROOT_RERUN_READBACK.json', 'SEALED_JSON_RESTORE.json']))
spec = importlib.util.spec_from_file_location('package_helper', BASE / 'm62-v313-pushed-progress-sync-oct03/package.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
public = helper.package('M6.3-legacy-backup-test-correction-and-review', groups, report.copy())
(OUT / 'PACKAGE_RECEIPT.json').write_text(json.dumps({'report': public}, indent=2) + '\n')
print(json.dumps({'legacy_test_correction': 'PASS65', 'static_review': 'no blocker', 'original_complete_gate': 'FAIL'}))
