"""Ordinary authorized source push; save all API bytes before checking them."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

base=Path('$HOME/.cache/learning-workbench-acceptance')
root=base/'m62-public-safe-oct02'
out=Path(__file__).parent
head='079a008cf88b37e4517cb391503a1e7393ccf374'
old='1e7ad7a8656c0dc8373d4181fa3002f385ed1847'
ref='feat/M6.3-local-control-bootstrap'
assert not (out/'READBACK.json').exists()
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def run(label,argv):
    assert not (out/(label+'-command.json')).exists()
    save(label+'-command.json',{'argv':argv,'cwd':str(root),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    r=subprocess.run(argv,cwd=root,capture_output=True)
    (out/(label+'.stdout')).write_bytes(r.stdout);(out/(label+'.stderr')).write_bytes(r.stderr)
    save(label+'-receipt.json',{'exit_code':r.returncode,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'stdout_sha256':sha(r.stdout),'stderr_sha256':sha(r.stderr)})
    return r
def gh(label,path):
    r=run(label,['gh','api',path]);assert r.returncode==0
    return json.loads(r.stdout)
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
# The root records the fixed audit report path and digest after reading it.
permit=json.loads((out/'AUDIT_ADMISSION.json').read_text())
assert permit['head']==head and permit['bounded_publication_pass'] is True
assert sha(Path(permit['report_path']).read_bytes())==permit['report_sha256']
assert git('rev-parse','HEAD').decode().strip()==head
assert git('branch','--show-current').decode().strip()==ref
assert git('status','--porcelain')==b''
assert subprocess.run(['git','merge-base','--is-ancestor',old,head],cwd=root).returncode==0
remote=git('config','--get','remote.origin.url').decode().strip()
assert remote in ['https://github.com/kl3574/Learning_Workbench.git','https://github.com/kl3574/Learning_Workbench','git@github.com:kl3574/Learning_Workbench.git']
assert gh('identity','user')['login']=='kl3574'
branch=gh('branch-before','repos/kl3574/Learning_Workbench/branches/'+ref)
pr=gh('pr-before','repos/kl3574/Learning_Workbench/pulls/56')
assert branch['commit']['sha']==old and pr['head']['sha']==old
assert pr['draft'] and pr['state']=='open' and pr['merged_at'] is None
assert pr['base']['sha']=='e2877101d9c2bda0f793a460db63ef496350c6b4'
r=run('sourcepush',['git','push','origin','HEAD:refs/heads/'+ref])
save('PUSH_COMMAND_OUTCOME.json',{'expected_head':head,'git_exit_code':r.returncode,
 'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'qualification':'gitexit alone does not confirm API branch/PR exacthead.'})
assert r.returncode==0
branch=gh('branch-after','repos/kl3574/Learning_Workbench/branches/'+ref)
pr=gh('pr-after','repos/kl3574/Learning_Workbench/pulls/56')
confirmed=branch['commit']['sha']==head and pr['head']['sha']==head and pr['draft'] and pr['state']=='open' and pr['merged_at'] is None
save('READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'ACTUAL_ORDINARY_SOURCEPUSH_EXACT_BRANCH_AND_DRAFT_PR_HEAD' if confirmed else 'GIT_SUCCESS_API_HEAD_CONFIRMATION_PENDING',
 'expected_head':head,'branch_head':branch['commit']['sha'],'pr_head':pr['head']['sha'],
 'git_exit_code':r.returncode,'draft':pr['draft'],'state':pr['state'],'merged_at':pr['merged_at'],
 'actual_model_calls':0,'github_merge_release_deploy':False})
print(json.dumps({'git_exit_code':r.returncode,'exact_head_confirmed':confirmed,'expected_head':head}))
