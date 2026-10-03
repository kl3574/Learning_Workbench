from pathlib import Path
import subprocess,json,hashlib,datetime
ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance')
OUT=Path(__file__).resolve().parent
OWNER=ROOT/'m62-authoring-observation-development-v1'
WORK=ROOT/'m62-authoring-observation-active'
HEAD='8b6629205a72593ab835e2c61a20b6e1eac7061e'
def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return json.loads(p.read_bytes())
def check(p,row):
 b=p.read_bytes(); assert len(b)==row['bytes'] and sha(b)==row['sha256'],str(p); return b
raw=(OWNER/'MANIFEST.json').read_bytes()
assert sha(raw)=='a552baf003e3a01ed3addea425742def41349e78042bd7643af44cd1584ab46a'
man=json.loads(raw)
for row in man['members']: check(OWNER/row['path'],row)
entries={}
for record in subprocess.check_output(['git','ls-tree','-r','-z',HEAD],cwd=WORK).split(b'\0'):
 if not record: continue
 meta,path=record.split(b'\t',1); mode,kind,oid=meta.split()
 if kind==b'blob': entries[path.decode()]=oid.decode()
oids=sorted(set(entries.values()))
proc=subprocess.run(['git','cat-file','--batch'],input=('\n'.join(oids)+'\n').encode(),capture_output=True,cwd=WORK,check=True)
blobs={}; offset=0
for oid in oids:
 end=proc.stdout.index(b'\n',offset); hdr=proc.stdout[offset:end].split(); length=int(hdr[2]); data=proc.stdout[end+1:end+1+length]
 assert hdr[0].decode()==oid and hdr[1]==b'blob'
 assert hashlib.sha1(b'blob '+str(length).encode()+b'\0'+data).hexdigest()==oid
 blobs[oid]=(sha(data),length); offset=end+2+length
assert offset==len(proc.stdout)
stages=[]; retained=set()
for stage in sorted(p for p in OWNER.iterdir() if p.is_dir() and p.name[:2].isdigit()):
 receipt=read(stage/'receipt.json'); before=read(stage/'inputs-before.json'); after=read(stage/'inputs-after.json')
 assert before==after and len(before)==receipt['input_count'] and receipt['inputs_unchanged']
 assert sha((stage/'run.log').read_bytes())==receipt['log_sha256']
 assert sha((stage/'inputs-before.json').read_bytes())==receipt['inputs_before_sha256']
 assert sha((stage/'inputs-after.json').read_bytes())==receipt['inputs_after_sha256']
 assert sha((OWNER/'run.py').read_bytes())==receipt['runner_sha256']
 differences=[]
 for row in before:
  data=check(OWNER/'source-by-sha256'/row['sha256'],row); retained.add(row['sha256'])
  assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['git_blob']
  oid=entries.get(row['path'])
  if not oid or blobs[oid]!=(row['sha256'],row['bytes']): differences.append(row['path'])
 stages.append({'stage':stage.name,'exit_code':receipt['exit_code'],'input_count':len(before),'before_after_equal':True,'candidate_matches':len(before)-len(differences),'candidate_differences':differences,'receipt_sha256':sha((stage/'receipt.json').read_bytes()),'log_sha256':receipt['log_sha256']})
claimed=read(OWNER/'GIT_SOURCE_BINDINGS.json')['stages']
for actual,claim in zip(stages,claimed,strict=True):
 assert actual['stage']==claim['stage'] and actual['candidate_matches']==claim['candidate_exact_matches'] and actual['candidate_differences']==claim['candidate_differences']
source=read(OUT/'source-pins.json')
for row in source['files']:
 data=check(OUT/'source'/row['path'],row)
 assert row['git_blob']==entries[row['path']] and blobs[entries[row['path']]]==(row['sha256'],len(data))
orig=read(OWNER/'original-red-bindings.json')
for row in orig['files']: check(ROOT/orig['cache']/row['path'],row)
report={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate':HEAD,'owner_manifest_sha256':sha(raw),'owner_members_verified':len(man['members']),'owner_git_binding_sha256':sha((OWNER/'GIT_SOURCE_BINDINGS.json').read_bytes()),'git_blobs_actually_read':len(blobs),'independent_source_files_verified':len(source['files']),'retained_distinct_source_bytes_verified':len(retained),'stage_scope':'Explicit engineering roots of owner run.py, not every Git file or external runtime input.','stages':stages,'original_failure_bindings_verified':orig,'reviewer_executed_product_tests':[],'result':'PASS'}
(OUT/'VERIFY.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'result':'PASS','owner_members':len(man['members']),'retained_unique':len(retained),'stages':stages},indent=2))
