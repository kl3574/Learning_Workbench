from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02';E=B/'m63-forward-guard-review-browser-diagnosis-oct07'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
manifest=(E/'17-ROOT-FINITE-REVIEW-MANIFEST.json').read_bytes()
assert sha(manifest)=='ddebc2eb2662319c5e0ef8cc7a7f6ce8fa0720e93ab761362940eb67241ef218'
m=json.loads(manifest);assert len(m['files'])==41
for e in m['files']:
 p=Path(e['path']);assert p.is_relative_to(B)
 raw=p.read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256']
assert sha((E/'SEAL.json').read_bytes())=='2fafe51f23b0d58c70f692e1c05cd7a497d673a3be40a0a76535105d52e8c1ef'
d=load(E/'06-BROWSER-DIAGNOSIS.json');timing=load(E/'02-original-review-history-timing.json')
assert timing['observed_timeout_ms']==30000 and timing['retry']==0
assert len(timing['phases'])==30 and len(timing['http'])==286 and all(v==0 for v in timing['dropped'].values())
byname={x['stage']:x['elapsed_ms'] for x in timing['phases']}
values={'reader_route_to_finally_ms':byname['body-finally']-byname['reader-route'],
 'assessment_interval_ms':byname['question-select']-byname['assessment-start'],
 'manual_interval_ms':byname['history-immutability']-byname['manual-review-and-grade']}
assert abs(values['reader_route_to_finally_ms']-0.680531)<1e-6
for key,left,right,count in [('assessment','assessment-start','question-select',33),('manual','manual-review-and-grade','history-immutability',23)]:
 events=[x for x in timing['http'] if byname[left]<=x['elapsed_ms']<byname[right] and x['event']=='request']
 assert len(events)==count
source=load(E/'09-SOURCE-BINDING.json')
assert len(source['files'])==16
for e in source['files']:
 raw=Path(e['path']).read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256']
 gitraw=subprocess.run(['git','show','079a008cf88b37e4517cb391503a1e7393ccf374:'+e['repo_path']],cwd=R,capture_output=True,check=True).stdout
 assert raw==gitraw
assert load(E/'14-finalize-receipt.json')['exit_code']==1
assert load(E/'16-finalize-v2-receipt.json')['exit_code']==0
assert d['product_defect']==d['root_cause']=='UNKNOWN' and not d['cause_closed']
(O/'ROOT-ADMISSION.json').write_text(json.dumps({'status':'BOUNDED_DIAGNOSTIC_ONLY_ORIGINAL_PR_FAIL_RETAINED',
 'root_scope':'41finite original hashes and16 named fixed079 source bytes independently rebound; complete diagnosis and summary read; timing arithmetic and interval starts recomputed. No whole production source/manual raw log semantic reread.',
 'source':'079a008cf88b37e4517cb391503a1e7393ccf374','original_PR':'37632662238/112830674946 attempt1;132P1F/shared30s',
 'timing':values,'body_only':True,'missing_original_setup_page_request_JSON_React':'NOT_CAPTURED',
 'inference':'Nearzero reader-route observed time is consistent with earlier shared deadline exhaustion; original fixture timing absent; product defect/cause UNKNOWN.',
 'historical_authorization_note':'The older proposed report wording is a timestamped suggestion. Existing user authorization permits ordinary local diagnostic work; no extra permission requirement was inferred.',
 'original_report_builder_failure':'14actualexit1wrongstreamfilename retained;16actual0; no producttest failure substitution.',
 'exclusions':'RawAuthCase/rawfullCI/API/ZIP/screenshots/DB/profile/originalbodytimingpayload; only bounded summaries admitted.',
 'whole_M63_CI_model_AC21_M7':'NOT_ACCEPTED','remote_mutation_model_probe':False},indent=2)+'\n')
sp=importlib.util.spec_from_file_location('helper',B/'m63-public079a008-progress-record-oct07/package-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
path=h.package('M6.3-public079-PR-Review-failure-finite-timing-readback-cause-unknown',[
 ('owner-finite',E.name,['06-BROWSER-DIAGNOSIS.json','07-BROWSER-DIAGNOSIS.md','08-INTERVAL-HTTP-SUMMARY.json','09-SOURCE-BINDING.json','11-SAFE-SUMMARY-CANDIDATE.json','17-ROOT-FINITE-REVIEW-MANIFEST.json','SEAL.json',
 '01-failure-artifact-command.json','01-failure-artifact-receipt.json','14-finalize-command.json','14-finalize-receipt.json','14-finalize.stderr','16-finalize-v2-command.json','16-finalize-v2-receipt.json','16-finalize-v2.stdout','16-finalize-v2.stderr']),
 ('root-finite',O.name,['verify.py','ROOT-ADMISSION.json'])],
 {'status':'DIAGNOSTIC_ONLY_CAUSE_UNKNOWN','source':'079a008cf88b37e4517cb391503a1e7393ccf374','original_PR':'132P1F/shared30s',
 'independent_bindings':'41 finite files/16fixed079namedsource bytes/timing arithmetic and starts',
 'reader_route_to_finally_ms':values['reader_route_to_finally_ms'],'product_defect':'UNKNOWN','repair':'NOT_IMPLEMENTED_IN_THIS_PACKET',
 'safe_next_observer':'552 separate candidate/gate; no deadline/retry/assertion changes or cause closure',
 'raw_zip_API_AUTH_DB_profile':'EXCLUDED','wholeM63':'NOT_ACCEPTED','model_calls':0,'source_push':False})
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');t['evidence_paths'].append(path)
s['verification']['m6_3_original079_PR_review_bounded_diagnosis']={'status':'CAUSE_UNKNOWN_DIAGNOSTIC_ONLY','original':'132P1F/shared30s',
 'reader_route_observed_ms':values['reader_route_to_finally_ms'],'original_missing':'fixture/page.request/JSONReact notcaptured','root41finite16source':True,'evidence':path}
save(s)
(O/'INSTALL-READBACK.json').write_text(json.dumps({'evidence':path,'status':'DIAGNOSTIC_ONLY'},indent=2)+'\n')
print('41finite and16 source bindings qualified; originalReview cause UNKNOWN retained.')
