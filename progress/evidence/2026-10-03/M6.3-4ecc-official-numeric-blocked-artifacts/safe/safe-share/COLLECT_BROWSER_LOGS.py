"""Read-only exact two successful browser job logs; raw output stays private."""
from pathlib import Path
import json,datetime,re
from bounded_api import bounded_get,sha
E=Path(__file__).resolve().parent
for run,job in [(37165685426,111327979162),(37165687627,111327985763)]:
 d=E/str(run)
 assert next(j for j in json.loads((d/'jobs.json').read_text())['jobs'] if j['id']==job)['name']=='browser'
 endpoint=f'repos/kl3574/Learning_Workbench/actions/jobs/{job}/logs'
 captured=datetime.datetime.now(datetime.timezone.utc).isoformat()
 raw,err=bounded_get(endpoint,15_000_000)
 with (d/'browser-private.log').open('xb') as f:f.write(raw)
 if err:(d/'browser-private.stderr').write_bytes(err)
 lines=raw.decode().splitlines();marker=next(i for i,l in enumerate(lines) if 'git log -1 --format=%H' in l);checkout=lines[marker+1].split()[-1]
 assert re.fullmatch('[a-f0-9]{40}',checkout)
 rec=dict(endpoint=endpoint,method='GET',captured_utc=captured,exit_code=0,job_id=job,run_id=run,bytes=len(raw),sha256=sha(raw),checkout_sha=checkout,checkout_line=marker+2)
 (d/'browser-log-invocation.json').write_text(json.dumps(rec,indent=2)+'\n')
 print(json.dumps(rec),flush=True)
for commit in sorted({json.loads((E/str(run)/'browser-log-invocation.json').read_text())['checkout_sha'] for run in [37165685426,37165687627]}):
 endpoint=f'repos/kl3574/Learning_Workbench/git/commits/{commit}';captured=datetime.datetime.now(datetime.timezone.utc).isoformat();raw,err=bounded_get(endpoint,2_000_000)
 v=json.loads(raw);assert v['sha']==commit
 with (E/(commit+'-commit.json')).open('xb') as f:f.write(raw)
 if err:(E/(commit+'-private.stderr')).write_bytes(err)
 (E/(commit+'-commit-invocation.json')).write_text(json.dumps(dict(endpoint=endpoint,method='GET',captured_utc=captured,exit_code=0,bytes=len(raw),sha256=sha(raw)),indent=2)+'\n')
 print(json.dumps(dict(commit=commit,tree=v['tree']['sha'],parents=[x['sha'] for x in v['parents']])),flush=True)
