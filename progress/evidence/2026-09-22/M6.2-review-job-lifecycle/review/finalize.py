from pathlib import Path
import subprocess,json,hashlib,shutil,sys
from datetime import datetime,timezone
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-review-job-lifecycle-active');p=Path(__file__).resolve().parent;head='d419562f7ec26c7919e9fa12973b4b8cf30bbac1';base='acb9e220deeaf1da7ee89ec6fda8bae9c21ca918';red='abab63eaf32a219694384e29362114b0e25fb598';source=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-review-job-lifecycle-verification-v1')
def sha(data):return hashlib.sha256(data).hexdigest()
def wr(name,value):(p/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()==head
changed=subprocess.check_output(['git','diff','--name-only',base,head],cwd=root).decode().splitlines();assert len(changed)==6
bindings={}
for ref,label in [(red,'red'),(head,'final')]:
 records=[]
 for item in subprocess.check_output(['git','ls-tree','-r','-z',ref],cwd=root).split(b'\0'):
  if not item:continue
  meta,name=item.decode().split('\t',1);mode,typ,blob=meta.split()
  if name.startswith('progress/'):continue
  data=subprocess.check_output(['git','cat-file','blob',blob],cwd=root);records.append({'path':name,'bytes':len(data),'sha256':sha(data),'git_blob_sha1':blob,'git_mode':mode})
  if name in changed:
   target=p/(label+'-source')/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  if ref==head:assert (root/name).read_bytes()==data
 bindings[ref]=records
 wr(label+'-source-binding.json',{'head':ref,'base':base,'changed_files':changed,'actual_git_source_count':len(records),'files':records})
(p/'final-six-file.patch').write_bytes(subprocess.check_output(['git','diff',base,head,'--',*changed],cwd=root))
(p/'repair.patch').write_bytes(subprocess.check_output(['git','diff',red,head],cwd=root))
gates=[]
for stage,ref in [('atomic-red',red),('atomic-green',head),('new-final',head),('ruff-final',head),('mypy-final',head),('regression-final',head)]:
 target=p/'reviewed-gates'/stage;target.mkdir(parents=True,exist_ok=True)
 for name in ['receipt.json','test.log','inputs-before.json','inputs-after.json']:shutil.copy2(source/stage/name,target/name)
 receipt=json.loads((target/'receipt.json').read_text());assert receipt['exit_code']==(1 if stage=='atomic-red' else 0) and receipt['code_commit']==ref
 assert sha((target/'test.log').read_bytes())==receipt['log_sha256']
 before=json.loads((target/'inputs-before.json').read_text());after=json.loads((target/'inputs-after.json').read_text());assert before==after
 assert {r['path']:r['sha256'] for r in before}=={r['path']:r['sha256'] for r in bindings[ref]}
 gates.append({'stage':stage,'head':ref,'exit_code':receipt['exit_code'],'source_count':len(before),'actual_git_match':True,'log_sha256':receipt['log_sha256'],'last_log_line':(target/'test.log').read_text().splitlines()[-1]})
wr('final-gate-audit.json',gates)
summary={'version':1,'created_at':datetime.now(timezone.utc).isoformat(),'spec_sha256':sha((root/'PRODUCT_DESIGN.md').read_bytes()),'base_commit':base,'initial_commit':'5fefa4e9c5374306a3bd7bfbf8fd5b7e935615c1','red_commit':red,'reviewed_final_commit':head,'changed_paths':changed,'final_source_count':len(bindings[head]),'result':'NO_REMAINING_BLOCKER_FOUND_IN_BOUNDED_INTERNAL_ADAPTER_SLICE','initial_findings':[{'id':'R1','severity':'P1','issue':'Inherited read/write methods allowed autocommit and cross-snapshot validation','status':'RESOLVED_AT_REVIEWED_FINAL_COMMIT'},{'id':'R2','severity':'P1','issue':'Late transition rejection could commit wrong-consumer or invalid-history writes when caller caught error','status':'RESOLVED_AT_REVIEWED_FINAL_COMMIT'}],'gates':gates,'independent_probe':json.loads((p/'fixed_probe.receipt.json').read_text()),'independent_probe_cases':json.loads((p/'fixed_probe.json').read_text()),'input_privacy_probe':json.loads((p/'input_privacy_probe.receipt.json').read_text()),'not_implemented_in_slice':['Quality repository and durable command/receipt history','Review worker and report artifacts','Review HTTP routes and JobService registration','Current candidate/session/Policy checks supplied by future Quality owner','Human approval and publish/diff/impact/restore'],'limits':['No new full-platform/browser gate executed by this review','42 new includes the 7 regression cases; counts are not additive','Shared Authoring lifecycle remains unchanged except consumer configuration extraction','Internal typed construction does not establish authorization or a human approval','Original initial harness failure and original RED are retained, not represented as product PASS']}
wr('summary.json',summary)
report="""# Independent review: typed Review intent and isolated Jobs lifecycle

**No remaining blocker found in the bounded internal adapter slice at d419562f7ec26c7919e9fa12973b4b8cf30bbac1.** This conclusion follows correction of two real issues found at the earlier 5fefa4e commit; it does not certify a Review workflow or publication capability.

The sole specification remains PRODUCT_DESIGN 3.0.7, SHA-256 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d. Review applied the owner boundaries, transaction/CAS and terminal rules in sections 7/15, engineering/publication boundaries in 18–20, Appendix-A review requests/decisions, and the unchanged core ReviewReceipt model. The six-file diff from acb9e220deeaf1da7ee89ec6fda8bae9c21ca918 was read independently. All 959 actual Git source blobs were checked at the original RED commit and final commit, and matched their recorded gate inventories; final worktree source bytes also match Git.

Two initial findings were independently reproduced using fresh synthetic SQLite fixtures: inherited operations accepted autocommit; and rejected transitions made writes before rejection, including cancelling a same-workspace Authoring job through the Review adapter if the caller caught the exception and committed. INITIAL_REPORT.md and initial probe outputs retain those facts. The permanent seven-case regression suite then produced 7 FAIL at abab63eaf32a219694384e29362114b0e25fb598 with unchanged source bytes.

The repair confines its changed behavior to ReviewJobRepository. It requires the caller transaction for create/load/transition; inherited claim/cancel/renew/snapshot/input therefore encounter the checked load. Transition reloads the actual consumer-owned row and complete history, rejects stale rows and unavailable transitions before writes, and uses a generated-name savepoint so malformed lease/result failures roll back only that operation. The old Authoring consumer kinds, initial states and transition rules retain their prior behavior. Typed input preserves workspace/review/candidate/request identities and safe repr/errors; no input construction is treated as authorization.

The completed final gate artifacts were independently read and matched to actual final Git blobs: **7 regression GREEN, 42 new tests PASS, 50 related tests PASS, Ruff PASS, mypy PASS (186 source files)**. The seven regression cases are included in the 42 new tests. The review independently exercised six focused cases beyond artifact readback: autocommit claim rejection, wrong-consumer rejection with an outer commit, three invalid transitions preserving the original row and pre-existing outer-transaction work, and a subsequent valid terminal transition followed by stale-row rejection. The original Authoring job stayed awaiting_approval and the reviews table remained empty. A separate DTO probe verified original bytes, empty repr/str, and three safe validation-error cases. These are focused probes, not an additional full test suite.

The request schemas reject client-supplied machine statuses/reviewer fields, duplicate checks or artifact IDs, invalid revisions and malformed Unicode. Public job snapshots retain safe generic fields and empty result_refs. Unknown draft_review remains unregistered in JobService; the test explicitly verifies JOB_KIND_UNAVAILABLE. There is no fabricated ReviewReceipt. The future Quality owner must still validate current actor, Policy, candidate/material/numeric history and append durable command/receipt records within its own transaction. Worker execution, review HTTP routes, report artifact access, human decisions, publication, version comparison, impact and restore remain unimplemented by this slice.

No engineering files were changed by this review. Probe databases were temporary and synthetic; no user key or vendor call was used. The first private harness failed before Review probes because it lacked a multiprocessing main guard; that harness-only failure is recorded separately and was not counted as a product test. Raw failure logs and all source/receipt evidence remain private. Only this report, the structured safe summary and hash references are publication candidates.
"""
(p/'REPORT.md').write_text(report)
sys.path.insert(0,str(root));from scripts.check_publication import inspect
scan=[]
for name in ['INITIAL_REPORT.md','REPORT.md','summary.json']:
 data=(p/name).read_bytes();issues=inspect('progress/evidence/2026-09-22/M6.2-review-job-lifecycle-independent/'+name,data);assert not issues,(name,issues)
 scan.append({'path':name,'bytes':len(data),'sha256':sha(data),'issues':issues})
wr('public-summary-scan.json',{'result':'PASS','files':scan})
records=[]
for f in sorted(p.rglob('*')):
 if not f.is_file() or '__pycache__' in f.parts or f.name=='manifest.json':continue
 data=f.read_bytes();records.append({'path':str(f.relative_to(p)),'bytes':len(data),'sha256':sha(data)})
wr('manifest.json',{'version':1,'scope':'Private independent review originals and safe summary; no raw private log publication implied','files':records})
for r in records:assert sha((p/r['path']).read_bytes())==r['sha256']
print(json.dumps({'files':len(records),'report_sha256':sha((p/'REPORT.md').read_bytes()),'summary_sha256':sha((p/'summary.json').read_bytes()),'manifest_sha256':sha((p/'manifest.json').read_bytes()),'raw_replay':'PASS','public_summary_scan':'PASS'},indent=2))
