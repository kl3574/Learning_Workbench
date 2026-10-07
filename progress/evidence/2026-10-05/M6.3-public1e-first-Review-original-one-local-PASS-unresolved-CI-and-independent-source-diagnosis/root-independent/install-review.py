from pathlib import Path
import hashlib, importlib.util, json, os, subprocess
O=Path(__file__).resolve().parent; B=O.parent
E=B/'m63-public1e-first-review-bounded-native-oct05'; P=E/'safe-share-original-v1'
T=B/'m63-public1e-first-review-bounded-owner-oct05'
HEAD='1e7ad7a8656c0dc8373d4181fa3002f385ed1847'
def sha(b): return hashlib.sha256(b).hexdigest()
assert sha((E/'FINAL_OUTER_ALLOWLIST-original-v1.json').read_bytes())=='dc61b06c79d74144d03507f5357320016db7f0d87568dd52d31db53534ff577c'
outer=json.loads((E/'FINAL_OUTER_ALLOWLIST-original-v1.json').read_bytes())
for e in outer['allow_only_outer']:
 b=(E/e['path']).read_bytes(); assert len(b)==e['size'] and sha(b)==e['sha256']
m=json.loads((E/'SAFE_CANDIDATES-original-v1.json').read_bytes())
assert m['head']==HEAD and len(m['entries'])==46
for e in m['entries']:
 raw=(B/e['original_cache_relative_path']).read_bytes(); b=(P/e['candidate_path']).read_bytes()
 assert len(raw)==e['original_size'] and sha(raw)==e['original_sha256']
 assert len(b)==e['candidate_size'] and sha(b)==e['candidate_sha256']
 assert b==(raw if e['conversion']=='identity' else raw.replace(b'$HOME',b'$HOME'))
 b.decode()
base=json.loads((B/'m63-turn-protocol-catalog-evidence-oct05/seal-27f/publication-candidates/FULL_GIT_INPUTS.json').read_bytes())
base=next(x for x in base['maps'] if x['head']=='27f549ff5a8fd67b0a601b67a5ba51ef35f6765f')
old={e['path']:(e['mode'],e['type'],e['blob'],e['size'],e['sha256']) for e in base['entries']}; assert len(old)==1541
runner=(E/'run_stage.py').read_bytes(); stages=[]
for name,code in [('setup-original',0),('list-first-original',1),('list-first-title-corrected',0),('native-first-original',0)]:
 before=(P/name/'before.json').read_bytes(); after=(P/name/'after.json').read_bytes(); assert before==after
 d=json.loads(before); actual={e['path']:(e['mode'],e['type'],e['blob'],e['size'],e['sha256']) for e in d['entries']}
 assert d['head']==HEAD and d['count']==1541 and actual==old
 c=json.loads((E/name/'command.json').read_bytes()); r=json.loads((E/name/'receipt.json').read_bytes()); log=(E/name/'run.log').read_bytes()
 assert c['source_head']==r['head']==HEAD and r['before_after_complete_exact'] and r['input_count']==1541
 assert r['command_exit_code']==r['wrapper_exit_code']==code
 assert c['runner_sha256']==r['runner_sha256']==sha(runner)
 assert len(log)==r['log_size'] and sha(log)==r['log_sha256']
 stages.append({'stage':name,'receipt':r,'command_sha256':sha((E/name/'command.json').read_bytes()),'map_sha256':sha(before)})
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=T).decode().strip()==HEAD
assert not subprocess.check_output(['git','status','--porcelain'],cwd=T)
tree={}
for row in subprocess.check_output(['git','ls-tree','-rz',HEAD],cwd=T).split(b'\0'):
 if row:
  h,p=row.split(b'\t',1); tree[p.decode()]=tuple(h.decode().split())
for p,e in old.items():
 assert tree[p]==e[:3]
 f=T/p; b=os.readlink(f).encode() if e[0]=='120000' else f.read_bytes()
 assert len(b)==e[3] and sha(b)==e[4]
 if e[0]!='120000': assert bool(f.stat().st_mode & 0o111)==(e[0]=='100755')
peer=json.loads((P/'source-readonly-peer/INPUT_ALLOWLIST.json').read_bytes())
assert peer['fixed_head']==HEAD and peer['source_file_count']==len(peer['source_files'])==21
for e in peer['source_files']:
 assert old[e['source_path']]==(e['mode'],e['type'],e['git_blob'],e['size'],e['sha256'])
