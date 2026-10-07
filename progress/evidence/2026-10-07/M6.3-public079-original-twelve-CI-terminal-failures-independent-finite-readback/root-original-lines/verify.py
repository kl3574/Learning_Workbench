from pathlib import Path
import datetime, hashlib, importlib.util, json, re, sys

O=Path(__file__).resolve().parent; B=O.parent
E=B/'m63-public079-terminal-jobs-independent-oct07'
C=B/'m63-ci-public079a008-observation-oct07'
R=B/'m62-public-safe-oct02'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
assert sha((E/'CANDIDATE-ALLOWLIST.json').read_bytes())=='6617ba673df588c769558fb90c491a923c87091a0df0ef16db9f0f32f687737b'
allow=load(E/'CANDIDATE-ALLOWLIST.json')
for f in allow['files']:
 raw=(E/f['path']).read_bytes();assert len(raw)==f['bytes'] and sha(raw)==f['sha256']
d=load(E/'FINAL-READBACK.json')
assert sha((E/'FINAL-READBACK.json').read_bytes())=='f09870316359261715e035304353fc367f6c4dbf891de6833502cd4c07d7687a'
snapraw=(C/d['source_snapshot']).read_bytes();assert sha(snapraw)==d['snapshot_sha256']
snap=json.loads(snapraw);assert snap['sequence']==98
assert len(d['jobs'])==12 and len(d['events'])==2
assert all(e['status']=='completed' and e['conclusion']=='failure' and e['run_attempt']==1 for e in d['events'])
bindings=[]; selected_count=0
for j in d['jobs']:
 raw=(C/j['original_file']).read_bytes()
 assert len(raw)==j['original_bytes'] and sha(raw)==j['original_sha256']
 stem=j['original_file'].removesuffix('.stdout')
 cr=(C/(stem+'-command.json')).read_bytes(); rr=(C/(stem+'-receipt.json')).read_bytes()
 assert sha(cr)==j['collector_command_sha256'] and sha(rr)==j['collector_receipt_sha256']
 cmd=json.loads(cr);rc=json.loads(rr)
 assert cmd['run_id']==j['run_id'] and cmd['job']['id']==j['id'] and cmd['run_attempt']==1
 assert rc['exit_code']==0 and rc['stdout_sha256']==sha(raw) and rc['stdout_bytes']==len(raw)
 err=(C/(stem+'.stderr')).read_bytes();assert not err and rc['stderr_sha256']==sha(err)
 lines=raw.decode('utf-8').splitlines()
 for s in j['safe_excerpt']:
  text=re.sub(r'^\d{4}-\d\d-\d\dT\S+\s*','',lines[s['line']-1])
  text=re.sub(r'\x1b\[[0-9;]*m','',text).strip()
  if s['category']=='bare_failed_test_identifier_only':
   text='FAILED '+re.match(r'^FAILED (tests/integration/[A-Za-z0-9_/]+\.py::[A-Za-z0-9_]+)',text)[1]
  assert text==s['text'];selected_count+=1
 bindings.append({'event':j['event'],'job_id':j['id'],'actual_conclusion':j['conclusion'],
                   'original_bytes':len(raw),'original_sha256':sha(raw),'selected_lines':len(j['safe_excerpt']),
                   'capture_exit':0,'original_test_conclusion_separate':True})
counts={}
for e in d['events']:
 js=[j for j in d['jobs'] if j['run_id']==e['id']]
 assert len(js)==6
 counts[e['event']]={'success':sum(j['conclusion']=='success' for j in js),'failure':sum(j['conclusion']=='failure' for j in js)}
assert counts=={'pull_request':{'success':4,'failure':2},'push':{'success':5,'failure':1}}
(O/'ROOT-ADMISSION.json').write_text(json.dumps({'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'BOTH_ORIGINAL_CI_FAIL_RETAINED','source':'079a008cf88b37e4517cb391503a1e7393ccf374','snapshot':98,
 'root_scope':'Whole7679B owner report read, allfinite candidate hashes/12 original capture quartet metadata and every admitted physical line rebound; no whole raw manual semantic reread.',
 'original_capture_bindings':bindings,'exact_admitted_source_lines':selected_count,'event_job_counts_not_additive':counts,
 'source_Git_tree':'Currente9PRmergetree23175equal079 verified separately; executiontime workingmaps NOT_CAPTURED',
 'failed_actual':'Bothintegration1F2518P2numericENVskip2warn; PRbrowser1F132P/whole30s; pushbrowser133P',
 'limits':'No later local fix replaces oldFAIL; ReviewcauseUNKNOWN; M63/model/host/AC21/M7NOT_ACCEPTED',
 'no_rerun_model_remote_mutation':True},ensure_ascii=False,indent=2)+'\n')
sp=importlib.util.spec_from_file_location('helper',B/'m63-public079a008-progress-record-oct07/package-helper.py')
h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
path=h.package('M6.3-public079-original-twelve-CI-terminal-failures-independent-finite-readback',[
 ('owner-finite',E.name,[e['path'] for e in allow['files']]+allow['included_seal_sidecars']),
 ('root-original-lines',O.name,['verify.py','ROOT-ADMISSION.json'])],
 {'status':'BOTH_ORIGINAL_EVENTS_FAILURE','source':snap['source'],'snapshot':98,
  'push':'37632652743/5SUCCESS1FAIL;integration2518P1F2numericENVskip;browser133PASS',
  'PR':'37632662238/4SUCCESS2FAIL;integration2518P1F2numericENVskip;browser132P1F whole30s',
  'original_failed_jobs':3,'capture_quartets':12,'admitted_original_safe_lines':selected_count,
  'counts':'Per event and job; never added to acceptance total','working_input_maps':'NOT_CAPTURED',
  'whole_M63_model_AC21_M7':'NOT_ACCEPTED','actual_model_calls':0,'remote_mutation':False})
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');t['evidence_paths'].append(path)
old=s['verification'].get('m6_3_current_public079_original_ci')
final={'source':snap['source'],'status':'BOTH_COMPLETED_FAILURE','snapshot':98,'observed_utc':snap['observed_utc'],
 'events':d['events'],'per_event_job_counts':counts,'scoped_counts':'eachbackend1114P3warn/frontend1421P167files/spec962P2warn; eachintegration2518P1F2ENVskip2warn;pushbrowser133P/PRbrowser132P1F',
 'previous_snapshot_record':old,'working_input_maps':'NOT_CAPTURED','evidence':path,'model_requests':0,'wholeM63':'NOT_ACCEPTED'}
s['verification']['m6_3_current_public079_original_ci']=final
s['verification']['ci']='Original079 twoCI completedFAIL:push5S1integrationF;PR4S1integrationF1ReviewbrowserF. Exact12original logs/finite physical lines qualified; executionbeforeafterNOT_CAPTURED. Newsource candidates and wholeM63 acceptance separate.'
t['current_local_checkpoint']['current_public_originalCI']=final
t['current_public_ci']=final
s['next_action']='正常本地合入经独立审阅的迁移夹具90c8、锁补丁232及备份8bd/Review安全计时552，保留公开079原双CI FAIL与4580P1F完整Python；对新组合运行一次完整门禁并同步真实结果。零真实模型外发，完整InputProof/受限runtime和物理数值仍缺，M6.3/AC21未验收，M7todo。'
save(s)
(O/'INSTALL-READBACK.json').write_text(json.dumps({'evidence':path,'status':'BOTH_ORIGINAL_CI_FAIL','source_push':False},indent=2)+'\n')
print('12original capture sets and '+str(selected_count)+' exact safe source lines qualified; bothCI FAIL recorded without rerun.')
