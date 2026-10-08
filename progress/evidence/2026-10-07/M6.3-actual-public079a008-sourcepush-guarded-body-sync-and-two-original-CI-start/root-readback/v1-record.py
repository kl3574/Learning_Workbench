from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02';E=B/'m63-d78-documentary-publication-oct07';S=B/'m63-public079a008-managed-sync-oct07';C=B/'m63-ci-public079a008-observation-oct07'
HEAD='079a008cf88b37e4517cb391503a1e7393ccf374'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()==HEAD and not subprocess.check_output(['git','status','--porcelain'],cwd=R)
pub=json.loads((E/'READBACK.json').read_bytes());sync=json.loads((S/'READBACK.json').read_bytes())
assert pub['git_exit_code']==0 and pub['expected_head']==pub['branch_head']==pub['pr_head']==HEAD and sync['public_head']==HEAD
binding=[]
for root,names in [(E,['identity','branch-before','pr-before','sourcepush','branch-after','pr-after']), (S,['identity','issue-before','pr-before','issue-write','issue-after','pr-write','pr-after'])]:
 for n in names:
  r=json.loads((root/(n+'-receipt.json')).read_bytes());raw=(root/(n+'.stdout')).read_bytes();err=(root/(n+'.stderr')).read_bytes()
  assert r['exit_code']==0 and r['stdout_sha256']==sha(raw) and r['stderr_sha256']==sha(err)
  binding.append({'root_alias':root.name,'name':n,'receipt':r})
ia=json.loads((S/'issue-after.stdout').read_bytes());pa=json.loads((S/'pr-after.stdout').read_bytes())
assert ia['body']==(S/'issue-body.md').read_text() and pa['body']==(S/'pr-body.md').read_text()
assert sha(ia['body'].encode())==sync['issue_body_sha256'] and sha(pa['body'].encode())==sync['pr_body_sha256']
assert pa['head']['sha']==HEAD and pa['draft'] and pa['state']=='open' and pa['merged_at'] is None
for n in ['01-SNAPSHOT.json','03-SNAPSHOT.json']:
 snap=json.loads((C/n).read_bytes());assert snap['source']==HEAD and {r['id'] for r in snap['actual_events']}=={37632652743,37632662238} and all(r['run_attempt']==1 for r in snap['actual_events'])
put('ACTUAL_REMOTE_ROOT_ADMISSION.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':HEAD,'actual_bound_commands':binding,
 'actual_push_readback':pub,'actual_managed_sync_readback':sync,'CI_originals':'push37632652743/PR37632662238 attempt1 actualstarted;01 and03 snapshots retained; no rerun/cancel',
 'private_exclusions':'Full API stdout keptprivate; only exact originallyrequested public body and command/receipt metadata admitted; no ZIP/DB/profile/PNG/payload',
 'terminal_tool_limit':'Initial observe tool76301 latermissing; saved allAPIreceipts0 and snapshot complete. No rootwrapper final0 invented; actual watcher46416 live separately observed.',
 'whole_M63_AC21_M7':'NOT_ACCEPTED','model_calls':0})
