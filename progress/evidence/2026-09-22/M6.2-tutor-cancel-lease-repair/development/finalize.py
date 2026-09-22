from pathlib import Path
import datetime
import hashlib
import json
import subprocess

BASE=Path(__file__).resolve().parent
TREE=BASE.parent/'m62-tutor-cancel-lease-active'

def sha(data):return hashlib.sha256(data).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=TREE)
head=git('rev-parse','HEAD').decode().strip()
assert head=='7442033e4952645bd26332b25b70c23fa94af89b'
assert not git('status','--porcelain')
original=json.loads((BASE/'07-complete-tutor-green/inputs-after.json').read_bytes())
rows=[]
for row in original:
 blob=git('rev-parse',head+':'+row['path']).decode().strip()
 data=git('cat-file','blob',blob)
 assert len(data)==row['bytes'] and sha(data)==row['sha256']
 rows.append({**row,'git_blob':blob,'git_matches':True})
dump(BASE/'final-source-binding.json',{'head':head,'source_count':len(rows),'all_git_match':True,'files':rows})
show=git('show','--format=fuller','--stat',head)
(BASE/'commit-readback.log').write_bytes(show)
runs=[]
for stage in sorted(BASE.glob('[0-9][0-9]-*')):
 if not stage.is_dir():continue
 r=json.loads((stage/'receipt.json').read_bytes());log=(stage/'test.log').read_bytes()
 assert len(log)==r['log_bytes'] and sha(log)==r['log_sha256']
 assert sha((stage/'runner.py').read_bytes())==r['runner_sha256']
 assert sha((stage/'lease_probe.py').read_bytes())==r['probe_sha256']
 before=json.loads((stage/'inputs-before.json').read_bytes());after=json.loads((stage/'inputs-after.json').read_bytes())
 assert before==after and len(before)==954 and r['source_unchanged']
 same={x['path']:(x['bytes'],x['sha256']) for x in before}=={x['path']:(x['bytes'],x['sha256']) for x in rows}
 assert same==(stage.name[:2] not in {'01','02'})
 for p in (stage/'source').rglob('*'):
  if p.is_file():
   relative=p.relative_to(stage/'source').as_posix();pin=next(x for x in before if x['path']==relative)
   assert len(p.read_bytes())==pin['bytes'] and sha(p.read_bytes())==pin['sha256']
 runs.append({'stage':stage.name,'exit_code':r['exit_code'],'log_sha256':r['log_sha256'],'source_count':954,'source_unchanged':True,'matches_final_commit_source_bytes':same,'actual_last_line':log.decode(errors='replace').splitlines()[-1]})
assert len(runs)==7
changed=git('diff-tree','--no-commit-id','--name-only','-r',head).decode().splitlines()
assert changed==['tests/integration/test_tutor_runs.py']
receipt={'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':head,'parent':git('rev-parse',head+'^').decode().strip(),'source_count':954,'all_source_matches_actual_git':True,'worktree_clean':True,'changed_files':changed,'production_files_changed':0,'test_sha256':sha((TREE/changed[0]).read_bytes()),'commit_readback_sha256':sha(show),'final_binding_sha256':sha((BASE/'final-source-binding.json').read_bytes()),'runs':runs,'scope':'Original failures remain failed; no product source change; targeted tests do not claim parent full gate or CI rerun.'}
dump(BASE/'final-receipt.json',receipt)
selected=[]
for name in ['REPORT.md','initial-pins.json','checkout-source-comparison.json','original-failure-facts.json','scope-proof.json','toolchain-link-receipt.json','candidate.patch.log','run.py','run-suite.py','run-ruff.py','lease_probe.py','finalize.py','final-source-binding.json','final-receipt.json','commit-readback.log']:
 selected.append(BASE/name)
for prefix in ['source','originals']:
 selected.extend(p for p in (BASE/prefix).rglob('*') if p.is_file())
for run in runs:
 stage=BASE/run['stage']
 for name in ['inputs-before.json','inputs-after.json','receipt.json','test.log','runner.py','lease_probe.py','probe-facts.json']:
  p=stage/name
  if p.exists():selected.append(p)
 selected.extend(p for p in (stage/'source').rglob('*') if p.is_file())
files=[{'path':p.relative_to(BASE).as_posix(),'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in sorted(set(selected))]
dump(BASE/'manifest.json',{'version':1,'private_only':True,'head':head,'files':files,'excluded':['Private pytest directories and SQLite databases','secret/session stores','toolchain/dependency trees'],'scope':'Selected immutable diagnosis, original local/CI failures and all seven bounded commands. Raw logs remain private pending any later exact sanitation.'})
print(json.dumps({'head':head,'files':len(files),'manifest_sha256':sha((BASE/'manifest.json').read_bytes()),'final_receipt_sha256':sha((BASE/'final-receipt.json').read_bytes()),'binding_sha256':receipt['final_binding_sha256']},indent=2))
