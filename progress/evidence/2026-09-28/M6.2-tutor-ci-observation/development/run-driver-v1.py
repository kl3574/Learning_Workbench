import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
BASE=Path(__file__).parent
ROOT=BASE.parent/'m62-tutor-ci-observation-active'
name=sys.argv[1]; command=sys.argv[2:]; target=BASE/name; target.mkdir(mode=0o700)
def snap(label):
 names=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
 out={}
 for name in sorted(set(names)):
  if not name or name.startswith('progress/') or not (ROOT/name).is_file(): continue
  raw=(ROOT/name).read_bytes(); out[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  if label=='before' and (name.startswith('apps/web/src/features/tutor/') or name.startswith('tests/e2e/tutor') or name.startswith('tests/tutor') or name=='services/api/app/application/tutor_worker.py' or name.startswith('tests/integration/test_tutor_observation')):
   dst=target/'source'/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
 (target/f'inputs-{label}.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');return out
before=snap('before'); start=datetime.now(timezone.utc).isoformat(); clock=time.monotonic()
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
with (target/'run.log').open('wb') as log: result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
after=snap('after');raw=(target/'run.log').read_bytes()
receipt={'command':command,'cwd':str(ROOT),'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'seconds':time.monotonic()-clock,'exit_code':result.returncode,'log_sha256':hashlib.sha256(raw).hexdigest(),'log_bytes':len(raw),'input_count_before':len(before),'input_count_after':len(after),'unchanged':before==after,'changed_paths':sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))}
(target/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));sys.exit(result.returncode)