sp=importlib.util.spec_from_file_location('helper',O/'package-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
stage_names=['final-doc-stage','final-staged-diff','final-publication','documentary-commit']
push_names=['identity','branch-before','pr-before','sourcepush','branch-after','pr-after']
pubnames=['audit.py','READONLY_PUBLICATION_REVIEW.json','CURRENT_CHANGED_BINDINGS.json','OUTGOING_OBJECT_BINDINGS.json','FINDINGS.json','AUDIT_ADMISSION.json','push.py','PUSH_COMMAND_OUTCOME.json','READBACK.json','COMMIT_READBACK.json','commit.py','commit-v1-guard-failed.py','COMMIT_GUARD_V1_FAILURE.json','CORRECTED_STAGE_READBACK.json']+[n+x for n in stage_names+push_names for x in ['-command.json','-receipt.json']]+['final-publication.stdout','final-publication.stderr','sourcepush.stdout','sourcepush.stderr']
syncnames=['sync.py','READBACK.json','issue-body.md','pr-body.md']+[n+x for n in ['identity','issue-before','pr-before','issue-write','issue-after','pr-write','pr-after'] for x in ['-command.json','-receipt.json']]
cinames=['observe-once.py','watch-fixed-events.py','fetch-completed-logs.py','01-SNAPSHOT.json','03-SNAPSHOT.json','ORIGINAL_OBSERVATION_HANDLE_READBACK.json']+[n+x for n in ['01-runs','01-jobs-37632662238','01-jobs-37632652743'] for x in ['-command.json','-receipt.json']]
ep=h.package('M6.3-actual-public079a008-sourcepush-guarded-body-sync-and-two-original-CI-start',[
 ('actual-source-publication',E.name,pubnames),('actual-managed-sync',S.name,syncnames),('original-CI-start',C.name,cinames),
 ('root-readback',O.name,['record.py','ACTUAL_REMOTE_ROOT_ADMISSION.json','package-helper.py'])],
 {'scope':'Actual ordinary sourcepush079/branch and draftPRhead exact/managedIssue32 and PR56body exact/initial originalCI observations only',
 'source':HEAD,'runtime_anchor':'d78c4d159a2831f7d5e1721a9a466ec5b3e66421','engineering_inputs':1561,
 'public_paths_scanned':23175,'changed_paths_scanned':894,'outgoing_objects_scanned':993,'bounded_findings':0,
 'sourcepush_utc':pub['recorded_utc'],'body_sync_utc':sync['recorded_utc'],'current_originalCI':'IN_PROGRESS_AT_ORIGINAL_RECORDED_SNAPSHOTS','current_full_acceptance':'NOT_PROVIDED',
 'old_public1eCI':'BOTH_FAIL_UNRESOLVED_UNKNOWN','github_merge_release_deploy':False,'model_calls':0,'whole_M63_AC21_M7':'NOT_ACCEPTED'})
dp=h.package('M6.3-production-turn-current-source-gap-readonly-baseline-122-test-diagnosis',[
 ('owner-readonly','production-turn-gap-oct07-receipts',['diagnosis.md','receipt.json','focused-tests.log','SHA256SUMS'])],
 {'scope':'Fixedd78 readonly production gap facts and one unchanged baselinefocused122PASS3warnings21.58s; no new implementation',
 'source':'d78c4d159a2831f7d5e1721a9a466ec5b3e66421','actual_result':'122PASS3warnings21.58s','source_changed':False,
 'complete_input_beforeafter':'NOT_CAPTURED_BY_THIS_COMMAND; cleanfixedsource only, not wholemapqualification',
 'remaining':'trusted complete actualfinalrequest producer/checker and independent production turn runtime/executor/stopreceipt unimplemented/unqualified; not proof of impossibility',
 'real_models':'NOT_RUN','whole_M63_AC21_M7':'NOT_ACCEPTED','model_calls':0,'remote_write':False})
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3')
s['checkpoint_history'].append({'reason':'Before actual079 publichead and14:00 guardedremote-body facts synchronization','checkpoint':copy.deepcopy(s['checkpoint']),'current_local_checkpoint':copy.deepcopy(t['current_local_checkpoint'])})
for p in ['progress/state.json','progress/CURRENT.md','progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md']:
 f=O/'before-current-record'/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((R/p).read_bytes())
for p in [ep,dp]:
 if p not in t['evidence_paths']:t['evidence_paths'].append(p)
t['publication_head']=HEAD;t['documentary_publication_head']=HEAD;t['last_issue_body_sha256']=sync['issue_body_sha256'];t['last_pr_body_sha256']=sync['pr_body_sha256'];t['last_issue_readback_at']=sync['recorded_utc']
c=t['current_local_checkpoint'];c['public_head']=HEAD;c['remote_source_push']={'status':pub['status'],'readback_utc':pub['recorded_utc'],'head':HEAD,'runtime_anchor':'d78c4d159a2831f7d5e1721a9a466ec5b3e66421','no_merge_release_deploy':True,'evidence':ep}
c['current_public_originalCI']={'source':HEAD,'snapshot':3,'push':37632652743,'pull_request':37632662238,'run_attempt':1,'status':'BOTH_IN_PROGRESS_AT_03; NOT_TERMINAL','beforeafter_working_maps':'NOT_CAPTURED','evidence':ep}
c['local_current_complete_python']='Current079 independentlockedowner assigned; business notyetstarted/NOT_RUN; do not prefill collected count'
s['verification']['m6_3_current_combined1561']=c;s['verification']['m6_3_current_public079_sourcepush']=c['remote_source_push'];s['verification']['m6_3_current_public079_original_ci']=c['current_public_originalCI']
s['verification']['m6_3_current_production_turn_diagnosis']={'evidence':dp,'real_final_request_runtime':'UNIMPLEMENTED_UNQUALIFIED','baseline':'UNCHANGED_SOURCE122PASS3WARN; no wholemaps/no realmodel'}
s['verification']['ci']='Current079 originalpush37632652743/PR37632662238 attempt1 IN_PROGRESS at14:00recorded snapshot3; backend/frontend jobs succeeded, otherjobs running then, no countersborrowed. Actualremotehead/body exact. Olderpublic1e bothCIFAIL/131P2F retained; newcompleteCI notyetaccepted.'
next_action='只读观察当前079两个原CI完整终态/原日志；在新隔离锁定树执行一次当前1561完整Python门禁，保留真实numeric环境skip及所有FAIL。继续§20.17.7备份历史可验而许可不可执行的真实实现核验；生产最终模型输入证明/受限runtime仍缺，不用静态或合成切片替代。M6.3/AC21未验收，M7todo；CI终态前不再push导致自动取消原事件。'
s['next_action']=t['next_action']=s['checkpoint']['next_action']=next_action
s['checkpoint'].update({'publication_head':HEAD,'documentary_head_at_actual_sourcepush':HEAD,'resume_base_code_commit':HEAD,'local_candidate_code_commit':HEAD,'local_resume_engineering_anchor':HEAD,
 'reason':'Actual079sourcepush/branchPRexact +14:00guardedmanagedbodies exact; two originalCI started; oldfailure preserved; currentwholepending',
 'working_tree':'Newtwofinite actualremote/productiongap packets and4progressdocuments localonly; nextcommit no sourcechanges; no furtherpush while originalCI running'})
text='## 2026-10-07 实际公开与新完整验收\n\n公开分支与草稿PR56已13:57:14.574769UTC逐字回读 `'+HEAD+'`，1561工程输入。该提交保存Broker6f/Authoring3d实际有限门禁、旧68完整4559PASS2numericENVskip、旧1e两CI各131PASS2FAIL及原定向3grading/1Review通过；不把不同源码或局部结果当新完整通过。Runtime锚点d78之后仅进度/证据与三个确切归档whitespace规则；原exit2/提交前guard错误保留。原用户b895检出保持干净，没有merge/release/deploy。\n\nIssue32管理区与草稿PR56正文已14:00:26.633161UTC实际PATCH/回读；原非管理正文、title/base/head/draft/open保持。正文原snapshot3仅PR2SUCCESS4running、push3SUCCESS3running；后续状态另记，不回填历史快照。新的原push37632652743/PR37632662238 attempt1仍未获整组终态，正在只读观察；原完整输入CIbefore/after未捕获。\n\n另一次未改固定d78的122项focused/3warnings只是生产缺口诊断：缺可信完整最终模型request producer/checker及独立受限turn runtime/执行器/停止事实，不是合同不可能的证明，也未增加准备版本/静态注册旁路。默认proof为空、executor=None，实际模型调用0。新当前079完整Python将按原命令在新锁定隔离树启动一次，尚不预填计数或结果。\n\n证据：`'+ep+'`；`'+dp+'`。\n\n'+next_action+'\n\n此前各时点原记录保持如下。\n\n'
for p in ['progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md']:(R/p).write_text(text+(R/p).read_text())
save(s)
put('LOCAL_RECORD_READBACK.json',{'actual_public_head':HEAD,'actual_issue_body_sha256':sync['issue_body_sha256'],'actual_pr_body_sha256':sync['pr_body_sha256'],'sourcepush_record':pub['recorded_utc'],'body_record':sync['recorded_utc'],'evidence':[ep,dp],'newCI':'CURRENT_ORIGINAL_IN_PROGRESS_AT_RECORDED_SNAPSHOT3','current_complete_python':'NOT_STARTED_IN_THIS_RECORD','model_calls':0,'whole_M63_AC21_M7':'NOT_ACCEPTED'})
print('Recorded actual sourcepush/guardedbody/initialCI original facts; next localrecords remainunpublished while originalCI running.')
