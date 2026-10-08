from pathlib import Path
import hashlib,json,subprocess,datetime
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
OLD='73ad831d5a1617e1ad478fb5371c1ae04b27c299'
SRC='6f5de88935c6ff7a79a87cf5440cc47f86fb0d10';BASE='68a280b9cf251bbf79c2ca188ac8b4aefe7562e0'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def tree(ref):
 result={}
 for row in git('ls-tree','-r','-z',ref).split(b'\0'):
  if row:
   meta,path=row.split(b'\t',1);result[path.decode()]=meta.decode()
 return result
review=B/'m63-broker6f-root-independent-oct05/READBACK.json';q=json.loads(review.read_bytes())
assert q['fixed_source']==SRC and q['candidate_count']==98 and q['actual_live_complete_inputs']==1558
assert q['source_review']['standards_P1_P2']==q['source_review']['spec_P1_P2']==0
assert git('rev-parse','HEAD').decode().strip()==OLD and not git('diff','--cached','--name-only')
dirty=git('diff','--name-only').decode().splitlines()
assert set(dirty)=={'progress/state.json','progress/CURRENT.md','progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md'}
assert not git('ls-files','--others','--exclude-standard').strip()
preserved={}
for p in dirty:
 b=(R/p).read_bytes();target=O/'before'/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b);preserved[p]=sha(b)
old,source,base=tree(OLD),tree(SRC),tree(BASE)
engineering=lambda m:{p:v for p,v in m.items() if not p.startswith('progress/')}
assert engineering(old)==engineering(base)
owned=git('diff','--name-only',BASE,SRC).decode().splitlines();assert len(owned)==8
assert sum(p not in old for p in owned)==5 and sorted(p for p in owned if p in old)==q['changed_prior_paths']
argv=['git','merge','--no-ff','-m','Merge independently verified synthetic Broker control owner and immutable history',SRC]
put('command.json',{'argv':argv,'cwd':str(R),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'review_sha256':sha(review.read_bytes()),'local_only':True})
x=subprocess.run(argv,cwd=R,capture_output=True);(O/'stdout').write_bytes(x.stdout);(O/'stderr').write_bytes(x.stderr)
put('receipt.json',{'exit_code':x.returncode,'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
assert x.returncode==0
head=git('rev-parse','HEAD').decode().strip();after=tree(head)
assert len(after)==len(old)+5 and all(after[p]==v for p,v in old.items() if p not in owned)
assert engineering(after)==engineering(source)
assert git('rev-list','--parents','-n','1',head).decode().split()==[head,OLD,SRC]
assert {p:sha((R/p).read_bytes()) for p in dirty}==preserved and not git('diff','--cached','--name-only')
assert not git('ls-files','--others','--exclude-standard').strip()
U=Path('$HOME/Desktop/learning/Learning_Workbench')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=U).decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=U)
put('READBACK.json',{'old':OLD,'source':SRC,'new':head,'parents':[OLD,SRC],'owned_paths':owned,'engineering_inputs':1558,
 'all_old_committed_paths_except3declared_source_changes_exact':len(old)-3,'all_old_progress_entries_exact':True,
 'dirty4docs_byte_exact':preserved,'untracked_empty_beforeafter':True,'source_engineering_tree_exact':True,
 'original_user_checkout_clean_unchanged':True,'index_empty':True,'qualification':'root98candidate fixedsource8maps15stages qualified; actual22focused473related5static; whole6f NOT_RUN',
 'limits':'synthetic_peer_only, explicit callback pump; no production modelproof/runtime registration, realIPC/processcleanup/numeric/wholeM6/M7 acceptance',
 'remote_head_unchanged':'1e7ad7a8656c0dc8373d4181fa3002f385ed1847','actual_scope':'ordinary local merge only; no remote/model/tool/probe'})
print(json.dumps({'local_merge':head,'engineering_inputs':1558,'dirty4docs_preserved':True,'remote_mutation':False}))
