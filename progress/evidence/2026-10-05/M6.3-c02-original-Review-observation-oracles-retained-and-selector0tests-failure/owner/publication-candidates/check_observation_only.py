"""Byte proof: remove only new observation text; all original statements remain."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

root = Path('$HOME/.cache/learning-workbench-acceptance/m63-review-history-timing-oct05')
base = '35aebd3039241abb3393300affd593f4826a4a0c'
path = 'tests/e2e/review.spec.ts'
original = subprocess.check_output(['git', 'show', base + ':' + path], cwd=root).decode()
current = (root / path).read_text()
first = "test('real history and exact material review"
second = "test('a delayed old review response"
assert original[:original.index(first)] == current[:current.index(first)]
assert original[original.index(second):] == current[current.index(second):]
old_body = original[original.index('  const errors: string[]', original.index(first)):original.index('\n})\n\n', original.index(first))]
new_body = current[current.index('  const errors: string[]', current.index(first)):current.index('\n  } finally {', current.index(first))]
new_body = re.sub(r"^  timingPhase\('[a-z-]+'\)\n?", '', new_body, flags=re.M)
new_body = re.sub(r" timingPhase\('[a-z-]+'\);", '', new_body)
assert new_body.rstrip('\n') == old_body
unchanged = ['tests/e2e/playwright.config.ts', 'tests/e2e/restartRuntime.ts', 'tests/e2e/assessmentTestData.ts',
             'tests/e2e/practiceTestData.ts', 'tests/e2e/responseJsonBarrier.ts', 'PRODUCT_DESIGN.md', 'Makefile']
for name in unchanged:
    assert (root / name).read_bytes() == subprocess.check_output(['git', 'show', base + ':' + name], cwd=root)
changed = subprocess.check_output(['git', 'diff', '--name-only', base], cwd=root, text=True).splitlines()
assert changed == [path], changed
digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
print(json.dumps({'status': 'PASS_OBSERVATION_ONLY_BYTE_CHECK', 'base': base, 'only_changed_path': path,
    'original_statements_restored_byte_exact': True, 'original_body_sha256': digest(old_body),
    'second_case_byte_exact': True, 'second_case_sha256': digest(original[original.index(second):]),
    'unchanged_exact_paths': unchanged, 'no_new_wait_or_timeout_or_assertion': True}, indent=2))
