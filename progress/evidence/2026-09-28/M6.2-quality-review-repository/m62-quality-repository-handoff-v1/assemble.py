from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, subprocess
BASE=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance')
ROOT=BASE/'m62-quality-repository-active'
OUT=Path(__file__).parent
DEV=BASE/'m62-quality-repository-verification-v1'
DEP=BASE/'m62-review-checks-verification-v1'
HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
TASK=['services/api/app/application/review_history_models.py','services/api/app/infrastructure/review_repository.py','tests/integration/test_review_repository.py','tests/integration/test_review_history.py','docs/adr/0024-quality-review-persistence.md']
DEPS=['services/api/app/application/review_checks.py','services/api/app/application/review_numeric.py','tests/integration/test_review_structure_checks.py','tests/integration/test_review_numeric_observations.py']
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
blobs={};trees={}
def blob(key):
 if key not in blobs:blobs[key]=git('cat-file','blob',key)
 return blobs[key]
def tree(commit):
 if commit not in trees:
  trees[commit]={}
  for r in git('ls-tree','-r','-z',commit).split(b'\0'):
   if not r:continue
   meta,path=r.split(b'\t');mode,kind,key=meta.decode().split()
   trees[commit][path.decode()]=(mode,key)
 return trees[commit]
# Original development and final combined gate receipts are preserved unchanged.
stages=[]
for path in sorted(DEV.glob('*/receipt.json')):
 r=json.loads(path.read_text());log=path.parent/'test.log';data=log.read_bytes()
 assert len(data)==r['log_bytes'] and sha(data)==r['log_sha256']
 b=json.loads((path.parent/'before.json').read_text());a=json.loads((path.parent/'after.json').read_text())
 assert b==a and r['source_unchanged'] and r['all_source_matches_git_before'] and r['all_source_matches_git_after']
 assert b['head']==r['code_commit'] and b['status']=='' and len(b['files'])==r['source_count']
 tr=tree(b['head']);expected={k for k in tr if not k.startswith('progress/')}
 assert {v['path'] for v in b['files']}==expected
 for f in b['files']:
  mode,key=tr[f['path']];raw=blob(key)
  assert mode==f['git_mode'] and key==f['git_blob_sha1']==f['actual_git_blob_sha1']
  assert len(raw)==f['bytes'] and sha(raw)==f['sha256'] and f['git_matches']
 lines=data.decode().splitlines()
 summary=next((line for line in reversed(lines) if ' passed' in line or ' failed' in line or ' errors' in line or line.startswith('Success:') or line=='All checks passed!'),None)
 stages.append({'stage':path.parent.name,'receipt':str(path.relative_to(BASE)),'receipt_sha256':sha(path.read_bytes()),'command':r['command'],'code_commit':r['code_commit'],'exit_code':r['exit_code'],'summary':summary,'log_sha256':r['log_sha256'],'log_bytes':len(data),'source_count':len(b['files']),'actual_git_binding':'PASS'})
# Copy immutable task source bytes and all intermediate task revisions needed to replay development.
commits=git('rev-list','--reverse','4bf176de1cdf0a76cdf0fa965027ec3a5367551f..'+HEAD).decode().splitlines()
source=[]
for commit in commits:
 paths=git('diff-tree','--no-commit-id','--name-only','-r',commit).decode().splitlines()
 for name in paths:
  if name not in TASK+DEPS:continue
  mode,key=tree(commit)[name];data=blob(key);dest=OUT/'source'/commit/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  source.append({'commit':commit,'path':name,'sha256':sha(data),'bytes':len(data),'git_blob_sha1':key,'copied_to':str(dest.relative_to(OUT))})
final=[]
for name in TASK+DEPS:
 mode,key=tree(HEAD)[name];data=blob(key)
 assert (ROOT/name).read_bytes()==data
 final.append({'path':name,'sha256':sha(data),'bytes':len(data),'git_blob_sha1':key,'owner':'quality_repository' if name in TASK else 'root_dependency'})
assert (ROOT/'PRODUCT_DESIGN.md').read_bytes()==Path('<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md').read_bytes()
dump(OUT/'source-index.json',{'implementation_commit':HEAD,'spec_sha256':sha((ROOT/'PRODUCT_DESIGN.md').read_bytes()),'base_commit':'4bf176de1cdf0a76cdf0fa965027ec3a5367551f','final_sources':final,'intermediate_source_copies':source,'commits':commits})
dump(OUT/'evidence-index.json',{'checked_at':datetime.now(timezone.utc).isoformat(),'stages':stages,'actual_git_trees_checked':len(trees),'unique_git_blobs_checked':len(blobs),'scope':'All raw development/final receipt logs and complete non-progress source lists checked against actual recorded Git objects; no claim of rerunning historical commands.'})
# Independent read-only review of the root privacy increment: source and execution evidence only.
root_commit='347312c80069249551368faa1038dcfbaf8fbd5c'
review_stages=[]
for name in ['warning-red','warning-red-corrected','warning-green','ruff-safe','mypy-safe']:
 d=DEP/name;r=json.loads((d/'receipt.json').read_text());data=(d/'test.log').read_bytes()
 assert sha(data)==r['log_sha256'] and len(data)==r['log_bytes']
 b=json.loads((d/'inputs-before.json').read_text());a=json.loads((d/'inputs-after.json').read_text())
 assert b==a and r['source_unchanged'] and len(b)==r['source_count']
 tr=tree(r['code_commit'])
 for f in b:
  mode,key=tr[f['path']];raw=blob(key)
  assert f['git_blob_sha1']==key and f['sha256']==sha(raw) and f['bytes']==len(raw)
 review_stages.append({'stage':name,'original_receipt':str((d/'receipt.json').relative_to(BASE)),'receipt_sha256':sha((d/'receipt.json').read_bytes()),'code_commit':r['code_commit'],'exit_code':r['exit_code'],'source_count':len(b),'actual_git_binding':'PASS','log_sha256':sha(data)})
