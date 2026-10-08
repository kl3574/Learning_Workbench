from pathlib import Path
import os,subprocess,json,hashlib,time,datetime
w=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-tutor-completion-observation-oct04');s=Path(__file__).parent
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=w,text=True).strip()
def mapping():
 out={}
 for row in subprocess.check_output(['git','ls-tree','-rz','HEAD'],cwd=w).split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1); path=name.decode()
  if path.startswith('progress/'):continue
  raw=(w/path).read_bytes(); blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
  assert blob==meta.decode().split()[2],path
  out[path]={'git_blob':blob,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 return out
before=mapping();(s/'inputs-before.json').write_text(json.dumps(before,sort_keys=True,indent=2)+'\n')
cmd=['bash','scripts/node.sh','apps/web/node_modules/.bin/tsc','--project',str(s.parent/'native-tsconfig.json')]
env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(s/'home'),'TMPDIR':str(Path((s/'private-temp-path.txt').read_text().strip())),'XDG_CACHE_HOME':str(s/'cache'),'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (s/'run.log').open('wb') as log:r=subprocess.run(cmd,cwd=w,env=env,stdout=log,stderr=subprocess.STDOUT)
after=mapping();(s/'inputs-after.json').write_text(json.dumps(after,sort_keys=True,indent=2)+'\n')
receipt={'head':head,'command':cmd,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'native_tsconfig_sha256':hashlib.sha256((s.parent/'native-tsconfig.json').read_bytes()).hexdigest(),'started_utc':utc,'seconds':time.monotonic()-start,'exit_code':r.returncode,'input_count':len(before),'source_equal':before==after,'log_sha256':hashlib.sha256((s/'run.log').read_bytes()).hexdigest(),'scope':'Fixed three original Tutor cases plus three synthetic DOM completion cases; only original Tutor loopback protocol. No real model/CLI/account. Total original 5s completion budget unchanged.'}
(s/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
