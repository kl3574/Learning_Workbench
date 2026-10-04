"""Pure Git/file readback of explicit workflow candidates; no product/CI run."""
from pathlib import Path
import json,hashlib,subprocess
here=Path(__file__).parent
repo=Path('$HOME/.cache/learning-workbench-acceptance/m63-review-history-timing-oct05')
seal=Path('$HOME/.cache/learning-workbench-acceptance/m63-review-history-timing-evidence-oct05/seal-905')
priorseal=seal.parent/'seal-c02e'
head='905eccdd667001ec8e545cb534d5282ef6949836';base='c02e9e5c73d7da5e8e1617731fbefdf94f44f0e8';workflow='.github/workflows/ci.yml'
sha=lambda b:hashlib.sha256(b).hexdigest()
mr=(seal/'SAFE_CANDIDATES.json').read_bytes();orr=(seal/'READBACK.json').read_bytes()
assert sha(mr)=='c9522dbd8e2a3b509e1b949d729479b5daebabaa92a300126a9e0d2d9d8c33ac'
assert sha(orr)=='08089dd2636d8967d5d8c62ad2b022bf3f03484f3db994bbd4ab0f437c9a875f'
m=json.loads(mr);assert len(m['files'])==18 and m['source']==head
payload={};entries={}
for e in m['files']:
 n=e['candidate_path'];assert not Path(n).is_absolute() and '..' not in Path(n).parts and n not in payload
 b=(seal/'publication-candidates'/n).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'] and e['transformation']=='none';b.decode('utf-8')
 payload[n]=b;entries[n]=e
git=lambda *args:subprocess.check_output(['git',*args],cwd=repo)
assert git('rev-parse',head+'^').decode().strip()==base
assert git('diff','--name-only',base,head).decode().splitlines()==[workflow]
line=b'            ${{ runner.temp }}/learning-workbench-e2e-results/**/review-history-timing.json\n'
old=git('show',base+':'+workflow);new=git('show',head+':'+workflow)
assert new.count(line)==1 and new.replace(line,b'')==old
assert new.index(b'- name: Retain synthetic browser failure diagnostics')<new.index(line)<new.index(b'  security-publication:')
assert payload['final-workflow.yml']==new
assert payload['workflow-only.patch']==git('diff','--binary',base,head,'--',workflow)
review=git('show',head+':tests/e2e/review.spec.ts')
assert payload['final-review.spec.ts']==review==git('show',base+':tests/e2e/review.spec.ts')
refs={};oids=set()
for h in [base,head]:
 ref={}
 for row in git('ls-tree','-rz',h).split(b'\0'):
  if not row:continue
  meta,path=row.split(b'\t',1);mode,kind,oid=meta.decode().split();path=path.decode()
  if path.startswith('progress/'):continue
  assert kind=='blob';ref[path]=dict(mode=mode,type=kind,git_blob=oid);oids.add(oid)
 refs[h]=ref
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
v,_=proc.communicate(('\n'.join(sorted(oids))+'\n').encode());assert proc.returncode==0
at=0;blobs={}
for oid in sorted(oids):
 end=v.index(b'\n',at);actual,kind,size=v[at:end].decode().split();size=int(size);b=v[end+1:end+1+size];at=end+size+2
 assert actual==oid and kind=='blob' and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 blobs[oid]=dict(bytes=size,sha256=sha(b))
assert at==len(v)
for ref in refs.values():
 for item in ref.values():item.update(blobs[item['git_blob']])
assert len(refs[base])==len(refs[head])==1524
assert [n for n in refs[base] if refs[base][n]!=refs[head][n]]==[workflow]
obj=json.loads(payload['git-905eccdd.json']);assert obj['head']==head and obj['count']==1524 and obj['files']==refs[head]
stages=[]
for n in ['workflow-delta-static','workflow-delta-diff']:
 a=json.loads(payload[n+'/before.json']);b=json.loads(payload[n+'/after.json']);assert a==b and a['head']==head and a['status']=='' and a['count']==1524 and a['files']==refs[head]
 cmd=json.loads(payload[n+'/command.json']);rec=json.loads(payload[n+'/receipt.json'])
 assert all(rec[k]==v for k,v in cmd.items()) and rec['source']==head and rec['exit_code']==0 and rec['inputs_equal']
 assert rec['log_sha256']==sha(payload[n+'/output.log']) and rec['runner_sha256']==sha(payload['run_gate.py'])
 stages.append(dict(stage=n,exit_code=rec['exit_code'],log_sha256=rec['log_sha256'],runner_sha256=rec['runner_sha256'],started_at=rec['started_at'],finished_at=rec['finished_at']))
prior=json.loads(payload['PRIOR_C02E_SEAL_BINDING.json']);assert prior['prior']==base and prior['final']==head
for name,entry in prior['old_seal_unchanged'].items():assert sha((priorseal/name).read_bytes())==entry['sha256']
pm=json.loads((priorseal/'SAFE_CANDIDATES.json').read_bytes());assert len(pm['files'])==64
for e in pm['files']:
 n=e['candidate_path'];assert not Path(n).is_absolute() and '..' not in Path(n).parts
 b=(priorseal/'publication-candidates'/n).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256']
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain')
for path,item in refs[head].items():
 b=(repo/path).read_bytes();assert len(b)==item['bytes'] and sha(b)==item['sha256']
assert refs[head]['PRODUCT_DESIGN.md']['sha256']=='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
result=dict(source=head,base=base,owner_safe_sha256=sha(mr),owner_outer_sha256=sha(orr),owner_candidates=[dict(path=n,bytes=e['bytes'],sha256=e['sha256'],transformation='none') for n,e in entries.items()],owner_candidate_count=18,owner_outer_count=2,changed_paths=[workflow],insertions=1,deletions=0,all_other_workflow_bytes_exact=True,added_artifact_line=line.decode().strip(),base_inputs=1524,final_inputs=1524,unchanged_base_nonowned_inputs=1523,two_immutable_heads_bindings=3048,distinct_blobs=len(oids),final_owner_git_map_bindings=1524,stage_maps=4,stage_bindings=6096,all_mode_type_blob_size_sha_exact=True,clean=True,final_live_bytes_exact=True,stages=stages,review_source_sha256=sha(review),review_bytes_exact_c02=True,prior64_candidates_and_two_outer_unchanged=True,new_product_test_execution=False,native_on_final='NOT_RUN',real_ci_upload='NOT_RUN',original_ci_cause='UNKNOWN',Standards_new_p1_p2=0,Spec_new_p1_p2=0,no_unlisted_runtime_read=True)
print(json.dumps(result,ensure_ascii=False,indent=2))
