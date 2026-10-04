"""Reproduce the safe numeric/path projection without printing original log lines."""
from pathlib import Path
import hashlib
import json
import re

p = Path(__file__).parent
d = json.loads((p / 'READBACK.json').read_text())
ansi = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
out = []
for r in d['logs']:
    raw = (p / r['raw_file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == r['raw_sha256']
    result = {k: r[k] for k in ['run_id', 'event', 'job_id', 'job_name', 'conclusion', 'raw_sha256', 'checkout_shas']}
    result.update(test_summaries=[], environment_skips=[], failed_tests=[])
    for i, line in enumerate(raw.decode(errors='replace').splitlines(), 1):
        line = ansi.sub('', line)
        counts = re.findall(r'\b(\d+) (passed|failed|skipped|deselected|errors?)\b', line)
        if counts:
            kind = 'test_files' if 'Test Files' in line else 'tests' if 'Tests' in line else 'pytest_or_playwright'
            duration = re.search(r'\bin ([0-9.]+)s\b', line)
            result['test_summaries'].append({'line': i, 'kind': kind,
                'counts': [{'n': int(n), 'outcome': s} for n, s in counts],
                'duration_seconds': float(duration.group(1)) if duration else None})
        if 'SKIPPED [' in line:
            locations = re.findall(r'(tests/[A-Za-z0-9_./-]+\.py):(\d+)', line)
            result['environment_skips'].append({'line': i,
                'locations': [{'path': x, 'line': int(n)} for x, n in locations],
                'blocked_environment': 'BLOCKED_ENVIRONMENT' in line})
        if re.search(r'\b\d+\) .*\.spec\.ts:', line):
            locations = re.findall(r'([A-Za-z0-9_./-]+\.spec\.ts):(\d+):(\d+)', line)
            result['failed_tests'].append({'line': i, 'locations': [
                {'path': x.split('/tests/')[-1], 'line': int(n), 'column': int(c)} for x, n, c in locations]})
    out.append(result)
assert out == json.loads((p / 'PARSED_LOGS.json').read_text())['jobs']
print(json.dumps({'status': 'PASS', 'logs_hashed_and_parsed': len(out), 'raw_logs_unchanged': True}))
