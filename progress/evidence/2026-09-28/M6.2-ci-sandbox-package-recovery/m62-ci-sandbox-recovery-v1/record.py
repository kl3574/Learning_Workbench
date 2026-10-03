import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

BASE = Path(__file__).resolve().parent
TREE = BASE.parent / 'm62-ci-sandbox-recovery-active'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def inputs():
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=TREE).decode().split('\0')
    return {name: sha((TREE / name).read_bytes()) for name in names if name and (TREE / name).is_file()}

parser = argparse.ArgumentParser()
parser.add_argument('stage')
parser.add_argument('--apt', action='store_true')
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command[1:] if args.command[:1] == ['--'] else args.command
if not command:
    raise SystemExit('command required')
prefix = BASE / args.stage
if prefix.with_suffix('.receipt.json').exists():
    raise SystemExit('refusing to overwrite stage')
environment = os.environ.copy()
if args.apt:
    environment['APT_CONFIG'] = str(BASE / 'apt/etc/apt.conf')
before = inputs()
prefix.with_suffix('.before.json').write_text(json.dumps(before, indent=2) + '\n')
started_at = datetime.now(timezone.utc).isoformat()
started = time.monotonic()
with prefix.with_suffix('.log').open('wb') as log:
    process = subprocess.run(command, cwd=TREE, env=environment, stdout=log, stderr=subprocess.STDOUT)
elapsed = time.monotonic() - started
after = inputs()
prefix.with_suffix('.after.json').write_text(json.dumps(after, indent=2) + '\n')
receipt = {
    'stage': args.stage, 'command': command, 'cwd': str(TREE),
    'environment_override': {'APT_CONFIG': environment['APT_CONFIG']} if args.apt else {},
    'started_at': started_at, 'finished_at': datetime.now(timezone.utc).isoformat(),
    'elapsed_seconds': elapsed, 'exit_code': process.returncode,
    'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=TREE).decode().strip(),
    'before_sha256': sha(prefix.with_suffix('.before.json').read_bytes()),
    'after_sha256': sha(prefix.with_suffix('.after.json').read_bytes()),
    'source_inputs_unchanged': before == after,
    'input_count': len(before), 'log_sha256': sha(prefix.with_suffix('.log').read_bytes()),
    'recorder_sha256': sha(Path(__file__).read_bytes()),
}
prefix.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
raise SystemExit(process.returncode)
