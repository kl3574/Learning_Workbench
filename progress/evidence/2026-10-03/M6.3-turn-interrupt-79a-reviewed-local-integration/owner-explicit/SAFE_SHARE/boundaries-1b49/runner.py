"""Private source-bound runner: no app imports and no environment capture."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-turn-interrupt-owner-oct04')
base=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-turn-interrupt-evidence-oct04')
stage=base/sys.argv[1]; stage.mkdir()
runner=Path(__file__).read_bytes(); (stage/'runner.py').write_bytes(runner)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
paths=[p for p in subprocess.check_output(['git','ls-files','-z'],cwd=root,text=True).split('\0') if p and not p.startswith('progress/')]
def manifest():
    items={}
    for p in paths:
        raw=(root/p).read_bytes(); git=subprocess.check_output(['git','show',head+':'+p],cwd=root)
        items[p]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'git_exact':raw==git}
    return items
before=manifest(); assert all(i['git_exact'] for i in before.values())
(stage/'inputs-before.json').write_text(json.dumps(before,indent=2)+'\n')
command=sys.argv[2:]
env=dict(os.environ); tmp=stage/'tmp'; tmp.mkdir(); env['TMPDIR']=str(tmp)
if 'pytest' in command: command += ['--basetemp='+str(tmp/'base'),'-o','cache_dir='+str(tmp/'cache'),'--tb=short']
start=datetime.datetime.now(datetime.UTC).isoformat(); timer=time.monotonic()
with (stage/'run.log').open('wb') as log: result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
end=datetime.datetime.now(datetime.UTC).isoformat(); elapsed=time.monotonic()-timer
after=manifest(); (stage/'inputs-after.json').write_text(json.dumps(after,indent=2)+'\n')
receipt={'head':head,'cwd':str(root),'command':command,'started_at':start,'ended_at':end,'elapsed_seconds':elapsed,'exit':result.returncode,'inputs_count':len(before),'git_exact':all(i['git_exact'] for i in after.values()),'unchanged':before==after,'runner_sha256':hashlib.sha256(runner).hexdigest(),'log_sha256':hashlib.sha256((stage/'run.log').read_bytes()).hexdigest()}
(stage/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt)); assert before==after
sys.exit(result.returncode)
