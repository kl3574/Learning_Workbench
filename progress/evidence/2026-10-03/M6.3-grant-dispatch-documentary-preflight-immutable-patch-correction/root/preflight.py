import datetime
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

B = Path('$HOME/.cache/learning-workbench-acceptance')
R = B / 'm62-public-safe-oct02'
O = Path(__file__).parent
sha = lambda b: hashlib.sha256(b).hexdigest()
assert not (O / 'receipt.json').exists()

def run(name, command):
    result = subprocess.run(command, cwd=R, capture_output=True)
    (O / (name + '.log')).write_bytes(result.stdout + result.stderr)
    (O / (name + '.command.json')).write_text(json.dumps({'command': command, 'exit_code': result.returncode, 'stdout_sha256': sha(result.stdout), 'stderr_sha256': sha(result.stderr)}, indent=2) + '\n')
    return result

original = run('diff-check-original', ['git', 'diff', '--cached', '--check'])
assert original.returncode == 2
paths = sorted(set(re.findall(r'^(.*?):\d+: trailing whitespace\.$', original.stdout.decode(), re.M)))
assert paths and all(p.startswith('progress/evidence/2026-10-03/M6.3-') and p.endswith('.patch') for p in paths)
assert all(line in ('+ ', '') or re.match(r'^.*?:\d+: trailing whitespace\.$', line) for line in original.stdout.decode().splitlines())
attributes = R / '.gitattributes'
old = attributes.read_bytes()
(O / 'attributes-before.txt').write_bytes(old)
attributes.write_bytes(old + b'\n# Exact immutable reviewed patch context; preserve original evidence bytes.\n' + ''.join(p + ' -whitespace\n' for p in paths).encode())
assert run('stage-attributes', ['git', 'add', '--', '.gitattributes']).returncode == 0
assert run('diff-check-fixed', ['git', 'diff', '--cached', '--check']).returncode == 0
assert run('publication-scan', ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/check_publication.py']).returncode == 0
assert run('spec', ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/verify_spec.py']).returncode == 0
staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=R, text=True).splitlines()
assert all(p.startswith('progress/') or p == '.gitattributes' for p in staged)
receipt = {'status': 'DOCUMENTARY_STAGED_DIFF_AND_PUBLICATION_SPEC_PASS_ORIGINAL_PATCH_WHITESPACE_FAIL_RETAINED', 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_head': 'b34428ab5e9d99c5e04c886af445be73490171f2', 'staged_count': len(staged), 'original_diff_check_exit': original.returncode, 'exact_patch_whitespace_exemptions': paths, 'patch_bytes_unchanged': True, 'attributes_original_sha256': sha(old), 'attributes_new_sha256': sha(attributes.read_bytes()), 'boundary': 'Exact immutable patch context only; no broad patch exemption, no trimming evidence, no app behavior/spec/source push/GitHub merge/release/deploy/model change. This preflight precedes final evidence receipt packaging; final staged scan is separately required.'}
(O / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('public_package', B / 'm62-v313-pushed-progress-sync-oct03/package.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sync = m.package('M6.3-latest-local-grant-dispatch-full-cancel-Issue32-sync', [('sync', 'm63-grant-dispatch-ui-latest-Issue32-sync-oct04', ['sync.py', 'issue-body.md', 'issue-patch.invocation.json', 'readback.json'])], {'status': 'ACTUAL_1055_ISSUE32_BODY_ONLY_SYNC_VERIFIED', 'scope': 'Issue32 actual latest local b344 / old0dc fullPASS / UI1201/nativefullACKPASS update; body SHA4034f1f32f4fb1cba13409526622d448a694fed23f94f870504e97c5a2e7bdc8. Outside managed block and metadata unchanged; PR56 body/head untouched.', 'boundary': 'Latest b344 whole combined NOT_RUN at sync checkpoint; no sourcepush, GitHubmerge/release/deploy/model.'})
preflight = m.package('M6.3-grant-dispatch-documentary-preflight-immutable-patch-correction', [('root', O.name, ['preflight.py', 'receipt.json', 'diff-check-original.log', 'diff-check-original.command.json', 'diff-check-fixed.log', 'diff-check-fixed.command.json', 'publication-scan.log', 'publication-scan.command.json', 'spec.log', 'spec.command.json'])], {'status': 'DOCUMENTARY_PREFLIGHT_PASS_EXACT_PATCH_WHITESPACE_ORIGINAL_FAIL_RETAINED', 'scope': 'Exact immutable reviewed patch context produces actual diffcheck2; exact listed attributes exemptions only then diffcheck/publication/spec0. Original patch bytes unchanged.', 'boundary': 'Archival source only; final package staged scan occurs separately, not whole runtime/actual model/wholeM6.3 acceptance.'})
state = m.read_state()
next(t for t in state['tasks'] if t['id'] == 'M6.3')['evidence_paths'] += [sync, preflight]
state['task_sync'] = 'VERIFIED_ISSUE32_1055_BODY_ONLY_LATEST_COMBINED_NOT_RUN'
m.save(state)
assert run('stage-final', ['git', 'add', '--', 'progress', '.gitattributes']).returncode == 0
assert run('final-diff-check', ['git', 'diff', '--cached', '--check']).returncode == 0
assert run('final-publication-scan', ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/check_publication.py']).returncode == 0
assert run('final-spec', ['uv', 'run', '--frozen', '--no-sync', 'python', 'scripts/verify_spec.py']).returncode == 0
commit = run('commit', ['git', 'commit', '-m', 'docs(M6.3): record grant dispatch full cancel checks and preserved failures'])
assert commit.returncode == 0 and not subprocess.check_output(['git', 'status', '--porcelain'], cwd=R)
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
paths_after = subprocess.check_output(['git', 'diff', '--name-only', 'b34428ab5e9d99c5e04c886af445be73490171f2', head], cwd=R, text=True).splitlines()
assert all(p.startswith('progress/') or p == '.gitattributes' for p in paths_after)
(O / 'FINAL_COMMIT.json').write_text(json.dumps({'status': 'DOCUMENTARY_COMMIT_FINAL_STAGED_CHECKS_PASS_CLEAN', 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'head': head, 'previous_source': 'b34428ab5e9d99c5e04c886af445be73490171f2', 'changed_count': len(paths_after), 'only_nonprogress_change': '.gitattributes exact immutable patch context exemptions', 'source_push': False}, indent=2) + '\n')
print(json.dumps({'status': 'CHECKPOINT_COMMITTED_FINAL_CHECKS_PASS', 'head': head, 'files': len(paths_after), 'exact_patch_exemptions': len(paths)}))
