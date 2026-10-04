"""Read-only audit of explicit fixed-source local evidence; no artifact discovery."""
from pathlib import Path
import datetime,hashlib,json,subprocess
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-artifact-ui-4353-owner-oct04')
e=Path(__file__).parent
base='4353a05570afd9f2378c904b5594998de21bc474';final='8f2c884510aef987b80ae62a018c33c83d89388c'
stages=['wire-red-01','wire-green-01','focused-fixed-01','fullweb-fixed-01','strict-fixed-01','build-fixed-01','spec-fixed-01','scope-red-01','scope-green-01','focused-fixed-02','fullweb-fixed-02','strict-fixed-02','build-fixed-02','spec-fixed-02']
sha=lambda data:hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
def write(name,value):(e/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
assert git('rev-parse','HEAD').decode().strip()==final and git('status','--porcelain')==b''
heads=[base,'d20ba00f69b9642da4cab7d02caf941fdf96a753','e10193638d20180638a515698cbada5b3eaf2e7b',git('rev-parse','f0566809').decode().strip(),'422fdbcaadcfbe4b6e59f54cd192b545345347c8','c61da5b7350e4f75616424c9a80847cfdbbb9e51','bc978839e7e28818ae341bb0367c87fe448662ea',final]
entries={};oids=set()
for head in heads:
 values={}
 for row in git('ls-tree','-rz',head).split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();path=name.decode()
  if path.startswith('progress/'):continue
  assert kind=='blob';values[path]={'mode':mode,'type':kind,'git_blob':oid};oids.add(oid)
 entries[head]=values
objects={};proc=subprocess.Popen(['git','cat-file','--batch'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
for oid in sorted(oids):
 proc.stdin.write((oid+'\n').encode());proc.stdin.flush();header=proc.stdout.readline().decode().split();assert header[:2]==[oid,'blob'];size=int(header[2]);data=proc.stdout.read(size);assert proc.stdout.read(1)==b'\n'
 assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()==oid
 objects[oid]={'bytes':size,'sha256':sha(data)}
proc.stdin.close();assert proc.wait()==0
for values in entries.values():
 for value in values.values():value.update(objects[value['git_blob']])
manifest={'heads':{h:{'count':len(v),'files':v} for h,v in entries.items()},'unique_checked_git_blobs':len(objects)}
write('FULL_GIT_MANIFESTS.json',manifest)
records=[]
for stage in stages:
 p=e/stage;r=json.loads((p/'receipt.json').read_text());before=json.loads((p/'source-before.json').read_text());after=json.loads((p/'source-after.json').read_text());assert before==after and before['status']=='' and before['head']==r['source_sha'];assert sha((p/'run.log').read_bytes())==r['log_sha256']
 expected=entries[r['source_sha']];assert len(expected)==before['count']
 for item in before['files']:
  actual=expected[item['path']];assert item['git_blob']==item['actual_blob']==actual['git_blob'] and item['sha256']==actual['sha256'] and item['matches_git']
 record={'stage':stage,'source_sha':r['source_sha'],'exit_code':r['exit_code'],'before_after_exact':True,'count':len(expected),'finished_at':r['finished_at'],'artifacts':{n:{'sha256':sha((p/n).read_bytes()),'bytes':(p/n).stat().st_size} for n in ['receipt.json','command.json','source-before.json','source-after.json','run.log']}}
 records.append(record)
owned=git('diff','--name-only',base,final).decode().splitlines();assert len(owned)==15
unchanged=[]
for name,value in entries[base].items():
 if name not in owned:assert entries[final][name]==value;unchanged.append(name)
for name,value in entries[final].items():assert sha((root/name).read_bytes())==value['sha256']
assert len(unchanged)==1489 and len(entries[final])==1504
red='c61da5b7350e4f75616424c9a80847cfdbbb9e51';green='bc978839e7e28818ae341bb0367c87fe448662ea';test='apps/web/src/features/codex/ArtifactImportNavigation.test.tsx';assert git('show',red+':'+test)==git('show',green+':'+test)
(e/'scope-red-01'/'ArtifactImportNavigation.test.tsx').write_bytes(git('show',red+':'+test));(e/'scope-green-01'/'ArtifactImportNavigation.test.tsx').write_bytes(git('show',green+':'+test))
(e/'owner-delta.patch').write_bytes(git('diff','--binary',base,final))
write('FINAL_BINDING.json',{'base':base,'source_sha':final,'status':'clean','spec_sha256':sha((root/'PRODUCT_DESIGN.md').read_bytes()),'complete_nonprogress_inputs':1504,'unchanged_base_inputs':len(unchanged),'changed_paths':owned,'git_manifest_sha256':sha((e/'FULL_GIT_MANIFESTS.json').read_bytes()),'records':records,'same_byte_scope_red_green_test_sha256':sha(git('show',red+':'+test)),'bounded_claim':'Artifact UI local implementation only; independent review owned by root; no overall M6.3/real runtime/learning acceptance.','audited_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
print(json.dumps({'heads':len(heads),'unique_git_blobs':len(objects),'stages':len(records),'inputs':1504,'unchanged':len(unchanged),'delta':len(owned)}))
