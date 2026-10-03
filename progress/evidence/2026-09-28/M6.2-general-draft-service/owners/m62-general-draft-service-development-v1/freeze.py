"""Freeze source-specific development evidence. No tests or product writes."""
from pathlib import Path
import hashlib
import io
import json
import re
import subprocess

B = Path(__file__).resolve().parent
R = B.parent / 'm62-general-draft-service-active'
HEAD = '5c6d9959fee4ef7cf22fe2cca8e0f07fa524c18d'
BASE = 'a944ebfbdb835a731393977a606db5b473846e98'
SPEC = '2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def item(path):
    raw = path.read_bytes()
    return {'sha256': digest(raw), 'bytes': len(raw)}


def write(name, value):
    (B / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=R)


assert not (B / 'PRIVATE_MANIFEST.json').exists(), 'already frozen'
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert git('status', '--porcelain') == b''
assert digest((R / 'PRODUCT_DESIGN.md').read_bytes()) == SPEC
tree = {}
for line in git('ls-tree', '-r', '-z', HEAD).split(b'\0'):
    if not line:
        continue
    header, path = line.split(b'\t', 1)
    mode, kind, oid = header.decode().split()
    name = path.decode()
    if name.startswith('progress/'):
        continue
    assert kind == 'blob'
    tree[name] = oid
response = subprocess.run(['git', 'cat-file', '--batch'], cwd=R,
    input=('\n'.join(tree.values()) + '\n').encode(), capture_output=True, check=True).stdout
stream = io.BytesIO(response)
actual = {}
for name, oid in tree.items():
    header = stream.readline().decode().split()
    assert header[:2] == [oid, 'blob']
    raw = stream.read(int(header[2]))
    assert stream.read(1) == b'\n'
    actual[name] = {'sha256': digest(raw), 'bytes': len(raw)}
    assert item(R / name) == actual[name]
assert stream.read() == b''
changed = git('diff', '--name-only', BASE, HEAD).decode().splitlines()
assert len(changed) == 21
assert not any(name.startswith(('progress/', 'packages/contracts/', 'apps/web/')) or
    name in {'PRODUCT_DESIGN.md', 'services/api/app/main.py'} or
    (name.startswith('migrations/') and name != 'migrations/0019_draft_edits.sql') for name in changed)
(B / 'final-change.diff').write_bytes(git('diff', '--binary', BASE, HEAD))
write('final-source-pins.json', {'base_commit': BASE, 'candidate_commit': HEAD, 'engineering_input_count': len(actual),
    'spec_sha256': SPEC, 'paths': {name: actual[name] | {'git_blob': tree[name]} for name in changed}})
pool = B / 'source-pool'
for path in pool.iterdir():
    assert path.is_file() and digest(path.read_bytes()) == path.name
ledger = []
references = set()
driver = digest((B / 'run.py').read_bytes())
stages = sorted(B.glob('*/receipt.json'))
assert len(stages) == 25
for path in stages:
    stage = path.parent.name
    receipt = json.loads(path.read_text())
    log = path.parent / 'run.log'
    assert item(log) == {'sha256': receipt['log_sha256'], 'bytes': receipt['log_bytes']}
    assert receipt['driver_sha256'] == driver
    before = json.loads((path.parent / 'inputs-before.json').read_text())
    after = json.loads((path.parent / 'inputs-after.json').read_text())
    assert before == after and receipt['unchanged'] and not receipt['changed_paths']
    assert len(before) == receipt['input_count_before'] == receipt['input_count_after']
    for name, details in before.items():
        assert item(pool / details['sha256']) == details
        references.add(details['sha256'])
    full_log = log.read_text()
    matching_final = before == actual
    if stage in {'22-final-related', '23-final-mypy', '24-final-ruff', '25-final-related-restricted'}:
        assert matching_final and receipt['actual_head'] == HEAD
    if stage in {'23-final-mypy', '24-final-ruff', '25-final-related-restricted'}:
        assert receipt['exit_code'] == 0
    match = re.findall(r'[^\n]*(?:\d+ passed|\d+ failed|no issues found|All checks passed!)[^\n]*', full_log)
    ledger.append({'stage': stage, 'receipt': stage + '/receipt.json', 'receipt_metadata': item(path),
        'log': stage + '/run.log', 'log_metadata': item(log), 'exit_code': receipt['exit_code'],
        'before': item(path.parent / 'inputs-before.json'), 'after': item(path.parent / 'inputs-after.json'),
        'input_count': len(before), 'source_unchanged': True, 'actual_head': receipt['actual_head'],
        'matches_final_engineering_git': matching_final,
        'changed_from_final': sorted(name for name in before.keys() | actual.keys() if before.get(name) != actual.get(name)),
        'terminal_line': match[-1] if match else full_log.splitlines()[-1]})
