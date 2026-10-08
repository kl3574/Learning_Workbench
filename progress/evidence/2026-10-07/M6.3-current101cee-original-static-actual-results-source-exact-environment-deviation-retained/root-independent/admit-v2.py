from pathlib import Path
import datetime,hashlib,importlib.util,json,sys
O=Path(__file__).resolve().parent;B=O.parent;E=B/'m63-integrated-1564-static-evidence-oct07';R=B/'m62-public-safe-oct02'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
a=load(E/'FINITE-ALLOWLIST.json');assert sha((E/'FINITE-ALLOWLIST.json').read_bytes())=='a24ee75396cf29815a272387ab9581fea22300014f73314ab340f6f997c8c27a'
assert len(a['files'])==a['finite_count']==57
for entry in a['files']:
 raw=(E/entry['path']).read_bytes();assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'],entry['path']
assert sha((E/'47-ENVIRONMENT-DEVIATION-CORRECTION.json').read_bytes())=='b77627cdbb029da9a376d68006320132262e113a4cc2d841eb96b8ad21b42774'
review=load(E/'REVIEW.json');assert review['fixed_commit']=='101cee47d8e746dddac81fb6e8829069fcabff09'
base=load(E/'03-SOURCE-BEFORE-SETUP.json');expected=load(B/'m63-integrated-four-candidates-local-merge-oct07/FINAL-SOURCE-METADATA.json')
assert base['count']==len(base['rows'])==len(expected)==1564
for row in base['rows']:
 e=expected[row['path']];assert all(row['git'][k]==e[k] for k in ['mode','type','blob']);assert int(row['git']['size'])==e['bytes']
comparisons=load(E/'40-ALL-SOURCE-MAP-COMPARISONS.json')['comparisons'];assert len(comparisons)==10
for comparison in comparisons:
 entry=comparison['map'];raw=(E/entry['path']).read_bytes();assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256']
 other=json.loads(raw);assert other['head']==base['head'] and other['count']==1564 and other['rows']==base['rows']
 assert other['git_index_metadata_sha256']==base['git_index_metadata_sha256'] and other['git_tree_metadata_sha256']==base['git_tree_metadata_sha256']
 assert comparison['all_1564_rows_exact_including_stat'] and all(not x for x in comparison['differences'].values())
commands=[]
for entry in a['files']:
 if entry['path'].endswith('/receipt.json'):
  group=Path(entry['path']).parent;receipt=load(E/entry['path']);command=load(E/group/'command.json')
  for stream in ['stdout','stderr']:
   data=(E/group/stream).read_bytes();assert len(data)==receipt[stream+'_bytes'] and sha(data)==receipt[stream+'_sha256']
  commands.append({'group':str(group),'argv':command['argv'],'exit_code':receipt['exit_code']})
assert len(commands)==11
assert next(c for c in commands if c['group']=='07-public-offline-locked-uv-sync')['exit_code']==2
for c in review['original_static_commands']:
 assert c['receipt']['exit_code']==0
assert 'Success: no issues found in 295 source files' in (E/'32-original-make-typecheck/stdout').read_text()
for n in ['00-NONCREDENTIAL-ENVIRONMENT.json','21-RESUME-NONCREDENTIAL-ENVIRONMENT.json']:
 env=load(E/n)['environment'];assert 'HOME' in env and 'CODEX_HOME' not in env
correction=load(E/'47-ENVIRONMENT-DEVIATION-CORRECTION.json');assert correction['finding']=='ACTUAL_EXECUTION_ENVIRONMENT_DEVIATION'
report={'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':base['head'],'finite_payloads':57,'command_quartets':commands,'strict_source_count':1564,'full_original_maps':10,'exact_including_stat':True,'actual_static_exit_codes':[0,0,0,0],'original_setup_env_exit':2,'execution_constraint':'HOME_ACTUALLY_OVERRIDDEN_POLICY_COMPLIANCE_WITHDRAWN;原件不改/不复跑','claim':'Actual four returncodes and source-preservation only; not fully compliant static acceptance','native_preliminary':'Separate owner exact5quartets0 with HOME/CODEX_HOME absent, independently captured in priorrootpacket','whole_M63':'NOT_ACCEPTED','M7':'TODO','model_calls':0}
put('ROOT-READBACK-V2.json',report)
sp=importlib.util.spec_from_file_location('helper',B/'m63-public079a008-progress-record-oct07/package-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
path=h.package('M6.3-current101cee-original-static-actual-results-source-exact-environment-deviation-retained',[
 ('owner-finite',E.name,[e['path'] for e in a['files']]+['FINITE-ALLOWLIST.json','SHA256SUMS','SEAL.json','47-ENVIRONMENT-DEVIATION-CORRECTION.json']),
 ('root-independent',O.name,['admit-v2.py','ROOT-READBACK-V2.json','FAILED-FIRST-PACKET-READBACK.json','root-command.json','root.stdout','root.stderr','root-receipt.json'])],json.loads(json.dumps(report,ensure_ascii=False).replace('$HOME','$HOME').replace('$RUNNER_HOME','$RUNNER_HOME')))
from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');v=s['verification']
v['m6_3_current101_static_before_terminal_record']=v['m6_3_current101_static']
v['m6_3_current101_static']={'status':'ORIGINAL_FOUR_ACTUAL_EXIT0_WITH_EXECUTION_ENVIRONMENT_DEVIATION_RETAINED','source':base['head'],'inputs':1564,'full_original_maps_exact':10,'derived_included':82,'targets':['make lint','make typecheck','make verify-spec','git diff --check 101cee47'],'initial_setup_exit2':'Python3.14.4 vs project3.12; resolvedseparately/oldoriginalretained','HOME_constraint':'Actualoverride in bothliteralENV; policycompliance withdrawn, no rerun','M0':'STRUCTURAL_ONLY_PRODUCT_NOT_RUN','evidence':path,'wholeM63':'NOT_ACCEPTED'}
if path not in t['evidence_paths']:t['evidence_paths'].append(path)
s['next_action']=t['next_action']='等待固定101原完整Python4589和全133浏览器的实际终态与1564输入前后回读。独立静态四原退出0含HOME执行环境偏差，已保留纠正，不能升格完全合规验收；浏览器前置另有无HOME覆盖的原lint/types/build/spec回执。保留公开079全部原FAIL、ReviewUNKNOWN、物理数值环境阻塞；当前101未推送，真实InputProof/runtime缺口仍在，M6.3/AC21未验收，M7todo。'
s['checkpoint']['next_action']=s['next_action'];save(s)
put('INSTALL-READBACK.json',{'evidence':path,'actual_static_original_exit_codes':[0,0,0,0],'HOME_deviation':'ACTUAL_RETAINED_NOT_COMPLIANT','source':base['head'],'source_mutation':False,'source_push':False})
print('57 finitepayloads/11originalquartets/10x1564 maps exact; HOME deviation included, no wholeacceptance inferred.')
