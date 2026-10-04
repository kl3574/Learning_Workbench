"""Fixed Git/source readback only; no application imports or execution."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(__file__).parent
repo=Path(sys.argv[1]) if len(sys.argv)>1 else root.parent/'m63-turn-interrupt-owner-oct04'
def git(*args):return subprocess.check_output(['git',*args],cwd=repo)
def sha(b):return hashlib.sha256(b).hexdigest()
head='79a3c0da4bef9d948bcd6a969a25ff55fd5833a0';base='cc2cc675f91a2794c44267e46687422d5ae50019';production='1b49cb6870f2b8e89337ddd26da82b5e46391e75'
assert git('merge-base',base,head).decode().strip()==base
names=git('diff','--name-only',base+'...'+head).decode().splitlines()
rows={}
for name in names+['PRODUCT_DESIGN.md','AGENTS.md','services/api/app/application/codex_bootstrap_access.py','services/api/app/infrastructure/codex_turn_jobs.py','services/api/app/application/codex_turn_worker.py']:
 data=git('show',head+':'+name);rows[name]={'blob':git('rev-parse',head+':'+name).decode().strip(),'sha256':sha(data),'bytes':len(data),'changed':name in names}
assert rows['PRODUCT_DESIGN.md']['sha256']=='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
assert git('diff','--name-only',production,head).decode().splitlines()==['tests/integration/test_codex_turn_interrupt_boundaries.py']
for name in names:
 if not name.startswith('tests/'):
  assert git('show',production+':'+name)==git('show',head+':'+name)
print(json.dumps({'scope':'static fixed Git only, zero product/test/CLI/DB execution','base':base,'head':head,'tree':git('rev-parse',head+'^{tree}').decode().strip(),'production':production,'changed_count':len(names),'source_bindings':rows,'complete_messages':git('log','--format=%H%n%B',base+'..'+head).decode(),'worktree_head':git('rev-parse','HEAD').decode().strip(),'worktree_status':git('status','--porcelain').decode(),'standards_findings':1,'standards_max_priority':'P3','spec_findings':0,'status':'SOURCE_BINDINGS_VERIFIED'},indent=2))