assert references == {path.name for path in pool.iterdir()}
write('run-ledger.json', ledger)
verification = {'candidate_commit': HEAD, 'base_commit': BASE, 'clean_worktree': True,
    'source_pins': item(B / 'final-source-pins.json'), 'all_final_engineering_git_inputs': len(actual),
    'all_source_pool_blobs_checked': len(references), 'all_stage_receipts_logs_inputs_checked': len(ledger),
    'all_before_after_unchanged': True, 'stages_matching_final_engineering_bytes': [row['stage'] for row in ledger if row['matches_final_engineering_git']],
    'excluded_engineering_prefix': 'progress/', 'spec_sha256': SPEC,
    'unchanged_protected_paths': 'Spec, core54/contracts, all prior migrations, main/HTTP/generated/frontend/progress',
    'runtime_databases_retained': False, 'controlled_fixture_scope': 'See controlled-fixture-scope-audit.md; stage22 interrupted and is not a completed gate'}
write('final-actual-git-verification.json', verification)
final = next(row for row in ledger if row['stage'] == '25-final-related-restricted')
source_tests = []
for line in (B / '25-final-related-restricted/run.log').read_text().splitlines():
    if line.startswith('tests/integration/test_draft_edit') and ' PASSED ' in line:
        source_tests.append(line.split(' PASSED ')[0])
assert len(source_tests) == 83
write('new-behavior-test-results.json', {'stage': '25-final-related-restricted', 'fixed_commit': HEAD,
    'passed_new_test_cases': len(source_tests), 'nodeids': source_tests})
