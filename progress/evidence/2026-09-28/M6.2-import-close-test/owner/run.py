from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess, sys, time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent / 'm62-review-import-close-active'
stage = BASE / sys.argv[1]
stage.mkdir(exist_ok=False)
command = sys.argv[2:]

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def snapshot():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    blobs = {}
    for entry in subprocess.check_output(['git', 'ls-tree', '-rz', head], cwd=ROOT).split(b'\0'):
        if entry:
            metadata, name = entry.split(b'\t', 1)
            blobs[name.decode()] = metadata.decode().split()[2]
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    rows = []
    pool = BASE / 'source-pool'
    pool.mkdir(exist_ok=True)
    for name in sorted(set(names)):
        if not name or name.startswith('progress/'):
            continue
        path = ROOT / name
        if not path.exists():
            rows.append({'path': name, 'absent': True, 'git_blob': blobs.get(name)})
            continue
        raw = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
        digest = sha(raw)
        target = pool / digest
        if target.exists():
            assert target.read_bytes() == raw
        else:
            target.write_bytes(raw)
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        rows.append({'path': name, 'bytes': len(raw), 'sha256': digest, 'git_blob': blobs.get(name), 'git_matches': blob == blobs.get(name)})
    return {'head': head, 'files': rows}

before = snapshot()
(stage / 'inputs-before.json').write_text(json.dumps(before, indent=2) + '\n')
start = datetime.now(timezone.utc).isoformat()
tick = time.monotonic()
environment = {**os.environ, 'CI': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
with (stage / 'test.log').open('wb') as log:
    process = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
after = snapshot()
(stage / 'inputs-after.json').write_text(json.dumps(after, indent=2) + '\n')
raw = (stage / 'test.log').read_bytes()
receipt = {'command': command, 'cwd': str(ROOT), 'head': before['head'], 'started_at': start,
           'finished_at': datetime.now(timezone.utc).isoformat(), 'seconds': time.monotonic() - tick,
           'exit_code': process.returncode, 'source_count': len(before['files']), 'inputs_unchanged': before == after,
           'runner_sha256': sha(Path(__file__).read_bytes()), 'log_sha256': sha(raw)}
(stage / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
print(raw.decode(errors='replace')[-10000:])
sys.exit(process.returncode)
