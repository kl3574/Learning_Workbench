from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,subprocess,sys,time
T=Path('$HOME/.cache/learning-workbench-acceptance/m63-capabilities-combined-oct03')
P=Path(__file__).parent
HEAD='ad49490e78c21174349595da8090c6c2b445bce9'
commands={
 'python':['uv','run','--frozen','--no-sync','pytest','--tb=short','--basetemp=$HOME/.cache/lw-m63-ad494/pytest','-o','cache_dir='+str(P/'pytest-cache')],
 'web':['bash','scripts/node.sh','npm','--prefix','apps/web','run','test'],
 'strict':['bash','scripts/node.sh','npm','--prefix','apps/web','run','lint'],
 'build':['bash','scripts/node.sh','npm','--prefix','apps/web','run','build'],
 'ruff':['uv','run','--frozen','--no-sync','ruff','check','.'],
 'mypy':['uv','run','--frozen','--no-sync','mypy','--cache-dir',str(P/'mypy-cache')],
 'verify':['uv','run','--frozen','--no-sync','python','scripts/verify_spec.py'],
}
def sha(data): return hashlib.sha256(data).hexdigest()
def capture(name):
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=T,text=True).strip()==HEAD
 items={}
 for name_ in subprocess.check_output(['git','ls-files','-z'],cwd=T).decode().split('\0'):
  if not name_ or name_.startswith('progress/'): continue
  data=(T/name_).read_bytes(); expected=subprocess.check_output(['git','show',HEAD+':'+name_],cwd=T)
  assert data==expected,name_
  items[name_]={'sha256':sha(data),'bytes':len(data)}
 data={'head':HEAD,'count':len(items),'scope':'All tracked nonprogress engineering inputs match fixed Git bytes; progress/, ignored installed tools, caches, runtime and build output excluded. Actual private runner below, no private product probe.','tracked':items,'private':{'run_gates.py':{'sha256':sha(Path(__file__).read_bytes()),'bytes':Path(__file__).stat().st_size}}}
 (P/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n'); return data
for name in sys.argv[1:]:
 before=capture(name+'-before'); start=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
 command=commands[name]
 env=os.environ.copy();env['TMPDIR']='$HOME/.cache/lw-m63-ad494';env['PYTHONDONTWRITEBYTECODE']='1'
 with (P/(name+'.log')).open('wb') as log:
  result=subprocess.run(command,cwd=T,env=env,stdout=log,stderr=subprocess.STDOUT)
 seconds=round(time.monotonic()-tick,3);after=capture(name+'-after')
 receipt={'head':HEAD,'cwd':str(T),'command':command,'started':start,'finished':datetime.now(timezone.utc).isoformat(),'duration_seconds':seconds,'exit_code':result.returncode,'inputs_unchanged':before==after,'count':before['count'],'log_sha256':sha((P/(name+'.log')).read_bytes())}
 (P/(name+'-receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 print(name,receipt['exit_code'],seconds,'seconds;',receipt['count'],'inputs unchanged',receipt['inputs_unchanged'],flush=True)
