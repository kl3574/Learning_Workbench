"""Read only exact owner candidates and immutable Git; never run product gates."""
from pathlib import Path
import hashlib,json,subprocess,re,math,collections,datetime
here=Path(__file__).parent
repo=Path('$HOME/.cache/learning-workbench-acceptance/m63-review-history-timing-oct05')
seal=Path('$HOME/.cache/learning-workbench-acceptance/m63-review-history-timing-evidence-oct05/seal-c02e')
base='35aebd3039241abb3393300affd593f4826a4a0c';head='c02e9e5c73d7da5e8e1617731fbefdf94f44f0e8'
owned='tests/e2e/review.spec.ts'
sha=lambda b:hashlib.sha256(b).hexdigest()
mr=(seal/'SAFE_CANDIDATES.json').read_bytes();orr=(seal/'READBACK.json').read_bytes()
assert sha(mr)=='014723c0835ce79be6f2649441acebbb34ea3c62c2315313b947b5678b0612a3'
assert sha(orr)=='7c08532fc094dae4394fbe261dd1ea0947c570feb75cfcafe9b281da9b972104'
m=json.loads(mr);assert m['source']==head and len(m['files'])==64
payload={};entries={}
for e in m['files']:
 n=e['candidate_path'];assert not Path(n).is_absolute() and '..' not in Path(n).parts and n not in payload
 b=(seal/'publication-candidates'/n).read_bytes()
 assert len(b)==e['bytes'] and sha(b)==e['sha256'] and e['transformation']=='none'
 b.decode('utf-8');payload[n]=b;entries[n]=e
assert not any(n.endswith('.png') for n in payload)
git=lambda *args:subprocess.check_output(['git',*args],cwd=repo)
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
assert [n for n in refs[base] if refs[base][n]!=refs[head][n]]==[owned]
assert payload['original-review.spec.ts']==git('show',base+':'+owned)
assert payload['fixed-review.spec.ts']==git('show',head+':'+owned)
assert payload['source.patch']==git('diff','--binary',base,head,'--',owned)
for h,n in [(base,'base-inputs.json'),(base,'git-35aebd30.json'),(head,'git-c02e9e5c.json')]:
 obj=json.loads(payload[n]);assert obj['head']==h and obj['count']==1524 and obj['files']==refs[h]
assert refs[head]['PRODUCT_DESIGN.md']['sha256']=='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
source=json.loads(payload['SOURCE_BINDINGS.json']);stages=source['stages'];assert len(stages)==9
stage_results=[];wip_exceptions=[]
for st in stages:
 n=st['stage'];before=json.loads(payload[n+'/before.json']);after=json.loads(payload[n+'/after.json'])
 assert before==after and before['count']==1524 and set(before['files'])==set(refs[head])
 wip=n.startswith('wip-');h=base if wip else head;assert before['head']==h
 if wip:assert before['status']==' M tests/e2e/review.spec.ts\n'
 elif 'status' in before:assert before['status']==''
 for path,item in before['files'].items():
  assert all(item[k]==refs[h][path][k] for k in ['mode','type','git_blob'])
  assert all(item[k]==refs[head][path][k] for k in ['bytes','sha256'])
  if wip and path==owned:wip_exceptions.extend([dict(map=n+'/'+suffix+'.json',path=path,git_head_blob=item['git_blob'],working_sha256=item['sha256']) for suffix in ['before','after']])
 assert sha(payload[n+'/before.json'])==st['before_sha256'] and sha(payload[n+'/after.json'])==st['after_sha256']
 cmd=json.loads(payload[n+'/command.json']);rn='run-receipt.json' if n.startswith('native-') else 'receipt.json';rec=json.loads(payload[n+'/'+rn])
 assert all(rec[k]==v for k,v in cmd.items()) and rec['source']==h
 assert rec['log_sha256']==sha(payload[n+'/output.log'])
 runner='run_native02.py' if n=='native-run-02' else 'run_native.py' if n=='native-run-01' else 'run_gate.py'
 assert rec['runner_sha256']==sha(payload[runner])
 assert rec['finished_at']>=rec['started_at'] and rec['elapsed_seconds']>=0
 expected=1 if n in ['wip-strict','native-run-01'] else 0;assert rec['exit_code']==expected
 eq=rec['source_before_after_exact'] if n.startswith('native-') else rec['inputs_equal'];assert eq
 stage_results.append(dict(stage=n,source=h,exit_code=rec['exit_code'],started_at=rec['started_at'],finished_at=rec['finished_at'],elapsed_seconds=rec['elapsed_seconds'],runner_sha256=rec['runner_sha256'],log_sha256=rec['log_sha256'],wip_not_clean_git=wip))
