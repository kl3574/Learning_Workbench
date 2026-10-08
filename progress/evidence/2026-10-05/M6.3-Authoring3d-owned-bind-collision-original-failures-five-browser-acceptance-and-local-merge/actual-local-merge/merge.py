from pathlib import Path
import json,hashlib,subprocess,datetime
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
OLD='89868473810d8cf32ce2828f39770af85f557eca';SRC='3d4520e9a35e325e3f6062429229fbce8ca5e105';BASE='68a280b9cf251bbf79c2ca188ac8b4aefe7562e0'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def tree(ref):
 d={}
 for row in git('ls-tree','-r','-z',ref).split(b'\0'):
  if row:
   meta,path=row.split(b'\t',1);d[path.decode()]=meta.decode()
 return d
review=B/'m63-authoring3d-root-independent-oct05/READBACK.json';q=json.loads(review.read_bytes())
assert q['fixed_source']==SRC and q['candidate_count']==72 and q['complete_engineering_inputs']==1556
assert q['source_review']['spec_P1_P2']==q['source_review']['standards_P1_P2']==0
assert git('rev-parse','HEAD').decode().strip()==OLD and not git('diff','--cached','--name-only')
dirty=git('diff','--name-only').decode().splitlines();assert set(dirty)=={'progress/state.json','progress/CURRENT.md','progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md'}
untracked=git('ls-files','--others','--exclude-standard').decode().splitlines()
assert len(untracked)==167 and all(p.startswith(('progress/evidence/2026-10-05/M6.3-Broker6f-synthetic-control-owner-original-failures-qualified-gates-and-local-merge/','progress/evidence/2026-10-05/M6.3-public1e-original-terminal86-failures-independent-twelve-job-readback/')) for p in untracked)
untracked_hash={p:sha((R/p).read_bytes()) for p in untracked};preserved={}
for p in dirty:
 b=(R/p).read_bytes();d=O/'before'/p;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(b);preserved[p]=sha(b)
old,source,base=tree(OLD),tree(SRC),tree(BASE);owned=git('diff','--name-only',BASE,SRC).decode().splitlines()
assert owned==['tests/e2e/authoringRuntime.ts','tests/e2e/ownedStartup.node.ts','tests/e2e/ownedStartup.ts','tests/e2e/ownedStartupBounds.node.ts']
assert old['tests/e2e/authoringRuntime.ts']==base['tests/e2e/authoringRuntime.ts'] and sum(p not in old for p in owned)==3
argv=['git','merge','--no-ff','-m','Merge reviewed bounded owned Authoring startup and actual five-case acceptance',SRC]
put('command.json',{'argv':argv,'cwd':str(R),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root_review_sha256':sha(review.read_bytes()),'local_only':True})
x=subprocess.run(argv,cwd=R,capture_output=True);(O/'stdout').write_bytes(x.stdout);(O/'stderr').write_bytes(x.stderr)
put('receipt.json',{'exit_code':x.returncode,'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
assert x.returncode==0
head=git('rev-parse','HEAD').decode().strip();after=tree(head)
assert len(after)==len(old)+3 and all(after[p]==v for p,v in old.items() if p not in owned)
assert all(after[p]==source[p] for p in owned) and len([p for p in after if not p.startswith('progress/')])==1561
assert git('rev-list','--parents','-n','1',head).decode().split()==[head,OLD,SRC]
assert {p:sha((R/p).read_bytes()) for p in dirty}==preserved
assert git('ls-files','--others','--exclude-standard').decode().splitlines()==untracked and {p:sha((R/p).read_bytes()) for p in untracked}==untracked_hash
assert not git('diff','--cached','--name-only')
U=Path('$HOME/Desktop/learning/Learning_Workbench');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=U).decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2' and not subprocess.check_output(['git','status','--porcelain'],cwd=U)
put('READBACK.json',{'old':OLD,'source':SRC,'new':head,'parents':[OLD,SRC],'owned_paths':owned,'engineering_inputs':1561,
 'all_old_committed_paths_except1declared_harness_exact':len(old)-1,'all_old_progress_and_Broker6f_entries_exact':True,
 'dirty4docs_byte_exact':preserved,'untracked167files_byte_exact':untracked_hash,'original_user_checkout_clean_unchanged':True,
 'qualification':'5fb10ownedNode behavior separate;final3dstrict4harnessTS/build/list0/actual5cases5PASS with all1556fixedinputsexact;root72candidates12stages qualified',
 'original_failures':'TS7016/listerrno122/CJSnamedexport/actuallongTMPDIR5FAIL remain; latter corrected only via explicitshortownedTMPDIR',
 'limits':'No actualVitecollisioninjection/whole133/new1561fullPython/newCI/Reviewgrading or physicalnumeric/wholeM6 acceptance',
 'public_remote_head_unchanged':'1e7ad7a8656c0dc8373d4181fa3002f385ed1847','scope':'local normal merge only; no remote/model/probe'})
print(json.dumps({'local_merge':head,'engineering_inputs':1561,'dirty4docs_preserved':True,'untracked167preserved':True,'remote_write':False}))
