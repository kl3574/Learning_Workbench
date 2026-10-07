"""One saved read-only observation of actual original CI events."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

out=Path(__file__).parent
head='079a008cf88b37e4517cb391503a1e7393ccf374'
sha=lambda b:hashlib.sha256(b).hexdigest()
existing=list(out.glob('*-SNAPSHOT.json'))
sequence=max([int(p.name.split('-')[0]) for p in existing]+[0])+1
def save(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def api(label,path):
    stem=f'{sequence:02d}-'+label
    assert not (out/(stem+'-command.json')).exists()
    save(stem+'-command.json',{'argv':['gh','api',path],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    r=subprocess.run(['gh','api',path],capture_output=True)
    (out/(stem+'.stdout')).write_bytes(r.stdout);(out/(stem+'.stderr')).write_bytes(r.stderr)
    save(stem+'-receipt.json',{'exit_code':r.returncode,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'stdout_sha256':sha(r.stdout),'stderr_sha256':sha(r.stderr)})
    assert r.returncode==0
    return json.loads(r.stdout)
data=api('runs','repos/kl3574/Learning_Workbench/actions/runs?head_sha='+head+'&per_page=100')
runs=[r for r in data['workflow_runs'] if r['head_sha']==head and r['event'] in ['push','pull_request'] and r['name']=='Implemented baseline checks']
rows=[]
for r in runs:
    jobs=api('jobs-'+str(r['id']),'repos/kl3574/Learning_Workbench/actions/runs/'+str(r['id'])+'/jobs?per_page=100')
    rows.append({'id':r['id'],'event':r['event'],'head_sha':r['head_sha'],'status':r['status'],
      'conclusion':r['conclusion'],'run_attempt':r['run_attempt'],'html_url':r['html_url'],
      'created_at':r['created_at'],'updated_at':r['updated_at'],
      'jobs':[{k:j[k] for k in ['id','name','status','conclusion','started_at','completed_at']} for j in jobs['jobs']]})
save(f'{sequence:02d}-SNAPSHOT.json',{'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source':head,'sequence':sequence,'actual_events':rows,'actual_event_count':len(rows),
 'status':'ACTUAL_EVENTS_SNAPSHOT' if rows else 'NO_MATCHING_EVENTS_IN_THIS_ACTUAL_RESPONSE',
 'wholeM6_3':'NOT_ACCEPTED','actual_model_calls':0,'rerun_cancel_or_remote_mutation':False})
print(json.dumps({'sequence':sequence,'events':[{'id':r['id'],'event':r['event'],'status':r['status'],'conclusion':r['conclusion'],
 'jobs':[{'name':j['name'],'status':j['status'],'conclusion':j['conclusion']} for j in r['jobs']]} for r in rows]},ensure_ascii=False))
