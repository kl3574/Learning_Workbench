import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
BASE=Path(__file__).parent
ROOT=BASE.parent/'m62-general-draft-service-active'
name=sys.argv[1]; command=sys.argv[2:]; target=BASE/name; target.mkdir(mode=0o700)
pool=BASE/'source-pool';pool.mkdir(exist_ok=True)
def snap(label):
 names=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
 out={}
 for name in sorted(set(names)):
  if not name or name.startswith('progress/') or not (ROOT/name).is_file(): continue
  raw=(ROOT/name).read_bytes();digest=hashlib.sha256(raw).hexdigest();out[name]={'sha256':digest,'bytes':len(raw)}
  dst=pool/digest
  if not dst.exists():dst.write_bytes(raw)
  elif dst.read_bytes()!=raw:raise RuntimeError('source pool mismatch')
 (target/f'inputs-{label}.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');return out
before=snap('before');start=datetime.now(timezone.utc).isoformat();clock=time.monotonic();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
with (target/'run.log').open('wb') as log:result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
after=snap('after');raw=(target/'run.log').read_bytes()
receipt={'command':command,'cwd':str(ROOT),'actual_head':head,'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'seconds':time.monotonic()-clock,'exit_code':result.returncode,'log_sha256':hashlib.sha256(raw).hexdigest(),'log_bytes':len(raw),'input_count_before':len(before),'input_count_after':len(after),'unchanged':before==after,'changed_paths':sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))}
(target/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));sys.exit(result.returncode)
