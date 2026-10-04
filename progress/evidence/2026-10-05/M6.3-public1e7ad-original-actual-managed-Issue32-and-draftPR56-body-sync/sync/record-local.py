from pathlib import Path
import json,sys,copy,hashlib
O=Path(__file__).parent;B=O.parent;R=B/'m62-public-safe-oct02'
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');sync=json.loads((O/'READBACK.json').read_bytes());push=json.loads((B/'m63-public1e7ad-sourcepush-oct05/READBACK.json').read_bytes())
assert sync['public_head']==push['branch_head']==push['pr_head']=='1e7ad7a8656c0dc8373d4181fa3002f385ed1847' and push['git_exit_code']==0 and sync['draft_open_unmerged']
for p in ['progress/state.json','progress/CURRENT.md','progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md']:
 dest=O/'before-local-record'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((R/p).read_bytes())
s.setdefault('checkpoint_history',[]).append({'reason':'beforeactual1e sourcepush and managedbody sync','checkpoint':copy.deepcopy(s['checkpoint']),'old_public_head':t['publication_head'],'previous_sourcepush':copy.deepcopy(s['verification'].get('m6_3_public6671_actual_sourcepush'))})
t['publication_head']=s['checkpoint']['publication_head']=sync['public_head'];t['last_issue_body_sha256']=sync['issue_body_sha256'];s['last_pr_body_sha256']=sync['pr_body_sha256']
s['task_sync']='ACTUAL_ISSUE32_DRAFTPR56_PUBLIC1E_SCOPED_GATES_NEWCI_RUNNING_LOCAL_FULLPYTHON_OBSERVED_FAILURE'
s['task_sync_readback_at']=sync['recorded_utc'];s['task_sync_last_scope']='Actual managed Issue32/draftPR56 body only, metadata/head/base/draft/open/unmerged preserved; sourcepush verified separately'
s['verification']['m6_3_public1e_actual_sourcepush']=push;s['verification']['m6_3_public1e_actual_body_sync']=sync
snapshot=json.loads((B/'m63-ci-public1e7ad-observation-oct05/01-SNAPSHOT.json').read_bytes())
s['verification']['m6_3_public1e_original_ci']=snapshot
f=json.loads((B/'m63-catalog27f-tutor-tsc-failure-diagnosis-oct05/focused-original/receipt.json').read_bytes())
assert f['head']==t['candidate_implementation_commit'] and f['command_exit_code']==f['wrapper_exit_code']==1 and f['before_after_complete_exact']
s['verification']['m6_3_catalog27f_original_targeted_node_requirement_failure']={'status':'ACTUAL1FAIL_NOT_REPAIRED','source':f['head'],'log_sha256':f['log_sha256'],'receipt':f,'actual_reason':'Node24.21.0 required; run make setup','case':'tests/contract/test_tutor_transport.py::test_emitted_sse_codec_real_typescript_and_stream_execution','scope':'Separate same-source focused run; originalfullsuiteunique failure reason still pending. Source/1541beforeafterexact, no code edit; freshisolated lockedsetup inprogress, originalfulltree environment unchanged.'}
full=s['verification']['m6_3_catalog27f_complete_python_original_gate'];full['observed_failure_marker']='test_tutor_transport progressline F, originalterminaldetails notyetavailable';full['status']='ACTUALLY_RUNNING_WITH_OBSERVED_FAILURE_NOT_TERMINAL';full['observed_skip_marker']='test_authoring_numeric_runtime progressline s; originalterminalreason pending, not prefilledENV'
t['current_local_checkpoint']['python']['whole_new_source']=full['status']
for k in ['unit','contract','integration']:s['verification'][k]+=' 原完整Python已见TutorTransport F，终态详情仍待；另行同源定向1FAIL实际Node24.21.0 setup缺失，未改源码或原full运行环境。'
s['verification']['ci']='新公开1e原attempt1 push37241154917/PR37241158099已实际创建，seq01各job queued/in_progress，尚无终态PASS，单producer45秒只读观察并逐原job终态采集log。旧公开6671原两CI各6SUCCESS、各133browser/2467integration2numericENVskip，仅旧源资格；原FAIL/UNKNOWN/LOSS及数值BLOCKED/409保留。'
next_action='取得公开1e两个原CI及27f完整Python原终态/原日志，保留已观察F/SKIP及原真实原因；在另一隔离树按现有make setup补锁定Node依赖并重验定向TypeScript失败，再完成必要新全门禁。继续现行规范内部RPC/response/terminal配对工程，生产InputProof/runtime未注册，真实模型/数值/全M6.3未验收；不重启被拒绝host probes。'
s['next_action']=t['next_action']=s['checkpoint']['next_action']=next_action
s['checkpoint'].update({'resume_base_code_commit':sync['public_head'],'local_resume_engineering_anchor':'8978880982f4190ce688d7fbf2a9be72d30d5657','working_tree':'Public1e exactdraftPR/branch confirmed; actualsync recorded in4localdirtyprogress files; originaluserb895clean. Original27ffullsuite81265 continues unchanged withobservedF; newlockedNodeenv tree onlysetup; nextRPC source separateisolatedcandidate.'})
for p in ['progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md']:
 (R/p).write_text('## 实际公开与新门禁补记\n\n公开branch/草稿PR56已实际确认 `1e7ad7a8656c0dc8373d4181fa3002f385ed1847`，Issue32/PR56正文已实际PATCH并回读；draft/open/unmerged。新push37241154917、PR37241158099原CI已创建，尚未整组PASS。\n\n原完整27f Python4441已观察F/skip标记，尚无终态详情；另同源定向SSE TypeScript case实1FAIL（Node24.21.0 required/setup缺失），1541工程输入前后不变。不追认完整原suite唯一根因；原运行环境不动，另一隔离树补锁定setup，尚未报修复。\n\n'+next_action+'\n\n'+(R/p).read_text())
save(s)
(O/'LOCAL_RECORD_READBACK.json').write_text(json.dumps({'actual_public_head':sync['public_head'],'issue_body_sha256':sync['issue_body_sha256'],'pr_body_sha256':sync['pr_body_sha256'],'new_CI':'ORIGINAL_EVENTS_CREATED_QUEUED_RUNNING','fullPython':'RUNNING_WITH_OBSERVED_F_NOT_TERMINAL','focus':'ACTUAL1FAIL_NODE_REQUIRED_NOT_REPAIRED','sourcepush':push['git_exit_code'],'remote_merge_release_deploy':False,'key_used_or_uploaded':False},indent=2)+'\n')
print('Recorded actualsourcepush/bodyreadback/neworiginalCI/currentfullF and independentNodefailure in4progress files.')
