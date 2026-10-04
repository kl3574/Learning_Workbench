from pathlib import Path
import hashlib,json,subprocess
base=Path('$HOME/.cache/learning-workbench-acceptance');root=base/'m62-public-safe-oct02'
producer=base/'m63-local-session-bootstrap-evidence-oct03'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
head='04500f20fd9727d9b15da081e820bbd81a780fad'
stage=producer/'stages/45-actual-profile-v3-control'
before=json.loads((stage/'before.json').read_text());after=json.loads((stage/'after.json').read_text());gate=json.loads((stage/'result.json').read_text())
assert before==after and before['head']==gate['head']==head
assert gate['exit_code']==0 and gate['input_count']==len(before['files'])==1364 and gate['inputs_unchanged'] and gate['all_match_git']
assert before['runner_sha256']==sha((producer/'run_stage.py').read_bytes())
tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',head],cwd=root,text=True).splitlines()
assert set(before['files'])=={path for path in tracked if not path.startswith('progress/')}
for name,item in before['files'].items():
 blob=subprocess.check_output(['git','show',head+':'+name],cwd=root)
 assert sha(blob)==item['sha256'] and len(blob)==item['bytes'] and item['matches_git']
 assert subprocess.check_output(['git','rev-parse',head+':'+name],cwd=root,text=True).strip()==item['git_blob']
actual=json.loads((producer/'actual-45/actual.json').read_text())
assert actual['source_head']==head and actual['runner_sha256']==sha((producer/'actual_control_45.py').read_bytes())
assert actual['status']=='PASS_REAL_RESTRICTED_CONTROL' and actual['create_status']==201 and actual['control_process_count']==1
assert actual['control_exit_codes']==[-9] and actual['pipes_closed'] and actual['original_response_replay_bytes_equal'] and actual['application_recreation_same_db_original_replay_bytes_equal']
assert actual['session_current']['status']=='ready' and actual['session_current']['revision']==2 and actual['session_current']['active_turn_id'] is None
assert actual['session_current']['capabilities']=={'approvals':False,'interrupt':False,'artifacts':False}
assert actual['create_response']['id']==actual['session_current']['id']==actual['consumed_preparation']['session_id']
assert actual['consumed_preparation']['actor_session_id']==actual['preparation_ack']['actor_session_id']==actual['decision_ack']['actor_session_id']
assert actual['consumed_preparation']['status']=='consumed' and actual['consumed_preparation']['validity']=='closed'
assert actual['prior_instance']['status']=='unknown' and actual['prior_instance']['id']!=actual['session_current']['id']
offline=json.loads((producer/'offline-schema-36/receipt.json').read_text())
assert offline['binary_sha256']=='12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad' and offline['binary_bytes']==289101384
assert offline['exit_code']==0 and offline['stdout_bytes']==offline['stderr_bytes']==0 and offline['within_budget'] and offline['generated_files']==len(offline['files'])==440
for item in offline['files']:
 data=(producer/'offline-schema-36/broker'/item['path']).read_bytes()
 assert len(data)==item['bytes'] and sha(data)==item['sha256']
selected={}
for name in ('ThreadStartParams.json','ThreadStartResponse.json','ThreadStartedNotification.json','ServerNotification.json'):
 blob=subprocess.check_output(['git','show',head+':services/api/app/infrastructure/codex_protocol/experimental/'+name],cwd=root)
 matches=[item for item in offline['files'] if Path(item['path']).name==name and item['sha256']==sha(blob)]
 assert len(matches)==1 and len(blob)==matches[0]['bytes']
 selected[name]=sha(blob)
report={'status':'PASS_SCOPED_REAL_CONTROL_INDEPENDENT_READBACK','head':head,'nonprogress_inputs':1364,'all_before_after_and_git_match':True,
 'actual_http_status':201,'session_status':'ready/r2','actual_create_seconds':actual['create_seconds'],'actual_control_processes':1,'owned_exit_codes':[-9],'pipes_closed':True,
 'original_ack_and_same_db_recreation_replay_equal':True,'no_additional_start_on_replay':True,'old_unknown_retained':True,
 'offline_schema_generation':{'files':440,'exit_code':0,'stdout_bytes':0,'stderr_bytes':0,'exact_selected_git_sha256':selected},
 'runner_bindings_verified':['run_stage.py','actual_control_45.py'],
 'boundary':'Independent readback and static runner/runtime review. Real fixed CLI control only; no turn/model/account/login/tool RPC, no global credential copy. Not whole M6.3/AC21/security audit. Prior three unknown instances and gate errors remain; new native/full integrated gates pending.',
 'original_root_readback_harness_errors':'First metadata print indexed intentionally empty events; second metadata print treated generated_files integer as list; both retained, no producer/source/product/remote mutation.'}
(Path(__file__).parent/'READBACK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('offline_schema_generation','runner_bindings_verified','original_root_readback_harness_errors')},ensure_ascii=False))
