from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import time

root = Path('$HOME/.cache/learning-workbench-acceptance/m63-bootstrap-independent-review-oct03')
dest = Path(__file__).parent
assert not (dest / 'before.json').exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
def inputs():
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    entries = {}
    for path in filter(None, paths):
        if path.startswith('progress/'):
            continue
        raw = (root / path).read_bytes()
        original = subprocess.check_output(['git', 'show', head + ':' + path], cwd=root)
        assert raw == original, path
        entries[path] = {'sha256': sha(raw), 'bytes': len(raw)}
    return {'head': head, 'count': len(entries), 'tracked': entries,
            'private_runner_sha256': sha(Path(__file__).read_bytes())}

before = inputs()
(dest / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
monotonic = time.monotonic()
command = ['uv', 'run', '--frozen', '--no-sync', 'pytest', 'tests/integration/test_backup_codex_control_history.py',
           '--tb=short', '--basetemp=' + str(dest / 'private-pytest'), '-o', 'cache_dir=' + str(dest / 'cache')]
result = subprocess.run(command, cwd=root, capture_output=True)
log = result.stdout + result.stderr
(dest / 'run.log').write_bytes(log)
after = inputs()
(dest / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
receipt = {'head': head, 'started': started, 'finished': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'duration_seconds': round(time.monotonic() - monotonic, 3), 'command': command,
           'exit_code': result.returncode, 'log_sha256': sha(log), 'inputs_unchanged': before == after,
           'input_count': before['count'], 'scope': 'Real backup CLI and synthetic Codex owner history. No actual Codex process/thread/model. Four history/authority cases. Not M7.1 restore acceptance; original complete gates retained.'}
(dest / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
raise SystemExit(result.returncode if before == after else 1)
