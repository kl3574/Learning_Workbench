import datetime, hashlib, importlib.util, json, subprocess, sys
from pathlib import Path
B=Path('$HOME/.cache/learning-workbench-acceptance')
R=B/'m62-public-safe-oct02'; O=Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='f11c170d7ba9bee88a88fe104f3a0a9b44bef753'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=R)
spec=importlib.util.spec_from_file_location('public_package',B/'m62-v313-pushed-progress-sync-oct03/package.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
records=[];peer_groups=[]
packages=[('owner','m63-turn-owner-evidence-oct04'),('current-ui-review','m63-current-session-static-40925d27-oct04'),('original-owner-review','m63-turn-owner-static-5a41101e-oct04'),('owner-closure','m63-turn-owner-closure-6f3f8107-oct04'),('numeric','m63-690-numeric-artifacts-review-oct04'),('numeric-errata','m63-690-numeric-transform-errata-oct04'),('original-client-review','m63-turn-client-static-5c845a0b-oct04'),('client-withdrawal','m63-turn-client-finding-withdrawal-97f8-oct04')]
for alias,dirname in packages:
 p=B/dirname; safe=json.loads((p/'SAFE_SHARE.json').read_text()); outer=json.loads((p/'PUBLIC_OUTER_ALLOWLIST.json').read_text()); names=[]
 if 'entries' in safe:
  entries=(json.loads((B/'m63-690-numeric-transform-errata-oct04/QUALIFIED_ALLOWLIST.json').read_text())['entries'] if alias=='numeric' else safe['entries'])
  for e in entries:
   raw=(p/e['raw_path']).read_bytes();candidate=(p/e['candidate_path']).read_bytes()
   assert {'sha256':sha(raw),'bytes':len(raw)}==e['raw']
   assert {'sha256':sha(candidate),'bytes':len(candidate)}==e['candidate']
   assert candidate==raw.replace(b'$HOME',b'$HOME'),(dirname,e['raw_path'])
   names.append(e['candidate_path'])
 else:
  entries=safe['files']
  for e in entries:
   raw=(p/e['path']).read_bytes();candidate=(p/'safe-share'/e['path']).read_bytes()
   assert sha(raw)==e['raw_sha256'] and len(raw)==e['raw_bytes']
   assert sha(candidate)==e['public_sha256'] and len(candidate)==e['public_bytes']
   assert candidate==raw.replace(b'$HOME',b'$HOME')
   names.append('safe-share/'+e['path'])
 for path,desc in (outer['files'].items() if isinstance(outer['files'],dict) else [(e['path'],e) for e in outer['files']]):
  data=(p/path).read_bytes();assert sha(data)==desc['sha256'] and len(data)==desc['bytes'];names.append(path)
 peer_groups.append((alias,dirname,names));records.append({'package':dirname,'safe_count':len(entries),'outer_count':len(outer['files']),'all_admitted_raw_candidate_and_transform_exact':True,'original_safe_manifest_sha256':sha((p/'SAFE_SHARE.json').read_bytes())})
assert records[4]['safe_count']==23 and not any(n.endswith('/SEAL.py') for n in peer_groups[4][2])
(O/'PEER_PACKAGE_READBACK-02.json').write_text(json.dumps({'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'QUALIFIED_EXPLICIT_CANDIDATES_PASS','packages':records,'previous_failure':'Original numeric SEAL.py single-prefix assertion failed; retained separately. New qualified list excludes it; peer two-prefix errata does not make transformed sealer executable.'},indent=2)+'\n')
(O/'EXPLICIT_PEER_GROUPS-02.json').write_text(json.dumps(peer_groups,indent=2)+'\n')
paths=[]
paths.append(m.package('M6.3-preparation-owner-reviews-and-client-finding-withdrawal',peer_groups+[('root-readback',O.name,['PEER_PACKAGE_READBACK-02.json','EXPLICIT_PEER_GROUPS-02.json','original-peer-package-readback-failure.json']),('root-owner-review','m63-turn-owner-root-review-oct04',['READBACK.json']),('closure-readback','m63-turn-owner-closure-readback-6f-oct04',['READBACK.json']),('initial-locator-errata','m63-turn-owner-static-readback-5a-oct04',['READBACK_AND_LOCATOR_ERRATA.json']),('client-locator-errata','m63-turn-client-static-readback-5c-oct04',['READBACK_AND_LOCATOR_ERRATA.json']),('numeric-readback','m63-690-numeric-artifacts-readback-oct04',['READBACK.json'])],{'status':'QUALIFIED_OWNER_CLOSURE_CLIENT_FALSE_POSITIVE_WITHDRAWN_NUMERIC_BLOCKED','preparation_owner':'Fixed6f static closure and actual416 related cases are separate; originals remain FAIL/private-hash-only where credential fixtures occurred','client':'Original5c static P2 withdrawn FALSE_POSITIVE on same production bytes after41 actual counterexamples and1109 fullWeb; no production fix','numeric':'690 actual four artifact JSON/transport receipts remain BLOCKED/409;23 candidates qualified, SEAL.py excluded and original transform error corrected','boundary':'No grant/dispatch/tools/manifest or actual CLI/model/wholeM6.3/quality acceptance by this archival checkpoint.'}))
ui=['red-after.json','fixed-source.json','full-web.log','test-only-source.json','red-before.json','strict.log','red-02.json','original-red.log','after.json','before.json','red-02.log','preflight-error.json','run_fixed.py','GATES.json','build.log','fixed-02/strict.log','fixed-02/full-web.log','fixed-02/before.json','fixed-02/build.log','fixed-02/harness-correction.json','fixed-02/after.json','fixed-02/run_fixed.py','fixed-02/GATES.json']
paths.append(m.package('M6.3-current-session-ui-source-native-and-integration',[
 ('ui-gates','m63-current-session-client-evidence-oct04',ui),
 ('backend-integration','m63-turn-preparation-canonical-integration-oct04',['before.json','after.json','merge.stdout','merge.stderr','receipt.json','original-readback-oracle-failure.json']),
 ('ui-integration','m63-current-session-canonical-integration-oct04',['cherry-0.stdout','cherry-0.stderr','cherry-1.stdout','cherry-1.stderr','cherry-2.stdout','cherry-2.stderr','receipt.json']),
 ('native','m63-current-session-native-oct04',['native.mjs','controlled_api.py','receipt.json','r3-1440.png','r3-390.png','r3-1440-geometry.json','r3-390-geometry.json','cleanup-correction.json','cleanup-root-cause-correction.json','fixed-02/native.mjs','fixed-02/controlled_api.py','fixed-02/receipt.json','fixed-02/COMMAND_READBACK.json','fixed-02/r3-1440.png','fixed-02/r3-390.png','fixed-02/r3-1440-geometry.json','fixed-02/r3-390-geometry.json'])
],{'status':'CURRENT_SESSION_METADATA_UI_AND_CONTROLLED_NATIVE_PASS','source':'Final UI409 and canonicalff are independently bound; bootstrap ACK/commands/memory remain unchanged','native':'Real Chrome154/UI/HTTP/SQLite/IDB r2 to r3 active to r5 null + restart/original201/202ACK. Explicitly synthetic bootstrap; original cleanup intervention retained, independent fixed02 terminalexit0 verified','screenshots':'Root read the final390 screenshot;1440/390 geometry has no overflow. Only synthetic test UI images admitted','boundary':'Not actual Codex CLI/model execution, no turn execution UI or wholeM6.3 acceptance.'}))
ci=[]
for run in ['37170415116','37170416801']:
 for job in ['backend','spec-contracts','integration','frontend','browser','security-publication']:
  ci += [f'{run}-{job}-api.log',f'{run}-{job}-api.stderr',f'{run}-{job}-api.invocation.json']
ci+=['collect.py','collect-02.py','collector-original-failure.json','37170415116-backend.log','37170415116-backend.stderr','37170415116-backend.invocation.json','receipt.json','receipt-02.json','69029bc1ab355efdbb6e0fdb8a86204c59cea71a.binding.json','6692d62db971b9b46cbf118efe6f26b4e0fd3b8c.binding.json']
paths.append(m.package('M6.3-690-complete-dual-CI-terminal-readback',[('ci','m63-v315-CI-terminal-690-oct04',ci)],{'status':'ACTUAL_690_TWO_WORKFLOWS_ALL_TWELVE_JOBS_SUCCESS','push_head':'69029bc1ab355efdbb6e0fdb8a86204c59cea71a','pr_checkout':'6692d62db971b9b46cbf118efe6f26b4e0fd3b8c','identical_tree':'09c22a9a18b064c36a84e05f091e37cf3e76e5cd','per_group':'825backend/809contract/2143integration with2actualnumericENVskip/1058Web/146files/130native; groups are not summed','collector':'Original gh run log commandexit0 emptybytes and collector failure retained; actual12 logs subsequently obtained from jobs API; receipt02 only strips ANSI for derived frontend summary, raw logs unchanged','boundary':'Remote690 is an earlier source than current local preparation/grant work. No merge/release/deploy or numeric/realProvider/wholeM6.3 claim.'}))
gates=[]
for kind,names in [('static',['run.py','before.json','after.json','GATES.json','ruff.log','mypy.log','generated.log','spec.log','full-web.log','strict.log','build.log']),('python',['run.py','before.json','after.json','GATES.json','full-python.log','environment-failure.json']),('python-fixed-02',['run.py','before.json','after.json','GATES.json','full-python.log'])]:
 gates += [('combined-'+kind,'m63-combined-preparation-gates-oct04',[kind+'/'+n for n in names])]
for kind in ['environment-focused-original','route-fixed-focused']:
 gates += [('repair-'+kind,'m63-full-python-repair-oct04',[kind+'/'+n for n in ['run.py','before.json','after.json','GATES.json','focused-original.log' if kind=='environment-focused-original' else 'focused-fixed.log']])]
paths.append(m.package('M6.3-combined-gates-full-failures-and-qualified-repair',gates,{'status':'FULL_PYTHON_FAIL_RETAINED_FOCUSED_REPAIR_PASS_COMPLETE_RERUN_PENDING','fixedff_static':'Ruff/mypy259/generated82/spec54core147/fullWeb1068strictbuild PASS;1405 completeGit inputs unchanged','original_complete_python':'1939PASS440FAIL1568ERROR1skip, explicit quota/SQLite errors retained; not overwritten','fixed_basetemp_complete_python':'3939PASS7FAIL2actualnumericENVskip; exactff fullgate FAIL, source unchanged1405. Two oldmethod assertions; two explicit Errno122; threeexit120 initially not classified','qualified_repair':'Unchangedff with only dedicated TMPDIR+basetemp had5PASS2oldrouteFAIL; test-only b0cf method contract fix then same7case7PASS. No production/runtime/timeout change. Not a complete gate','harness_label_erratum':'route-fixed-focused GATES status label FOCUSED_ORIGINAL_PASS is a reused label; its actualcommand/head/scope establish fixed-seven-casePASS, not original-fullPASS','boundary':'Original failures preserved; next latest integrated completePython not run yet, real numeric skips remain BLOCKED, actual provider zero.'}))
client=['original-notrun.json','pattern-static-finding-counterevidence.json','pattern-primitives.log']
for directory in ['formal-fixed','formal-counterexamples']:
 client += [directory+'/'+n for n in ['run.py','before.json','after.json','GATES.json','full-web.log','strict.log','build.log']]
paths.append(m.package('M6.3-turn-client-binding-counterevidence-and-local-integration',[
 ('client','m63-turn-client-evidence-oct04',client),
 ('integration','m63-turn-client-canonical-integration-oct04',['before.json','after.json','merge.stdout','merge.stderr','receipt.json'])
],{'status':'CLIENT_BINDING_1109_WEB_PASS_SAME_PRODUCTION_FINDING_WITHDRAWN_INTEGRATED','source':'97f8ca60 exacttwofile bindings integrated normally into f11c170d;1405 pre-existing source paths byte-identical','gates':'5c fullWeb1099;97f test-onlycounterexamples fullWeb1109/148files/strict/build/41focused;1407 completeGit inputs bound per source, no newline production fix','boundary':'Client transport/validation only, new turn panel still being implemented separately; no external model, wholeturn or quality acceptance.'}))
paths.append(m.package('M6.3-Issue32-preparation-current-sync-checkpoint',[('sync','m63-preparation-current-Issue32-sync-oct04',['sync.py','issue-body.md','issue-patch.invocation.json','readback.json'])],{'status':'HISTORICAL_0846_ISSUE32_BODY_UPDATE_VERIFIED','scope':'Issue32 actual body-only update at08:46; metadata and PR56 untouched. At that instant fixedff fullPythonRUNNING; subsequent terminal7FAIL recorded separately here','boundary':'Historical receipt, not current fullgatePASS, no sourcepush/merge/release/model.'}))
state=m.read_state();task=next(t for t in state['tasks'] if t['id']=='M6.3');task['evidence_paths'] += paths
next_action='闭合新的grant两项真实P2及固定门禁、独立读回整合后，在专属TMPDIR/basetemp运行最新完整Python/Web/静态；新turn准备/安全控制UI并行实施。当前公开690双CI全部成功与本地ff完整失败分开；生产proof缺失零外发，整个M6.3未完成。'
state['next_action']=next_action;task['next_action']=next_action;task['verification']='IN_PROGRESS: actual preparation/currentUI/controller validated, combined fullPython failures retained and7case repairPASS; grant currentP2 fixes pendingcomplete readback/integration; no wholeM6.3 acceptance'
state['verification']['m6_3_preparation_current_combined']='Fixedff1405Git inputs: static1068WebPASS and controlledChrome/realHTTP/SQLite/IDB r3active to r5null restartPASS. Actual completePython original1939PASS440FAIL1568ERROR1skip, fixedbasetemp3939PASS7FAIL2ENVskip remainFAIL. Sameff TMPDIR+basetemp only5PASS2routeFAIL; b0cf test-only GET/method fix then7PASS, not completePASS.'
state['verification']['m6_3_690_actual_ci']='Actual push37170415116/PR37170416801 all12jobsSUCCESS; push690/PRcheckout6692 same09c22 tree. Each825backend809contract2143integration+2numericENVskip1058Web130native; actual12APIlogs retained with original empty-log collector failure, no source/result conflation.'
state['verification']['m6_3_turn_client_counterevidence']='Actual97 test-only counterexamples41PASS and1109fullWeb/strict/build1407inputsGitexact; same5c production bytes. Peer originalnewlineP2 withdrawnFALSE_POSITIVE in separate immutableclosure. Localnormalmergef11 exact2newfiles, all1405 existing nonprogress paths unchanged; panel/realexecution stillincomplete.'
state['verification']['m6_3_690_numeric_artifacts']='Four actual690 push/PR single/restore artifact IDs11291717091/11291407336/11291472698/11291288003 independently checked metadata+archives+sixJSON. All physicalBLOCKED_ENVIRONMENT/exit1/outputnull/noassertions, publication409PUBLISH_NUMERIC_REQUIRED.23qualifiedsafe candidates;SEAL.py excluded with explicit two-prefix transformerrata.'
state['task_sync']='VERIFIED_ISSUE32_0846_BODY_ONLY_LATER_TERMINAL_SYNC_PENDING'
m.save(state)
old=(R/'progress/M6.3-next.md').read_text();(R/'progress/M6.3-next.md').write_text('# 2026-10-04 本地完整失败保留、定向修复通过，690双CI成功\n\n当前本地f11整合真实准备/安全控制后端6f、当前sessionUI409及新的turnClient97。ff完整Python3939PASS7FAIL2真实数值环境跳过；另一次配额失败原件保留。相同源码仅换TMPDIR/basetemp五项通过、剩两旧方法断言；b0cf测试修正后原七项7PASS，不替代全套。新grant两项真实到期/记录形状P2已有反例和小修，待固定完整关联门禁/独审整合；新的准备/安全控制UI在独立树实施。原误报newlineP2已独立撤回，生产未为此修补。\n\n公开源码690双CI实际12SUCCESS，原数值四artifact仍BLOCKED/409；当前新源码未推送，PR56保持draft/open/unmerged。整个M6.3/AC21、生产完整proof/真实模型与质量、M7仍未验收；用户checkout b895保持。\n\n下一任务：'+next_action+'\n\n以下原时点保留。\n\n'+old)
(O/'PACKAGED_PATHS-02.json').write_text(json.dumps({'paths':paths,'head_before_documentary':'f11c170d7ba9bee88a88fe104f3a0a9b44bef753','source_push':False},indent=2)+'\n')
print(json.dumps({'status':'LOCAL_PROGRESS_CHECKPOINT_BUILT','packages':len(paths),'source_push':False}))
