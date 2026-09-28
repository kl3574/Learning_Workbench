"""Local-only derivation from original CI captures, safe for incomplete snapshots."""
from pathlib import Path, PurePosixPath
import hashlib,json,re,sys,zipfile
BASE=Path(__file__).resolve().parent
HEAD='fb16dcc3857830acc22677f83dbd285701bea202'
MERGE='74f76a4254d5a6dcd3e4df578b8cf3d5a64a78b3'
RUNS={'push':36371453103,'pull_request':36371456878}
PACKAGES={'bubblewrap':'0.11.1-1ubuntu0.3','apparmor':'5.0.2-0ubuntu1~26.04.1','libapparmor1:amd64':'5.0.2-0ubuntu1~26.04.1','libseccomp2:amd64':'2.6.0-2ubuntu5'}
JOBS={'backend','integration','browser','frontend','spec-contracts','security-publication'}
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    label=sys.argv[1];target=BASE/(label+'-audit.json');assert not target.exists()
    verified=[];acquisition_failures=[]
    for p in sorted(BASE.rglob('*.receipt.json')):
        r=json.loads(p.read_bytes());data=(BASE/r['stdout_file']).read_bytes();error=p.with_name(p.name.removesuffix('.receipt.json')+'.stderr').read_bytes()
        assert len(data)==r['stdout_bytes'] and sha(data)==r['stdout_sha256'] and sha(error)==r['stderr_sha256']
        assert r['reader_sha256']==sha((BASE/'readback.py').read_bytes())
        verified.append(str(p.relative_to(BASE)))
        if r['exit_code']!=0:acquisition_failures.append(str(p.relative_to(BASE)))
    source=json.loads((BASE/'source/verification.json').read_bytes());assert source['head']==HEAD and source['pr_actual_checkout']==MERGE and source['tree_equal'] and source['workflows_equal']
    runs={};apt_api=apt_log=completed=0
    for event,identifier in RUNS.items():
        run=json.loads((BASE/(label+'-'+event+'-run.json')).read_bytes());jobs=json.loads((BASE/(label+'-'+event+'-jobs.json')).read_bytes())['jobs']
        assert run['head_sha']==HEAD and run['id']==identifier and run['event']==event and run['run_attempt']==1
        assert len(jobs)==6 and {j['name'] for j in jobs}==JOBS
        out=[]
        for j in jobs:
            assert j['head_sha']==HEAD
            facts={'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],'log_status':'NOT_YET_AVAILABLE'}
            if j['name'] in {'backend','integration','browser'}:
                step=next(s for s in j['steps'] if s['name']=='Install fixed official Ubuntu document sandbox dependencies');facts['apt_step']=step['conclusion'];apt_api+=int(step['conclusion']=='success')
            p=BASE/'logs'/f"{event}-{j['name']}-{j['id']}.log"
            if p.exists():
                r=json.loads(p.with_suffix('.receipt.json').read_bytes())
                if r['exit_code']!=0:facts['log_status']='ACQUISITION_FAILED'
                else:
                    assert j['status']=='completed';completed+=1;facts['log_status']='CAPTURED';facts['log_sha256']=sha(p.read_bytes());facts['log_path']=str(p.relative_to(BASE))
                    lines=p.read_text(errors='replace').splitlines();pins=[];packages={};summaries=[];failures=[]
                    for n,line in enumerate(lines):
                        line=re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',line)
                        if 'git log -1 --format=%H' in line:
                            pin=lines[n+1].split()[-1];assert pin==({'push':HEAD,'pull_request':MERGE}[event]);pins.append({'line':n+2,'sha':pin})
                        for name,version in PACKAGES.items():
                            if name+'\t' in line:
                                assert line.endswith(name+'\t'+version);packages[name]={'version':version,'line':n+1}
                        if re.search(r'\b\d+ (?:passed|failed)(?:,| in | \()',line) or re.search(r'\b(?:Tests|Test Files)\s+\d+ passed',line) or 'Success: no issues found' in line or 'All checks passed!' in line or 'staged/tracked files' in line:summaries.append({'line':n+1,'text':line})
                        if '##[error]' in line or re.search(r'\bFAILED |Error:|AssertionError|TimeoutError',line):failures.append({'line':n+1,'text':line})
                    assert len(pins)==1;facts.update(checkout=pins[0],installed_packages=packages,summaries=summaries,failures=failures)
                    if j['name'] in {'backend','integration','browser'} and facts.get('apt_step')=='success':assert set(packages)==set(PACKAGES);apt_log+=1
            out.append(facts)
        runs[event]={'run_id':identifier,'head_sha':HEAD,'status':run['status'],'conclusion':run['conclusion'],'jobs':out}
    artifacts=[]
    for p in sorted((BASE/'artifacts').glob('*.zip')) if (BASE/'artifacts').exists() else []:
        receipt=json.loads(p.with_suffix('.receipt.json').read_bytes());entry={'path':str(p.relative_to(BASE)),'sha256':sha(p.read_bytes()),'acquisition_exit_code':receipt['exit_code'],'members':[]}
        if receipt['exit_code']==0:
            with zipfile.ZipFile(p) as z:
                for info in z.infolist():
                    name=PurePosixPath(info.filename)
                    assert not name.is_absolute() and '..' not in name.parts and '\\' not in info.filename
                    assert info.file_size<=20_000_000
                    if info.is_dir():continue
                    assert name.name=='error-context.md' or name.name.startswith('test-failed') and name.suffix=='.png' or name.name in {'reader-load-diagnostic.json','tutor-completion-diagnostic.json'}
                    b=z.read(info);entry['members'].append({'path':info.filename,'bytes':len(b),'sha256':sha(b)})
        artifacts.append(entry)
    out={'scope':'Read-only verification of original API/log/archive bytes. No product tests or CI actions.','poll':label,'head':HEAD,'pr_actual_checkout':MERGE,'source':source,'verified_acquisition_receipts':verified,'acquisition_failures':acquisition_failures,'apt_step_success_count':apt_api,'apt_exact_package_log_count':apt_log,'completed_logs_verified':completed,'runs':runs,'artifacts':artifacts}
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'audit':target.name,'sha256':sha(target.read_bytes()),'completed_logs':completed,'apt_step_success':apt_api,'apt_exact_logs':apt_log,'artifacts':len(artifacts),'acquisition_failures':acquisition_failures}))
if __name__=='__main__':main()
