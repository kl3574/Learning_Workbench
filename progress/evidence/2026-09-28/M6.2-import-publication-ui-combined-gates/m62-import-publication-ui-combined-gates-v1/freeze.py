from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,re
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-active');base=Path(__file__).resolve().parent
sha=lambda data:hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
def write(name,data):(base/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
head='4a5c6de3b74fdc1659389326c746e05ef19ff00b'
assert not (base/'MANIFEST.json').exists(),'Do not overwrite a frozen gate cache'
results=[];blobs={}
for stage in ['web','web-lint','web-build','spec']:
 path=base/stage
 receipt=json.loads((path/'receipt.json').read_text());assert receipt['code_commit']==head
 log=(path/'test.log').read_bytes();assert sha(log)==receipt['log_sha256'] and len(log)==receipt['log_bytes']
 before=json.loads((path/'inputs-before.json').read_text());after=json.loads((path/'inputs-after.json').read_text());assert before==after and len(before)==1040
 tree={}
 for item in git('ls-tree','-r','-z',head).split(b'\0'):
  if item:
   info,name=item.split(b'\t',1);mode,kind,blob=info.decode().split()
   if not name.startswith(b'progress/'):tree[name.decode()]=(mode,blob)
 assert len(tree)==len(before)
 for row in before:
  mode,blob=tree[row['path']];assert (mode,blob)==(row['git_mode'],row['git_blob_sha1'])
  if blob not in blobs:
   data=git('cat-file','blob',blob);blobs[blob]=(len(data),sha(data))
  assert blobs[blob]==(row['bytes'],row['sha256']) and row['git_matches']
 text=log.decode(errors='replace');plain=re.sub(r'\x1b\[[0-9;]*m','',text)
 lines=[line for line in plain.splitlines() if any(token in line for token in [' passed',' failed',' skipped','SKIPPED','Success:','modules transformed','All checks passed!'])]
 results.append({'stage':stage,**receipt,'actual_git_verified':True,'selected_result_lines':lines})
composition=json.loads((base/'composition.json').read_text());assert composition['candidate']==head and len(composition['engineering_inputs'])==1040
for row in composition['engineering_inputs']:
 data=git('show',row['source_commit']+':'+row['path']);assert len(data)==row['bytes'] and sha(data)==row['sha256']
write('verification.json',{'utc':datetime.now(timezone.utc).isoformat(),'source_commit':head,'status':'PASS' if all(r['exit_code']==0 for r in results) else 'HAS_FAILED_GATE','results':results,'composition_reverified':True,'engineering_input_count':1040,'distinct_actual_git_blobs':len(blobs),'full_python_here':'NOT_RERUN_UI_ONLY_DELTA; original62118f8 full2892PASS1ENVSKIP retained', 'full_native':'NOT_RUN','provider':'NOT_RUN','full_M6_2':'NOT_ACCEPTED'})
rows=[]
for f in sorted(base.rglob('*')):
 if f.is_file() and '__pycache__' not in f.parts and f.name!='MANIFEST.json':
  data=f.read_bytes();rows.append({'path':f.relative_to(base).as_posix(),'bytes':len(data),'sha256':sha(data)})
write('MANIFEST.json',{'members':rows,'count':len(rows)})
print(json.dumps({'source_commit':head,'results':[{'stage':r['stage'],'exit_code':r['exit_code'],'result_lines':r['selected_result_lines']} for r in results],'members':len(rows),'manifest_sha256':sha((base/'MANIFEST.json').read_bytes())},ensure_ascii=False))
