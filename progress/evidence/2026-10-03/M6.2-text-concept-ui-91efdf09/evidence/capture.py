import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-text-concepts-ui-oct03')
out = Path(__file__).resolve().parent / sys.argv[1]
out.mkdir(exist_ok=True)
command = sys.argv[2:]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def inputs():
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    names += subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=root).decode().split('\0')
    return [{'path': name, 'sha256': digest((root / name).read_bytes())} for name in sorted(set(names)) if name and (root / name).is_file()]

before = inputs()
(out / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
with (out / 'run.log').open('wb') as log:
    result = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
after = inputs()
(out / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
receipt = {'command': command, 'cwd': str(root), 'started_at': start, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exit_code': result.returncode, 'input_count': len(before), 'unchanged': before == after, 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip(), 'status': subprocess.check_output(['git', 'status', '--short'], cwd=root).decode(), 'log_sha256': digest((out / 'run.log').read_bytes()), 'before_sha256': digest((out / 'before.json').read_bytes()), 'after_sha256': digest((out / 'after.json').read_bytes())}
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'stage': out.name, 'exit_code': result.returncode, 'input_count': len(before), 'unchanged': before == after, 'log_sha256': receipt['log_sha256']}))
sys.exit(result.returncode)
