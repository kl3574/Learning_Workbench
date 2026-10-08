import hashlib
import json
import subprocess
import sys
from pathlib import Path

from pydantic import ValidationError

R = Path.cwd()
O = Path(__file__).parent
H = '8da88ed890a25ee9ed6753fb6b4599625e449bf8'
BEFORE = '760af1e44c5447f60ba53248fbdd694ee25c774d'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == H
assert not subprocess.check_output(['git', 'status', '--porcelain'])
paths = ['services/api/app/codex_turn_dto.py', 'tests/contract/test_codex_turn_dto.py',
         'tests/contract/codex_turn_samples.py', 'PRODUCT_DESIGN.md']
bindings = {}
for path in paths:
    data = (R / path).read_bytes()
    assert data == subprocess.check_output(['git', 'show', H + ':' + path])
    bindings[path] = hashlib.sha256(data).hexdigest()
changed = subprocess.check_output(['git', 'diff', '--name-only', BEFORE, H], text=True).splitlines()
assert changed == ['services/api/app/codex_turn_dto.py', 'tests/contract/test_codex_turn_dto.py']
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / 'tests/contract'))
from codex_turn_samples import samples, NOW, LATER, HASH
from services.api.app.codex_turn_dto import GenericApprovalView

cases = []
for execution, revision in [('started', 2), ('completed', 2), ('failed', 3), ('unknown', 3)]:
    value = samples()['GenericApprovalView']
    value.update(decision='approve_once', decided_at=NOW, started_at=NOW,
                 execution=execution, revision=revision)
    if execution != 'started':
        value.update(finished_at=LATER, result_sha256=HASH)
    try:
        GenericApprovalView.model_validate(value)
    except ValidationError:
        cases.append({'execution': execution, 'revision': revision, 'result': 'REJECTED'})
    else:
        raise AssertionError('Stage revision counterexample still accepted')
value = samples()['GenericApprovalView']
value.update(decision='approve_once', revision=2, decided_at=NOW, validity='closed')
assert GenericApprovalView.model_validate(value).execution == 'not_started'
value.update(execution='started', started_at=NOW, revision=3)
GenericApprovalView.model_validate(value)
for execution in ['completed', 'failed', 'unknown']:
    value.update(execution=execution, revision=4, finished_at=LATER, result_sha256=HASH)
    GenericApprovalView.model_validate(value)
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == H
assert not subprocess.check_output(['git', 'status', '--porcelain'])
for path, digest in bindings.items():
    assert hashlib.sha256((R / path).read_bytes()).hexdigest() == digest
receipt = {'status': 'ROOT_DTO_STAGE_REVISION_P2_CLOSED_SCOPED', 'source': H,
    'original_source': BEFORE, 'changed_paths': changed, 'source_bindings': bindings,
    'counterexamples': cases, 'valid_stage_and_unstarted_closure_cases': 'PASS',
    'standards': 'No confirmed non-tooling breach in the eight-path DTO/derived seam.',
    'spec': 'Original completed/r2 acceptance P2 confirmed at760; four phase negatives now reject. Owner full history remains necessary.',
    'boundary': 'Root independent static diff review plus pure in-memory DTO checks only; no database, CLI, model, network or operating-system probes. Does not accept runtime/approvals/entire M6.3.'}
(O / 'CLOSURE.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({key: value for key, value in receipt.items() if key != 'source_bindings'}, ensure_ascii=False))