assert len(wip_exceptions)==6
assert b'TS7016' in payload['wip-strict/output.log']
assert b'No tests found.' in payload['native-run-01/output.log']
assert b'Total: 1 test in 1 file' in payload['fixed-first-list/output.log']
assert b'1 passed (18.3s)' in payload['native-run-02/output.log'] and b'(15.4s)' in payload['native-run-02/output.log']
assert json.loads(payload['native-run-02/command.json'])['command'][-1]=='review.spec.ts:36'
shim=payload['playwright-official-types.d.ts'].decode();assert ' any' not in shim and 'import(' in shim
cfg=json.loads(payload['focused-types.json']);assert cfg['compilerOptions']['strict'] and cfg['compilerOptions']['noEmit']
tn=next(n for n in payload if n.endswith('/review-history-timing.json'))
t=json.loads(payload[tn]);assert sha(payload[tn])=='26dd74a9a9e50c2f44e3dd267224228e171d69668bf27817ba2aa103a248a4ba'
assert set(t)==set(['version','body_started_at','observed_timeout_ms','retry','phases','http','dropped','limits','scope'])
assert t['version']=='review-history-metadata-v1' and t['observed_timeout_ms']==30000 and t['retry']==0
assert t['limits']==dict(phases=128,http=512) and t['dropped']==dict(phases=0,http=0)
assert len(t['phases'])==43 and len(t['http'])==298
fixed=payload['fixed-review.spec.ts'].decode();route_start=fixed.index('  const timingRoutes:');route_end=fixed.index('  const timingPending')
allowed_routes=set(re.findall(r", '(/api/v1/[^']+)'",fixed[route_start:route_end]))
allowed_stages=set(re.findall(r"timingPhase\('([^']+)'\)",fixed))
seq={}
for row in t['phases']:
 assert set(row)==set(['sequence','elapsed_ms','stage']) and row['stage'] in allowed_stages
 assert row['sequence'] not in seq;seq[row['sequence']]=row['elapsed_ms']
for row in t['http']:
 required=set(['sequence','elapsed_ms','event','route','method'])
 assert required<=set(row)<=required|set(['status','request_elapsed_ms'])
 assert row['route'] in allowed_routes and row['method'] in ['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS']
 assert row['event'] in ['request','response-headers','request-finished','request-failed']
 assert row['sequence'] not in seq;seq[row['sequence']]=row['elapsed_ms']
 if 'status' in row:assert type(row['status'])==int and 100<=row['status']<=599 and row['event']=='response-headers'
 if 'request_elapsed_ms' in row:assert math.isfinite(row['request_elapsed_ms']) and row['request_elapsed_ms']>=0
assert set(seq)==set(range(1,342))
assert all(math.isfinite(v) and v>=0 for v in seq.values())
assert list(sorted(seq,key=seq.get))==list(range(1,342))
tr=json.loads(payload['TIMING_READBACK.json']);assert tr['phase_times']==t['phases'] and tr['body_elapsed_ms']==t['phases'][-1]['elapsed_ms']
assert tr['timing_sha256']==sha(payload[tn]) and tr['timing_bytes']==len(payload[tn])
counts=collections.Counter((r['method'],r['route'],r['status']) for r in t['http'] if 'status' in r)
assert counts==collections.Counter({(g['method'],g['route'],g['status']):g['count'] for g in tr['static_route_status_groups']})
status=collections.Counter(str(r['status']) for r in t['http'] if 'status' in r);assert dict(status)==tr['http_status_counts']
start=datetime.datetime.fromisoformat(t['body_started_at'].replace('Z','+00:00'));nr=json.loads(payload['native-run-02/run-receipt.json'])
assert datetime.datetime.fromisoformat(nr['started_at'])<start<datetime.datetime.fromisoformat(nr['finished_at'])
current=git('rev-parse','HEAD').decode().strip()
result=dict(source=head,base=base,owner_safe_sha256=sha(mr),owner_outer_sha256=sha(orr),candidate_count=64,outer_count=2,candidates=[dict(path=n,bytes=e['bytes'],sha256=e['sha256'],transformation='none') for n,e in entries.items()],immutable_head_bindings=3048,distinct_git_blobs=len(oids),stage_maps=18,stage_bindings=27432,all_five_fields_git_exact_records=27426,wip_working_bytes_exceptions=wip_exceptions,all_other_mode_type_blob_size_sha_exact=True,stage_results=stage_results,timing=dict(path=tn,bytes=len(payload[tn]),sha256=sha(payload[tn]),phase_count=43,http_count=298,dropped=t['dropped'],body_elapsed_ms=tr['body_elapsed_ms'],observed_timeout_ms=30000,retry=0,http_status_counts=dict(status),closed_shapes_static_routes_no_payload_ids=True),native01='SELECTOR_FAILURE_0_TESTS_CASE_NOT_RUN',native02='FIRST_ACTUAL_CASE_1_PASS_ONCE',failed_body_finally_dynamic='NOT_RUN: actual body PASS',original_ci_cause='UNKNOWN: owner handoff metadata only; referenced CI files not read by this reviewer',new_product_tests=False,no_unlisted_runtime_read=True,current_checkout_head=current,current_checkout_qualification='905 single workflow descendant reported separately; c02 graph and original stage snapshots reviewed immutably, no old live readback updated')
print(json.dumps(result,ensure_ascii=False,indent=2))
