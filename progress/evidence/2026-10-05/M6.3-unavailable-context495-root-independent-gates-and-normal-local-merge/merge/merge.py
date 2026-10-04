import datetime, hashlib, json, subprocess
from pathlib import Path
b=Path('$HOME/.cache/learning-workbench-acceptance');r=b/'m62-public-safe-oct02';o=Path(__file__).parent
base='6671dd5c924edbac8ca7f479c4f51d4afec14480';source='495e4daddddb64460326659be5af341085654131'
def sha(x):return hashlib.sha256(x).hexdigest()
def g(*a):return subprocess.check_output(['git',*a],cwd=r)
def tree(ref):
 result={}
 for row in g('ls-tree','-rz',ref).split(b'\0'):
  if row:
   h,p=row.split(b'\t',1);result[p.decode()]=h.decode()
 return result
assert g('rev-parse','HEAD').decode().strip()==base and not g('diff','--cached','--name-only')
review=b/'m63-unavailable-context495-root-independent-oct05/READBACK.json';q=json.loads(review.read_text())
assert q['source']==source and not q['standards_findings'] and not q['spec_findings'] and q['final_focused_passed']==30 and q['final_related_passed']==334
owned=g('diff','--name-only',base,source).decode().splitlines();assert len(owned)==6 and all(not x.startswith('progress/') for x in owned)
dirty=g('diff','--name-only').decode().splitlines();assert set(dirty)=={'progress/state.json','progress/CURRENT.md','progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md'}
files=dirty+g('ls-files','--others','--exclude-standard').decode().splitlines()
assert all(x.startswith('progress/') for x in files)
before={}
for name in files:
 raw=(r/name).read_bytes();p=o/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);before[name]=sha(raw)
old=tree(base);owner=tree(source)
assert all(old[x]==owner[x] for x in old if x not in owned)
assert len(owner)==len(old)+2
argv=['git','merge','--no-ff','-m','Merge verified M6.3 unavailable preparation context',source]
(o/'command.json').write_text(json.dumps({'argv':argv,'cwd':str(r),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root_review_sha256':sha(review.read_bytes()),'local_only':True},indent=2)+'\n')
x=subprocess.run(argv,cwd=r,capture_output=True);(o/'stdout').write_bytes(x.stdout);(o/'stderr').write_bytes(x.stderr)
(o/'receipt.json').write_text(json.dumps({'exit_code':x.returncode,'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
assert x.returncode==0
head=g('rev-parse','HEAD').decode().strip();after=tree(head);assert after==owner
assert g('rev-list','--parents','-n','1','HEAD').decode().strip().split()==[head,base,source]
assert {x:sha((r/x).read_bytes()) for x in files}==before and not g('diff','--cached','--name-only')
user=Path('$HOME/Desktop/learning/Learning_Workbench');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=user).decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2' and not subprocess.check_output(['git','status','--porcelain'],cwd=user)
result={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'old_canonical':base,'source':source,'new_canonical':head,'parents':[base,source],
 'source_changed_paths':owned,'preserved_committed_nonoverlap_paths':len(old)-len([p for p in owned if p in old]),'preserved_local_files':before,
 'all_old_progress_git_entries_exact':True,'all_local_dirty_and_untracked_bytes_exact':True,'index_empty':True,'user_checkout_unchanged_clean':True,
 'engineering_inputs':sum(not p.startswith('progress/') for p in after),'focused_original':30,'related_original':334,
 'owner_publication_seal':'PENDING_SEPARATE_QUALIFICATION','public_branch_pr_head':base,'public6671_original_CI':'TWO_INTEGRATION_RUNNING_OTHER_TEN_JOBS_SUCCESS',
 'new_combination_whole_python_native':'NOT_RUN','whole_M6_3_AC21_M7':'NOT_ACCEPTED','remote_mutation_or_model':False}
(o/'READBACK.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'local_merge':head,'preserved_local_files':len(files),'engineering_inputs':result['engineering_inputs'],'remote_mutation':False}))
