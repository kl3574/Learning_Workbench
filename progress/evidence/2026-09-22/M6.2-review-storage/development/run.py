from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, subprocess, sys, os
ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-review-storage-active')
CACHE=Path(__file__).parent

def snapshot():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    paths=subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    files={p:{'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),'bytes':(ROOT/p).stat().st_size} for p in sorted(set(paths)) if p and (ROOT/p).is_file()}
    return {'head':head,'status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'files':files}

def dump(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
stage=CACHE/sys.argv[1];stage.mkdir()
command=sys.argv[2:]
dump(stage/'before.json',snapshot())
start=datetime.now(timezone.utc).isoformat()
with (stage/'test.log').open('wb') as stream:
    result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
end=datetime.now(timezone.utc).isoformat()
dump(stage/'after.json',snapshot())
log=(stage/'test.log').read_bytes()
receipt={'command':command,'cwd':str(ROOT),'started_at':start,'ended_at':end,'exit_code':result.returncode,'log_bytes':len(log),'log_sha256':hashlib.sha256(log).hexdigest()}
dump(stage/'receipt.json',receipt)
print(json.dumps(receipt));print(log.decode(errors='replace')[-3500:])
sys.exit(result.returncode)
