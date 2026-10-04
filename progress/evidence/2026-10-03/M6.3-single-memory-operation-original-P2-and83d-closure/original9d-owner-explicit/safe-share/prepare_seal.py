"""Prepare a local explicit evidence package, never copy a database or temp tree."""
import hashlib, importlib.util, json, re, subprocess
from pathlib import Path
root=Path(__file__).parent
repo=root.parent/'m63-generic-approval-execution-oct04'
base='fdd3a949fc9bc6edb2d136b912f3d8d1cdba4b81'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,value):(root/p).write_text(json.dumps(value,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=repo)
head=git('rev-parse','HEAD').decode().strip()
assert not git('status','--porcelain')
changed={}
for name in git('diff','--name-only',base,head).decode().splitlines():
    data=git('show',head+':'+name)
    changed[name]={'git_blob':git('rev-parse',head+':'+name).decode().strip(),'sha256':sha(data),'bytes':len(data)}
originals=['services/api/app/application/provider_codex_profile.py','services/api/app/application/provider_codex_execution.py','services/api/app/application/codex_approval_models.py','services/api/app/codex_bootstrap_dto.py','services/api/app/codex_turn_dto.py','migrations/0001_baseline.sql','packages/contracts/domain_models.py','PRODUCT_DESIGN.md']
assert all(git('show',base+':'+name)==git('show',head+':'+name) for name in originals)
write('SOURCE_BINDINGS.json',{'base':base,'final_head':head,'final_tree':git('rev-parse','HEAD^{tree}').decode().strip(),'spec_sha256':sha(git('show',head+':PRODUCT_DESIGN.md')),'changed_paths':changed,'unchanged_original_paths':originals,'request_profile_reference':'351f7afa5bd1554696f4a8e3cb1683c24f98deac','source_scope':'1430 tracked nonprogress inputs; full before/after maps per formal stage','runtime_scope':'Synthetic explicit literal-memory interpreter only; production operation registry empty; no CLI/model/account/host tool/network acceptance.'})
stages=['approved-operation-red','first-owned-execution','authority-boundaries','unknown-turn-red','unknown-turn-green','operation-history','final-related']
history=[]
for name in stages:
    r=json.loads((root/name/'receipt.json').read_text());log=(root/name/'run.log').read_bytes()
    summaries=[line for line in log.decode().splitlines() if re.match(r'^\d+ (?:passed|failed)',line)]
    history.append({'stage':name,'head':r['head'],'exit':r['exit_code'],'count':r['source_count'],'seconds':r['elapsed_seconds'],'log_sha256':sha(log),'pytest_summary':summaries})
write('GATE_HISTORY.json',{'stages':history,'nonformal_failures':['wip-mypy.log: 19 type errors on implementation WIP','wip-mypy-02.log: 1 remaining optional-owner type error; no source map or formal acceptance claimed']})
pairs=[]
for red,green,path in [('approved-operation-red','first-owned-execution','tests/integration/test_codex_approved_operation_http.py'),('unknown-turn-red','unknown-turn-green','tests/integration/test_codex_operation_execution_boundaries.py')]:
    a=next(x['head'] for x in history if x['stage']==red);b=next(x['head'] for x in history if x['stage']==green)
    data=git('show',a+':'+path);assert data==git('show',b+':'+path)
    pairs.append({'red':red,'green':green,'red_head':a,'green_head':b,'path':path,'whole_file_sha256':sha(data),'whole_file_equal':True})
write('RED_GREEN_BINDINGS.json',{'pairs':pairs})
raw=['run_gate.py','run_static.py','run_static_final.py','prepare_seal.py','SOURCE_BINDINGS.json','GATE_HISTORY.json','RED_GREEN_BINDINGS.json','REPORT.md','wip-ruff.log','wip-mypy.log','wip-mypy-02.log','first-owned-mypy.log','VERIFY_ATTEMPT_01.stdout','VERIFY_ATTEMPT_01.json']
for name in stages:
    raw += [name+'/'+file for file in ['before.json','after.json','receipt.json','run.log']]
for name in ['static-final-01','static-final-02']:
    raw += [name+'/'+file for file in ['before.json','after.json','receipt.json','ruff.log','mypy.log','generated.log','spec.log','typescript.log','whitespace.log']]
assert len(raw)==len(set(raw))
# Failed output remains private even if a broad scanner does not flag it.
private={'wip-mypy.log','wip-mypy-02.log'} | {x['stage']+'/run.log' for x in history if x['exit']!=0}
spec=importlib.util.spec_from_file_location('publication_scan',repo/'scripts/check_publication.py');scan=importlib.util.module_from_spec(spec);spec.loader.exec_module(scan)
files=[];safe=[];rejected=[]
for name in raw:
    data=(root/name).read_bytes();files.append({'path':name,'sha256':sha(data),'bytes':len(data)})
    if name in private:continue
    public=data.replace(bytes([47,104,111,109,101,47,108,107,120]),b'$HOME')
    if scan.inspect('progress/evidence/generic-memory/'+name,public) or re.search(rb'(?i)(authorization|x-csrf-token|cookie)["\x27]?\s*[:=]\s*["\x27]?[A-Za-z0-9_+/=-]{16,}',public):
        rejected.append({'path':name,'sha256':sha(data)});continue
    dest=root/'safe-share'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(public)
    safe.append({'path':name,'raw_sha256':sha(data),'raw_bytes':len(data),'public_sha256':sha(public),'public_bytes':len(public),'transform':'exact ASCII prefix [47,104,111,109,101,47,108,107,120] -> $HOME'})
write('RAW_MANIFEST.json',{'count':len(files),'files':files,'scope':'Explicit original evidence only; excludes all databases, basetemp, TMPDIR, profiles and unrelated files.'})
write('SAFE_SHARE.json',{'count':len(safe),'files':safe,'private_only':sorted(private),'scanner_rejected':rejected,'scope':'Only these exact derived files may be copied. No glob or raw log publication.'})
print(json.dumps({'head':head,'raw_count':len(files),'safe_count':len(safe),'rejected_count':len(rejected)}))
