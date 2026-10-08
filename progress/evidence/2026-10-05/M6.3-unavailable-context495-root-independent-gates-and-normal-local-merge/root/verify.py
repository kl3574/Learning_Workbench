import datetime, hashlib, json, os, subprocess
from pathlib import Path
b=Path('$HOME/.cache/learning-workbench-acceptance')
r=b/'m63-production-preparation-closure-oct05';e=b/'m63-production-preparation-closure-evidence-oct05';o=Path(__file__).parent
head='495e4daddddb64460326659be5af341085654131';base='6671dd5c924edbac8ca7f479c4f51d4afec14480'
def sha(x): return hashlib.sha256(x).hexdigest()
def git(*x):return subprocess.check_output(['git',*x],cwd=r)
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain')
expected={}
for row in git('ls-tree','-rz',head).split(b'\0'):
 if not row:continue
 h,p=row.split(b'\t',1);p=p.decode();mode,typ,blob=h.decode().split()
 if not p.startswith('progress/'):expected[p]=(mode,typ,blob)
assert len(expected)==1527
stages=['focused-final-02','related-final-02','ruff-final-02','mypy-final-02','spec-final-02','generated-final-02','diff-final-02'];qualified=[]
for stage in stages:
 p=e/stage;c=json.loads((p/'command.json').read_text());v=json.loads((p/'receipt.json').read_text());a=json.loads((p/'before.json').read_text());z=json.loads((p/'after.json').read_text());log=(p/'run.log').read_bytes()
 assert c['source_head']==v['head']==a['head']==head and a==z and v['before_after_complete_exact']
 assert v['command_exit_code']==v['wrapper_exit_code']==0 and a['count']==v['input_count']==len(a['entries'])==1527
 assert sha(log)==v['log_sha256'] and len(log)==v['log_size']
 assert c['runner_sha256']==v['runner_sha256']==sha((e/'run_stage.py').read_bytes())
 assert {x['path']:(x['mode'],x['type'],x['blob']) for x in a['entries']}==expected
 qualified.append({'stage':stage,'command':c['argv'],'receipt_sha256':sha((p/'receipt.json').read_bytes()),'log_sha256':sha(log),'before_sha256':sha((p/'before.json').read_bytes()),'after_sha256':sha((p/'after.json').read_bytes()),'command_and_wrapper_exit':0,'complete_inputs':1527})
# One full exact bounded current source read independently verifies all declared blobs.
for x in a['entries']:
 p=r/x['path'];body=os.readlink(p).encode() if x['mode']=='120000' else p.read_bytes()
 assert len(body)==x['size'] and sha(body)==x['sha256']
 assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==x['blob']
counts=[json.loads(x) for x in (e/'focused-final-02/case-receipts.jsonl').read_text().splitlines()]
assert len(counts)==18 and all(len(x['counts'])==9 and set(x['counts'].values())=={0} and x['synthetic_bootstrap_setup_calls']==1 for x in counts)
for name,code in [('first-behavior-red',1),('first-behavior-green',0),('mypy-01',1),('ruff-final',1)]:
 p=e/name;v=json.loads((p/'receipt.json').read_text());raw=(p/'run.log').read_bytes();assert v['command_exit_code']==code and sha(raw)==v['log_sha256']
first='tests/integration/test_codex_unavailable_preparation_closure.py'
assert git('show','7c1058f977f33b167036830c315b693cfbae2084:'+first)==git('show','de4d12da56100a6b06c065e41881b69ba0ee8127:'+first)
owned=git('diff','--name-only',base,head).decode().splitlines();assert len(owned)==6
for item in ['PRODUCT_DESIGN.md','migrations/0001_baseline.sql','packages/contracts/domain_models.py','services/api/app/application/codex_bootstrap_models.py','services/api/app/application/codex_turn_models.py','services/api/app/application/codex_turn_execution_models.py','services/api/app/codex_turn_dto.py','services/api/app/main.py']:
 assert git('rev-parse',base+':'+item)==git('rev-parse',head+':'+item)
report={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':base,'source':head,
 'reviewer':'root independent reviewer; implementation owner is separate','source_review':'Full five changed application files and final439line test read; existing owner ports/static bindings read; no P1/P2 finding',
 'standards_findings':[],'spec_findings':[], 'sole_spec_sha256':'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec',
 'qualified_original_stages':qualified,'final_focused_passed':30,'final_related_passed':334,'related_files':9,
 'one_live_source_scan_inputs':1527,'original_stage_map_bindings':21378,'case_receipts':18,'named_seam_zero_counts':162,
 'counter_limit':'Nine named application seams during new unavailable phase only; synthetic bootstrap setup1 each, two history setups each2 memory transport calls excluded. Not global OS or actual model monitoring.',
 'preserved_originals':['first desired behavior RED1FAIL; same original83line test GREEN1PASS','mypy-01 commandFAIL with3diagnostics, notpytest3FAIL','ruff-final originalF401 unused import; final495 onlyremoves import; originalnotrewritten'],
 'legacy_limit':'v1/v3 decoder roundtrip fixture uses declared manual codec pair, not real Provider oldproduction authorization. v2 related memory peer notactual CLI.',
 'qualification':'SCOPED_FINAL495_HTTP_SQLITE_PREPARE_READ_UNAVAILABLE_AND_STATIC_QUALIFIED; no new test executed by root',
 'production_input_proof_profile_checker_executor':'MISSING_IMPLEMENTATION_NOT_RUN','actual_external_model_calls':0,
 'whole_new_python_native_and_physical_broker':'NOT_RUN','whole_M6_3_AC21_M7':'NOT_ACCEPTED',
 'publication_candidates_qualification':'PENDING_OWNER_EXPLICIT_SEAL_READBACK; notyet source publication audit'}
(o/'READBACK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'source':head,'inputs':1527,'stage_bindings':21378,'focused':30,'related':334,'source_findings':0,'owner_seal_pending':True}))
