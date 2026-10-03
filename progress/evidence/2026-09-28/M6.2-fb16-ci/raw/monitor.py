"""One bounded read-only monitor; 150-second polling interval; no product actions."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,time
BASE=Path(__file__).resolve().parent
started=datetime.now(timezone.utc).isoformat()
for index in range(3,19):
    for _ in range(3):
        time.sleep(50)
        if (BASE/'STOP_MONITOR').exists():
            print(json.dumps({'monitor_stopped':True,'reason':'handoff stop file'}),flush=True);raise SystemExit(0)
    label=f'p{index:02}'
    result=subprocess.run(['python',str(BASE/'readback.py'),label],capture_output=True,timeout=240)
    (BASE/(label+'-monitor.stdout')).write_bytes(result.stdout)
    (BASE/(label+'-monitor.stderr')).write_bytes(result.stderr)
    print(result.stdout.decode(errors='replace'),flush=True)
    if result.returncode:
        print(json.dumps({'monitor_exit':result.returncode,'label':label}),flush=True);raise SystemExit(result.returncode)
    summary=json.loads((BASE/(label+'-summary.json')).read_bytes())
    if len(summary['runs'])==2 and all(r['status']=='completed' for r in summary['runs'].values()):
        final={'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),'terminal_poll':label,'monitor_status':'completed','pipeline_conclusions':{k:v['conclusion'] for k,v in summary['runs'].items()}}
        (BASE/'monitor-terminal.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(final),flush=True);break
else:
    print(json.dumps({'monitor_status':'poll_budget_exhausted','last_label':label}),flush=True)
