import hashlib,json,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
root=Path('WORKTREE')
base=Path(__file__).parent
stage=sys.argv[1]; command=sys.argv[2:]; out=base/stage; out.mkdir(exist_ok=False)
def digest(b): return hashlib.sha256(b).hexdigest()
def capture():
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    return [{'path':p,'bytes':len(b),'sha256':digest(b)} for p in paths if p and not p.startswith('progress/') for b in [(root/p).read_bytes()]]
def write(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
before=capture(); write(out/'inputs-before.json',before)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
started=datetime.now(timezone.utc).isoformat(); timer=time.monotonic()
with (out/'run.log').open('wb') as log:
    result=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
after=capture(); write(out/'inputs-after.json',after)
receipt={'command':command,'source_head':head,'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-timer,3),'exit_code':result.returncode,'source_count':len(before),'source_scope':'all tracked files except progress; external tools/dependencies/runtime not captured','inputs_unchanged':before==after,'before_sha256':digest((out/'inputs-before.json').read_bytes()),'after_sha256':digest((out/'inputs-after.json').read_bytes()),'log_sha256':digest((out/'run.log').read_bytes()),'runner_sha256':digest(Path(__file__).read_bytes())}
write(out/'receipt.json',receipt); print(json.dumps(receipt)); print((out/'run.log').read_text()[-1800:]); sys.exit(result.returncode)
