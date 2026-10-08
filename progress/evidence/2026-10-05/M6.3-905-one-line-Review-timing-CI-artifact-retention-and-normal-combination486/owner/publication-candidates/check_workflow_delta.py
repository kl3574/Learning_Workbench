"""One upload path only; this is a static check, not a CI upload test."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path('$HOME/.cache/learning-workbench-acceptance/m63-review-history-timing-oct05')
prior = 'c02e9e5c73d7da5e8e1617731fbefdf94f44f0e8'
head = '905eccdd667001ec8e545cb534d5282ef6949836'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == head
assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True) == ''
path = '.github/workflows/ci.yml'
old = subprocess.check_output(['git', 'show', prior + ':' + path], cwd=root)
new = (root / path).read_bytes()
line = b'            ${{ runner.temp }}/learning-workbench-e2e-results/**/review-history-timing.json\n'
assert new.count(line) == 1 and new.replace(line, b'') == old
assert new.index(b'- name: Retain synthetic browser failure diagnostics') < new.index(line) < new.index(b'  security-publication:')
assert subprocess.check_output(['git', 'diff', '--name-only', prior, head], cwd=root, text=True).splitlines() == [path]
review = 'tests/e2e/review.spec.ts'
assert (root / review).read_bytes() == subprocess.check_output(['git', 'show', prior + ':' + review], cwd=root)
assert set(subprocess.check_output(['git', 'diff', '--name-only', '35aebd3039241abb3393300affd593f4826a4a0c', head], cwd=root, text=True).splitlines()) == {review, path}
print(json.dumps({'status': 'PASS_STATIC_ONE_ADDED_FAILURE_UPLOAD_PATH', 'head': head, 'prior': prior,
    'only_added_line': line.decode().strip(), 'all_other_workflow_bytes_exact': True,
    'review_source_sha256': hashlib.sha256((root / review).read_bytes()).hexdigest(),
    'review_source_identical_to_tested_c02e': True, 'actual_ci_upload': 'NOT_RUN',
    'native_on_new_head': 'NOT_RUN_NO_RERUN'}, indent=2))
