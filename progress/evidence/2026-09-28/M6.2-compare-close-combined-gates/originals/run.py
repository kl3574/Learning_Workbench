"""Fixed isolated combination gates; adapted from the prior combined runner."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, signal, subprocess, sys, time

root = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-active')
base = Path(__file__).resolve().parent
expected_head = '4442b3e8c85bd1eca75c4af1dc74dad7d1b6cd4a'
name = sys.argv[1]
commands = {
    'web': ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'test'],
    'web-lint': ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'lint'],
    'web-build': ['bash', 'scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'build'],
    'spec': ['.venv/bin/python', 'scripts/verify_spec.py'],
}
cmd = commands[name]
stage = base / name
stage.mkdir(exist_ok=False)

def now():
    return datetime.now(timezone.utc).isoformat()

def write(name, data):
    (stage / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)

def sources():
    head = git('rev-parse', 'HEAD').decode().strip()
    assert head == expected_head
    entries = {}
    for entry in git('ls-tree', '-rz', head).split(b'\0'):
        if not entry:
            continue
        metadata, path = entry.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        assert kind == 'blob'
        entries[path.decode()] = (mode, blob)
    rows = []
    for entry in git('ls-files', '--stage', '-z').split(b'\0'):
        if not entry:
            continue
        metadata, path = entry.split(b'\t', 1)
        mode, blob, index = metadata.decode().split()
        name = path.decode()
        if name.startswith('progress/'):
            continue
        assert index == '0' and entries[name] == (mode, blob)
        f = root / name
        data = os.readlink(f).encode() if f.is_symlink() else f.read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        rows.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                     'git_blob_sha1': blob, 'git_matches': actual == blob, 'git_mode': mode})
    return rows

head = git('rev-parse', 'HEAD').decode().strip()
before = sources()
write('inputs-before.json', before)
assert all(row['git_matches'] for row in before), 'Gate requires fixed committed bytes'
untracked = git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0')
assert not [p for p in untracked if p and not p.startswith(b'progress/')]
env = {'PATH': os.environ['PATH'], 'HOME': str(Path.home()), 'LANG': 'C.UTF-8', 'CI': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
start = now()
tick = time.monotonic()
timedout = False
with (stage / 'test.log').open('wb') as out:
    process = subprocess.Popen(cmd, cwd=root, env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    write('process.json', {'pid': process.pid, 'pgid': process.pid, 'started_at': start, 'root': str(root), 'command': cmd, 'source': head})
    try:
        exitcode = process.wait(timeout=1500)
    except subprocess.TimeoutExpired:
        timedout = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        exitcode = process.returncode
finish = now()
after = sources()
write('inputs-after.json', after)
log = (stage / 'test.log').read_bytes()
receipt = {'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'code_commit': head,
           'head_after': git('rev-parse', 'HEAD').decode().strip(), 'cwd': str(root), 'command': cmd,
           'start': start, 'finish': finish, 'seconds': time.monotonic() - tick, 'exit_code': exitcode,
           'timeout': timedout, 'source_count': len(before), 'source_unchanged': before == after,
           'all_source_matches_git_before': all(row['git_matches'] for row in before),
           'all_source_matches_git_after': all(row['git_matches'] for row in after),
           'log_bytes': len(log), 'log_sha256': hashlib.sha256(log).hexdigest()}
write('receipt.json', receipt)
print(json.dumps(receipt, indent=2))
print(log.decode(errors='replace')[-3500:])
sys.exit(0 if exitcode == 0 and before == after else 1)
