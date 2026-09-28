from pathlib import Path
import difflib
import hashlib
import json
import subprocess

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent / 'm62-review-import-close-active'
BEFORE = 'a944ebfbdb835a731393977a606db5b473846e98'
FINAL = '36b501cf8da071909fbb5628b7354de70d5d1825'
CHANGED = 'apps/web/src/features/draftReview/ReviewImportShell.test.tsx'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def write(name, value):
    (BASE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


assert git('rev-parse', 'HEAD').decode().strip() == FINAL
assert git('status', '--porcelain=v1') == b''
assert git('diff', '--name-only', BEFORE, FINAL).decode().splitlines() == [CHANGED]
assert (BASE / 'original-test.tsx').read_bytes() == git('show', f'{BEFORE}:{CHANGED}')
assert (BASE / 'ci-push-frontend.log').read_bytes() == (BASE.parent / 'm62-publication-a944-ci-v1/logs/push-frontend-108791498320.log').read_bytes()
(BASE / 'final.diff').write_bytes(git('diff', BEFORE, FINAL, '--', CHANGED))
(BASE / 'probe-single-variable.diff').write_text(''.join(difflib.unified_diff(
    (BASE / 'probe-publication-ledger-source.tsx').read_text().splitlines(keepends=True),
    (BASE / 'probe-enabled-click-source.tsx').read_text().splitlines(keepends=True),
    fromfile='probe-publication-ledger-source.tsx', tofile='probe-enabled-click-source.tsx')))

heads = {}
actual_blobs = {}


def actual_tree(head):
    if head not in heads:
        values = {}
        for entry in git('ls-tree', '-rz', head).split(b'\0'):
            if entry:
                metadata, name = entry.split(b'\t', 1)
                values[name.decode()] = metadata.decode().split()[2]
        missing = sorted(set(values.values()) - actual_blobs.keys())
        stream = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT, input=('\n'.join(missing) + '\n').encode(), stdout=subprocess.PIPE, check=True).stdout
        offset = 0
        for expected in missing:
            end = stream.index(b'\n', offset)
            object_id, kind, size = stream[offset:end].split()
            assert object_id.decode() == expected and kind == b'blob'
            offset = end + 1
            raw = stream[offset:offset + int(size)]
            assert len(raw) == int(size)
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == expected
            actual_blobs[expected] = sha(raw)
            offset += int(size) + 1
        heads[head] = values
    return heads[head]


summaries = {
    '01-original-focused': '1 PASS, 1 filtered/skipped; original failure not reproduced',
    '02-publication-ledger-red': '1 FAIL, 1 filtered/skipped; controlled disabled click leaves Import open',
    '03-publication-ledger-enabled-control': '1 PASS, 1 filtered/skipped; release then enabled click closes',
    '04-fixed-shell-behavior': '2 PASS, 1 FAIL; new no-dirty probe closed before confirmation, different scope',
    '05-strict-lint': 'PASS; strict TypeScript on stage04 source',
    '06-dirty-shell-guard': '3 PASS; dirty form guard regression',
    '07-related-final': '49 PASS, 9 files; final fixed Review and Publication tests',
    '08-strict-final': 'PASS; final strict TypeScript including noUnused checks',
}
ledger = []
for name, summary in summaries.items():
    folder = BASE / name
    receipt = json.loads((folder / 'receipt.json').read_text())
    before = json.loads((folder / 'inputs-before.json').read_text())
    after = json.loads((folder / 'inputs-after.json').read_text())
    assert before == after and receipt['inputs_unchanged'] is True
    assert receipt['source_count'] == len(before['files'])
    assert receipt['log_sha256'] == sha((folder / 'test.log').read_bytes())
    assert receipt['runner_sha256'] == sha((BASE / 'run.py').read_bytes())
    tree = actual_tree(before['head'])
    mismatches = []
    for row in before['files']:
        assert not row.get('absent')
        raw = (BASE / 'source-pool' / row['sha256']).read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
        expected = tree.get(row['path'])
        assert expected == row['git_blob']
        equal = expected is not None and actual_blobs[expected] == row['sha256']
        assert row['git_matches'] is equal
        if not equal:
            mismatches.append(row['path'])
    if name in ('01-original-focused', '07-related-final', '08-strict-final'):
        assert not mismatches
    ledger.append({'stage': name, 'summary': summary, **receipt, 'actual_git_source_mismatches': mismatches,
                   'receipt_sha256': sha((folder / 'receipt.json').read_bytes()),
                   'inputs_before_sha256': sha((folder / 'inputs-before.json').read_bytes()),
                   'inputs_after_sha256': sha((folder / 'inputs-after.json').read_bytes())})

