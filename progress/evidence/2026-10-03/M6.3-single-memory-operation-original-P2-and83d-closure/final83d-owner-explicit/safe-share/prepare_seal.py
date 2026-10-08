"""Explicit local package; failed output never becomes an implicit candidate."""
import hashlib, importlib.util, json, re, subprocess
from pathlib import Path
root=Path(__file__).parent
repo=root.parent/'m63-operation-closure-fix-oct04'
base='9d3ffb0cebd6df099376ee4de37026e210891b02'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):(root/p).write_text(json.dumps(v,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=repo)
head=git('rev-parse','HEAD').decode().strip();assert not git('status','--porcelain')
changed={}
for name in git('diff','--name-only',base,head).decode().splitlines():
 b=git('show',head+':'+name);changed[name]={'git_blob':git('rev-parse',head+':'+name).decode().strip(),'sha256':sha(b),'bytes':len(b)}
unchanged=['services/api/app/application/provider_codex_profile.py','services/api/app/application/provider_codex_execution.py','services/api/app/application/codex_approval_models.py','services/api/app/application/codex_operation_models.py','services/api/app/infrastructure/codex_approval_repository.py','services/api/app/codex_bootstrap_dto.py','services/api/app/codex_turn_dto.py','migrations/0001_baseline.sql','packages/contracts/domain_models.py','PRODUCT_DESIGN.md']
assert all(git('show',base+':'+n)==git('show',head+':'+n) for n in unchanged)
write('SOURCE_BINDINGS.json',{'base':base,'final_head':head,'final_tree':git('rev-parse','HEAD^{tree}').decode().strip(),'spec_sha256':sha(git('show',head+':PRODUCT_DESIGN.md')),'changed_paths':changed,'unchanged_original_paths':unchanged,'request_profile_reference':'351f7afa5bd1554696f4a8e3cb1683c24f98deac','fixed_input_count':1434})
stages=['closure-red','closure-green','boundary-green','final-related','final-related-02','dependency-red','dependency-green','dependency-green-02','final-related-03'];history=[]
for name in stages:
 r=json.loads((root/name/'receipt.json').read_text());b=(root/name/'run.log').read_bytes()
 history.append({'stage':name,'head':r['head'],'exit':r['exit_code'],'source_equal':r['before_equals_after'],'count':r['source_count'],'seconds':r['elapsed_seconds'],'log_sha256':sha(b),'pytest_summary':[x for x in b.decode().splitlines() if re.match(r'^\d+ (?:passed|failed)',x)]})
write('GATE_HISTORY.json',{'stages':history,'boundary_green_limitation':'34 tests passed, but after map captured concurrent test edits. Not a fixed-source gate; original maps/receipt/log retained. Final related repeats all applicable cases on a clean frozen commit.','nonformal_static':'wip-static-01.json records one mypy type error from the tool result; no original standalone stderr file or fixed-source gate is claimed.'})
a=history[0]['head'];b=history[1]['head'];pairs=[]
for n in ['tests/unit/test_codex_operation_closure.py','tests/integration/test_codex_operation_closure_http.py']:
 raw=git('show',a+':'+n);assert raw==git('show',b+':'+n)
 pairs.append({'red_head':a,'green_head':b,'path':n,'whole_file_sha256':sha(raw),'whole_file_equal':True})
a=history[5]['head'];b=history[7]['head'];n='tests/unit/test_codex_operation_dependency_closure.py';raw=git('show',a+':'+n);assert raw==git('show',b+':'+n)
pairs.append({'red_head':a,'green_head':b,'path':n,'whole_file_sha256':sha(raw),'whole_file_equal':True})
write('RED_GREEN_BINDINGS.json',{'pairs':pairs,'old_boundary_test_not_same_bytes':'Old execute replacement instrumentation was replaced with bounded test-thread observation of the unchanged function. Original 9d tests remain in Git and its sealed evidence; do not call the boundary file a same-byte reversal.'})
raw=['PRESEAL_REPORT_EDIT.json','preseal-report-01/REPORT.md','preseal-report-01/RAW_MANIFEST.json','preseal-report-01/SAFE_SHARE.json','preseal-report-01/VERIFICATION.json','run_gate.py','run_static.py','run_static_final.py','run_static_complete.py','wip-dependency-ruff.log','wip-dependency-mypy.log','prepare_seal.py','SOURCE_BINDINGS.json','GATE_HISTORY.json','RED_GREEN_BINDINGS.json','REPORT.md','wip-static-01.json','legacy-v1-runtime.json','legacy-capture-receipt.json']
for stage in stages:raw += [stage+'/'+n for n in ['before.json','after.json','receipt.json','run.log']]
for stage in ['static-final-01','static-final-02','static-final-03']:
 raw += [stage+'/'+n for n in ['before.json','after.json','receipt.json','ruff.log','mypy.log','generated.log','spec.log','typescript.log','whitespace.log']]
private={x['stage']+'/run.log' for x in history if x['exit']!=0} | {'wip-dependency-mypy.log','preseal-report-01/REPORT.md','preseal-report-01/RAW_MANIFEST.json','preseal-report-01/SAFE_SHARE.json','preseal-report-01/VERIFICATION.json'}
spec=importlib.util.spec_from_file_location('scan',repo/'scripts/check_publication.py');scan=importlib.util.module_from_spec(spec);spec.loader.exec_module(scan)
files=[];safe=[];rejected=[]
for name in raw:
 data=(root/name).read_bytes();files.append({'path':name,'sha256':sha(data),'bytes':len(data)})
 if name in private:continue
 public=data.replace(bytes([47,104,111,109,101,47,108,107,120]),b'$HOME')
 if scan.inspect('progress/evidence/operation-closure/'+name,public) or re.search(rb'(?i)(authorization|x-csrf-token|cookie)["\']?\s*[:=]\s*["\']?[A-Za-z0-9_+/=-]{16,}',public):
  rejected.append({'path':name,'sha256':sha(data)});continue
 dest=root/'safe-share'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(public)
 safe.append({'path':name,'raw_sha256':sha(data),'raw_bytes':len(data),'public_sha256':sha(public),'public_bytes':len(public),'transform':'exact ASCII prefix [47,104,111,109,101,47,108,107,120] -> $HOME'})
write('RAW_MANIFEST.json',{'count':len(files),'files':files,'scope':'Explicit originals only; no DB, basetemp, TMPDIR, profiles or unrelated material.'})
write('SAFE_SHARE.json',{'count':len(safe),'files':safe,'private_only':sorted(private),'scanner_rejected':rejected,'scope':'Only named derivatives, never glob or raw failed log.'})
print(json.dumps({'raw':len(files),'safe':len(safe),'rejected':len(rejected),'head':head}))
