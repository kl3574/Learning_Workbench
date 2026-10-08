from pathlib import Path
import json,hashlib,datetime,subprocess
O=Path(__file__).resolve().parent
for run in [37241154917,37241158099]:
 stem='run-'+str(run)+'-artifacts-01';argv=['gh','api','repos/kl3574/Learning_Workbench/actions/runs/'+str(run)+'/artifacts?per_page=100']
 assert not (O/(stem+'-command.json')).exists()
 (O/(stem+'-command.json')).write_text(json.dumps({'argv':argv,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Read-only actual fixed original run artifact inventory; no rerun/cancel/dispatch'},indent=2)+'\n')
 x=subprocess.run(argv,capture_output=True);(O/(stem+'.stdout')).write_bytes(x.stdout);(O/(stem+'.stderr')).write_bytes(x.stderr)
 (O/(stem+'-receipt.json')).write_text(json.dumps({'exit_code':x.returncode,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stdout_sha256':hashlib.sha256(x.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(x.stderr).hexdigest()},indent=2)+'\n')
 assert x.returncode==0
 d=json.loads(x.stdout);print(json.dumps({'run':run,'total_count':d['total_count'],'artifacts':[{k:a.get(k) for k in ['id','name','size_in_bytes','digest','expired']} for a in d['artifacts']]}))
