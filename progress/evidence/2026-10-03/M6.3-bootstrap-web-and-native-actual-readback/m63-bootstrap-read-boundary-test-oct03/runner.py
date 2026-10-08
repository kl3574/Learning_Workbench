from pathlib import Path
import subprocess,json,hashlib,datetime,time,os
r=Path('$HOME/.cache/learning-workbench-acceptance/m63-local-session-bootstrap-ui-oct03'); e=Path(__file__).parent

def snapshot(name):
 files=[]
 for row in subprocess.check_output(['git','ls-tree','-rz','--full-tree','HEAD'],cwd=r).split(b'\0'):
  if not row: continue
  meta,path=row.split(b'\t');mode,kind,blob=meta.decode().split();p=path.decode(); f=r/p;raw=str(f.readlink()).encode() if mode=='120000' else f.read_bytes()
  files.append(dict(path=p,mode=mode,git_blob_sha1=blob,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),exact_git=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob))
 value=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),status=subprocess.check_output(['git','status','--porcelain'],cwd=r,text=True),count_all_tracked=len(files),count_nonprogress=sum(not v['path'].startswith('progress/') for v in files),all_exact_git=all(v['exact_git'] for v in files),files=files)
 (e/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');return value
b=snapshot('before.json');assert b['status']=='' and b['all_exact_git']
env=os.environ.copy();env['PATH']=str(r/'.toolchain/node-v24.21.0-linux-x64/bin')+':'+env['PATH'];env['TMPDIR']='$HOME/.cache/lwb63n2'
commands=[('01-focused',['npm','--prefix','apps/web','test','--','src/features/authoring/AuthoringBootstrap.test.tsx','src/features/codex/CodexBootstrapPanel.test.tsx','src/features/codex/bootstrapClient.test.ts','src/features/codex/bootstrapCommands.test.ts']),('02-full-web',['npm','--prefix','apps/web','test']),('03-strict',['npm','--prefix','apps/web','run','lint']),('04-build',['npm','--prefix','apps/web','run','build'])]
for label,cmd in commands:
 rec=dict(head=b['head'],command=cmd,start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());start=time.monotonic()
 (e/(label+'-start.json')).write_text(json.dumps(rec,indent=2)+'\n')
 with (e/(label+'.log')).open('wb') as log:p=subprocess.run(cmd,cwd=r,env=env,stdout=log,stderr=subprocess.STDOUT)
 rec.update(finish_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),duration_monotonic_seconds=time.monotonic()-start,exit_code=p.returncode)
 (e/(label+'.json')).write_text(json.dumps(rec,indent=2)+'\n');print(label,p.returncode,flush=True)
a=snapshot('after.json');(e/'source-receipt.json').write_text(json.dumps(dict(head=a['head'],clean=a['status']=='',all_exact_git=a['all_exact_git'],all_inputs_unchanged=a['files']==b['files'],count_all_tracked=a['count_all_tracked'],count_nonprogress=a['count_nonprogress']),indent=2)+'\n')
