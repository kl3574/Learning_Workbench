"""Audit only after the single 8701 monitor reaches both actual terminal states."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

C=Path(__file__).resolve().parent
HEAD='8701c8a04b654c2462e4311f0128201507ebaf7e'
PACKAGES={'apparmor':'5.0.2-0ubuntu1~26.04.1','bubblewrap':'0.11.1-1ubuntu0.3',
          'libapparmor1':'5.0.2-0ubuntu1~26.04.1','libseccomp2':'2.6.0-2ubuntu5'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_text())
def write(name,value):
    p=C/name;assert not p.exists();p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def main():
    terminal=read(C/'monitor-terminal.json');label=terminal['terminal_poll']
    assert terminal['head']==HEAD and terminal['status']=='terminal_readback'
    binding=read(C/'checkout-tree-binding.json')
    checkouts={row['event']:row['sha'] for row in binding['actual_checkouts']}
    tree=binding['local_public_head_tree'];jobs=[];artifacts=[];runs={}
    for event,run_id in [('push',36389800538),('pull_request',36389807970)]:
        run=read(C/f'{label}-{event}-run.json')
        assert run['status']=='completed' and run['head_sha']==HEAD and run['id']==run_id and run['run_attempt']==1
        runs[event]={'id':run_id,'status':run['status'],'conclusion':run['conclusion'],'head':HEAD,
                     'actual_checkout':checkouts[event],'tree':tree}
        remote_jobs=read(C/f'{label}-{event}-jobs.json')['jobs']
        assert len(remote_jobs)==6 and all(j['status']=='completed' for j in remote_jobs)
        for job in remote_jobs:
            name=f"logs/{event}-{job['name']}-{job['id']}";raw=(C/(name+'.log')).read_bytes()
            receipt=read(C/(name+'.receipt.json'))
            assert receipt['exit_code']==0 and receipt['stdout_bytes']==len(raw) and receipt['stdout_sha256']==sha(raw)
            assert sha((C/(name+'.stderr')).read_bytes())==receipt['stderr_sha256']
            lines=[re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',line) for line in raw.decode().splitlines()]
            marker=next(i for i,line in enumerate(lines) if '[command]/usr/bin/git log -1 --format=%H' in line)
            assert lines[marker+1].split()[-1]==checkouts[event]
            summaries=[];skip=[];installed={};failures=[]
            for i,line in enumerate(lines,1):
                if re.search(r'\b\d+ (?:passed|failed|skipped)(?:,| in | \(|$)|\b(?:Tests|Test Files)\s+|PASS: scanned|Success: no issues|All checks passed!',line):
                    summaries.append({'line':i,'text':line})
                if re.search(r'\b(?:SKIPPED|ENV_NOT_READY|ENVIRONMENT_NOT_READY)\b|numeric.*(?:skip|not.ready)|sandbox.*(?:skip|not.ready)',line,re.I):
                    skip.append({'line':i,'text':line})
                if re.search(r'##\[error\]|Error:|AssertionError|TimeoutError|\bFAILED ',line):
                    failures.append({'line':i,'text':line})
                for package,version in PACKAGES.items():
                    if re.search(r'Z\s+'+re.escape(package)+r'(?::amd64)?\s+'+re.escape(version)+r'$',line):
                        installed[package]={'line':i,'version':version}
            apt=next((s['conclusion'] for s in job['steps'] if s['name']=='Install fixed official Ubuntu document sandbox dependencies'),None)
            jobs.append({'event':event,'id':job['id'],'name':job['name'],'status':job['status'],'conclusion':job['conclusion'],
                'started_at':job['started_at'],'completed_at':job['completed_at'],'log_path':name+'.log','log_sha256':sha(raw),'log_bytes':len(raw),
                'checkout':{'sha':checkouts[event],'line':marker+2},'tree':tree,'apt_step':apt,'installed_packages':installed,
                'scope_summaries':summaries,'environment_or_skip_evidence':skip,'failure_lines':failures,'actual_steps':job['steps']})
        remote=read(C/f'{label}-{event}-artifacts.json')
        assert remote['total_count']==len(remote['artifacts'])
        for artifact in remote['artifacts']:
            assert not artifact['expired']
            name=f"artifacts/{event}-{artifact['id']}";raw=(C/(name+'.zip')).read_bytes();receipt=read(C/(name+'.receipt.json'))
            assert receipt['exit_code']==0 and receipt['stdout_sha256']==sha(raw) and artifact['digest']=='sha256:'+sha(raw)
            members=[]
            with zipfile.ZipFile(C/(name+'.zip')) as archive:
                for entry in archive.infolist():
                    path=Path(entry.filename)
                    assert not path.is_absolute() and '..' not in path.parts
                    assert (entry.external_attr>>16)&0o170000!=0o120000 and entry.file_size<=25_000_000
                    if entry.is_dir():continue
                    data=archive.read(entry);dest=C/'extracted'/Path(name).name/path
                    dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(data)
                    members.append({'path':entry.filename,'bytes':len(data),'sha256':sha(data)})
            artifacts.append({'event':event,'id':artifact['id'],'name':artifact['name'],'bytes':len(raw),'sha256':sha(raw),
                'server_digest':artifact['digest'],'members':members})
    write('FINAL_JOB_EVIDENCE.json',{'head':HEAD,'pr_actual_checkout':checkouts['pull_request'],'actual_tree':tree,
        'terminal_poll':label,'runs':runs,'jobs':jobs,'artifacts':artifacts,
        'warning':'Actual 8701-only CI scopes overlap. Do not sum pass counts or substitute earlier 4cc/a944 outcomes.'})
    write('TASK_RECEIPT.json',{'status':'terminal-collected-awaiting-bounded-analysis-and-public-packaging','head':HEAD,
        'runs':runs,'actual_job_logs':len(jobs),'failed_jobs':[j['event']+'/'+j['name'] for j in jobs if j['conclusion']=='failure'],
        'apt_exact_installations':sum(len(j['installed_packages'])==4 for j in jobs),'failure_archives':len(artifacts),
        'artifact_members':sum(len(a['members']) for a in artifacts),'product_tests_run_locally':False,
        'rerun_or_dispatch':False,'source_or_progress_modified':False,'remote_methods':['GET']})
    print(json.dumps({'runs':runs,'logs':len(jobs),'artifacts':len(artifacts),
        'failures':[j['event']+'/'+j['name'] for j in jobs if j['conclusion']=='failure']}))

if __name__=='__main__':main()
