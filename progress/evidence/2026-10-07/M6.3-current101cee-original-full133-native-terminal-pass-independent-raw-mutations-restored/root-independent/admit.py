from pathlib import Path
import datetime,hashlib,importlib.util,json,re,sys
O=Path(__file__).resolve().parent;B=O.parent;E=B/'m63-integrated-1564-full-native-evidence-oct07';R=B/'m62-public-safe-oct02'
H='101cee47d8e746dddac81fb6e8829069fcabff09'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
manifest=load(E/'ROOT-MANIFEST.json');assert sha((E/'ROOT-MANIFEST.json').read_bytes())=='083e639fdec352808bc57d4e8d1efeefd97ec2d7b8a9099828c7f905431f11c9'
assert len(manifest['files'])==159
for e in manifest['files']:
 raw=(E/e['path']).read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256'],e['path']
quartets=[]
for e in manifest['files']:
 if not e['path'].endswith('-receipt.json'):continue
 receipt=load(E/e['path'])
 for k in ['command','stdout','stderr']:
  item=receipt[k];raw=(E/item['path']).read_bytes();assert len(raw)==item['size_bytes'] and sha(raw)==item['sha256']
 command=load(E/receipt['command']['path']);assert 'HOME' not in command['environment'] and 'CODEX_HOME' not in command['environment']
 quartets.append({'label':receipt['label'],'argv':receipt['argv'],'exit_code':receipt['exit_code']})
assert len(quartets)==23
for label in ['22-restore-native-artifacts','23-after-restore-map']:assert next(x for x in quartets if x['label']==label)['exit_code']==1
for label in ['22b-continue-restoration','23b-continue-post-map']:assert next(x for x in quartets if x['label']==label)['exit_code']==0
full=load(E/'20-full-native-receipt.json');assert full['exit_code']==0 and full['status']=='COMPLETED' and full['argv']==['make','test-e2e']
stdout=(E/'20-full-native-stdout').read_text();assert stdout.count('133 passed (20.9m)')==1
passed=[line for line in stdout.splitlines() if re.match(r'^\s*✓\s+\d+\s',line)];assert len(passed)==133
lines=load(E/'safe-candidates/SAFE-ORIGINAL-LINES.json');assert len(lines)==166
originals={}
for row in lines:
 file=row['original_file'];raw=originals.setdefault(file,(E/file).read_bytes())
 assert sha(raw)==row['original_sha256']
 assert raw.decode().splitlines()[row['line_number']-1]==row['text'],(file,row['line_number'])
expected=load(B/'m63-integrated-four-candidates-local-merge-oct07/FINAL-SOURCE-METADATA.json')
setup=load(E/'before-setup-SOURCE-MAP.json');before=load(E/'before-native-SOURCE-MAP.json');rawafter=load(E/'raw-after-native-SOURCE-MAP.json');after=load(E/'after-guard-restore-SOURCE-MAP.json')
for m in [setup,before,rawafter,after]:
 assert m['head']==H and m['source_count']==len(m['source_files'])==1564 and not m['git_index_deltas']
 for row in m['source_files']:
  x=expected[row['path']];assert all(row['git'][k]==x[k] for k in ['mode','type','blob']);assert row['index']['blob']==x['blob'] and row['index']['mode']==x['mode']
assert setup['source_files']==before['source_files']==after['source_files']
changed=[x['path'] for x,y in zip(before['source_files'],rawafter['source_files'],strict=True) if x!=y]
restore=load(E/'safe-candidates/22-TRACKED-NATIVE-ARTIFACT-RESTORE.json');assert len(changed)==restore['actual_tracked_mutation_count']==5
assert set(changed)=={x['path'] for x in restore['mutations']}
pre={x['path']:x for x in before['source_files']};post={x['path']:x for x in rawafter['source_files']}
for x in restore['mutations']:
 actual=(E/x['preserved_actual_private_artifact']).read_bytes();assert len(actual)==x['actual_bytes'] and sha(actual)==x['actual_sha256']==post[x['path']]['live']['sha256']
 assert pre[x['path']]['live']['sha256']==x['restored_sha256'] and x['post_guard_restore']=='EXACT'
timings=[]
for n,events in [('review-history-timing.json','http'),('review-history-setup-helper-timing.json','polls')]:
 t=load(E/'safe-candidates'/n);assert t['observed_timeout_ms']==30000 and t['retry']==0 and not any(t['dropped'].values())
 assert len(t['phases'])<=t['limits']['phases'] and len(t[events])<=t['limits'][events]
 assert all(set(x)=={'sequence','elapsed_ms','stage'} for x in t['phases'])
 assert all(set(x)<= {'sequence','elapsed_ms','event','route','method','status','caller','request_elapsed_ms'} for x in t[events])
 assert all('?' not in x['route'] and '#' not in x['route'] for x in t[events])
 timings.append({'artifact':n,'phase_count':len(t['phases']),'event_count':len(t[events]),'last_phase':t['phases'][-1],'scope':t['scope']})
