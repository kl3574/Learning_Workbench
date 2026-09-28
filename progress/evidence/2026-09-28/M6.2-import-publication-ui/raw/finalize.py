from pathlib import Path
import hashlib,json,subprocess
from datetime import datetime,timezone
base=Path(__file__).resolve().parent
work=base.parent/'m62-import-publication-ui-active'
head='fa71351e7d6b9358d4b0ef2f46184999f84e5e08'
initial='833f0a84168638ba5ce421c70cd2f20a71e45e48'
def sha(b): return hashlib.sha256(b).hexdigest()
def dump(path,value): (base/path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def git(*args): return subprocess.check_output(['git',*args],cwd=work)
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain')
entries={}
for row in git('ls-tree','-r','-z',head).split(b'\0'):
 if row:
  meta,path=row.split(b'\t',1);mode,kind,oid=meta.decode().split()
  if kind=='blob': entries[path.decode()]=oid
ids=sorted(set(entries.values()))
p=subprocess.run(['git','cat-file','--batch'],input=('\n'.join(ids)+'\n').encode(),cwd=work,stdout=subprocess.PIPE,check=True)
data=p.stdout;offset=0;blobs={}
for oid in ids:
 end=data.index(b'\n',offset);header=data[offset:end].decode().split();size=int(header[2]);body=data[end+1:end+1+size];offset=end+2+size
 assert header[0]==oid and header[1]=='blob' and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+body).hexdigest()==oid
 blobs[oid]=body
assert offset==len(data)
changed=git('diff','--name-only',initial,head).decode().splitlines()
pins=[]
for path in changed:
 b=blobs[entries[path]];assert (work/path).read_bytes()==b
 dest=base/'fixed-source'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
 pins.append({'path':path,'git_blob':entries[path],'bytes':len(b),'sha256':sha(b),'copy':str(dest.relative_to(base))})
outer=Path('<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md').read_bytes(); assert sha(outer)=='2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d'
(base/'sole-spec.md').write_bytes(outer)
dump('source-pins.json',{'base':initial,'head':head,'spec_sha256':sha(outer),'changed_files':pins,'scope':'Actual final 17 changed Git blobs; all stage source coverage is separately reported.'})
(base/'candidate.patch').write_bytes(git('diff','--binary',initial,head))
stages=[]
for d in sorted(base.glob('[0-9][0-9]-*')):
 if not d.is_dir():continue
 r=json.loads((d/'receipt.json').read_text());before=json.loads((d/'inputs-before.json').read_text());after=json.loads((d/'inputs-after.json').read_text())
 assert before==after and r['inputs_unchanged'] and sha((d/'run.log').read_bytes())==r['log_sha256']
 for name in ['before','after']:assert sha((d/f'inputs-{name}.json').read_bytes())==r[f'inputs_{name}_sha256']
 matched=[];different=[];missing=[]
 for item in before:
  source=base/'source-by-sha256'/item['sha256'];b=source.read_bytes();assert len(b)==item['bytes'] and sha(b)==item['sha256']
  actual=blobs.get(entries.get(item['path'],''))
  if actual is None: missing.append(item['path'])
  elif actual==b:matched.append(item['path'])
  else:different.append(item['path'])
 stages.append({'stage':d.name,'exit_code':r['exit_code'],'log_sha256':r['log_sha256'],'inputs_before_sha256':r['inputs_before_sha256'],'inputs_after_sha256':r['inputs_after_sha256'],'input_count':len(before),'actual_final_git_matches':len(matched),'different_paths':different,'absent_final_paths':missing,'matches':matched,'receipt_sha256':sha((d/'receipt.json').read_bytes())})
dump('GIT_SOURCE_BINDINGS.json',{'base':initial,'head':head,'verification':'Every raw input CAS stream hashed and compared with actual cat-file bytes of fixed final Git blobs. Omitted final paths are not claimed executed. Source roots are exactly run.py ROOTS, not every Git file.','stages':stages})
private=[]
for p in sorted((base/'18-native-publication/artifacts').rglob('*')):
 if p.is_file() and (p.suffix=='.png' or p.name=='publication-flow.json'):
  b=p.read_bytes();private.append({'path':str(p.relative_to(base)),'bytes':len(b),'sha256':sha(b),'reason':'Actual synthetic reviewer session identity appears in this private native evidence. Exclude original screenshots and complete flow from a public package; retain this explicit hash binding. No pixel editing or broad regex deletion.'})
dump('PRIVATE_NATIVE_EXCLUSIONS.json',private)
dump('TASK_RECEIPT.json',{'task_id':'M6.2-import-text-publication-ui','requirement_ids':['14','15.1','15.2','15.3','16.1','20.1','20.3','20.8','Appendix A publish/current'], 'spec_sha256':sha(outer),'implementation_commit':head,'base_commit':initial,'changed_paths':changed,'stage_count':len(stages),'commands':[json.loads((base/s['stage']/'receipt.json').read_text())['command'] for s in stages],'exit_codes':[s['exit_code'] for s in stages],'test_summary':{'19-fixed-whole-web':'501 PASS / 86 files / 6.15s','15-web-fixed-focus':'48 PASS / 9 files','18-native-publication':'1 actual synthetic native PASS / 7.9s case / 8.3s total / retries 0','16-web-lint':'PASS','17-native-types':'strict PASS with existing official Playwright declarations bridge','20-fixed-build':'strict TS/build PASS; existing chunk-size warning','21-fixed-spec':'PASS','22-fixed-scanner':'17 changed files PASS, zero exceptions'},'screenshot_paths':[p['path'] for p in private if p['path'].endswith('.png')],'migrations':[],'security_review':'Current author/Policy and generation guard; no credentials stored; native synthetic session IDs remain private with explicit exclusion bindings; independent review pending in separate owner reports.','not_run':['real model/provider calls','real human content quality approval','all backend Python tests in this UI tree','whole native suite','cross-tab true multiple-browser concurrency','general Draft/Authoring/private-solution/group publication'], 'blockers':[],'next_task_id':'independent dual-axis review and safe public evidence package; parent integration only after actual review','created_at':datetime.now(timezone.utc).isoformat()})
print(json.dumps({'head':head,'changed_files':len(pins),'stages':[(s['stage'],s['exit_code'],s['actual_final_git_matches'],s['input_count']) for s in stages],'private_native_files':len(private)}))
