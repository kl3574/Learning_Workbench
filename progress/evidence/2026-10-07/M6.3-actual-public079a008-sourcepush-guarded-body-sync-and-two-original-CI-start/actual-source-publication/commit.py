from pathlib import Path
import datetime,hashlib,json,subprocess
O=Path(__file__).resolve().parent;R=O.parent/'m62-public-safe-oct02';H='d78c4d159a2831f7d5e1721a9a466ec5b3e66421'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def run(n,argv):
 assert not (O/(n+'-command.json')).exists();put(n+'-command.json',{'argv':argv,'cwd':str(R),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x=subprocess.run(argv,cwd=R,capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr)
 put(n+'-receipt.json',{'exit_code':x.returncode,'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert x.returncode==0,(n,x.returncode)
assert git('rev-parse','HEAD').decode().strip()==H
selection=json.loads((O/'CORRECTED_SELECTION.json').read_bytes())['files'];assert len(selection)==458
assert sorted(git('diff','--cached','--name-only').decode().splitlines())==sorted(selection)
docs=['progress/state.json','progress/CURRENT.md','progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md']
assert set(git('diff','--name-only').decode().splitlines())<=set(docs)
run('final-doc-stage',['git','add','--',*docs])
run('final-staged-diff',['git','diff','--cached','--check'])
run('final-publication',['uv','run','--frozen','--no-sync','python','scripts/check_publication.py'])
assert not git('diff','--name-only') and not git('ls-files','--others','--exclude-standard')
run('documentary-commit',['git','commit','-m','Record Broker and Authoring scoped verification with original terminal failures'])
new=git('rev-parse','HEAD').decode().strip();assert git('rev-parse','HEAD^').decode().strip()==H and not git('status','--porcelain')
assert sorted(git('diff','--name-only',H,new).decode().splitlines())==sorted(selection)
nonprogress=git('diff','--name-only',H,new,'--','.',':(exclude)progress/**').decode().splitlines();assert nonprogress==['.gitattributes']
def tree(ref):
 d={}
 for row in git('ls-tree','-rz',ref).split(b'\0'):
  if row:
   h,p=row.split(b'\t',1);d[p.decode()]=tuple(h.decode().split())
 return d
old,current=tree(H),tree(new)
assert set(old)<=set(current) and all(current[p]==v for p,v in old.items() if p not in docs+['.gitattributes'])
assert len([p for p in current if not p.startswith('progress/')])==1561
user=Path('$HOME/Desktop/learning/Learning_Workbench')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=user).decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=user)
put('COMMIT_READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_head':new,'parent':H,'paths':458,'evidence_files':453,'progress_docs':4,
 'engineering_count':1561,'nonprogress_change_only':'.gitattributes three exact immutable archive rules','other1560engineering_inputs_exact_d78':True,
 'old_progress_except4docs_exact':True,'clean':True,'user_b895_clean_unchanged':True,'sourcepush':False,'whole_M63_AC21_M7':'NOT_ACCEPTED','model_calls':0})
print(json.dumps({'new_head':new,'paths':458,'engineering':1561,'ordinary_local_commit':True,'sourcepush':False}))
