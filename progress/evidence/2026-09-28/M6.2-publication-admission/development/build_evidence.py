"""Retain command truth and bind the final engineering input set to actual Git."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent / 'm62-review-state-owner-active'
COMMIT = 'b1c88befba47193cdee776dd8a5496ed41462858'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    (BASE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+'\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


assert git('rev-parse','HEAD').decode().strip() == COMMIT
assert not git('status','--porcelain=v1')
spec_sha = sha((ROOT / 'PRODUCT_DESIGN.md').read_bytes())
assert spec_sha == '2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d'
stages = []
for path in sorted(BASE.glob('*/receipt.json')):
    value = json.loads(path.read_bytes())
    assert value['driver_sha256'] == sha((BASE/'run.py').read_bytes())
    assert value['log_sha256'] == sha((path.parent/'run.log').read_bytes())
    before = json.loads((path.parent/'inputs-before.json').read_bytes())
    assert value['unchanged'] and before == json.loads((path.parent/'inputs-after.json').read_bytes())
    for source in (path.parent/'source').rglob('*'):
        if source.is_file():
            name = str(source.relative_to(path.parent/'source'))
            assert before[name] == dict(bytes=source.stat().st_size, sha256=sha(source.read_bytes()))
    lines = (path.parent/'run.log').read_text().splitlines()
    summary = next((line for line in reversed(lines) if re.search(r'\d+ passed|\d+ failed|All checks passed|Success:',line)), None)
    stages.append(dict(stage=path.parent.name, command=value['command'], exit_code=value['exit_code'],
        summary=summary, raw_receipt=str(path.relative_to(BASE)), log_sha256=value['log_sha256'],
        started_at=value['started_at'], finished_at=value['finished_at'], seconds=value['seconds']))
expected = json.loads((BASE/'08-fixed-related-regressions/inputs-before.json').read_bytes())
tree = {}
for line in git('ls-tree','-r','-z','--full-tree',COMMIT).split(b'\0'):
    if line:
        meta,name = line.split(b'\t',1)
        tree[name.decode()] = meta.decode().split()[-1]
bindings = {}
for name, value in expected.items():
    raw = git('cat-file','blob',tree[name])
    assert value == dict(bytes=len(raw),sha256=sha(raw)), name
    bindings[name] = dict(value,git_blob=tree[name])
for name in ['08-fixed-related-regressions','09-fixed-ruff','10-fixed-mypy']:
    assert expected == json.loads((BASE/name/'inputs-before.json').read_bytes())
    assert expected == json.loads((BASE/name/'inputs-after.json').read_bytes())
write('GIT_SOURCE_BINDINGS.json',dict(actual_commit=COMMIT,input_count=len(bindings),
    stages=['08-fixed-related-regressions','09-fixed-ruff','10-fixed-mypy'],files=bindings))
paths = git('diff','--name-only',COMMIT+'^',COMMIT).decode().splitlines()
for name in paths:
    destination = BASE/'fixed-source'/name
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(git('show',COMMIT+':'+name))
write('TASK_RECEIPT.json',dict(task_id='M6.2-publication-admission-readonly-local',
    requirement_ids=['R-21','R-22','R-24','R-25','R-29'],spec_sha256=spec_sha,
    implementation_commit=COMMIT,actual_base='c2c5ee8c5f22c3ed5fd00a210b831819e962146c',
    changed_paths=paths,commands=[dict(stage=x['stage'],argv=x['command']) for x in stages],
    exit_codes=[dict(stage=x['stage'],exit_code=x['exit_code']) for x in stages],test_summary=stages,
    screenshot_paths=[],migrations=[],security_review=[
        'Same current transaction, current author/session/workspace/Policy, original owner materials and complete Review/numeric/artifact histories.',
        'Exact candidate id/revision/hash and requested review ID; last actual human receipt, required structure and applicability; no cached observation grants permission.',
        'Whole required numeric member/plan coverage uses the last matching frozen owner-ordered check; actual approval/start/completed/output/exit0/assertions required.',
        'Old numeric failures remain checked; recovery PASS must be seen by a new machine review, never upgrade the old observation.',
        'Actual error/warning coverage, private Import question exclusion and currently absent seven question-quality facts fail closed.',
        'Synthetic human and numeric ledger facts are protocol tests, not expert approval or physical sandbox evidence.'
    ],not_run=['Actual Content publication, private solution publication, draft state/CAS or global active review selection',
        'HTTP/main/startup/generated binding/UI changes, migrations, browser acceptance or full suite',
        'Real provider calls, real numeric execution, real human content approval or teaching evaluation',
        'Remote push, release or complete M6.2 acceptance'],
    blockers=['Current Import member/private/numeric coverage and seven generated-question semantic checks remain unsupported where identified; this does not permanently prohibit their later publication.'],
    next_task_id='M6.2-publication-owner-and-state-contract',
    independent_review=dict(status='Both independent axes complete, no blocking findings; neither reviewer reran product tests.',
        spec=dict(cache='m62-publication-admission-independent-v1',
            report_sha256='76d48942b014d357b6e03507586c5e4a874f2831425b17b8f101ca02f3163b77',
            manifest_sha256='501b686e7d81fdaddadf96c6e0c35717b24433019c4abe5222e7c5a50492cfc2'),
        standards=dict(cache='m62-publication-admission-root-standards-v1',
            report_sha256='06e13569230a625dd4df1019992be92181e333d609332354dca37452f9621195',
            manifest_sha256='d119ced374f34d2d71bb8443650f20e2691f480865fef44ced039c85c8f5cd71'),
        initial_assembly='assembly-before-review preserves initial pending-review metadata bytes referenced by the reviewer.'),
    source_binding='GIT_SOURCE_BINDINGS.json',raw_index='PRIVATE_RAW_INDEX.json'))
items = []
for path in sorted(BASE.rglob('*')):
    if path.is_dir():
        path.chmod(0o700)
    elif path.is_file() and path != BASE/'PRIVATE_RAW_INDEX.json':
        path.chmod(0o600)
        raw = path.read_bytes()
        items.append(dict(path=str(path.relative_to(BASE)),bytes=len(raw),sha256=sha(raw)))
write('PRIVATE_RAW_INDEX.json',dict(files=items,file_count=len(items),total_bytes=sum(x['bytes'] for x in items)))
(BASE/'PRIVATE_RAW_INDEX.json').chmod(0o600)
for name in ['TASK_RECEIPT.json','GIT_SOURCE_BINDINGS.json','PRIVATE_RAW_INDEX.json']:
    print(name,sha((BASE/name).read_bytes()))
print('files',len(items),'bytes',sum(x['bytes'] for x in items))
