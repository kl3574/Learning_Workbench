from pathlib import Path
import subprocess,json,hashlib,datetime,time,os,sys
r=Path('$HOME/.cache/learning-workbench-acceptance/m63-local-task-document-oct04');e=Path(__file__).parent
label=sys.argv[1];cmd=sys.argv[2:];stage=e/label;stage.mkdir(exist_ok=False)
def snap(name):
 files=[]
 for p in sorted(set(subprocess.check_output(['git','ls-files','-z'],cwd=r).decode().split('\0'))- {''}):
  if p.startswith('progress/'):continue
  f=r/p;raw=str(f.readlink()).encode() if f.is_symlink() else f.read_bytes()
  old=subprocess.run(['git','rev-parse','HEAD:'+p],cwd=r,text=True,capture_output=True)
  blob=old.stdout.strip() if old.returncode==0 else None
  files.append(dict(path=p,git_blob=blob,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),exact_git=blob==hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()))
 v=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),status=subprocess.check_output(['git','status','--porcelain'],cwd=r,text=True),count_nonprogress=len(files),all_exact_git=all(x['exact_git'] for x in files),files=files)
 (stage/name).write_text(json.dumps(v,indent=2)+'\n');return v
b=snap('before.json');env=os.environ.copy();env['TMPDIR']='$HOME/.cache/lwb63task';Path(env['TMPDIR']).mkdir(exist_ok=True)
rec=dict(command=cmd,source_head=b['head'],start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());start=time.monotonic()
with (stage/'run.log').open('wb') as log:p=subprocess.run(cmd,cwd=r,env=env,stdout=log,stderr=subprocess.STDOUT)
a=snap('after.json');rec.update(exit_code=p.returncode,finish_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),duration_monotonic_seconds=time.monotonic()-start,inputs_unchanged=a['files']==b['files'],count_nonprogress=a['count_nonprogress'],all_exact_git=a['all_exact_git'],clean=a['status']=='')
(stage/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec),flush=True)
