from pathlib import Path
import hashlib,importlib.util,json,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02';E=B/'m63-backup8bd-combined-independent-oct07';C=E/'safe-candidate'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
for path,expected,count in [(E/'private-originals-manifest.json','01bcaa86864a106950c8f9778ba0bdb901dbf48153c57f42e0f53361e41c53b9',38),
 (C/'manifest.json','ffa6e860526f772db814f50743bde45231a6d3076b3bbb315468009086dd4e87',8)]:
 raw=path.read_bytes();assert sha(raw)==expected
 m=json.loads(raw);assert m['count']==count
 for e in m['files']:
  b=(path.parent/e['path']).read_bytes();assert len(b)==e['size'] and sha(b)==e['sha256']
rc=load(E/'private/combined-pytest/receipt.json');cmdraw=(E/'private/combined-pytest/command.json').read_bytes()
assert sha(cmdraw)==rc['command_sha256']
assert rc['command_exit_code']==rc['wrapper_exit_code']==0 and rc['before_after_complete_exact']
assert rc['input_count']==1564
for stream in ['stdout','stderr']:
 raw=(E/'private/combined-pytest'/ (stream+'.bin')).read_bytes()
 assert len(raw)==rc[stream+'_size'] and sha(raw)==rc[stream+'_sha256']
raw=(E/'private/combined-pytest/stdout.bin').read_bytes()
assert b'6 passed, 2 warnings in 19.41s' in raw and b'collected 6 items' in raw
fixed=load(E/'fixed-inputs.json');entries={e['path']:e for e in fixed['entries']}
assert len(entries)==1564
for name in ['before.json','after.json']:
 d=load(E/'private/combined-pytest'/name)
 assert d['complete_exact'] and d['errors']==[] and d['count']==1564 and d['status']==''
 assert set(entries)=={e['path'] for e in d['entries']}
 for e in d['entries']:
  f=entries[e['path']];assert e['fixed_git']==f and e['matches_fixed_git']
  assert e['index']['stage']=='0'
  for k in ['mode','type','blob']:assert f[k]==e['index'][k]==e['live'][k]
  for k in ['size','sha256']:assert f[k]==e['live'][k]
review=load(C/'SPEC_REVIEW.json');result=load(C/'RESULT.json')
assert review['status']=='PASS_BOUNDED_SCOPE' and review['blocking_findings']==[]
assert result['collected']==result['passed']==6 and result['full_combined_launch_count']==1
assert result['old2P_execution_source']=='32e+untracked; not frozen8bd'
assert all(x['entered_lifespan'] and not x['alive_after_context'] and x['contract_assertions_completed'] for x in result['safe_lifespan_observations'])
assert all(all(v==0 for v in x['forbidden_calls'].values()) for x in result['safe_lifespan_observations'])
(O/'ROOT-ADMISSION.json').write_text(json.dumps({'status':'SOURCE_AND_SCOPED_COMBINED6_INDEPENDENTLY_QUALIFIED',
 'source':'8bd930b6bfcad8b824ca73dd2bd9c475ccf86ab4','root_scope':'All3 test source files previously read in full; wholeSpec/source/result now read;38private+8safe hashes and originalpytest quartet/1564beforeafter entries rebound. No whole raw manually semantic review claimed.',
 'actual':'6PASS2warnings19.41s;actual0/wrapper0;singlelaunch;all1564Git/index/live exact',
 'old2P':'32e+untracked retained separately; not added to6P',
 'behavior':'Historical actors/grants/ACKs preserved; freshauth cannot execute old approval; real owned lifecycle refuses blocked jobs and shuts down; no automatic terminal fabricated.',
 'standards':'Root full3file source read found no blocker; independent Spec0blocking; existing onlinewriter/sanitizer/executionguard unchanged.',
 'M7_preview_commit_actualturn_host':'NOT_RUN_NOT_ACCEPTED','real_model_calls':0,'no_canonical_source_remote_mutation':True},indent=2)+'\n')
sp=importlib.util.spec_from_file_location('helper',B/'m63-public079a008-progress-record-oct07/package-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
path=h.package('M6.3-backup8bd-historical-records-closed-grants-original-six-combined-independent-readback',[
 ('safe-candidate',E.name,['safe-candidate/'+e['path'] for e in load(C/'manifest.json')['files']]+['safe-candidate/manifest.json']),
 ('root-finite',O.name,['verify.py','ROOT-ADMISSION.json'])],
 {'status':'SCOPED6PASS_NOT_INTEGRATED','source':result['source_head'],'base':result['base'],
  'actual':'6PASS2warn19.41s/command0/wrapper0/1564allbeforeafterexact','source_changes':'Three added tests only; inherited1561source unchanged',
  'old_results':'Originalobserver1F1P testseamfixturefail/old2P32e+untracked retained separately; not additive.',
  'scope':'§20.17.7 only; existing productionguards tested, notnewproductionrepair',
  'old_queued':'Retained queued/active; no fabricated terminal convergence','wholeM63_AC21_M7_model_host':'NOT_ACCEPTED','model_calls':0,'source_push':False})
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');t['evidence_paths'].append(path)
s['verification']['m6_3_backup8bd_qualified_candidate']={'status':'SCOPED6PASS_INDEPENDENT_REVIEW_NOT_INTEGRATED','source':result['source_head'],
 'actual':'6P2warn19.41s/all1564beforeafterexact/old2P32euntrackedseparate','scope':'20.17.7only/M7todo/actualmodelNOT_RUN','evidence':path}
save(s)
(O/'INSTALL-READBACK.json').write_text(json.dumps({'evidence':path,'status':'SCOPED6PASS_NOT_INTEGRATED'},indent=2)+'\n')
print('Backup8bd original6PASS scope independentlybound; grants remain nonexecutable, M7todo.')