assert b'1 passed (19.0s)' in (P/'native-first-original/run.log').read_bytes()
assert b'Total: 0 tests in 0 files' in (P/'list-first-original/run.log').read_bytes()
assert b'Total: 1 test in 1 file' in (P/'list-first-title-corrected/run.log').read_bytes()
cfg=(P/'source/tests/e2e/playwright.config.ts').read_bytes()
assert b'timeout: 30000' in cfg and b'workers: 1' in cfg
timings=[]
for n in ['original-review-timing-37241154917.json','original-review-timing-37241158099.json','original-local-first-review-timing.json']:
 b=(P/'explicit-timing-readback'/n).read_bytes();d=json.loads(b)
 assert d['observed_timeout_ms']==30000 and d['retry']==0
 timings.append({'path':n,'sha256':sha(b),'phases':len(d['phases']),'http_events':len(d['http'])})
admission={'role':'root independent exact finite46 copies / eight1541maps / immutable public source and live1541 continuity; original selfrunner/log/receipt qualification, no rerun',
 'source':HEAD,'candidate_count':46,'stage_map_bindings':4*2*1541,'source_peer_bindings':21,'stages':stages,'timing_metadata':timings,
 'actual_business':'one original firstReview1PASS16.4s / suite19.0s / wrapper19.35910998s',
 'manual_read':'Complete original744B success,476B zero-test listFAIL, corrected list and owner/report/peerMD; peer source semantic coverage is separately declared, root doesnot invent a full21file semantic audit',
 'baseline':'Previously root-qualified immutable27f1541engineering reused by mode/type/blob/size/SHA; all live1541files checked, no oldpayload recat',
 'limits':['No product fix or oldCIcause closure; old public1e CI FAIL remains UNKNOWN','Fixture/page.request/JSONReact/exactURLpoll NOT_CAPTURED; whole/body difference not fixture time','Current1561 whole Python/native/newCI NOT_RUN; model0; M6.3/AC21/M7 NOT_ACCEPTED','Only explicit metadata and finite sources; PNG/ZIP/DB/profile/privatepayload excluded']}
(O/'REVIEW_ROOT_ADMISSION.json').write_text(json.dumps(admission,ensure_ascii=False,indent=2)+'\n')
sp=importlib.util.spec_from_file_location('packet_helper',B/'m63-412abe-progress-checkpoint-oct05/package-helper-archived.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
path=h.package('M6.3-public1e-first-Review-original-one-local-PASS-unresolved-CI-and-independent-source-diagnosis',[
 ('original-owner-qualified','m63-public1e-first-review-bounded-native-oct05/safe-share-original-v1',[e['candidate_path'] for e in m['entries']]),
 ('seal','m63-public1e-first-review-bounded-native-oct05',['FINAL_OUTER_ALLOWLIST-original-v1.json','SAFE_CANDIDATES-original-v1.json','PACKET_READBACK-original-v1.json']),
 ('root-independent','m63-broker6f-progress-checkpoint-oct05',['install-review.py','REVIEW_ROOT_ADMISSION.json'])],
 {'scope':'one unchanged public1e firstReview original business PASS; source read-only peer21 metadata separate; no product repair',
 'source':HEAD,'inputs':1541,'actual_business_passed':1,'case_seconds':16.4,'suite_seconds':19.0,'wrapper_seconds':19.359109979995992,
 'qualified':'46finitecandidates/eightmaps12328bindings/21peerbindings/live1541exact/selfrunner/originalfourstages; zero-test listFAIL retained',
 'original_CI':'FAIL_UNRESOLVED_UNKNOWN','missing_observation':'fixture/page.request/JSONReact/exactURLpoll NOT_CAPTURED','current1561whole':'NOT_RUN','whole_M63_AC21_M7':'NOT_ACCEPTED','model_calls':0,'remote_write':False})
(O/'REVIEW_INSTALL_READBACK.json').write_text(json.dumps({'review_evidence':path,'actual_original_first_case':'1PASS16.4s; single unchanged business','oldCI':'FAIL_UNKNOWN','source_changed':False},indent=2)+'\n')
print('Qualified46finite Review candidates, original one-case PASS and unchanged1541 source; no oldCI repair claim.')
