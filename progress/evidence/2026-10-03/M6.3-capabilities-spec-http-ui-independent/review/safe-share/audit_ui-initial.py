from pathlib import Path
import hashlib,json,subprocess,importlib.util
p=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-capabilities-ui-evidence-oct03');e=Path(__file__).parent;t=e.parent/'m63-spec-http-independent-oct03';h=lambda b:hashlib.sha256(b).hexdigest();head='54fc266798a1e4be2142266012f24f468a57fb98';m=json.loads((p/'MANIFEST.json').read_text());share=json.loads((p/'SAFE_SHARE.json').read_text())['items'];before={x['path']:h((p/x['path']).read_bytes()) for x in m['items']}
assert len(m['items'])==32 and len(share)==33
assert h((p/'MANIFEST.json').read_bytes())=='c18a0bf7b05cf52d1b37d08c9bef548c3cda0b249043adfda0ab4a89e50b187e'
for x in m['items']:
 b=(p/x['path']).read_bytes();assert h(b)==x['sha256'] and len(b)==x['bytes']
assert {x['source'] for x in share}==set(before)|{'MANIFEST.json'}
sp=importlib.util.spec_from_file_location('scan',t/'scripts/check_publication.py');mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod);findings=[]
for x in share:
 raw=(p/x['source']).read_bytes();candidate=(p/x['candidate']).read_bytes();assert h(raw)==x['raw_sha256'] and h(candidate)==x['candidate_sha256']
 assert candidate==raw.replace(b'<LOCAL_HOME>',b'<LOCAL_HOME>').replace(b'<RUNNER_HOME>',b'<RUNNER_HOME>')
 assert x['transformation']==('none' if raw==candidate else 'exact home prefixes to <LOCAL_HOME>/<RUNNER_HOME>')
 for reason in mod.inspect('progress/evidence/M63-ui/'+x['source'],candidate):findings.append({'path':x['candidate'],'reason':reason})
assert not findings
stages=[]
for name,runner in [('focused','gates.py'),('strict','gates.py'),('native-types','gates-native.py'),('native','gates-native.py')]:
 b=json.loads((p/(name+'-before.json')).read_text());a=json.loads((p/(name+'-after.json')).read_text());r=json.loads((p/(name+'-receipt.json')).read_text());assert a==b and r['head']==head and r['exit_code']==0 and r['inputs_unchanged'] and r['input_count']==b['count']==len(b['tracked'])==1320
 assert h((p/(name+'.log')).read_bytes())==r['log_sha256'] and h((p/runner).read_bytes())==b['runner_sha256']
 for path,expected in b['tracked'].items():
  data=subprocess.check_output(['git','show',head+':'+path],cwd=t);assert h(data)==expected,path
 stages.append({'stage':name,'exit_code':0,'log_sha256':r['log_sha256'],'tracked_inputs':1320,'before_after_equal':True,'duration_seconds':r['duration_seconds']})
actual_path=next(x['source'] for x in share if x['source'].endswith('codex-capabilities-actual.json'));raw=(p/actual_path).read_bytes();assert h(raw)=='2d6fc09436b7add2dc90d0a236157bf4ce6e1cffcd4649dea5ccf8f0396b43c0';actual=json.loads(raw)
for stage in ['first','second']:
 a=actual[stage];assert a['status']==200;v=a['capabilities'];assert v['available'] is True and v['authorized'] is False and v['adapter_version']=='codex-cli/0.160.0' and v['capabilities']=={'approvals':False,'interrupt':False,'artifacts':False}
assert actual['first']==actual['second'];assert actual['api_processes']==2
assert {x['path']:h((p/x['path']).read_bytes()) for x in m['items']}==before
receipt={'status':'PASS_BOUNDED_UI_EVIDENCE_ONLY','source':head,'raw_manifest_sha256':h((p/'MANIFEST.json').read_bytes()),'raw_entries_rechecked':32,'share_entries_rechecked':33,'all_candidates_exact_transform':True,'stages':stages,'actual_path':actual_path,'actual_sha256':h(raw),'actual_key_names':list(actual),'two_actual_observations':'200, available true, authorized false, three product flags false','api_processes':2,'scan_findings':findings,'original_members_unchanged':True,'known_security_limit_sha256':h((p/'SECURITY_LIMITATION.json').read_bytes()),'boundary':'This validates retained evidence and actual source binding only, not a new native run or fence safety. Existing learner native assertion is UI admission, not direct HTTP denial. The separately added SECURITY_LIMITATION records P1 IPC and P2 FIFO, and final publication remains held pending owner fix/review.'}
(e/'UI_EVIDENCE_REVIEW.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'status':receipt['status'],'raw':32,'share':33,'stages':len(stages),'receipt_sha256':h((e/'UI_EVIDENCE_REVIEW.json').read_bytes())}))
