import json,hashlib
from pathlib import Path
BASE=Path(__file__).parent
pins=json.loads((BASE/'final-source-pins.json').read_text());ledger=json.loads((BASE/'run-ledger.json').read_text())
status={
'01-first-publication-red':'1 failed: requested service absent (module import), initial feature RED',
'02-first-publication':'1 PASS: real Import/Review/human/service/Content chain',
'03-terminal-and-history':'7 PASS: original command and real terminal histories',
'04-recorded-admission-red':'1 failed: TRUE product RED, rehashed result removed original required warning ACK but was accepted',
'05-recorded-admission-green':'40 PASS: full historical owner/admission revalidation repaired 04',
'06-integrity-and-atomic':'35 PASS / 1 fixture failure: nonexistent provenance Import FK prevented corruption setup, not product RED',
'07-integrity-fixture-corrected':'36 PASS: fixture now uses a second real staged Import before membership corruption',
'08-first-ruff':'PASS',
'09-first-mypy':'16 static typing errors in import_publication union narrowing; fixed local payload narrowing',
'10-owner-scope':'10 PASS / 1 fixture failure: workspace INSERT used nonexistent name column, not product RED',
'11-scope-and-cas':'20 PASS: corrected workspace title/created_at fixture',
'12-original-job-binding-red':'1 failed: TRUE product RED, historical ACK omitted actual Import Job input binding',
'13-original-job-binding-green':'49 PASS: Jobs owner origin/input/status fact port used on new and historical paths',
'14-upgrade-and-later-evidence':'3 PASS: actual old DB upgrade and both early/late recursive attachment corruption',
'15-review-race':'1 PASS: actual concurrent Review rejection and publication serialize safely',
'16-final-mypy':'PASS: 10 application/repository source files',
'17-final-ruff':'PASS: 10 sources and 4 task tests',
'18-final-related':'238 PASS / 11 files; 2 existing Starlette/httpx deprecation warnings; 144.45 seconds reported by pytest',
'19-migration-regression':'55 PASS / 3 files; 1.38 seconds reported by pytest',
}
assert set(status)=={r['stage'] for r in ledger}
rows='\n'.join(f"| {r['stage']} | {r['receipt']['exit_code']} | {status[r['stage']]} | `{r['receipt']['log_sha256']}` |" for r in ledger)
text=f'''# M6.2 narrow Import text-block publication service — fixed candidate

Implementation `{pins['implementation_commit']}`; baseline `{pins['baseline']}`. Sixteen files, isolated worktree clean at freeze. Sole product/engineering specification `PRODUCT_DESIGN.md` SHA256 `{pins['spec_sha256']}`; repository copy equals the user's current-directory file. This is a real application service with actual immutable Content writes; HTTP/UI registration and overall M6.2 acceptance remain outside this slice.

## Implemented outcome and exact boundary

`DraftPublicationService(database, reviews, imports).publish(identity, draft_id, body, key) -> ContentRef` accepts the existing strict four-field `DraftPublishWrite`. The only supported new write is an actual still-pending, learner-visible Import explicitly parsed as markdown/text, with original metadata r1 and an unused original Content object ID, no private solutions, symbols/assets, base revision, concepts or dependencies. It requires a real complete machine Review plus an explicit persisted human mathematical N/A reason and sources APPROVED, exact candidate/material, original owner warnings, current author/session/Policy and actual physical source/report/body bytes. Tests supply explicit synthetic human actions; no model or user approval is invented.

One actual writer transaction adopts the candidate now and records its independent draft→in_review→approved→published lifecycle with server-private CAS. The exact original candidate/review revision/hash and selected human record are frozen. These are current adoption and checks, not fabricated past state changes or a global latest-Review rule. Content's owned port performs absence CAS, actual immutable metadata/body write, current pointer, invalidation/outbox; Provenance freezes the exact original Import/source relation. Producer DTO/state and the existing Import.commit algorithm remain unchanged. Migration 0018 adds only its owned lifecycle, events, permanent command and result tables with immutability/transition triggers.

An original successful actor/route/key command is permanent and rechecks all current access, full current Quality history including recursive attachments, original approval/admission/warnings, actual Import Job/input/source membership, original physical source/body and historical immutable Content before returning the original ACK. Later rejection or Content r2 does not rewrite that ACK. Real Import cancellation or explicitly copy-remapped whole-Import commit also preserves it; a new command is refused. Unmapped original Import.commit still returns its existing ID collision, mapping rehashes its actual parent graph, and the copied block receives no approval by shared body/Import ID. Generic cache-clock advancement to 2200 plus a new service instance exercises cache independence; this is not a 24-hour wall-clock soak test.

Actual two-connection publication races (same/different key), original Import.commit race, and Review rejection race are covered. Five SQLite fault locations prove all owned database tables remain unchanged on failure, followed by real successful retry. Content writes use the existing BlobStore durability implementation; fixtures already staged the body bytes, so these tests do not claim to create or recover new orphan blobs. An actual pre-0018 database holding pending Import/Review/human facts is upgraded with its online backup, original tables/Review preserved, and then published.

## Evidence and failures retained

Final stage 18: 238 related behavior tests passed across 11 named files. Stage 19: 55 database/migration tests passed across 3 files. Stages 16/17: mypy and Ruff passed for the changed code. These are separate focused gates, not a full-suite pass. `final-actual-git-verification.json` proves every one of the 1021 engineering inputs of each final stage equals its before/after manifest and the actual committed Git bytes. `run-ledger.json` verifies all 19 receipts/log hashes and every retained source copy; complete logs and source snapshots remain in each stage directory.

| Stage | Exit | Actual outcome | Complete log SHA256 |
|---|---:|---|---|
{rows}

The two reproduced integrity defects are stage 04 (recorded warning admission trusted too much) and stage 12 (original Jobs input identity missing on historical replay). Both have permanent real-owner regressions and green repaired runs, finally included in stage 18. Stages 06/10 were incorrect test setup and stage 09 a typing failure; they remain intact and are not counted as product RED. Stage 01 demonstrated a missing implementation, not an exercised integrity defect. No failed log or fixture error was removed.

## Security, review and pending work

Current workspace/session/role/revocation/expiry are checked again even for stored-command ACK. All three live assessment modes reject the private Quality/publication read while existing safe Job control remains usable. Rehashed records, source and report byte damage, recursive attachments added before or after publication, Review command membership damage, exact original source membership and publication chain/command damage fail closed without repair writes. Protected model instances are revalidated with serializer warnings treated as errors; diagnostics use fixed ApiErrors.

Self-check complete; independent Spec and Standards reviews are requested against this fixed commit and remain pending. No external network, real Provider, real numeric execution, actual user human approval, HTTP registration/test, browser publication UI, global lifecycle GET/needs_changes workflow, mathematical/generated/private-solution/question/group publication, existing-object update publication or full platform suite was performed. Machine math/source/teaching NOT_RUN is retained; the nested read-only admission observation retains publication NOT_RUN because it is not itself a publication receipt.

Next: independent review and any required correction, then root-owned HTTP/main/generated integration and real HTTP contract tests. No push, main-tree edit, credential access or specification edit occurred.
'''
(BASE/'REPORT.md').write_text(text)
receipt={
 'task_id':'M6.2-publication-service-narrow-import',
 'requirement_ids':['§7 owner application ports','§9.3 atomic immutable Content','§15.1 Draft lifecycle','§19.3 task receipt','§20.1 exact candidate and hash','§20.2 current Policy','§20.3 applicable human approval','§20.8 command/CAS rules','Appendix A POST /drafts/{draft_id}/publish'],
 'spec_sha256':pins['spec_sha256'],'implementation_commit':pins['implementation_commit'],'baseline_commit':pins['baseline'],
 'changed_paths':[p['path'] for p in pins['changed_files']],
 'commands':[{'stage':r['stage'],'argv':r['receipt']['command'],'receipt':r['stage']+'/receipt.json','log':r['stage']+'/run.log'} for r in ledger],
 'exit_codes':{r['stage']:r['receipt']['exit_code'] for r in ledger},
 'test_summary':{'final_related':'238 passed in 11 files; focused, not full suite','migration_regression':'55 passed in 3 files','mypy':'10 changed sources passed','ruff':'14 changed source/test files passed','real_product_red_stages':['04-recorded-admission-red','12-original-job-binding-red'],'fixture_failures':['06-integrity-and-atomic','10-owner-scope'],'static_failure':['09-first-mypy'],'initial_missing_feature':['01-first-publication-red'],'all_final_gate_inputs_match_actual_git':1021},
 'screenshot_paths':[], 'migrations':['migrations/0018_draft_publications.sql'],
 'security_review':{'self_check':'complete; actual access/Policy/history/bytes and corruption tests','independent_spec':'requested, pending','independent_standards':'requested, pending','credentials':'not accessed','human_facts':'explicit synthetic fixture decisions only'},
 'not_run':['HTTP/main/generated registration and HTTP tests','browser publication UI','real Provider and numeric execution','actual user human approval','full platform suite','global lifecycle status/editing/needs_changes','mathematical/generated/question/group/private-solution publication','existing-object update publication','24-hour wall-clock soak'],
 'blockers':[], 'pending_review':['fixed-source independent Spec and Standards axes'],
 'next_task_id':'M6.2-publication-service-independent-review-then-root-http-integration',
 'source_pins':'final-source-pins.json','verification':'final-actual-git-verification.json','run_ledger':'run-ledger.json',
}
(BASE/'TASK_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
files=[]
for path in sorted(BASE.rglob('*')):
 if path.is_file() and path.name!='PRIVATE_MANIFEST.json':
  raw=path.read_bytes();files.append({'path':path.relative_to(BASE).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
(BASE/'PRIVATE_MANIFEST.json').write_text(json.dumps({'implementation_commit':pins['implementation_commit'],'files':files},sort_keys=True,indent=2)+'\n')
for name in ['REPORT.md','TASK_RECEIPT.json','PRIVATE_MANIFEST.json']:
 raw=(BASE/name).read_bytes();print(name,len(raw),hashlib.sha256(raw).hexdigest())
print('members',len(files))
