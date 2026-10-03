"""Local finalization of terminal CI raw originals, no tests or network."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

C=Path(__file__).resolve().parent
HEAD='4cc4fd5c24fe135186147dfb86d3f071b26f4fb7'
MERGE='538bf74da04fac1cdea69cc70e1416d54c5643cd'
TREE='7014f0f0abfe5f692141415752403922624e10f9'
PACKAGES={'apparmor':'5.0.2-0ubuntu1~26.04.1','bubblewrap':'0.11.1-1ubuntu0.3',
          'libapparmor1':'5.0.2-0ubuntu1~26.04.1','libseccomp2':'2.6.0-2ubuntu5'}

def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,value):
    path=C/name;assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

jobs=[];artifacts=[]
for event,checkout in [('push',HEAD),('pull_request',MERGE)]:
    run=json.loads((C/f'terminal/{event}-run.json').read_text())
    assert run['status']=='completed' and run['conclusion']=='failure'
    for job in json.loads((C/f'terminal/{event}-jobs.json').read_text())['jobs']:
        name=f"logs/{event}-{job['name']}-{job['id']}.log";raw=(C/name).read_bytes()
        receipt=json.loads((C/(name+'.receipt.json')).read_text())
        assert receipt['exit_code']==0 and receipt['stdout']=={'bytes':len(raw),'sha256':sha(raw)}
        lines=[re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',line) for line in raw.decode().splitlines()]
        marker=next(i for i,line in enumerate(lines) if '[command]/usr/bin/git log -1 --format=%H' in line)
        assert lines[marker+1].split()[-1]==checkout
        summaries=[];skip=[];installed={}
        for i,line in enumerate(lines,1):
            if re.search(r'\b\d+ (?:passed|failed|skipped)(?:,| in | \(|$)|\b(?:Tests|Test Files)\s+',line):
                summaries.append({'line':i,'text':line})
            if re.search(r'\b(?:SKIPPED|ENV_NOT_READY|ENVIRONMENT_NOT_READY)\b|numeric.*(?:skip|not.ready)|sandbox.*(?:skip|not.ready)',line,re.I):
                skip.append({'line':i,'text':line})
            for package,version in PACKAGES.items():
                if re.search(r'Z\s+'+re.escape(package)+r'\s+'+re.escape(version)+r'$',line):
                    installed[package]={'line':i,'version':version}
        apt=next((s['conclusion'] for s in job['steps'] if s['name']=='Install fixed official Ubuntu document sandbox dependencies'),None)
        if job['name'] in ['backend','integration','browser']:assert apt=='success' and len(installed)==4
        jobs.append({'event':event,'id':job['id'],'name':job['name'],'status':job['status'],'conclusion':job['conclusion'],
                     'started_at':job['started_at'],'completed_at':job['completed_at'],'log_path':name,'log_sha256':sha(raw),
                     'log_bytes':len(raw),'checkout':{'sha':checkout,'line':marker+2},'tree':TREE,
                     'apt_step':apt,'installed_packages':installed,'scope_summaries':summaries,
                     'environment_or_skip_evidence':skip,'actual_steps':job['steps']})
    remote=json.loads((C/f'terminal/{event}-artifacts.json').read_text())
    assert remote['total_count']==len(remote['artifacts'])==1
    artifact=remote['artifacts'][0]
    old='push-browser-10955211920.zip' if event=='push' else 'browser-10954533289.zip'
    raw=(C/'browser-diagnosis'/old).read_bytes()
    assert artifact['digest']=='sha256:'+sha(raw)
    target=C/f"artifacts/{event}-{artifact['id']}.zip";target.parent.mkdir(exist_ok=True);target.write_bytes(raw)
    members=[]
    with zipfile.ZipFile(target) as archive:
        for entry in archive.infolist():
            if entry.is_dir():continue
            assert not Path(entry.filename).is_absolute() and '..' not in Path(entry.filename).parts
            data=archive.read(entry);dest=C/'extracted'/target.stem/entry.filename
            dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(data)
            members.append({'path':entry.filename,'bytes':len(data),'sha256':sha(data)})
    artifacts.append({'event':event,'id':artifact['id'],'name':artifact['name'],'bytes':len(raw),'sha256':sha(raw),
                      'server_digest':artifact['digest'],'members':members})
assert len(jobs)==12 and sum(j['conclusion']=='failure' for j in jobs)==2
assert sum(len(j['installed_packages'])==4 for j in jobs)==6
save('FINAL_JOB_EVIDENCE.json',{'head':HEAD,'pr_actual_checkout':MERGE,'actual_tree':TREE,'jobs':jobs,'artifacts':artifacts,
    'warning':'Source-specific job scopes overlap; do not sum counts into a unique total. Both failures remain Tutor 5000ms assertions.'})
save('TASK_RECEIPT.json',{'status':'complete','head':HEAD,'pr_actual_checkout':MERGE,'actual_tree':TREE,
    'runs':{'push':36386011041,'pull_request':36386016520},'conclusions':{'push':'failure','pull_request':'failure'},
    'actual_job_logs':12,'apt_exact_installations':6,'failure_archives':2,'artifact_members':16,
    'failed_jobs':['push/browser','pull_request/browser'],'original_tutor_cause':'UNKNOWN',
    'rerun_or_dispatch':False,'remote_methods':['GET'],'product_tests_run_locally':False,
    'source_or_progress_modified':False,'scope':'4cc terminal CI; prior a944 and 4cc local PASS remain distinct.'})
for job in jobs:
    print(json.dumps({'event':job['event'],'name':job['name'],'conclusion':job['conclusion'],
                      'summaries':job['scope_summaries'][-4:],'skip':job['environment_or_skip_evidence'][-2:]},ensure_ascii=False))
