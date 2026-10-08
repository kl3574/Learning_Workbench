"""Official read-only CI metadata. No credentials/headers emitted."""
from pathlib import Path
import json,datetime
from bounded_api import bounded_get,sha
E=Path(__file__).resolve().parent
for run in [37165685426,37165687627]:
 d=E/str(run);d.mkdir(exist_ok=False)
 for name,tail in [('run',''),('jobs','/jobs?per_page=100'),('artifacts','/artifacts?per_page=100')]:
  endpoint=f'repos/kl3574/Learning_Workbench/actions/runs/{run}{tail}'
  now=datetime.datetime.now(datetime.timezone.utc).isoformat()
  raw,err=bounded_get(endpoint,2_000_000);json.loads(raw)
  (d/(name+'.json')).write_bytes(raw)
  if err:(d/(name+'-private-stderr')).write_bytes(err)
  (d/(name+'-invocation.json')).write_text(json.dumps(dict(endpoint=endpoint,method='GET',captured_utc=now,exit_code=0,bytes=len(raw),sha256=sha(raw)),indent=2)+'\n')
 m=json.loads((d/'run.json').read_bytes());j=json.loads((d/'jobs.json').read_bytes());a=json.loads((d/'artifacts.json').read_bytes())
 print(json.dumps(dict(run=run,head=m['head_sha'],status=m['status'],conclusion=m['conclusion'],jobs=[{'id':x['id'],'name':x['name'],'conclusion':x['conclusion']} for x in j['jobs']],artifacts=[{'id':x['id'],'name':x['name'],'size':x['size_in_bytes'],'digest':x['digest']} for x in a['artifacts']])),flush=True)
