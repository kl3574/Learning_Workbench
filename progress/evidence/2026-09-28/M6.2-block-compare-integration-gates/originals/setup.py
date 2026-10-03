from pathlib import Path
import datetime, hashlib, json, os, subprocess

BASE = Path(__file__).resolve().parent
TREE = BASE.parent / 'm62-block-compare-integration-active'
DONOR = BASE.parent / 'm62-active'
GIT_CONTEXT = BASE.parent / 'm62-block-version-compare-active'
BASE_COMMIT = 'a944ebfbdb835a731393977a606db5b473846e98'
OWNER = '05aa1af2fd000654b0d7b62e5eae32998c81d43f'
BRANCH = 'test/M6.2-block-compare-integration'
assert not TREE.exists()
log = []

def run(argv, cwd):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    log.append({'command': argv, 'cwd': str(cwd), 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
    (BASE / 'setup-commands.json').write_text(json.dumps(log, indent=2) + '\n')
    assert result.returncode == 0, log[-1]
    return result.stdout.strip()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def protected():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=DONOR, text=True).strip()
    index = Path(subprocess.check_output(['git', 'rev-parse', '--git-path', 'index'], cwd=DONOR, text=True).strip())
    return {'head': head, 'index_sha256': sha(index.read_bytes()), 'status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=DONOR, text=True)}

before = protected()
assert before['head'] == BASE_COMMIT and before['status'] == ''
(BASE / 'protected-main-before.json').write_text(json.dumps(before, indent=2) + '\n')
run(['git', 'worktree', 'add', '-b', BRANCH, str(TREE), BASE_COMMIT], GIT_CONTEXT)
run(['git', 'cherry-pick', 'b20f4aa9110829cf096bcae21e980e95b358a048'], TREE)
run(['git', 'cherry-pick', OWNER], TREE)
head = run(['git', 'rev-parse', 'HEAD'], TREE)
changed = run(['git', 'diff', '--name-only', BASE_COMMIT, head], TREE).splitlines()
expected = run(['git', 'diff', '--name-only', '833f0a84168638ba5ce421c70cd2f20a71e45e48', OWNER], TREE).splitlines()
assert changed == expected and len(changed) == 12
for path in changed:
    assert subprocess.check_output(['git', 'show', head + ':' + path], cwd=TREE) == subprocess.check_output(['git', 'show', OWNER + ':' + path], cwd=TREE)
links = []
assert (TREE / 'apps/web/package-lock.json').read_bytes() == (DONOR / 'apps/web/package-lock.json').read_bytes()
assert (TREE / 'apps/web/package.json').read_bytes() == (DONOR / 'apps/web/package.json').read_bytes()
assert (TREE / 'uv.lock').read_bytes() == (DONOR / 'uv.lock').read_bytes()
for name in ['.venv', '.toolchain', 'apps/web/node_modules']:
    destination = TREE / name
    assert not destination.exists() and not destination.is_symlink()
    target = (DONOR / name).resolve(strict=True)
    destination.symlink_to(target, target_is_directory=True)
    links.append({'path': name, 'target': str(target)})
versions = {name: run(cmd, TREE) for name, cmd in {
    'node': ['bash', 'scripts/node.sh', 'node', '--version'],
    'npm': ['bash', 'scripts/node.sh', 'npm', '--version'],
    'python': ['.venv/bin/python', '--version'],
}.items()}
assert run(['git', 'status', '--porcelain'], TREE) == ''
after = protected()
assert after == before
(BASE / 'protected-main-after-setup.json').write_text(json.dumps(after, indent=2) + '\n')
receipt = {'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'base_commit': BASE_COMMIT, 'owner_source': OWNER, 'combination_commit': head, 'branch': BRANCH,
           'changed_paths': changed, 'links': links, 'versions': versions, 'package_lock_sha256': sha((TREE / 'apps/web/package-lock.json').read_bytes()),
           'uv_lock_sha256': sha((TREE / 'uv.lock').read_bytes()), 'main_head_index_status_unchanged': True, 'native_requested': False, 'backend_requested': False}
(BASE / 'SETUP.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
