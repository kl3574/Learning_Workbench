"""Bounded, append-only readback; all GitHub calls are GET, no rerun/dispatch."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib,json,re,subprocess,sys,os
from pathlib import Path
BASE=Path(__file__).resolve().parent
REPO='repos/kl3574/Learning_Workbench/'
HEAD='8701c8a04b654c2462e4311f0128201507ebaf7e'
RUNS={'push':36389800538,'pull_request':36389807970}
ENV={k:os.environ[k] for k in ['PATH','HOME','LANG','LC_ALL','XDG_CONFIG_HOME'] if k in os.environ}
ENV['PYTHONDONTWRITEBYTECODE']='1'
def sha(b):return hashlib.sha256(b).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
def dump(p,v):
    assert not p.exists(),str(p)
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def capture(name,endpoint,extension='.json'):
    target=BASE/(name+extension);assert not target.exists(),str(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    argv=['gh','api',REPO+endpoint];started=stamp();timeout=False
    try:
        proc=subprocess.run(argv,capture_output=True,timeout=35,env=ENV);out,err,code=proc.stdout,proc.stderr,proc.returncode
    except subprocess.TimeoutExpired as exc:
        out,err,code=exc.stdout or b'',exc.stderr or b'',124;timeout=True
    target.write_bytes(out);(BASE/(name+'.stderr')).write_bytes(err)
    receipt={'command':argv,'started_at':started,'finished_at':stamp(),'exit_code':code,'timeout_seconds':35,'timed_out':timeout,'stdout_file':str(target.relative_to(BASE)),'stdout_bytes':len(out),'stdout_sha256':sha(out),'stderr_sha256':sha(err),'reader_sha256':sha(Path(__file__).read_bytes())}
    dump(BASE/(name+'.receipt.json'),receipt)
    if code:return {'capture_failed':True,'exit_code':code,'receipt':name+'.receipt.json'}
    return json.loads(out) if extension=='.json' else receipt

def log_facts(path):
    lines=path.read_text(errors='replace').splitlines();facts={'path':str(path.relative_to(BASE)),'sha256':sha(path.read_bytes()),'checkout':[],'packages':[],'summaries':[],'failures':[]}
    for n,line in enumerate(lines):
        clean=re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',line)
        if 'git log -1 --format=%H' in clean and n+1<len(lines):
            candidate=lines[n+1].split()[-1]
            if re.fullmatch('[a-f0-9]{40}',candidate):facts['checkout'].append({'line':n+2,'sha':candidate})
        if re.search(r'\b(?:bubblewrap|apparmor|libapparmor1(?::amd64)?|libseccomp2(?::amd64)?)\t',clean):facts['packages'].append({'line':n+1,'text':clean})
        if re.search(r'\b\d+ (?:passed|failed)(?:,| in | \()',clean) or re.search(r'\b(?:Tests|Test Files)\s+\d+ passed',clean) or 'Success: no issues found' in clean or 'All checks passed!' in clean or 'staged/tracked files' in clean:facts['summaries'].append({'line':n+1,'text':clean})
        if re.search(r'##\[error\]|^.*FAILED |Error:|AssertionError|TimeoutError|\d+\) \[.*\].*›',clean):facts['failures'].append({'line':n+1,'text':clean})
    return facts

def main():
    label=sys.argv[1];assert re.fullmatch('[0-9a-z-]+',label)
    assert not (BASE/(label+'-summary.json')).exists()
    calls=[(event,kind,f'actions/runs/{identifier}'+tail) for event,identifier in RUNS.items() for kind,tail in [('run',''),('jobs','/jobs?per_page=100'),('artifacts','/artifacts?per_page=100')]]
    def get(c):
        event,kind,endpoint=c;return event,kind,capture(f'{label}-{event}-{kind}',endpoint)
    views={};errors=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for event,kind,result in pool.map(get,calls):
            if result.get('capture_failed'):errors.append({'event':event,'kind':kind,**result});continue
            if kind=='run':assert result['head_sha']==HEAD and result['id']==RUNS[event] and result['event']==event and result['run_attempt']==1
            views.setdefault(event,{})[kind]=result
    downloads=[]
    for event,view in views.items():
        for job in view.get('jobs',{}).get('jobs',[]):
            assert job['head_sha']==HEAD
            assert re.fullmatch('[A-Za-z0-9_-]+',job['name'])
            name=f"logs/{event}-{job['name']}-{job['id']}"
            if job['status']=='completed' and not (BASE/(name+'.log')).exists():downloads.append((name,f"actions/jobs/{job['id']}/logs",'.log'))
        for artifact in view.get('artifacts',{}).get('artifacts',[]):
            name=f"artifacts/{event}-{artifact['id']}"
            if not artifact['expired'] and not (BASE/(name+'.zip')).exists():downloads.append((name,f"actions/artifacts/{artifact['id']}/zip",'.zip'))
    with ThreadPoolExecutor(max_workers=4) as pool:acquired=list(pool.map(lambda x:capture(*x),downloads))
    summaries={}
    for event,view in views.items():
        run=view.get('run',{});summaries[event]={'run_id':RUNS[event],'head_sha':run.get('head_sha'),'status':run.get('status'),'conclusion':run.get('conclusion'),'jobs':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],'apt':next((s['conclusion'] for s in j['steps'] if s['name']=='Install fixed official Ubuntu document sandbox dependencies'),None),'running_steps':[s['name'] for s in j['steps'] if s['status']=='in_progress']} for j in view.get('jobs',{}).get('jobs',[])],'artifacts':[{'id':a['id'],'name':a['name'],'size_in_bytes':a['size_in_bytes'],'digest':a.get('digest')} for a in view.get('artifacts',{}).get('artifacts',[])]}
    facts=[log_facts(p) for p in sorted((BASE/'logs').glob('*.log'))] if (BASE/'logs').exists() else []
    result={'recorded_at':stamp(),'runs':summaries,'capture_errors':errors,'new_acquisitions':acquired,'log_facts':facts}
    dump(BASE/(label+'-summary.json'),result)
    print(json.dumps({'recorded_at':result['recorded_at'],'runs':summaries,'captured_logs':len(facts),'capture_errors':errors,'new_acquisition_errors':[x for x in acquired if x.get('capture_failed')]}))
if __name__=='__main__':main()
