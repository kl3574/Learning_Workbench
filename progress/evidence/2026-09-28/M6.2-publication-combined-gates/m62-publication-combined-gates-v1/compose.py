from pathlib import Path
import subprocess,json,hashlib,os
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-active');out=Path(__file__).resolve().parent
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
head=git('rev-parse','HEAD').decode().strip();assert head.startswith('62118f8')
base='ce42bf8cae734e49166a1472184fd9c3fa875bc7'
groups={'observer':('e947b1be7804dc043df879039bcb6df5dbcf161e',base),'service':('dec1d937523f4596da4c39bcc27750d9132c752c',base),'http':('833f0a84168638ba5ce421c70cd2f20a71e45e48','dec1d937523f4596da4c39bcc27750d9132c752c')}
owners={};counts={}
for label,(commit,parent) in groups.items():
 paths=[p for p in git('diff','--name-only',parent,commit).decode().splitlines() if not p.startswith('progress/')];counts[label]=len(paths)
 for p in paths:
  assert p not in owners;owners[p]=(label,commit)
rows=[]
for raw in git('ls-files','-z').split(b'\0'):
 if not raw or raw.startswith(b'progress/'):continue
 p=raw.decode();label,origin=owners.get(p,('unchanged-base',base));f=root/p;data=os.readlink(f).encode() if f.is_symlink() else f.read_bytes()
 assert data==git('show',head+':'+p)==git('show',origin+':'+p),p
 rows.append({'path':p,'source':label,'source_commit':origin,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
assert len(rows)==1028 and counts=={'observer':9,'service':16,'http':8}
(out/'composition.json').write_text(json.dumps({'candidate':head,'base':base,'changed_groups':counts,'engineering_inputs':rows,'verified_actual_worktree_and_both_git_sources':True},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'code_commit':head,'engineering_inputs':len(rows),'groups':counts,'status':'COMPOSITION_VERIFIED_GATES_NOT_RUN'}))
