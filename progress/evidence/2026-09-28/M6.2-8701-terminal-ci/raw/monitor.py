"""One owner process, append-only 150-second GET cadence, no remote mutations."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

C=Path(__file__).resolve().parent
env={k:os.environ[k] for k in ['PATH','HOME','LANG','LC_ALL','XDG_CONFIG_HOME'] if k in os.environ}
env['PYTHONDONTWRITEBYTECODE']='1'
lock=C/'monitor-start.json'
assert not lock.exists()
lock.write_text(json.dumps({'pid':os.getpid(),'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'cadence_seconds':150,'max_polls':32,'head':'8701c8a04b654c2462e4311f0128201507ebaf7e',
    'runs':{'push':36389800538,'pull_request':36389807970}},indent=2)+'\n')
for index in range(1,33):
    label=f'p{index:02d}';start=time.monotonic()
    command=[sys.executable,str(C/'readback.py'),label]
    with (C/(label+'-monitor.stdout')).open('wb') as out,(C/(label+'-monitor.stderr')).open('wb') as err:
        result=subprocess.run(command,env=env,stdout=out,stderr=err)
    (C/(label+'-monitor.receipt.json')).write_text(json.dumps({'command':command,'exit_code':result.returncode,
        'seconds':time.monotonic()-start,'reader_sha256':hashlib.sha256((C/'readback.py').read_bytes()).hexdigest(),
        'monitor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
    if result.returncode:
        print(json.dumps({'poll':label,'local_readback_failed':result.returncode}),flush=True)
    else:
        summary=json.loads((C/(label+'-summary.json')).read_text())
        print(json.dumps({'poll':label,'runs':{k:{'status':v['status'],'conclusion':v['conclusion'],
            'completed_jobs':sum(j['status']=='completed' for j in v['jobs']),
            'failed_jobs':[j['name'] for j in v['jobs'] if j['conclusion']=='failure']} for k,v in summary['runs'].items()},
            'capture_errors':summary['capture_errors']}),flush=True)
        if len(summary['runs'])==2 and all(r['status']=='completed' for r in summary['runs'].values()):
            (C/'monitor-terminal.json').write_text(json.dumps({'status':'terminal_readback','terminal_poll':label,
                'head':'8701c8a04b654c2462e4311f0128201507ebaf7e','conclusions':{k:v['conclusion'] for k,v in summary['runs'].items()},
                'download_integrity_still_requires_final_audit':True},indent=2)+'\n')
            break
    if index==32:
        (C/'monitor-bounded-stop.json').write_text(json.dumps({'status':'bounded_poll_limit','last_poll':label})+'\n')
        break
    deadline=start+150
    while time.monotonic()<deadline:
        time.sleep(min(5,deadline-time.monotonic()))