for name in DEPS:
 assert blob(tree(root_commit)[name][1])==(ROOT/name).read_bytes()
dump(OUT/'root-privacy-review.json',{'reviewed_commit':root_commit,'reviewed_paths':DEPS,'review_type':'independent source and raw evidence readback; no independent test rerun','findings':[],'evidence':review_stages,'checks':['Original protected entry points serialize with warnings=error before full strict revalidation.','Both preserve the original fixed safe ApiError mapping and suppress exception chaining.','No hash/ownership/Policy/numeric execution/structural semantics are relaxed.','Corrected RED proves five structure warnings without marker disclosure and two numeric warnings with synthetic marker disclosure.','First RED preserves the fixture error expecting 503 instead of original numeric 409.','7 focused GREEN tests, Ruff and mypy were run by root at exact source; their raw receipts and Git input bindings have been independently checked.']})
(OUT/'root-privacy-review.md').write_text('Independent review of root 347312c80069249551368faa1038dcfbaf8fbd5c: no blocking finding.\n\nThe protected structure and numeric revalidation points now reject Pydantic serializer warnings before model validation and return the original fixed ApiError with suppressed chaining. The four-file change preserves ownership, Policy, complete hashes, numeric read-only behavior and structural status semantics.\n\nRaw corrected RED: five structure cases emitted warnings but did not show the chosen synthetic marker; two numeric cases did show their synthetic marker. The first RED additionally contained a numeric expected-status fixture error, corrected before the second RED. Raw 7-case GREEN and fixed-source Ruff/mypy receipts were checked against original logs and actual Git inputs; this review did not independently rerun those commands.\n')
# Final task receipt is emitted only once final composed regression has an actual terminal receipt.
final_names=['final-composed-regression','final-composed-ruff','final-composed-mypy']
chosen=[next(s for s in stages if s['stage']==name) for name in final_names]
assert all(s['exit_code']==0 and s['code_commit']==HEAD for s in chosen)
receipt={'task_id':'M6.2-quality-review-repository','requirement_ids':['R-21','R-22','R-24','R-27','R-29','R-36','R-38'],'spec_sha256':sha((ROOT/'PRODUCT_DESIGN.md').read_bytes()),'implementation_commit':HEAD,'owned_implementation_commit':'9fff7cc116d6f5546d7de043697878c40b21a1e1','changed_paths':TASK,'dependency_changed_paths':DEPS,'commands':[s['command'] for s in chosen],'exit_codes':[s['exit_code'] for s in chosen],'test_summary':[s['summary'] for s in chosen],'screenshot_paths':[],'migrations':{'new':[],'dependency':'0017_review_history.sql from 4bf176de1cdf0a76cdf0fa965027ec3a5367551f; no migration changed in this slice'},'security_review':{'status':'INTERNAL_SCOPE_VERIFIED_PENDING_ROOT_ACCEPTANCE','facts':['machine mathematical/sources/independent_pedagogy remain NOT_RUN','complete typed canonical history, original ACKs and real Jobs source are rechecked','each Quality mutation uses a savepoint; caller retains responsibility for earlier Jobs/artifact writes','read-only history does not repair corrupted records','malformed revalidation emits no private serializer warnings in tested cases','fixtures are synthetic; no actual human content approval or vendor call'],'root_privacy_dependency_review':'root-privacy-review.json'},'not_run':['Review application/HTTP/worker integration','Quality physical artifact owner authentication','Publish/revision/impact analysis','Platform real vendor invocation','Independent mathematical/source/pedagogy review','Full repository Python suite at this composition','Browser product acceptance'],'blockers':['No blocker to this persistence slice; application-level implementation and root independent acceptance remain pending.'],'next_task_id':'M6.2-review-application-worker','evidence_index':'evidence-index.json','source_index':'source-index.json','scope':'Internal persistence slice only; not M6.2 completion.'}
dump(OUT/'task-receipt.json',receipt)
(OUT/'REPORT.md').write_text('Quality review persistence candidate is ready for root independent acceptance.\n\nFixed composed commit: '+HEAD+'; owned implementation: 9fff7cc116d6f5546d7de043697878c40b21a1e1. Five owned files provide closed history/command models, persistence and focused real SQLite tests. Root structure/numeric privacy dependencies are explicit in source-index.json.\n\nFinal actual gates: '+'; '.join(str(s['summary']) for s in chosen)+'. All '+str(chosen[0]['source_count'])+' engineering inputs remained fixed and match actual Git blobs. Historical failed gates, fixture errors and RED evidence are retained in evidence-index.json. This is not a full-suite or browser/HTTP/worker acceptance.\n\nThe repository rechecks real Jobs binding, complete canonical history and original command ACKs, and uses savepoints to prevent partial Quality writes even if the caller catches errors. It never claims to authenticate current Policy, physical artifact access, a real human decision or mathematical/source correctness. Machine human-review fields remain NOT_RUN; production review worker and publish remain future work.\n')
manifest=[]
for path in sorted(OUT.rglob('*')):
 if path.is_file() and path.name!='manifest.json':
  data=path.read_bytes();manifest.append({'path':str(path.relative_to(OUT)),'bytes':len(data),'sha256':sha(data)})
dump(OUT/'manifest.json',{'files':manifest})
print(json.dumps({'implementation_commit':HEAD,'stages':len(stages),'source_copies':len(source),'manifest_items':len(manifest),'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'report_sha256':sha((OUT/'REPORT.md').read_bytes()),'task_receipt_sha256':sha((OUT/'task-receipt.json').read_bytes())}))
