"""Record independent static gate logs and all current non-progress Git inputs."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

root=Path('[LOCAL_HOME]/.cache/learning-workbench-acceptance/m54-active')
base=Path(__file__).parent
commands=[('01-ruff',['.venv/bin/ruff','check','.']),('02-mypy',['.venv/bin/mypy']),
 ('03-spec',['.venv/bin/python','scripts/verify_spec.py']),
 ('04-web-lint',['bash','scripts/node.sh','npm','--prefix','apps/web','run','lint']),
 ('05-web-typecheck',['bash','scripts/node.sh','npm','--prefix','apps/web','run','typecheck'])]
def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def snapshot():
 listed=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=root).decode().split('\0')
 result=[]
 for name in sorted(set(x for x in listed if x and not x.startswith('progress/'))):
  p=root/name
  if p.is_symlink():
   b=os.readlink(p).encode();kind='symlink'
  elif p.is_file():b=p.read_bytes();kind='file'
  else:
   result.append({'path':name,'kind':'missing','bytes':None,'sha256':None});continue
  result.append({'path':name,'kind':kind,'bytes':len(b),'sha256':sha(b)})
 return {'scope':'git ls-files --cached --others --exclude-standard, excluding progress/**; includes tracked output images, generated files and untracked nonignored source',
         'files':result,'count':len(result),'aggregate_sha256':sha(json.dumps(result,sort_keys=True,separators=(',',':')).encode())}
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
results=[]
for name,cmd in commands:
 out=base/name;out.mkdir()
 git_before=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
 before=snapshot();write(out/'source-before.json',before)
 started=now();failure=None
 env=dict(os.environ,TMPDIR='[LOCAL_HOME]/.cache/lw-proof54',PYTHONDONTWRITEBYTECODE='1')
 with (out/'run.log').open('wb') as log:
  try:code=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
  except Exception as error:
   code=127;failure=type(error).__name__;log.write((failure+' while starting gate\n').encode())
 finished=now();after=snapshot();write(out/'source-after.json',after)
 git_after=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
 b={x['path']:x for x in before['files']};a={x['path']:x for x in after['files']}
 changes=[x for x in sorted(b.keys()|a.keys()) if b.get(x)!=a.get(x)]
 receipt={'gate':name,'command':cmd,'cwd':str(root),'git_before':git_before,'git_after':git_after,
 'started_at':started,'finished_at':finished,'exit_code':code,'driver_start_error':failure,
 'driver_sha256':sha(Path(__file__).read_bytes()),'log_sha256':sha((out/'run.log').read_bytes()),
 'source_before_sha256':sha((out/'source-before.json').read_bytes()),'source_after_sha256':sha((out/'source-after.json').read_bytes()),
 'source_before_count':before['count'],'source_after_count':after['count'],
 'source_before_aggregate':before['aggregate_sha256'],'source_after_aggregate':after['aggregate_sha256'],
 'source_inputs_unchanged':not changes,'changed_inputs':changes}
 write(out/'receipt.json',receipt)
 results.append({'gate':name,'exit_code':code,'source_inputs_unchanged':not changes,'receipt_sha256':sha((out/'receipt.json').read_bytes())})
 print(json.dumps(results[-1]),flush=True)
 print((out/'run.log').read_text(),flush=True)
write(base/'summary.json',{'gates':results,'scope':'These five static gates were actually run; no build, web unit, full Python or native suite.'})
sys.exit(0 if all(x['exit_code']==0 and x['source_inputs_unchanged'] for x in results) else 1)