report = f'''# Generic text-block Draft service — fixed development receipt

Candidate `{HEAD}`, base `{BASE}`; 21 changed files, clean tree. Sole normative source is PRODUCT_DESIGN.md SHA256 `{SPEC}`. ADR0032 records implementation choices, not a new product specification. No main/progress/remote or older evidence package was modified.

Implemented: genuine exact nonnull historical public text-block copy, strict create/PATCH models, title/body whitelist, complete body/candidate hashes, authoring_edit owner, immutable chained revisions, real head CAS, permanent original command ACKs, same-transaction Content/Provenance metadata/body checks, and Quality edit materials with a current-head gate only for new Review commands. Old queued workers and original review receipts remain tied to immutable old revisions. Current identity/author/Policy and physical evidence are revalidated. No approval crosses an edit revision. Editing admission/publication is explicitly unsupported.

Migration0019 preserves all original ordinary columns and rowids across the eleven-table FK closure with foreign keys enabled, restores old triggers and retains checksums of earlier migrations. Real nonempty Import, two-revision Review, explicit synthetic human decision and completed publication histories survive unchanged; the original ACKs still verify. Separate synthetic persisted Import/single/group shapes and all prior FK definitions also survive. Two actual migration fault points restore prior schema/data/migration records. Synthetic generated records are schema fixtures, not authenticated Provider histories.

Final restricted related gate: **{final['terminal_line']}** on the fixed commit. It selects 16 local integration files and explicitly excludes controlled-generation fixtures; it is not the full suite. Of those results, **83 new behavior cases** belong to this slice. Final mypy: 208 source files PASS; final Ruff: 19 changed Python files PASS. These static/behavior results are separate evidence and must not be added into an invented full-suite total. No HTTP, UI, generated-contract or whole-M6.2 acceptance ran in this slice.

Actual failures retained: 01 old source-kind schema constraint (1 FAIL)→02 migration (3 PASS); 03 absent service→04 real create/PATCH; 05 missing Quality material profile→06 real Review; 07 recursive JSON budget missing (1 FAIL/45 PASS); 08 forged catalog bypass (2 FAIL); both corrected in09 (50 PASS); 10 repository append left a head change when outer caller caught SQL failure (1 FAIL/13 PASS)→11 savepoint (14 PASS); 14 ordinary model repr expanded synthetic academic content (1 FAIL/1 PASS)→15 diagnostic checks (7 PASS). The Unicode scalar case already passed at14 and is not a second RED. 12 Ruff unused imports and13 mypy union narrowing are static failures, fixed in17/18 and final23/24. 19 was two new fixture-construction errors plus4PASS; 20 fixes only the fixtures and passes2. 21 private-original descriptor and immutable-store tests pass2.

Stage22 was interrupted after a test-selection mistake included two existing controlled loopback generation fixtures. It has a nonzero driver receipt and pytest interruption/teardown traceback, **not a completed PASS or product regression**. The observed two fixture DBs each had one Provider dispatch and terminal, and zero numeric check/execution rows. Those counts are explicitly transcribed observations; the temporary DBs disappeared before a later JSON export, whose AssertionError is retained. See controlled-fixture-scope-audit.md. Do not claim zero Provider activity across this entire development record. No real vendor request, user-key access, real numeric execution or real human approval occurred. Stage25 corrects the selection on unchanged fixed source.

Source inheritance copies frozen citation/rights/warning descriptors. It verifies the public base metadata and physical public body, **not private-original physical bytes or source truth**. A synthetic private-visibility fixture with an unreadable original confirms that boundary. Missing source descriptors retain original IDs plus unresolved warning. Real recursive Quality evidence corruption rejects receipt/ACK/download. Mathematics/source/independent teaching remain machine NOT_RUN; human decision fixtures are synthetic. New/edit/source operations do not write Content, provenance, outbox or publication lifecycle.

Applicable matrix coverage and remaining limits are in TEST_MATRIX_RESULT.md. In particular no claim is made for every race in the earlier design matrix, generated-owner runtime regression, a higher published restoration revision, dependency impact, general Draft state/GET, nullable-base creation, other kinds or full draft workflow. Resources have explicit local limits documented in ADR0032.

Evidence: all25 stage logs, commands, exit codes, before/after input hashes and content-addressed source bytes are retained. final-source-pins.json binds21 changed files; final-actual-git-verification.json checks all{len(actual)} final engineering inputs against actual Git and every earlier source-pool reference. Earlier dirty-stage sources are preserved as actual bytes, not retroactively called Git commits. Runtime DBs/blobs, pytest caches and toolchain environments are excluded; no missing runtime is fabricated. The package is private and not yet a publication package.

Review status: pending independent root/peer review. These are implementer-executed results, not an independent review. Next task is independent source/evidence review, then a separately validated actual HTTP adapter and generated contract wiring if accepted.
'''
(B / 'REPORT.md').write_text(report)
write('TASK_RECEIPT.json', {'task': 'M6.2 exact historical text-block Draft create/PATCH service',
    'status': 'IMPLEMENTED_LOCAL_SERVICE_INDEPENDENT_REVIEW_PENDING', 'candidate_commit': HEAD, 'base_commit': BASE,
    'spec_sha256': SPEC, 'changed_files': 21, 'final_engineering_inputs': len(actual),
    'behavior': {'stage': final['stage'], 'terminal': final['terminal_line'], 'new_cases_passed': 83, 'full_suite': 'NOT_RUN'},
    'static': {'mypy_source_files': 208, 'ruff_changed_python_files': 19, 'result': 'PASS'},
    'controlled_provider_fixture_correction': 'stage22: two controlled loopback generation fixtures executed; interrupted gate retained; stage25 excludes them',
    'real_vendor_provider': 'NOT_RUN', 'numeric_execution': 'NOT_RUN', 'real_human_approval': 'NOT_RUN',
    'http_ui_generated_routes_editing_publication': 'NOT_IMPLEMENTED_IN_THIS_SLICE',
    'independent_review': 'PENDING', 'publication': 'NOT_RUN', 'raw_stages_preserved': 25,
    'excluded': ['pytest runtime databases/blobs', 'pytest caches', 'virtual environment/toolchain', 'progress from engineering input snapshots'],
    'next_task': 'Independent source/evidence review before HTTP adapter integration'})
assert (B / 'TEST_MATRIX_RESULT.md').is_file()
members = {str(path.relative_to(B)): item(path) for path in sorted(B.rglob('*')) if path.is_file()}
write('PRIVATE_MANIFEST.json', {'format': 'sha256-private-evidence-manifest-v1', 'members': members})
print(json.dumps({'members': len(members), 'manifest': item(B / 'PRIVATE_MANIFEST.json'),
    'report': item(B / 'REPORT.md'), 'receipt': item(B / 'TASK_RECEIPT.json'), 'verification': item(B / 'final-actual-git-verification.json')}))
