"""Private, replayable evidence index; does not alter the implementation tree."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent / 'm62-review-workflow-active'
FINAL = 'f5c80556a48e348cc6dbdebe6482ff54ad822693'
FIRST = 'e3fd9795c54b901e075015f168b1114ed7cb74e5'
DEPENDENCY = 'fa82a0b'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, data):
    (BASE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


assert git('rev-parse', 'HEAD').decode().strip() == FINAL
assert git('status', '--porcelain=v1') == b''
assert (BASE / '24-fixed-final-regressions/receipt.json').is_file()
spec = (ROOT / 'PRODUCT_DESIGN.md').read_bytes()
assert spec == Path('<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md').read_bytes()
assert sha(spec) == '2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d'
receipts = []
drivers = {sha((BASE / path).read_bytes()) for path in ['run.py', 'run-v1.py']}
for path in sorted(BASE.glob('*/receipt.json')):
    data = json.loads(path.read_bytes())
    assert data['driver_sha256'] in drivers
    assert data['log_sha256'] == sha((path.parent / 'run.log').read_bytes())
    before = json.loads((path.parent / 'inputs-before.json').read_bytes())
    after = json.loads((path.parent / 'inputs-after.json').read_bytes())
    assert data['unchanged'] and before == after
    for source in (path.parent / 'source').rglob('*'):
        if source.is_file():
            rel = str(source.relative_to(path.parent / 'source'))
            assert sha(source.read_bytes()) == before[rel]['sha256']
    lines = (path.parent / 'run.log').read_text().splitlines()
    summary = next((line for line in reversed(lines) if re.search(r'\d+ passed|\d+ failed|\d+ error|All checks passed|Success:|Found \d+ error', line)), None)
    receipts.append(dict(stage=path.parent.name, command=data['command'], exit_code=data['exit_code'],
        summary=summary, raw_receipt=str(path.relative_to(BASE)), log_sha256=data['log_sha256'],
        started_at=data['started_at'], finished_at=data['finished_at'], seconds=data['seconds']))

groups = []
for commit, stages in [(FIRST, ['11-fixed-owner-regressions', '12-fixed-ruff', '13-fixed-mypy']),
        (FINAL, ['22-increment-ruff', '23-increment-mypy', '24-fixed-final-regressions'])]:
    entries = {}
    for line in git('ls-tree', '-r', '-z', '--full-tree', commit).split(b'\0'):
        if not line:
            continue
        meta, name = line.split(b'\t', 1)
        mode, kind, blob = meta.decode().split()
        if kind == 'blob':
            entries[name.decode()] = blob
    expected = json.loads((BASE / stages[0] / 'inputs-before.json').read_bytes())
    checked = {}
    for name, actual in expected.items():
        assert name in entries, (commit, name)
        raw = git('cat-file', 'blob', entries[name])
        assert actual == dict(sha256=sha(raw), bytes=len(raw)), (commit, name)
        checked[name] = dict(actual, git_blob=entries[name])
    for stage in stages:
        assert expected == json.loads((BASE / stage / 'inputs-before.json').read_bytes())
        assert expected == json.loads((BASE / stage / 'inputs-after.json').read_bytes())
    groups.append(dict(actual_commit=commit, stages=stages, input_count=len(checked), files=checked))
write('GIT_SOURCE_BINDINGS.json', dict(version=1, scope='Tracked engineering inputs excluding progress/', groups=groups))

changed = git('diff', '--name-only', DEPENDENCY, FINAL).decode().splitlines()
write('TASK_RECEIPT.json', dict(
    task_id='M6.2-review-application-worker-report-local',
    requirement_ids=['R-13', 'R-21', 'R-22', 'R-24', 'R-25', 'R-27', 'R-29'],
    spec_sha256=sha(spec), implementation_commit=FINAL, implementation_commits=[FIRST, FINAL],
    actual_base='1391e8c87737d21ed8caf3af773040cfc96b4581',
    prerequisite_commits=['3995eb0', 'fa82a0b'],
    changed_paths=changed, commands=[dict(stage=r['stage'], argv=r['command']) for r in receipts],
    exit_codes=[dict(stage=r['stage'], exit_code=r['exit_code']) for r in receipts],
    test_summary=receipts, screenshot_paths=[], migrations=[],
    security_review=[
        'Current session, workspace, author and Policy rechecked for content and explicit decisions; safe Jobs controls retain stop access.',
        'Same-transaction original ACK authentication, actual owner material/numeric history, full Review/Jobs history and physical report bytes.',
        'External Import and recursive Quality evidence require current owner access and exact history; cycles rejected.',
        'Report, receipt, history and terminal pointers commit together; expired lease or failure rolls DB back; immutable orphan bytes may remain.',
        'Real author N/A with original reason preserved for non-math material; explicit formula/structure signals block bypass, never prove whole-text classification.',
        'Malformed scheduling rows isolated and diagnosed, never granted leases or repaired.',
        'No Provider, credential or numeric execution; human decisions and materials in tests are explicitly synthetic.'
    ],
    not_run=['HTTP/CSRF/startup/generated bindings/Jobs routing composition in this slice',
        'Draft in_review/approved projection, publication/version comparison/impact propagation/restore',
        'Complete backend/frontend suite, browser acceptance and hosted CI on this candidate',
        'Real provider/model calls, numeric sandbox execution, real expert mathematical/source approval or teaching evaluation',
        'Remote push or release'],
    blockers=['M6.2 remains partial: root owns HTTP composition; draft status projection and publication lifecycle remain follow-up owner work.'],
    next_task_id='M6.2-review-http-composition-and-draft-state-owner',
    source_binding='GIT_SOURCE_BINDINGS.json', private_raw_index='PRIVATE_RAW_INDEX.json',
    independent_review=dict(cache='m62-review-workflow-independent-v1', report='REPORT.md',
        report_sha256='8548d31de6dfec6dd20ac10377076108d83026389445a54c9e4ebe39bdee9205',
        manifest_sha256='1daedd3eab70ae084c058599dfd40a90fe85c68addf8e7f731825369e5178e5c',
        standards_open=0, spec_open=0, reviewer_reran_tests=False),
    evidence_boundary='This private bundle is not publication sanitized. Earlier failures remain original and are not rewritten as passes.'
))

for path in BASE.rglob('*'):
    if path.is_dir():
        path.chmod(0o700)
    elif path.is_file():
        path.chmod(0o600)
BASE.chmod(0o700)
files = []
for path in sorted(BASE.rglob('*')):
    if path.is_file() and path.name != 'PRIVATE_RAW_INDEX.json':
        raw = path.read_bytes()
        files.append(dict(path=str(path.relative_to(BASE)), bytes=len(raw), sha256=sha(raw)))
write('PRIVATE_RAW_INDEX.json', dict(version=1, files=files, file_count=len(files), total_bytes=sum(r['bytes'] for r in files)))
(BASE / 'PRIVATE_RAW_INDEX.json').chmod(0o600)
for name in ['TASK_RECEIPT.json', 'GIT_SOURCE_BINDINGS.json', 'REPORT.md', 'PRIVATE_RAW_INDEX.json']:
    raw = (BASE / name).read_bytes()
    print(name, sha(raw), len(raw))
print('indexed', len(files), sum(r['bytes'] for r in files))
