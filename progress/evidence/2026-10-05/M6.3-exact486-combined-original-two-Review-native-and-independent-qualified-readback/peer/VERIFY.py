"""Verify only exact admitted gate metadata and Git inputs; never execute tests."""
from pathlib import Path
import json,hashlib,subprocess,re,math,collections,datetime
repo=Path('$HOME/.cache/learning-workbench-acceptance/m63-review-combined-486939-oct05')
seal=Path('$HOME/.cache/learning-workbench-acceptance/m63-review-combined-486939-evidence-oct05/seal-486939')
head='4869393654446c1dfcb0da97b9dca5fa7429b36f'
sha=lambda b:hashlib.sha256(b).hexdigest()
mr=(seal/'SAFE_CANDIDATES.json').read_bytes();orr=(seal/'READBACK.json').read_bytes()
assert sha(mr)=='da7b3e578495cf6ed3cae61e1df925c350d3028aa4e38c099267597d3520485a'
assert sha(orr)=='2a3b9b7c7846ea584976c9e5c2d036aa8d0e3ad2bc06eb978eaee40b7f89cd8a'
m=json.loads(mr);assert m['source']==head and m['count']==len(m['entries'])==26
payload={};entries={}
for e in m['entries']:
 n=e['candidate_path'];assert not Path(n).is_absolute() and '..' not in Path(n).parts and n not in payload
 b=(seal/'publication-candidates'/n).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'] and e['transformation']=='none';b.decode('utf-8')
 payload[n]=b;entries[n]=e
assert not any(n.endswith('.png') for n in entries)
git=lambda *args:subprocess.check_output(['git',*args],cwd=repo)
ref={};oids=set()
for row in git('ls-tree','-rz',head).split(b'\0'):
 if not row:continue
 meta,path=row.split(b'\t',1);mode,kind,oid=meta.decode().split();path=path.decode()
 if path.startswith('progress/'):continue
 assert kind=='blob';ref[path]=dict(mode=mode,type=kind,git_blob=oid);oids.add(oid)
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
v,_=proc.communicate(('\n'.join(sorted(oids))+'\n').encode());assert proc.returncode==0
at=0;blobs={}
for oid in sorted(oids):
 end=v.index(b'\n',at);actual,kind,size=v[at:end].decode().split();size=int(size);b=v[end+1:end+1+size];at=end+size+2
 assert actual==oid and kind=='blob' and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 blobs[oid]=dict(bytes=size,sha256=sha(b))
assert at==len(v)
for item in ref.values():item.update(blobs[item['git_blob']])
assert len(ref)==1525
mapnames=[n for n in payload if n.endswith(('/before.json','/after.json'))]+['FIXED_SOURCE_INPUTS.json']
assert len(mapnames)==7
for n in mapnames:
 o=json.loads(payload[n]);assert o['head']==head and o['count']==1525 and o['files']==ref
assert ref['PRODUCT_DESIGN.md']['sha256']=='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
source=json.loads(payload['SOURCE_BINDINGS.json']);assert source['head']==head and source['config_sha256']==ref['tests/e2e/playwright.config.ts']['sha256']
for e in source['source_bindings']:
 assert e['sha256']==ref[e['path']]['sha256'] and e['bytes']==ref[e['path']]['bytes'] and e['exact']
 assert git('show',e['reference']+':'+e['path'])==git('show',head+':'+e['path'])