for path in (BASE / 'source-pool').iterdir():
    assert path.name == sha(path.read_bytes())
sources = [
    CHANGED, 'PRODUCT_DESIGN.md', 'AGENTS.md',
    'apps/web/src/features/draftReview/ReviewPanel.tsx',
    'apps/web/src/features/draftReview/ReviewForms.tsx',
    'apps/web/src/features/draftReview/useReview.ts',
    'apps/web/src/features/draftPublication/usePublication.ts',
    'apps/web/src/features/draftPublication/PublicationPanel.tsx',
    'apps/web/src/features/draftPublication/publicationCommands.ts',
    'apps/web/src/features/imports/ImportWorkflow.tsx',
    'apps/web/src/workbench/Shell.tsx', 'apps/web/src/workbench/Controls.tsx',
    'apps/web/package.json', 'apps/web/package-lock.json', 'apps/web/vite.config.ts',
]
pins = []
tree = actual_tree(FINAL)
for name in sources:
    raw = git('show', f'{FINAL}:{name}')
    path = BASE / 'final-source' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    assert (ROOT / name).read_bytes() == raw
    pins.append({'path': name, 'bytes': len(raw), 'sha256': sha(raw), 'git_blob': tree[name]})
spec_sha = sha((ROOT / 'PRODUCT_DESIGN.md').read_bytes())
assert spec_sha == '2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d'
write('run-ledger.json', ledger)
write('final-source-pins.json', {'base': BEFORE, 'head': FINAL, 'clean': True, 'changed_paths': [CHANGED], 'sources': pins})
write('VERIFY.json', {'head': FINAL, 'source_clean': True, 'all_eight_stage_inputs_unchanged': True,
    'all_recorded_git_claims_compared_to_actual_git_objects': True,
    'final_engineering_source_count': ledger[-1]['source_count'], 'source_pool_members': len(list((BASE / 'source-pool').iterdir())),
    'actual_heads': sorted(heads), 'actual_distinct_git_objects_read': len(actual_blobs),
    'original_ci_log_byte_exact': True, 'original_test_byte_exact': True,
    'changed_paths': [CHANGED], 'product_paths_changed': [],
    'debug_probe_retained_privately_only': not any(ROOT.glob('apps/web/src/features/draftReview/*diagnostic*'))})
write('TASK_RECEIPT.json', {
    'task_id': 'M6.2-review-import-close-test-diagnosis',
    'requirement_ids': ['PRODUCT_DESIGN section 4.3', 'PRODUCT_DESIGN section 19.3', 'PRODUCT_DESIGN section 20.8 existing unsaved close protection'],
    'spec_sha256': spec_sha, 'implementation_commit': FINAL, 'changed_paths': [CHANGED],
    'commands': [{'stage': row['stage'], 'command': row['command']} for row in ledger],
    'exit_codes': {row['stage']: row['exit_code'] for row in ledger},
    'test_summary': {row['stage']: row['summary'] for row in ledger},
    'screenshot_paths': [], 'migrations': [],
    'security_review': 'No product, API, Policy, actor, secret, provider, main-tree or remote changes. Actual publication command store load is delayed then delegated; mock restored after each case. Independent review pending.',
    'not_run': ['No new full frontend suite', 'No backend or native browser suite', 'No remote CI retry/dispatch', 'No live provider calls', 'No historical CI click-time trace available'],
    'blockers': ['Historical remote failure mechanism remains supported candidate, not established uniquely; original CI failure preserved.', 'Stage04 no-dirty parent notification window is a separate observation, not fixed or certified by this test-only change.'],
    'next_task_id': 'Independent review of 36b501c and evidence; parent decides integration. Separate no-dirty window assessment if warranted.',
})
print(json.dumps({'head': FINAL, 'stages': len(ledger), 'pool': len(list((BASE / 'source-pool').iterdir())), 'verified': True}, indent=2))
