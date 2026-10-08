"""Self-bound, source-complete records for the isolated original selected gate."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys
import tarfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent / 'm63-authoring-bind5fb-locked-environment-oct05'
HEAD = '7c71dec8fdcddb7ff24dbd082b88401426de95ef'
ARCHIVE = OUT.parent / 'm62-public-safe-oct02/.toolchain/node-v24.21.0-linux-x64.tar.xz'
ARCHIVE_SHA = 'fd8e59d5a511510f6a298afb548f18c7d2b1be404d8b4a27d94fbe49f56cb2d6'
# Known public executable locations only; no inherited credential/config variables.
ENV = {'HOME': '$HOME', 'PATH': '$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8'}
SELECTED = ['authoring.spec.ts', 'authoring-groups.spec.ts']
HARNESSES = ['authoringRuntime.ts', 'ownedStartup.ts', 'ownedStartup.node.ts', 'ownedStartupBounds.node.ts']

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def put(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, env=ENV)

def snapshot():
    entries = []
    for row in git('ls-tree', '-r', '-z', 'HEAD').split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        mode, kind, blob = meta.decode().split()
        path = name.decode()
        if kind != 'blob' or path.startswith('progress/'):
            continue
        raw = (ROOT / path).read_bytes()
        original = subprocess.check_output(['git', 'cat-file', 'blob', blob], cwd=ROOT, env=ENV)
        entries.append({'path': path, 'mode': mode, 'git_blob': blob, 'bytes': len(raw), 'sha256': sha(raw), 'equals_git_blob_bytes': raw == original})
    return {'head': git('rev-parse', 'HEAD').decode().strip(), 'tree': git('rev-parse', 'HEAD^{tree}').decode().strip(), 'status_porcelain': git('status', '--porcelain').decode(), 'enumeration': 'All HEAD blobs except progress/; generated/derived files retained without another exclusion', 'file_count': len(entries), 'all_equal_git_blob_bytes': all(e['equals_git_blob_bytes'] for e in entries), 'files': entries}

def command(stage):
    if stage == 'setup':
        return ['make', 'setup']
    if stage == 'semantic':
        return ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'exec', '--', 'tsc', '--noEmit', '--strict', '--target', 'ES2022', '--module', 'ESNext', '--moduleResolution', 'bundler', '--allowImportingTsExtensions', '--skipLibCheck', '--types', 'node', '--typeRoots', str(ROOT / 'apps/web/node_modules/@types'), *[str(ROOT / 'tests/e2e' / name) for name in HARNESSES]]
    if stage == 'build':
        return ['make', 'build']
    if stage in ('list', 'browser'):
        argv = ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'test:e2e', '--', *SELECTED]
        return argv + ['--list'] if stage == 'list' else argv
    raise ValueError(stage)

stage = sys.argv[1]
directory = OUT / ('fixed-' + stage)
directory.mkdir(exist_ok=False)
put(directory / 'before.json', snapshot())
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert not git('status', '--porcelain')
if stage == 'setup':
    raw = ARCHIVE.read_bytes()
    assert len(raw) == 31890184 and sha(raw) == ARCHIVE_SHA
    toolchain = ROOT / '.toolchain'
    toolchain.mkdir(exist_ok=False)
    target = toolchain / ARCHIVE.name
    target.write_bytes(raw)
    with tarfile.open(target) as archive:
        archive.extractall(toolchain, filter='data')
    put(OUT / 'NODE_ARCHIVE_REUSE.json', {'source': str(ARCHIVE), 'bytes': len(raw), 'sha256': sha(raw), 'target': str(target), 'action': "Exact pinned public cache archive copied and extracted with filter='data'; no profile/credentials/full-gate environment copied"})
env = dict(ENV)
if stage in ('list', 'browser'):
    data = OUT / ('owned-fixed-' + stage + '-data')
    data.mkdir(exist_ok=False)
    output = OUT / ('owned-fixed-' + stage + '-results')
    cache = OUT / ('owned-fixed-' + stage + '-cache')
    temporary = OUT / ('owned-fixed-' + stage + '-tmp')
    cache.mkdir(exist_ok=False)
    temporary.mkdir(exist_ok=False)
    env.update({'LEARNING_E2E_DATA_DIR': str(data), 'LEARNING_E2E_OUTPUT_DIR': str(output), 'PWTEST_CACHE_DIR': str(cache), 'TMPDIR': str(temporary)})
argv = command(stage)
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
runner = Path(__file__).read_bytes()
put(directory / 'command.json', {'argv': argv, 'cwd': str(ROOT), 'environment': env, 'started_utc': started, 'source_head': HEAD, 'runner': str(Path(__file__).resolve()), 'runner_bytes': len(runner), 'runner_sha256': sha(runner), 'selection': SELECTED if stage in ('list', 'browser') else None, 'global_timeout_modified': False, 'retry_modified': False})
with (directory / 'run.log').open('wb') as log:
    result = subprocess.run(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
put(directory / 'after.json', snapshot())
raw = (directory / 'run.log').read_bytes()
before = (directory / 'before.json').read_bytes()
after = (directory / 'after.json').read_bytes()
put(directory / 'receipt.json', {'exit_code': result.returncode, 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'log_bytes': len(raw), 'log_sha256': sha(raw), 'runner_bytes': len(runner), 'runner_sha256': sha(runner), 'before_bytes': len(before), 'before_sha256': sha(before), 'after_bytes': len(after), 'after_sha256': sha(after), 'before_after_exact': before == after, 'source_head': HEAD, 'only_owned_local_loopback_runtime': stage == 'browser', 'actual_model_or_remote_mutation': False})
print(json.dumps({'stage': stage, 'exit_code': result.returncode, 'log_bytes': len(raw), 'log_sha256': sha(raw), 'before_after_exact': before == after}))
sys.exit(result.returncode)
