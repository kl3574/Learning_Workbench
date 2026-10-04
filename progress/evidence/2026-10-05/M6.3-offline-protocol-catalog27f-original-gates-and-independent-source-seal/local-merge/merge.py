from pathlib import Path
import hashlib,json,subprocess,datetime
OUT=Path(__file__).resolve().parent
R=Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
OLD='0d67327f701f3768bc3cc7e084cf0f811f742dc2';SRC='27f549ff5a8fd67b0a601b67a5ba51ef35f6765f';BASE='8b8699d3aad45180ab3b339ea60979c1478f0b92'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def put(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def tree(ref):
 d={}
 for row in git('ls-tree','-r','-z',ref).split(b'\0'):
  if row:
   h,p=row.split(b'\t',1);d[p.decode()]=h.decode()
 return d
review=Path('$HOME/.cache/learning-workbench-acceptance/m63-catalog27f-root-independent-oct05/READBACK.json')
q=json.loads(review.read_bytes());assert q['final']==SRC and q['candidate_count']==98 and q['final_inputs']==1541
assert git('rev-parse','HEAD').decode().strip()==OLD and not git('diff','--cached','--name-only')
dirty=git('diff','--name-only').decode().splitlines();assert set(dirty)=={'progress/state.json','progress/CURRENT.md'}
assert not git('ls-files','--others','--exclude-standard')
preserved={}
for p in dirty:
 b=(R/p).read_bytes();target=OUT/'before'/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b);preserved[p]=sha(b)
old=tree(OLD);source=tree(SRC);owned=git('diff','--name-only',BASE,SRC).decode().splitlines()
assert len(owned)==14 and all(p not in old for p in owned)
assert {p:v for p,v in old.items() if not p.startswith('progress/')}=={p:v for p,v in tree(BASE).items() if not p.startswith('progress/')}
argv=['git','merge','--no-ff','-m','Merge verified offline Codex turn protocol catalog',SRC]
put('command.json',{'argv':argv,'cwd':str(R),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'review_sha256':sha(review.read_bytes()),'local_only':True})
x=subprocess.run(argv,cwd=R,capture_output=True);(OUT/'stdout').write_bytes(x.stdout);(OUT/'stderr').write_bytes(x.stderr)
put('receipt.json',{'exit_code':x.returncode,'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
assert x.returncode==0
head=git('rev-parse','HEAD').decode().strip();after=tree(head)
assert len(after)==len(old)+14 and all(after[p]==v for p,v in old.items())
assert {p:v for p,v in after.items() if not p.startswith('progress/')}=={p:v for p,v in source.items() if not p.startswith('progress/')}
assert git('rev-list','--parents','-n','1',head).decode().split()==[head,OLD,SRC]
assert {p:sha((R/p).read_bytes()) for p in dirty}==preserved and not git('diff','--cached','--name-only')
U=Path('$HOME/Desktop/learning/Learning_Workbench');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=U).decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2' and not subprocess.check_output(['git','status','--porcelain'],cwd=U)
put('READBACK.json',{'old':OLD,'source':SRC,'new':head,'parents':[OLD,SRC],'owned_paths':owned,'engineering_inputs':1541,'old_committed_paths_preserved_exact':len(old),'old_progress_entries_exact':True,'dirty_files_byte_exact':preserved,'source_engineering_tree_exact':True,'index_empty':True,'original_user_checkout_clean_unchanged':True,'actual_scope':'ordinary local source merge only; no remote release/merge/model','qualification':'68 focused/186 related/5 static original final27f gates, independently bound; not full Python/native/production execution acceptance'})
print(json.dumps({'local_merge':head,'inputs':1541,'old_paths_preserved':len(old),'dirty_preserved':2}))
