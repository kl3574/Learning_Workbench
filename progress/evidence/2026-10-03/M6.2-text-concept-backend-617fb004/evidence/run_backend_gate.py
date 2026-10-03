from pathlib import Path
import hashlib
import json
import subprocess
import time

ROOT = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-text-concept-retention-oct03')
OUT = Path(__file__).resolve().parent
PYTHON = '<LOCAL_HOME>/Desktop/learning/Learning_Workbench/.venv/bin/python'


def inventory():
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    return {name: {'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), 'bytes': (ROOT / name).stat().st_size}
            for name in names if name and not name.startswith('progress/')}


before = inventory()
source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert source == '617fb0045383c868e07cdf9a76428b4214cbd4fa'
(OUT / 'fixed-backend-inputs-before.json').write_text(json.dumps({'source_commit': source,
    'scope': 'All git-tracked files except progress/; no ignored toolchain/cache/temporary DB files.',
    'files': before}, indent=2) + '\n')
tests = sorted({str(p.relative_to(ROOT)) for pattern in [
    'tests/contract/test_draft_edit*.py', 'tests/integration/test_draft_edit*.py',
    'tests/integration/test_edit_publication*.py', 'tests/integration/test_content_restore_http.py',
    'tests/integration/test_content_repository.py', 'tests/integration/test_content_http.py'] for p in ROOT.glob(pattern)})
cmd = [PYTHON, '-m', 'pytest', *tests, '--tb=short', '-q',
       '--basetemp=' + str(OUT / 'fixed-backend-tmp'), '-o', 'cache_dir=' + str(OUT / 'pytest-cache')]
started = time.time()
with (OUT / '12-fixed-backend-related.log').open('wb') as log:
    result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
after = inventory()
(OUT / 'fixed-backend-inputs-after.json').write_text(json.dumps({'source_commit': source,
    'files': after, 'unchanged': before == after}, indent=2) + '\n')
(OUT / 'fixed-backend-gate.json').write_text(json.dumps({'source_commit': source, 'command': cmd,
    'cwd': str(ROOT), 'exit_code': result.returncode, 'elapsed_seconds': time.time() - started,
    'input_count': len(before), 'inputs_unchanged': before == after,
    'log': '12-fixed-backend-related.log', 'tests': tests}, indent=2) + '\n')
print(json.dumps({'exit_code': result.returncode, 'input_count': len(before), 'unchanged': before == after}))
raise SystemExit(result.returncode or int(before != after))
