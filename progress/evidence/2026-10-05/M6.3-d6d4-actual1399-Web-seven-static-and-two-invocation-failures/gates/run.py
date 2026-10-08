"""Fixed complete Git-input binding for ordinary HTTP and static gates only."""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

root = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
out = Path(__file__).parent / sys.argv[1]
command = sys.argv[2:]
assert command and not out.exists()
out.mkdir()
def sha(b):
    return hashlib.sha256(b).hexdigest()
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)
head = git('rev-parse', 'HEAD').decode().strip()
assert not git('status', '--porcelain')
def snapshot():
    entries = {}
    for record in git('ls-tree', '-r', '-z', head).split(b'\0'):
        if not record:
            continue
        meta, name = record.split(b'\t', 1)
        name = name.decode()
        if name.startswith('progress/'):
            continue
        mode, kind, oid = meta.split()
        assert kind == b'blob'
        data = (root / name).read_bytes()
        assert data == git('show', head + ':' + name), name
        entries[name] = {'git_blob': oid.decode(), 'git_mode': mode.decode(), 'git_type': kind.decode(), 'sha256': sha(data), 'bytes': len(data)}
    return {'head': head, 'count': len(entries), 'files': entries}
before = snapshot()
(out / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
(out / 'command.json').write_text(json.dumps({'command': command, 'cwd': str(root)}, indent=2) + '\n')
tmp = out / 'tmp'
tmp.mkdir(mode=0o700)
env = {**os.environ, 'TMPDIR': str(tmp)}
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
tick = time.monotonic()
with (out / 'run.log').open('wb') as log:
    process = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, env=env)
elapsed = time.monotonic() - tick
after = snapshot()
(out / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
assert before == after and git('rev-parse', 'HEAD').decode().strip() == head and not git('status', '--porcelain')
receipt = {'status': 'PASS' if process.returncode == 0 else 'ORIGINAL_GATE_FAIL_RETAINED',
           'head': head, 'command': command, 'started_at': start,
           'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'exit_code': process.returncode, 'elapsed_seconds': elapsed,
           'complete_nonprogress_git_inputs': before['count'], 'before_after_git_exact': True,
           'log_sha256': sha((out / 'run.log').read_bytes()),
           'boundary': 'Actual command defines scope: React/fetch/IndexedDB Web checks or static checks; no CLI/actual external model/network/host security probe. Integrated reviewed Artifact512/SSE95, AA/Tutor218/Artifact8f/Event80b and GenericApproval43 plus Review69 lifecycle. Original412 fullFAIL retained; d69 full133PASS qualified by 1521/1522 input continuity with only documentary .gitattributes exception. Client late-consumption coverage remains separate OPEN_EVIDENCE. No physical production tool or remote model execution is established. Gate scope is its command, not whole M6.3/AC21 acceptance; physical sandbox skipped items are not PASS. Runner is private tooling, maps bind all repository Git inputs.'}
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
raise SystemExit(process.returncode)
