import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path(os.environ.get('TURN_TEST_SOURCE', '$HOME/.cache/learning-workbench-acceptance/m63-turn-preparation-owner-oct04'))
evidence=Path(__file__).parent
stage=evidence/sys.argv[1];stage.mkdir(exist_ok=True)
def source():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    entries=subprocess.check_output(['git','ls-files','-s','-z'],cwd=root).split(b'\0')
    rows={}
    for entry in entries:
        if not entry:continue
        meta,name=entry.split(b'\t');name=name.decode()
        if name.startswith('progress/'):continue
        mode,blob,_=meta.decode().split()
        actual=(root/name).read_bytes();expected=subprocess.check_output(['git','cat-file','blob',blob],cwd=root)
        rows[name]={'git_blob':blob,'sha256':hashlib.sha256(actual).hexdigest(),'git_sha256':hashlib.sha256(expected).hexdigest(),'size':len(actual),'equal':actual==expected}
    return {'head':head,'status':subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True),'count':len(rows),'inputs':rows,'all_exact':all(x['equal'] for x in rows.values())}
before=source();(stage/'before.json').write_text(json.dumps(before,indent=2)+'\n');assert before['all_exact'] and not before['status']
args=['$HOME/.local/bin/uv','run','--frozen','--no-sync','pytest',*sys.argv[2:],'--basetemp',str(stage/'basetemp'),'--tb=line','-q']
env=dict(os.environ);env['TMPDIR']=str(evidence/'tmp')
start=time.monotonic()
with (stage/'run.log').open('wb') as out:code=subprocess.call(args,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT)
after=source();(stage/'after.json').write_text(json.dumps(after,indent=2)+'\n')
(stage/'receipt.json').write_text(json.dumps({'command':args,'exit_code':code,'elapsed_seconds':time.monotonic()-start,'before_equals_after':before==after,'head':before['head'],'source_count':before['count']},indent=2)+'\n')
print(json.dumps({'exit':code,'source_equal':before==after,'count':before['count']}))
