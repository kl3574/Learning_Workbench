from pathlib import Path
import hashlib,json,subprocess
from datetime import datetime,timezone
BASE=Path(__file__).parent
ROOT=BASE.parent/'m62-review-storage-active'
REVIEW=BASE.parent/'m62-review-storage-independent-v1'
def sha(data):return hashlib.sha256(data).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
audit=json.loads((BASE/'source-audit.json').read_text())
review_manifest=json.loads((REVIEW/'MANIFEST.json').read_text())
for row in review_manifest['files']:
 data=(REVIEW/row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
stages=[]
for item in audit['stages']:
 stage=BASE/item['stage'];receipt=json.loads((stage/'receipt.json').read_text());log=(stage/'test.log').read_bytes()
 assert sha(log)==receipt['log_sha256'] and len(log)==receipt['log_bytes']
 stages.append({'stage':item['stage'],**receipt,'recorded_summary':log.decode().splitlines()[-1],
                'actual_git_audit':item})
summary={'task_id':'M6.2-review-storage','requirement_ids':['R-21','R-22','R-26'],
 'spec_sha256':'2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d',
 'baseline':audit['baseline'],'final':audit['final'],'changed_paths':audit['changed_paths'],
 'commits_in_order':audit['final_parent_chain_commits'],'stages':stages,
 'stage_count':len(stages),'final_engineering_source_count':964,
 'independent_manifest':{'path':'m62-review-storage-independent-v1/MANIFEST.json','sha256':sha((REVIEW/'MANIFEST.json').read_bytes()),'files':len(review_manifest['files'])},
 'test_boundary':'Final 101 storage tests/Ruff at 4bf176d; 246 related regression/mypy186/verify-spec at e0b30f0. The sole final difference is stronger tests; results retain actual commit attribution and are not added as coverage.',
 'failures':[
  {'stage':'migration-red','classification':'expected pre-implementation absence of 0017/new tables','failed':2},
  {'stage':'constraints-initial','classification':'test fixture defect: nonexistent content_blobs.media_type; not product RED','failed':57,'passed':20},
  {'stage':'command-fk-red','classification':'real persistent command event reference gap','failed':5}],
 'non_final_run':'regression: 229 actual PASS but one new test file changed during the run; not a fixed-source final gate',
 'backup_facts':['16-to-17 online backup preserves original old review/jobs/catalog bytes with 16 migration records',
  'deliberate failure after DDL rolls back schema/index/new tables/migration record and original rows',
  'actual backup script permits NULL legacy reviewer_session_id and removes sessions without rewriting receipt',
  'nonempty new history/commands retained in online-copy session cleanup; original synthetic database unchanged'],
 'migrations':['0017_review_history.sql forward only; new tables empty on migration; no approval/history backfill'],
 'scope':'Quality persistence schema, actual SQLite tests and short ADR only',
 'security_review':'SQL FK/JSON/hash shape do not authenticate owner, Policy, content verdict or canonical hashes; future checked ports required',
 'not_run':['Quality repository/worker/HTTP','real provider','numeric execution','production user database migration','M7 restore acceptance','full repository/browser suite on storage branch'],
 'blockers':[],'next_task_id':'M6.2 Quality checked repository and atomic machine/human history integration',
 'publication':'NOT_PUBLISHED; root main untouched',
 'toolchain':{'python':'3.12.13','sqlite':'3.53.1'}}
dump(BASE/'summary.json',summary)
report='''# M6.2 Quality review storage — local implementation receipt

Sole specification: PRODUCT_DESIGN.md 3.0.7 (SHA in summary.json). This accepts only the forward SQLite schema slice, not M6.2 or a working review application.

Fixed final source: `4bf176de1cdf0a76cdf0fa965027ec3a5367551f`, based on authorized `16f4ae1355c4398a6b419b2fa883ec5211624c3d`. Exactly four new paths: migrations/0017_review_history.sql, tests/integration/test_review_storage_migration.py, tests/integration/test_review_storage_constraints.py, docs/adr/0023-review-history-storage.md. Main and its progress files were not changed. No user database, permission, provider, numeric runtime or remote write was used.

0017 adds empty immutable review_jobs, review_revisions, review_artifact_bindings and review_commands. Actual Jobs ID/workspace/draft_review kind, complete catalog candidate and source-kind, same-review adjacent predecessor/hash, real artifact ID/workspace/blob and original command route/key/revision domains are bound. All four tables guard UPDATE/DELETE and every UNIQUE-key REPLACE, including both artifact unique keys with recursive triggers OFF and ON. Generated per-kind command revision columns retain actual Job event/Review history foreign keys. JSON validity, these keys, owner tags and digest shape do not authenticate permissions, canonical hashes, real machine execution or a human verdict.

Original failures remain intact. Initial migration tests failed twice because 0017/new tables did not yet exist, then passed after implementation. The first 77-case constraint run had 57 failures and 20 passes because its artifact fixture used a nonexistent content_blobs.media_type column; that is a fixture defect, not a product RED. Correcting it produced 77 passes. An independent review found the substantive initial command-reference defect: insert-time EXISTS alone allowed later deletion/rekeying of referenced Job events. Five permanent cases failed at c2a9304 and passed after e0b30f0 installed persistent foreign keys. Independent distinct-endpoint probes reproduced five original orphans at 4b0296f and rejected all five at e0b30f0.

Final 4bf176d has 101 storage/migration tests PASS and Ruff PASS, both with all 964 engineering sources matching actual Git and unchanged across execution. At e0b30f0, 99 storage tests, 246 related regression tests, Ruff, mypy (186 files), and verify-spec passed with the same source checks. The final difference is only stronger tests that individually mutate create event 1 and cancel basis 1/result 2 without accidental primary-key collision. Those earlier checks are attributed to e0b30f0, not relabeled as executions on 4bf176d. The independent reviewer separately ran 99 tests on e0b30f0 and reviewed the final test-only diff. Counts from overlapping stages are not added as coverage. An earlier 229-test regression did pass, but a newly added test changed during that invocation; its complete receipt is retained and it is not a fixed-source final gate.

Migration tests preserve exact legacy receipt/Job/catalog bytes and leave all four new tables empty. The migration runner produced a real consistent online backup at schema 16 before 17. Deliberately invalid SQL after the new DDL rolled back schema, indexes, rows and migration record. The actual backup script still clears legacy reviewer_session_id on its isolated copy without rewriting receipts. Nonempty new histories and original commands also survive online-copy session cleanup with unchanged raw bytes; original synthetic databases remain unchanged. None of this claims M7 restore completeness or authorizes a production user migration.

0001, 0016, PRODUCT_DESIGN and the generated core model bytes are unchanged. All 38 before/after inventories across 19 stages match their respective actual commits; only the explicitly qualified initial regression has a test-only before/after difference. source-audit.json retains the 8-commit chain, exact source snapshots/diffs, protected byte bindings and source attribution. Raw test databases are excluded from evidence inventories and publication.

Independent review reports no remaining blocking finding within this scope. Quality repository/worker/HTTP, current Policy checks, machine report artifacts, actual human decisions, publication and M7 restore remain future work. No ReviewReceipt is manufactured by product code in this slice. Next: checked Quality repository and one atomic machine/human history integration, then real application routes/worker tests before claiming a review workflow.
'''
(BASE/'REPORT.md').write_text(report)
files=[]
for path in sorted(BASE.rglob('*')):
 if path.is_file() and path.name!='MANIFEST.json':
  data=path.read_bytes();files.append({'path':str(path.relative_to(BASE)),'bytes':len(data),'sha256':sha(data)})
dump(BASE/'MANIFEST.json',{'files':files})
print(json.dumps({'manifest_files':len(files),'manifest_sha256':sha((BASE/'MANIFEST.json').read_bytes()),'report_sha256':sha((BASE/'REPORT.md').read_bytes()),'stage_count':len(stages),'independent_files':len(review_manifest['files'])},indent=2))