config=git('show',head+':tests/e2e/playwright.config.ts').decode()
assert 'workers: 1, timeout: 30000' in config and 'retries:' not in config
stages=[]
for n in ['static-list-01','static-list-02','native-run-02']:
 cmd=json.loads(payload[n+'/command.json']);rec=json.loads(payload[n+'/run-receipt.json'])
 assert all(rec[k]==v for k,v in cmd.items()) and rec['source']==head and rec['exit_code']==0
 assert rec['source_before_after_exact'] and payload[n+'/before.json']==payload[n+'/after.json']
 runner='run.py' if n=='static-list-01' else 'run-exact-file.py'
 assert rec['runner_sha256']==sha(payload[runner]) and rec['input_binding_sha256']==sha(payload['SOURCE_BINDINGS.json'])
 assert rec['log_sha256']==sha(payload[n+'/output.log'])
 assert rec['observation_source_sha256']==ref['tests/e2e/review.spec.ts']['sha256'] and rec['config_sha256']==ref['tests/e2e/playwright.config.ts']['sha256']
 assert datetime.datetime.fromisoformat(rec['started_at'])<datetime.datetime.fromisoformat(rec['finished_at']) and rec['elapsed_seconds']>0
 stages.append(dict(stage=n,command=rec['command'],command_exit=rec['exit_code'],log_sha256=rec['log_sha256'],runner_sha256=rec['runner_sha256'],started_at=rec['started_at'],finished_at=rec['finished_at'],elapsed_seconds=rec['elapsed_seconds']))
l1=payload['static-list-01/output.log'].decode();l2=payload['static-list-02/output.log'].decode();native=payload['native-run-02/output.log'].decode()
assert 'Total: 3 tests in 2 files' in l1 and 'draft-review.spec.ts:17:1' in l1
failure=json.loads(payload['static-list-01/failure.json']);assert failure['kind']=='AssertionError' and failure['command_exit']==0
lf=json.loads(payload['LIST_SELECTION_FAILURE.json']);assert lf['wrapper_exit']==1 and lf['command_exit']==0 and lf['native_cases_executed']==0 and lf['native_product_status']=='NOT_RUN'
assert 'Total: 2 tests in 1 file' in l2 and 'draft-review.spec.ts' not in l2
assert json.loads(payload['static-list-02/run-receipt.json'])['selected_tests']==2
assert 'Running 2 tests using 1 worker' in native and '2 passed (29.1s)' in native and '(15.4s)' in native and '(10.7s)' in native
assert ':36:1' in native and ':187:1' in native and ' failed' not in native
assert stages[-1]['command'][-1]=='tests/e2e/review.spec.ts' and '--list' not in stages[-1]['command']
runner=payload['run-exact-file.py'].decode();assert "listed['exit_code'] == 0 and listed['selected_tests'] == 2" in runner and "listed['runner_sha256'] == digest(Path(__file__).read_bytes())" in runner
tr=json.loads(payload['TIMING_READBACK.json']);metadata=tr['metadata_files'];assert len(metadata)==2
for e in metadata:assert sha(payload[e['path']])==e['sha256'] and len(payload[e['path']])==e['bytes']
t=json.loads(payload[metadata[0]['path']]);late=json.loads(payload[metadata[1]['path']])
assert set(t)==set(['version','body_started_at','observed_timeout_ms','retry','phases','http','dropped','limits','scope'])
assert t['observed_timeout_ms']==30000 and t['retry']==0 and t['limits']==dict(phases=128,http=512) and t['dropped']==dict(phases=0,http=0)
assert len(t['phases'])==43 and len(t['http'])==306
fixed=git('show',head+':tests/e2e/review.spec.ts').decode();rs=fixed[fixed.index('  const timingRoutes:'):fixed.index('  const timingPending')]
allowed_routes=set(re.findall(r", '(/api/v1/[^']+)'",rs));allowed_stages=set(re.findall(r"timingPhase\('([^']+)'\)",fixed));seq={}
for r in t['phases']:
 assert set(r)==set(['sequence','elapsed_ms','stage']) and r['stage'] in allowed_stages and r['sequence'] not in seq;seq[r['sequence']]=r['elapsed_ms']
for r in t['http']:
 required=set(['sequence','elapsed_ms','event','route','method']);assert required<=set(r)<=required|set(['status','request_elapsed_ms'])
 assert r['route'] in allowed_routes and r['method'] in ['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'] and r['event'] in ['request','response-headers','request-finished','request-failed']
 assert r['sequence'] not in seq;seq[r['sequence']]=r['elapsed_ms']
 if 'status' in r:assert type(r['status'])==int and 100<=r['status']<=599 and r['event']=='response-headers'
 if 'request_elapsed_ms' in r:assert math.isfinite(r['request_elapsed_ms']) and r['request_elapsed_ms']>=0
