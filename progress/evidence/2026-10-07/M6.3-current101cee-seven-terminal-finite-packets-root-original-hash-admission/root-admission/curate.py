from pathlib import Path
import datetime,hashlib,importlib.util,json,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sanitized(x):return json.loads(json.dumps(x,ensure_ascii=False).replace('$HOME','$HOME').replace('$RUNNER_HOME','$RUNNER_HOME'))
sp=importlib.util.spec_from_file_location('package_helper',B/'m63-public079a008-progress-record-oct07/package-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
checks=[];paths={}
def finite(dirname,manifest,expected,kind,key,extras):
 p=B/dirname;raw=(p/manifest).read_bytes();assert sha(raw)==expected,(dirname,manifest)
 m=json.loads(raw);es=m[key];names=[]
 for e in es:
  n=e[kind];f=p/n;assert f.is_file() and not f.is_symlink();v=f.read_bytes();assert len(v)==e['bytes'] and sha(v)==e['sha256'],(dirname,n);names.append(n)
 assert len(names)==len(set(names));checks.append({'directory':dirname,'manifest':manifest,'manifest_sha256':sha(raw),'verified_payload':len(names),'finite_only':True})
 return names+extras
reviews=[('m63-current101-progress-finite-publication-review-oct07','765ffc376e6a7a4717917a9161eb5bfeca8bc2cfa1578e7acb0ee9e052484aed','M6.3-current101cee-twelve-progress-packets-finite-publication-independent-review'),('m63-current101-exact-archive-whitespace-independent-oct07','84b2c2074c4b0a47b3497b59d6ed812a8a1e6b48821fb11d868dfb2cf63cb621','M6.3-current101cee-ten-exact-archive-whitespace-rules-independent-review'),('m63-current101-full-native-finite-independent-oct07','6c9fecb161d5a458a4c57769d208e29b93a5a65937e67c685743b7dfa1d159bc','M6.3-current101cee-full-native-finite-publication-supplement-independent-review')]
for d,digest,name in reviews:
 names=finite(d,'FINITE-ALLOWLIST.json',digest,'file','entries',['FINITE-ALLOWLIST.json','SHA256SUMS','SEAL.json'])
 paths[d]=h.package(name,[('independent-review',d,names)],sanitized({'status':'FINITE_PAYLOAD_BINDINGS_VERIFIED','scope':'Finite declared provenance; archived helper failures retained; no original tests rerun and no whole directory copy','payload_count':len(names)-3,'M6_3':'NOT_ACCEPTED','M7':'NOT_UNLOCKED','actual_model_calls_by_root':0}))
d='m63-current101-complete-python-independent-oct07'
names=finite(d,'ALLOWLIST.json','19ca134d6771e1b015c241f497b64e56cf836c3d3d79cee0f6b0a1b2ed3eddb4','path','entries',['ALLOWLIST.json','SHA256SUMS','SEAL.json'])
paths['python']=h.package('M6.3-current101cee-original-complete-Python4587PASS-numeric-ENV-skips-independent-final-closure',[('independent-review',d,names)],sanitized({'source':'101cee47d8e746dddac81fb6e8829069fcabff09','actual_argv':['uv','run','--frozen','--offline','pytest'],'collected':4589,'passed':4587,'failed':0,'errors':0,'numeric_environment_skips':2,'warnings':3,'pytest_seconds':3172.43,'original_command_wrapper_exit':[0,0],'launches':1,'all56_originals_and13_full1564_maps_independently_exact':True,'original_RESULT_PENDING_FREEZE':'RETAINED; subsequent FINAL binds actual frozen closure','later_canonical_change':'Only exact archive attrs applied after captured final closure; not same full1564 live bytes now','M6_3':'NOT_ACCEPTED','M7':'NOT_UNLOCKED','host_full_stat_or_zero_network_proof':'NOT_CAPTURED_NOT_PROVEN'}))
d='m63-current101-frontend232-original-vitest-code-closure-oct07';p=B/d
m=json.loads((p/'ROOT-MANIFEST.json').read_bytes());assert sha((p/'ROOT-MANIFEST.json').read_bytes())=='86d12d0752099830809e9259dbca45555fe4b59c21bced08ee23053db90afada'
for e in m['files']:
 f=p/e['path'];v=f.read_bytes();assert not f.is_symlink() and len(v)==e['bytes'] and sha(v)==e['sha256']
assert len(m['files'])==64
names=finite(d,'SAFE-CANDIDATE-MANIFEST.json','b228bf7e9116b0c522b5179618419aea394537b4cfcf010de0e378d06b31d080','path','files',['SAFE-CANDIDATE-MANIFEST.json','ROOT-MANIFEST.json','SEAL.json'])
original=B/'m63-public079-npm-security-evidence-oct07'
for e in json.loads((p/'05-ORIGINAL-VITEST-REFERENCES.json').read_bytes()):
 raw=(original/e['name']).read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256']
raw=(original/'20-frontend-vitest-full.stdout').read_bytes();lines=raw.decode().splitlines()
for e in json.loads((p/'06-SAFE-ORIGINAL-FOOTER-LINES.json').read_bytes()):assert sha(raw)==e['original_stdout_sha256'] and lines[e['line_number']-1]==e['text_original']
f=json.loads((p/'FINAL-REPORT.json').read_bytes());assert f['confirmed_compared_files_total']==564 and f['conclusion']=='IMPORT_CLOSURE_NOT_FULLY_DEMONSTRATED' and f['current_vitest_status']=='NOT_RERUN'
paths['frontend']=h.package('M6.3-current101cee-frontend564-source-comparison-original232-Vitest-reference-import-closure-gap-retained',[('finite-safe',d,names)],sanitized({'confirmed_files':564,'directory_files':561,'supplemental_operator_files':3,'current_source':'101cee47d8e746dddac81fb6e8829069fcabff09','original_source':'2323558615803830049a02ddfade49450d3fd77e','original_vitest_only':'1421PASS167files/exit0; original footer lines byte-bound','current101_vitest':'NOT_RERUN','complete_import_closure':'NOT_FULLY_DEMONSTRATED; four module-core recovery nodes; not accepted as full result reuse','all64_private_owner_file_hashes_verified':True,'publication_scope':'Only eight declared safe candidates plus three sidecars; no private raw logs','M6_3':'NOT_ACCEPTED'}))
d='m63-current101-exact-archive-whitespace-apply-oct07'
names=['APPLY-COMMAND.json','APPLY-RECEIPT.json','SOURCE-BEFORE.json','SOURCE-AFTER.json','ACTUAL-ATTRIBUTE-READBACK.json']+[x+'/'+n for x in ['fixed101-attrs','current-attrs'] for n in ['command.json','receipt.json','stdout','stderr']]
a=json.loads((B/d/'APPLY-RECEIPT.json').read_bytes());assert a['changed_source_paths']==['.gitattributes'] and a['other1563exact']
paths['archive_apply']=h.package('M6.3-current101cee-ten-exact-archive-rules-post-gate-actual-apply-and-Git-attribute-readback',[('actual-apply',d,names)],sanitized({'source_fixed_gate':'101cee47d8e746dddac81fb6e8829069fcabff09','actual_apply':'COMPLETED_AFTER_BOTH_FULL_GATES_AND_FINAL_SOURCE_CLOSURE','changed_source_paths':['.gitattributes'],'other1563_git_mode_type_blob_bytes_exact':True,'ten_literal_progress_attributes_only':True,'all1564_nonprogress_whitespace_values_unchanged':True,'original_default_staged_diff':'exit2 retained in prior original evidence; new check pending','tests_rerun':False,'actual_apply_capture_limit':'inline Python source not separately archived; actual file write metadata and two original Git attribute quartets retained','source_push':False,'M6_3':'NOT_ACCEPTED'}))
d='m63-current101-complete-terminal-managed-sync-oct07'
r=json.loads((B/d/'root-receipt.json').read_bytes());assert r['actual_exit']==0
names=['sync.py','run-recorded.py','READBACK.json','issue-body.md','pr-body.md','root-command.json','root-receipt.json','root.stdout','root.stderr']+[n+suffix for n in ['identity','issue-before','pr-before','branch-before','issue-write','issue-after','pr-write','pr-after'] for suffix in ['-command.json','-receipt.json','.stderr']]
paths['managed_sync']=h.package('M6.3-current101cee-complete-terminal-actual-guarded-Issue32-draftPR56-body-sync',[('actual-managed-sync',d,names)],sanitized({'actual_root_command_exit':0,'scope':'Issue32 managed region and draftPR56 body only; metadata and draft/open/unmerged preserved','source_public':'079a008cf88b37e4517cb391503a1e7393ccf374','source_local_gate_anchor':'101cee47d8e746dddac81fb6e8829069fcabff09','current_gates':'4587P2numericENVskip3warnings/uv0wrapper0; native133P0F20.9m/make0wrapper0','raw_GitHub_API_payloads':'PRIVATE_NOT_COPIED','source_push_merge_release_deploy':False,'M6_3':'NOT_ACCEPTED'}))
put('ROOT-FINITE-ADMISSION.json',sanitized({'checks':checks,'frontend_owner64hashes_and_original7refs2footer_lines':'EXACT','packets':paths,'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}))
s=h.read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');s['verification']['m6_3_current101_terminal_finite_curation']={'status':'ACTUAL_FINITE_HASH_AND_BYTE_ADMISSION','packets':paths,'current_full_python':'4587PASS2numericENVskip3warn/uv0wrapper0/3172.43s','native':'133PASS0FAIL20.9m/make0wrapper0','frontend':'564confirmed files only; import closure NOT_FULLY_DEMONSTRATED; current101NOT_RERUN','archival_attrs':'Ten literal rules applied after fixed101 closure; other1563exact','wholeM6_3':'NOT_ACCEPTED','M7':'NOT_UNLOCKED'};t['current_local_checkpoint']['python']['current1564']['evidence']=paths['python'];t['current_local_checkpoint']['frontend_reference_qualification']={'evidence':paths['frontend'],'current101':'NOT_RERUN','scope':'564confirmed only/importclosureNOT_FULLY_DEMONSTRATED'};h.save(s)
print('Seven finite packets admitted; original failures and qualifications retained.')
