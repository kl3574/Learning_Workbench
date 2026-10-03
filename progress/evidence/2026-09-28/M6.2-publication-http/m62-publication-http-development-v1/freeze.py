from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-publication-http-active')
base=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
def save(name,obj):(base/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
head='833f0a84168638ba5ce421c70cd2f20a71e45e48'
assert git('rev-parse','HEAD').decode().strip()==head
assert not git('status','--porcelain','--untracked-files=all')
verified=[]; cached={}
for name in ['red','http','contracts','mypy','http-final','review-http','spec','ruff','web-types','web-types-final']:
 d=base/name;r=json.loads((d/'receipt.json').read_text());log=(d/'test.log').read_bytes()
 assert sha(log)==r['log_sha256'] and len(log)==r['log_bytes']
 before=json.loads((d/'inputs-before.json').read_text());after=json.loads((d/'inputs-after.json').read_text());assert before==after
 tree={}
 for entry in git('ls-tree','-r','-z',r['code_commit']).split(b'\0'):
  if entry:
   m,p=entry.split(b'\t',1);mode,kind,blob=m.decode().split()
   if not p.startswith(b'progress/'):tree[p.decode()]=(mode,blob)
 assert len(tree)==len(before)==r['source_count']
 for item in before:
  mode,blob=tree[item['path']];assert mode==item['git_mode'] and blob==item['git_blob_sha1']
  if blob not in cached:
   data=git('cat-file','blob',blob);cached[blob]=(len(data),sha(data))
  assert cached[blob]==(item['bytes'],item['sha256']) and item['git_matches']
 verified.append({'stage':name,**r,'verified_all_actual_git_inputs':True})
paths=git('diff','--name-only','dec1d937523f4596da4c39bcc27750d9132c752c',head).decode().splitlines();assert len(paths)==8
pins=[]
for name in paths:
 data=git('show',head+':'+name);assert data==(root/name).read_bytes()
 out=base/'source'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
 pins.append({'path':name,'bytes':len(data),'sha256':sha(data),'git_blob_sha1':git('rev-parse',head+':'+name).decode().strip()})
(base/'http-final.diff').write_bytes(git('diff','dec1d937523f4596da4c39bcc27750d9132c752c',head))
(base/'fixture-only-final.diff').write_bytes(git('diff','966b6c6cf616df816d6c114675c920621ba84573',head))
assert git('diff','--name-only','966b6c6cf616df816d6c114675c920621ba84573',head).decode().splitlines()==['tests/integration/test_draft_publication_http.py']
save('source-pins.json',{'commit':head,'http_changed_files':pins})
save('verification.json',{'utc':datetime.now(timezone.utc).isoformat(),'source_commit':head,'source_files':1023,'stages':verified,'distinct_actual_git_blobs_verified':len(cached),'generation_receipt_scope':'Actual generator exit and four changed paths; not represented as a full before/after source manifest.'})
save('TASK_RECEIPT.json',{'status':'HTTP_IMPLEMENTED_LOCAL_GATES_PASSED_INDEPENDENT_REVIEW_PENDING','code_commit':head,'service_commit':'dec1d937523f4596da4c39bcc27750d9132c752c','implemented_operations':97,'declared_operations':119,'current_gates':{'publication_http':'14 PASS, 2 dependency warnings','review_http':'30 PASS, 2 dependency warnings','ruff':'PASS','spec':'PASS','strict_web_types':'PASS'},'prior_966_gates':{'api_projection':'100 PASS','mypy':'204 source files PASS','delta_to_final':'Only precise selected-draft body assertion in one HTTP test; no implementation or contract change.'},'retained_failures':{'red':'1 absent-route 404 failure','http':'13 PASS, 1 fixture expectation failure; selected first heading block versus expected later paragraph','web-types':'Required Node absent; failed before compiler; existing identical-lock toolchain linked, then strict compiler passed'},'not_run':['UI/native publication','full Python suite on this source','real provider','real sealed numeric calculation','actual human content approval','full M6.2 acceptance']})
report="""# Narrow Import publication HTTP integration

Fixed source `833f0a84168638ba5ce421c70cd2f20a71e45e48`, 1023 engineering inputs. Relative to independently reviewed service `dec1d937`, eight files wire the actual strict four-field POST `/drafts/{id}/publish` through the existing session, unique-header, Origin/CSRF, idempotency and private/no-store boundaries, register the real service, generate four contract projections and exercise the real HTTP stack. Registered operations are 97 of 119; full M6.2 remains incomplete.

On the final source, 14 publication HTTP tests and 30 existing Review HTTP tests passed, each with two dependency warnings. Ruff, structural spec verification and strict web TypeScript passed. On `966b6c6`, 100 actual API projection tests and mypy over 204 source files passed; the only subsequent source change is the precise selected-draft body assertion retained in `fixture-only-final.diff`. These gates are not claimed to have rerun on final bytes. Every stage's complete input set, log and receipt was independently checked against its own recorded Git tree by freeze.py. Generation has its actual command/exit/four-path receipt, not invented full-input snapshots.

The positive HTTP test imports real synthetic markdown, runs the real Import and Review workers, makes explicit synthetic mathematical N/A and source approval decisions, publishes an actual immutable ContentRef, reads exact metadata hash/body and replays the original key. It checks no producer/Review mutation and no whole-course commit. Other tests cover current rejection before publication, later rejection with original historical ACK versus a rejected new command, invalid/duplicate headers, Origin/CSRF, strict body/query validation and current author/session enforcement even for old ACK. These test decisions are not actual user content approval.

Original failures are preserved in full. `red` is one true missing-route failure. The first implemented `http` run had 13 passing tests and one fixture expectation error: the chosen first parsed block was the heading, while the assertion expected the later paragraph; the final assertion compares the exact selected draft body bytes. `web-types` failed before compilation because this isolated tree lacked the ignored Node toolchain; existing installed dependencies with the same package lock were linked, then `web-types-final` passed. No product assertion or isolation constraint was weakened.

No publication browser UI, full Python suite, real provider execution, sealed numerical execution, genuine human content approval or full M6.2 acceptance is claimed here. The independently reviewed service's SQL rollback versus possible unreferenced physical blob distinction still applies. Separate independent HTTP reviews follow; this owner's receipt deliberately retains its original review-pending timepoint.
"""
(base/'REPORT.md').write_text(report)
rows=[]
for p in sorted(base.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts and p.name!='PRIVATE_MANIFEST.json':
  data=p.read_bytes();rows.append({'path':p.relative_to(base).as_posix(),'bytes':len(data),'sha256':sha(data)})
save('PRIVATE_MANIFEST.json',{'members':rows,'count':len(rows)})
print(json.dumps({'status':'PASS','stages':len(verified),'files':len(rows),'manifest_sha256':sha((base/'PRIVATE_MANIFEST.json').read_bytes()),'report_sha256':sha((base/'REPORT.md').read_bytes())}))