assert set(seq)==set(range(1,350)) and list(sorted(seq,key=seq.get))==list(range(1,350))
assert all(math.isfinite(v) and v>=0 for v in seq.values())
assert tr['phase_count']==43 and tr['http_event_count']==306 and tr['dropped']==t['dropped'] and tr['body_finally_elapsed_ms']==t['phases'][-1]['elapsed_ms']
for stage,value in tr['selected_stage_elapsed_ms'].items():assert next(r for r in t['phases'] if r['stage']==stage)['elapsed_ms']==value
counts=collections.Counter((r['method'],r['route'],r['status']) for r in t['http'] if 'status' in r)
assert counts==collections.Counter({(r['method'],r['route'],r['status']):r['count'] for r in tr['response_header_counts']})
expectedlate=[dict(event='handler-enter',invocation=1),dict(event='captured',invocation=1,status=200),dict(event='other-independent-visible'),dict(event='fulfill-enter',invocation=1),dict(event='fulfill-complete',invocation=1),dict(event='handlers-drained'),dict(event='client-chain-observed')]
assert late==tr['late_response_phases']==expectedlate
pres=json.loads(payload['PRIOR_SEAL_PRESERVATION.json']);pb=Path(pres['base'])
for n,digest in pres['exact_outer_metadata'].items():
 assert n in ['seal-c02e/SAFE_CANDIDATES.json','seal-c02e/READBACK.json','seal-905/SAFE_CANDIDATES.json','seal-905/READBACK.json']
 assert sha((pb/n).read_bytes())==digest
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain')
for path,e in ref.items():
 b=(repo/path).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256']
result=dict(source=head,reviewer='/root/m63_artifact_final_review_oct04',scope='Existing two-Review gate qualification only; no repeated source two-axis review',owner_safe_sha256=sha(mr),owner_outer_sha256=sha(orr),candidate_count=26,outer_count=2,candidate_bytes=sum(e['bytes'] for e in entries.values()),candidate_entries=[dict(path=n,bytes=e['bytes'],sha256=e['sha256'],transformation='none') for n,e in entries.items()],fixed_git_inputs=1525,distinct_git_blobs=len(oids),maps=mapnames,map_bindings=10675,all_mode_type_blob_size_sha_exact=True,all_three_before_after_exact=True,live_inputs_exact=True,stages=stages,list01=dict(command_exit=0,listed_tests=3,listed_files=2,wrapper_exit=1,wrapper_exit_evidence='Explicit LIST_SELECTION_FAILURE metadata cites original exec result; receipt exit_code is command0; original failure.json confirms guard assertion',business='NOT_RUN'),list02=dict(command_exit=0,wrapper_exit=0,listed_tests=2,listed_files=1),native=dict(command_exit=0,wrapper_exit=0,tests_passed=2,tests_failed=0,individual_seconds=[15.4,10.7],playwright_total_seconds=29.1,wrapper_seconds=stages[-1]['elapsed_seconds'],whole_133='NOT_RUN_ON_486'),budget=dict(timeout_ms=30000,workers=1,retry=0),timing=dict(bytes=metadata[0]['bytes'],sha256=metadata[0]['sha256'],phase_count=43,http_count=306,dropped=t['dropped'],body_finally_elapsed_ms=t['phases'][-1]['elapsed_ms'],closed_static_shapes=True),late=dict(bytes=metadata[1]['bytes'],sha256=metadata[1]['sha256'],phases=late,scope='One captured200/handler completion/finite JSON client-chain marker; subset zero-count/current409 assertions via original PASS log, not all React effects'),prior_four_outer_metadata_unchanged=True,no_screenshot_or_business_body_read=True,new_product_test_execution=False,no_unlisted_runtime_read=True,original_public35ae_CI_failures='PRESERVED_UNKNOWN; originals not admitted/read by this gate',whole_M63='NOT_ACCEPTED')
print(json.dumps(result,ensure_ascii=False,indent=2))