report=load(E/'REPORT.json');assert report['full_native']['actual_original_counts']=={'passed':133,'failed':0,'skipped':0,'did_not_run':0,'flaky':0}
assert report['full_native']['exit_code']==0 and not report['original_ci_separate']['repair_claim']
root={'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':H,'finite_originals':159,'exact_original_quartets':23,'original_native':'133PASS20.9m/exit0 once/133successlines','source_inputs':1564,
 'source_maps':'Fourfull1564Git/index exact;setup=before=after_restore live;rawafter actually5mutated, notmislabelledexact','private_actual_artifacts':5,'safe_original_lines':166,
 'metadata_order_errors':'22/23actualexit1 preserved;22b/23bguarded continuation0;no testsrerun','timings':timings,
 'root_read_error':'13b7e8 actualexit1 mistakenlytreatedSAFEarrayasdict; corrected after real schema read; notproductFAIL',
 'execution_environment':'All23originalcommand environments HOME/CODEX_HOME absent; no broad acceptance of anotherstaticHOMEoverridecapture',
 'old_PR_failure':'1F132P remains;causeUNKNOWN;thisnewfullPASSnotretroactiveclosure','model':'Realprovider/CodexNOT_RUN/0actualexternalrequests','M63':'NOT_ACCEPTED','M7':'TODO'}
put('ROOT-READBACK.json',root)
sp=importlib.util.spec_from_file_location('helper',B/'m63-public079a008-progress-record-oct07/package-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
safe=load(E/'SAFE-CANDIDATE-MANIFEST.json')
selected=[e['path'] for e in safe['candidates'] if not e['path'].endswith('SAFE-ORIGINAL-LINES.txt')]
assert len(selected)==11
path=h.package('M6.3-current101cee-original-full133-native-terminal-pass-independent-raw-mutations-restored',[
 ('owner-safe',E.name,selected+['SAFE-CANDIDATE-MANIFEST.json','ROOT-MANIFEST.json','SEAL.json']),
 ('root-independent',O.name,['admit.py','ROOT-READBACK.json'])],json.loads(json.dumps(root,ensure_ascii=False).replace('$HOME','$HOME').replace('$RUNNER_HOME','$RUNNER_HOME')))
from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');v=s['verification']
v['m6_3_current101_full_native_running_temporal_snapshot']=v['m6_3_current101_full_native']
v['m6_3_current101_full_native']={'status':'ORIGINAL_COMPLETE133PASS_TERMINAL0_INDEPENDENT_READBACK_QUALIFIED','source':H,'inputs':1564,'original_argv':['make','test-e2e'],
 'actual_counts':{'passed':133,'failed':0,'skipped':0},'elapsed_seconds':full['elapsed_seconds'],'original_footer':'133 passed (20.9m)','finished_at':full['finished_utc'],'original_budgets':'unchanged1worker/retry0/default30s andcasesoverrides',
 'before_after':'raw5trackedoutputsmutated/privatepreserved;guardrestoreall1564exact;Git/indexexactthroughout',
 'evidence':path,'old_PR_cause':'UNKNOWN','original_PR_failure':'1F132Pretained','real_provider_codex':'NOT_RUN','wholeM63':'NOT_ACCEPTED'}
v['browser_native']='Current101 originalfull133PASS20.9m/exit0 once;independent159hash/23quartets/166originallines/4x1564mapreadback;raw5outputsmutated/privatepreservedthenexactrestore. Original079PR132P1F/causeUNKNOWNretained;notwholeM63.'
t['current_local_checkpoint']['native']['current_combined1564full133']=v['m6_3_current101_full_native']
if path not in t['evidence_paths']:t['evidence_paths'].append(path)
s['next_action']=t['next_action']='固定101完整原生133项已实际通过20.9m并独立封包；继续原完整Python4589，等待实际终态与全部1564输入闭包。归档10确切空白规则仅private计划，等源闭包结束再应用；不改/重跑门禁。保留旧079全部失败、ReviewUNKNOWN、数值环境阻塞、静态HOME偏差。当前101未推送，生产InputProof/runtime仍缺，零真实模型调用，M6.3/AC21未验收，M7todo。'
s['checkpoint']['next_action']=s['next_action'];save(s)
put('INSTALL-READBACK.json',{'evidence':path,'original_full_native':'133PASS20.9m','source':H,'source_mutation':False,'remote_mutation':False,'M63':'NOT_ACCEPTED'})
print('159original hashes/23quartets/166exact lines/four1564maps and5private mutations verified; originalfull133PASSqualified, oldFAIL and scope retained.')
