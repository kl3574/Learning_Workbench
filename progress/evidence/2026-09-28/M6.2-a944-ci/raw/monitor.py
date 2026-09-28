"""One read-only monitor, immediate initial poll then 150-second cadence."""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import subprocess
import time

BASE = Path(__file__).resolve().parent
started = datetime.now(timezone.utc).isoformat()
with (BASE / 'RUNNER.json').open('x') as stream:
    json.dump({'pid': os.getpid(), 'started_at': started, 'cadence_seconds': 150,
               'individual_sleep_seconds': 50, 'allowed_remote_methods': ['GET']}, stream)

for index in range(1, 25):
    if index > 1:
        for _ in range(3):
            time.sleep(50)
            if (BASE / 'STOP_MONITOR').exists():
                print(json.dumps({'monitor_stopped': True, 'reason': 'explicit handoff stop file'}), flush=True)
                raise SystemExit(0)
    label = f'p{index:02}'
    with (BASE / (label + '-monitor.stdout')).open('xb') as stdout, (BASE / (label + '-monitor.stderr')).open('xb') as stderr:
        proc = subprocess.Popen(['python', str(BASE / 'readback.py'), label], stdout=stdout, stderr=stderr)
        deadline = time.monotonic() + 240
        while proc.poll() is None:
            try:
                proc.wait(timeout=min(40, max(0.1, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                if time.monotonic() >= deadline:
                    proc.terminate()
                    proc.wait(timeout=5)
                    raise RuntimeError('read-only acquisition exceeded bounded deadline')
    print((BASE / (label + '-monitor.stdout')).read_text(), flush=True)
    if proc.returncode:
        print(json.dumps({'monitor_exit': proc.returncode, 'label': label}), flush=True)
        raise SystemExit(proc.returncode)
    summary = json.loads((BASE / (label + '-summary.json')).read_bytes())
    if len(summary['runs']) == 2 and all(r['status'] == 'completed' for r in summary['runs'].values()):
        final = {'started_at': started, 'completed_at': datetime.now(timezone.utc).isoformat(),
                 'terminal_poll': label, 'monitor_status': 'completed',
                 'pipeline_conclusions': {k: v['conclusion'] for k, v in summary['runs'].items()}}
        (BASE / 'monitor-terminal.json').write_text(json.dumps(final, indent=2) + '\n')
        print(json.dumps(final), flush=True)
        break
else:
    print(json.dumps({'monitor_status': 'poll_budget_exhausted', 'last_label': label}), flush=True)
