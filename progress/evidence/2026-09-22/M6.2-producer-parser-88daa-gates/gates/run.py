from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-active');base=Path(__file__).resolve().parent
name=sys.argv[1];stage=base/name;stage.mkdir(exist_ok=False)
commands={'python':['.venv/bin/pytest','-q'],'ruff':['.venv/bin/ruff','check','.'],'mypy':['.venv/bin/mypy','services/api'],'spec':['.venv/bin/python','scripts/verify_spec.py']}
cmd=commands[name]
def now():return datetime.now(timezone.utc).isoformat()
def write(name,data):(stage/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def sources():
 rows=[]
 for entry in subprocess.check_output(['git','ls-files','--stage','-z'],cwd=root).split(b'\0'):
  if not entry:continue
  metadata,path=entry.split(b'\t',1);mode,blob,index=metadata.decode().split();name=path.decode()
  if name.startswith('progress/'):continue
  f=root/name;data=os.readlink(f).encode() if f.is_symlink() else f.read_bytes()
  actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  rows.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'git_blob_sha1':blob,'git_matches':actual==blob,'git_mode':mode})
 return rows
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()
before=sources();write('inputs-before.json',before)
assert all(row['git_matches'] for row in before),'Gate requires committed fixed source bytes'
assert not subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=root).strip(),'Unexpected untracked input'
env={'PATH':os.environ['PATH'],'HOME':str(Path.home()),'LANG':'C.UTF-8','CI':'1','PYTHONDONTWRITEBYTECODE':'1'}
start=now();tick=time.monotonic();timedout=False
with (stage/'test.log').open('wb') as out:
 try:p=subprocess.run(cmd,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=1500);exitcode=p.returncode
 except subprocess.TimeoutExpired:timedout=True;exitcode=None
finish=now();after=sources();write('inputs-after.json',after);log=(stage/'test.log').read_bytes()
receipt={'code_commit':head,'command':cmd,'start':start,'finish':finish,'seconds':time.monotonic()-tick,'exit_code':exitcode,'timeout':timedout,'source_count':len(before),'source_unchanged':before==after,'all_source_matches_git_before':all(x['git_matches'] for x in before),'all_source_matches_git_after':all(x['git_matches'] for x in after),'log_bytes':len(log),'log_sha256':hashlib.sha256(log).hexdigest()};write('receipt.json',receipt)
print(json.dumps(receipt,indent=2));print(log.decode(errors='replace')[-2500:]);sys.exit(0 if exitcode==0 and before==after else 1)
