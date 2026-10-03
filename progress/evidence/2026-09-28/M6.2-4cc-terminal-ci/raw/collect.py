"""Single bounded terminal readback; no workflow rerun or repository mutation."""
from pathlib import Path
import concurrent.futures
import datetime
import hashlib
import json
import os
import subprocess
import time

C = Path(__file__).resolve().parent
OLD = C.parent/'m62-publication-4cc-ci-browser-diagnosis-v1'
REPO = 'repos/kl3574/Learning_Workbench'
ENV = {k:os.environ[k] for k in ['PATH','HOME','LANG','LC_ALL','XDG_CONFIG_HOME'] if k in os.environ}
RUNS = {'push':36386011041,'pull_request':36386016520}

def meta(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def write(name,raw):
    p=C/name
    p.parent.mkdir(parents=True,exist_ok=True)
    assert not p.exists(),name
    p.write_bytes(raw)

def fetch(name,endpoint):
    command=['gh','api',endpoint]
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
    try:
        result=subprocess.run(command,env=ENV,capture_output=True,timeout=35)
        out,err,code=result.stdout,result.stderr,result.returncode
    except subprocess.TimeoutExpired as e:
        out,err,code=e.stdout or b'',e.stderr or b'',124
    write(name,out);write(name+'.stderr',err)
    receipt={'command':command,'started_at':started,'seconds':time.monotonic()-clock,'exit_code':code,
             'stdout':meta(out),'stderr':meta(err),'driver':meta(Path(__file__).read_bytes())}
    write(name+'.receipt.json',(json.dumps(receipt,indent=2)+'\n').encode())
    assert code==0,(name,code)
    return {'path':name,**meta(out)}

def main():
    old_manifest=(OLD/'MANIFEST.json').read_bytes()
    assert meta(old_manifest)['sha256']=='9f60aaf81378fa671dbb3635ff60a6cb5528cf9fa105808f111fd803f5526288'
    entries=json.loads(old_manifest)['members']
    for entry in entries:
        assert meta((OLD/entry['path']).read_bytes())=={k:entry[k] for k in ['bytes','sha256']}
    copies=[]
    for p in sorted(OLD.rglob('*')):
        if p.is_file():
            relative=p.relative_to(OLD).as_posix();raw=p.read_bytes();name='browser-diagnosis/'+relative
            write(name,raw);copies.append({'original_cache':OLD.name,'original_path':relative,'copy':name,**meta(raw)})
    write('ORIGINAL_BROWSER_COPIES.json',(json.dumps(copies,indent=2)+'\n').encode())
    requests=[]
    for event,run in RUNS.items():
        for kind,suffix in [('run',''),('jobs','/jobs?per_page=100'),('artifacts','/artifacts?per_page=100')]:
            requests.append((f'terminal/{event}-{kind}.json',f'{REPO}/actions/runs/{run}{suffix}'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        metadata=list(pool.map(lambda pair:fetch(*pair),requests))
    logs=[]
    for event,run in RUNS.items():
        actual=json.loads((C/f'terminal/{event}-run.json').read_text())
        assert actual['id']==run and actual['head_sha']=='4cc4fd5c24fe135186147dfb86d3f071b26f4fb7'
        assert actual['status']=='completed' and actual['conclusion']=='failure' and actual['run_attempt']==1
        jobs=json.loads((C/f'terminal/{event}-jobs.json').read_text())['jobs']
        assert len(jobs)==6 and all(j['status']=='completed' for j in jobs)
        assert [(j['name'],j['conclusion']) for j in jobs if j['conclusion']!='success']==[('browser','failure')]
        for job in jobs:
            logs.append((f"logs/{event}-{job['name']}-{job['id']}.log",f"{REPO}/actions/jobs/{job['id']}/logs"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        downloaded=list(pool.map(lambda pair:fetch(*pair),logs))
    for event,name in [('push','push-browser-108811427645.log'),('pull_request','browser-108811444631.log')]:
        new=next((C/'logs').glob(event+'-browser-*.log'))
        assert new.read_bytes()==(OLD/name).read_bytes()
    write('COLLECTION.json',(json.dumps({'status':'PASS','metadata':metadata,'logs':downloaded,
          'old_frozen_members_verified':len(entries),'old_actual_files_copied':len(copies),
          'complete_job_logs':len(downloaded),'remote_mutations':0,'product_tests':0},indent=2)+'\n').encode())
    print(json.dumps({'status':'PASS','complete_job_logs':len(downloaded),'copied_raw_files':len(copies)}))

if __name__=='__main__':main()
