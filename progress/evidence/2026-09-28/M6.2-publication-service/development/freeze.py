import hashlib, json, subprocess
from pathlib import Path
BASE=Path(__file__).parent
ROOT=BASE.parent/'m62-publication-service-active'
BASELINE='ce42bf8cae734e49166a1472184fd9c3fa875bc7'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(name,obj): (BASE/name).write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
commit=git('rev-parse','HEAD').decode().strip()
assert not git('status','--porcelain'), 'Candidate must be clean'
changed=git('diff','--name-only',BASELINE,commit).decode().splitlines()
pins=[]
for path in changed:
 raw=git('show',f'{commit}:{path}')
 assert raw==(ROOT/path).read_bytes()
 pins.append({'path':path,'sha256':sha(raw),'bytes':len(raw),'git_blob':git('rev-parse',f'{commit}:{path}').decode().strip()})
spec=(ROOT/'PRODUCT_DESIGN.md').read_bytes()
assert spec==Path('<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md').read_bytes()
save('final-source-pins.json',{'baseline':BASELINE,'implementation_commit':commit,'tree':git('rev-parse',f'{commit}^{{tree}}').decode().strip(),'spec_sha256':sha(spec),'changed_files':pins})
ledger=[]
for directory in sorted(p for p in BASE.iterdir() if p.is_dir() and (p/'receipt.json').exists()):
 receipt=json.loads((directory/'receipt.json').read_text())
 before=json.loads((directory/'inputs-before.json').read_text());after=json.loads((directory/'inputs-after.json').read_text())
 raw=(directory/'run.log').read_bytes()
 assert receipt['log_sha256']==sha(raw) and receipt['log_bytes']==len(raw)
 assert before==after and receipt['unchanged'] is True
 source=[]
 for path in sorted((directory/'source').rglob('*')):
  if path.is_file():
   relative=path.relative_to(directory/'source').as_posix()
   assert before[relative]=={'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size}
   source.append(relative)
 ledger.append({'stage':directory.name,'receipt':receipt,'retained_source_count':len(source),'all_retained_sources_match_before':True,
   'receipt_sha256':sha((directory/'receipt.json').read_bytes()),'inputs_before_sha256':sha((directory/'inputs-before.json').read_bytes()),'inputs_after_sha256':sha((directory/'inputs-after.json').read_bytes())})
save('run-ledger.json',ledger)
actual={}
for path in git('ls-tree','-r','--name-only',commit).decode().splitlines():
 if path.startswith('progress/'): continue
 raw=git('show',f'{commit}:{path}')
 actual[path]={'sha256':sha(raw),'bytes':len(raw)}
final=[]
for stage in ['16-final-mypy','17-final-ruff','18-final-related','19-migration-regression']:
 before=json.loads((BASE/stage/'inputs-before.json').read_text());after=json.loads((BASE/stage/'inputs-after.json').read_text())
 assert before==after==actual,stage
 assert json.loads((BASE/stage/'receipt.json').read_text())['exit_code']==0
 final.append({'stage':stage,'input_count':len(before),'all_git_inputs_match_before_and_after':True})
save('final-actual-git-verification.json',{'implementation_commit':commit,'source_count':len(actual),'stages':final,'all_stage_logs_receipts_and_retained_sources_verified':True,'verified_stage_count':len(ledger),'clean_worktree':True})
print(json.dumps({'commit':commit,'changed_files':len(pins),'stage_count':len(ledger),'actual_git_input_count':len(actual),'final_stages':final},indent=2))
