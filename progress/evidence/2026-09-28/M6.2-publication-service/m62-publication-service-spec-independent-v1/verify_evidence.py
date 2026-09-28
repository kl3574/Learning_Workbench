from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;RAW=BASE/'m62-publication-service-development-v1';WORK=BASE/'m62-publication-service-active';HEAD='dec1d937523f4596da4c39bcc27750d9132c752c'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def check(p,row):
 data=p.read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256'],str(p);return data
manraw=(RAW/'PRIVATE_MANIFEST.json').read_bytes();assert sha(manraw)=='50ce35ab42f77d36b523c6ff9b0587a4d9b96903051cf6e93321e0405b29e8f9';manifest=json.loads(manraw)
for row in manifest['files']:check(RAW/row['path'],row)
assert {str(p.relative_to(RAW)) for p in RAW.rglob('*') if p.is_file()}=={r['path'] for r in manifest['files']}|{'PRIVATE_MANIFEST.json'}
pins=read(OUT/'source-pins.json');ledger=read(RAW/'run-ledger.json');entries={}
for row in subprocess.check_output(['git','ls-tree','-r','-z',HEAD],cwd=WORK).split(b'\0'):
 if not row:continue
 meta,path=row.split(b'\t',1);_,kind,oid=meta.split()
 if kind==b'blob':entries[path.decode()]=oid.decode()
finalnames=['16-final-mypy','17-final-ruff','18-final-related','19-migration-regression'];names={r['path'] for r in pins['files']}
for name in finalnames:names.update(read(RAW/name/'inputs-before.json'))
oids=sorted({entries[n] for n in names});proc=subprocess.run(['git','cat-file','--batch'],input=('\n'.join(oids)+'\n').encode(),capture_output=True,cwd=WORK,check=True);blobs={};cursor=0
for oid in oids:
 end=proc.stdout.index(b'\n',cursor);header=proc.stdout[cursor:end].split();size=int(header[2]);data=proc.stdout[end+1:end+size+1]
 assert header[0].decode()==oid and header[1]==b'blob' and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()==oid
 blobs[oid]={'bytes':size,'sha256':sha(data)};cursor=end+size+2
assert cursor==len(proc.stdout)
for row in pins['files']:
 check(OUT/'source'/row['path'],row);assert entries[row['path']]==row['git_blob'] and blobs[row['git_blob']]=={'bytes':row['bytes'],'sha256':row['sha256']}
results=[]
for entry in ledger:
 stage=RAW/entry['stage'];receipt=read(stage/'receipt.json');before=read(stage/'inputs-before.json');after=read(stage/'inputs-after.json')
 assert receipt==entry['receipt'] and before==after and len(before)==receipt['input_count_before']==receipt['input_count_after']
 assert receipt['unchanged'] and not receipt['changed_paths']
 assert sha((stage/'receipt.json').read_bytes())==entry['receipt_sha256']
 assert sha((stage/'inputs-before.json').read_bytes())==entry['inputs_before_sha256'] and sha((stage/'inputs-after.json').read_bytes())==entry['inputs_after_sha256']
 log=(stage/'run.log').read_bytes();assert sha(log)==receipt['log_sha256'] and len(log)==receipt['log_bytes']
 assert sha((RAW/'run.py').read_bytes())==receipt['driver_sha256']
 retained=[]
 for f in (stage/'source').rglob('*'):
  if f.is_file():n=str(f.relative_to(stage/'source'));check(f,before[n]);retained.append(n)
 assert len(retained)==entry['retained_source_count'] and entry['all_retained_sources_match_before']
 exact=None
 if stage.name in finalnames:
  assert len(before)==1021
  for n,row in before.items():assert blobs[entries[n]]==row,n
  exact=len(before)
 results.append({'stage':stage.name,'exit_code':receipt['exit_code'],'input_count':len(before),'before_after_equal':True,'retained_sources_verified':len(retained),'actual_git_exact_inputs':exact,'receipt_sha256':entry['receipt_sha256'],'log_sha256':receipt['log_sha256']})
ownerpins=read(RAW/'final-source-pins.json');assert ownerpins['implementation_commit']==HEAD
ours={r['path']:r for r in pins['files']}
for row in ownerpins['changed_files']:
 assert all(ours[row['path']][k]==row[k] for k in ['bytes','sha256','git_blob'])
result={'verified_at':datetime.now(timezone.utc).isoformat(),'candidate':HEAD,'baseline':pins['baseline'],'spec_sha256':pins['spec_sha256'],'owner_private_manifest_sha256':sha(manraw),'owner_members_verified':len(manifest['files']),'independent_source_files':len(pins['files']),'changed_source_files':len(ownerpins['changed_files']),'actual_git_blobs_read':len(blobs),'stages':results,'interpretation':'Each final stage has all 1021 owner-declared engineering inputs matched against actual Git bytes; previous stage retained subsets and whole before/after hashes are checked separately. No claim to freeze external interpreter/sandbox inputs.','product_tests_rerun':[],'result':'PASS'}
(OUT/'VERIFY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':'PASS','members':len(manifest['files']),'stages':len(results),'retained_source_total':sum(r['retained_sources_verified'] for r in results),'final_actual_git_counts':[r['actual_git_exact_inputs'] for r in results if r['actual_git_exact_inputs']],'source_files':len(pins['files'])}))
