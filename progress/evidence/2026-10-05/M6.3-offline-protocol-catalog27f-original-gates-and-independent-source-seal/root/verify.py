from pathlib import Path
import hashlib,json,subprocess
OUT=Path(__file__).resolve().parent
SEAL=Path('$HOME/.cache/learning-workbench-acceptance/m63-turn-protocol-catalog-evidence-oct05/seal-27f')
P=SEAL/'publication-candidates'
TREE=Path('$HOME/.cache/learning-workbench-acceptance/m63-turn-protocol-catalog-oct05')
FINAL='27f549ff5a8fd67b0a601b67a5ba51ef35f6765f';BASE='8b8699d3aad45180ab3b339ea60979c1478f0b92'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(TREE),*a])
def put(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
manifest=json.loads((SEAL/'SAFE_CANDIDATES.json').read_bytes())
assert sha((SEAL/'SAFE_CANDIDATES.json').read_bytes())=='e44aa239e17ca704d33c6343a8d103d415e3e38244bbfe8b1030f94abdd6866c'
assert sha((SEAL/'READBACK.json').read_bytes())=='108bec2c3318e4d78e3ed6de2a1b7accf3ea390f30094853f0606d5a6f638888'
rows=[]
for e in manifest['entries']:
 p=Path(e['candidate_path']); assert not p.is_absolute() and '..' not in p.parts
 raw=(P/p).read_bytes();assert len(raw)==e['candidate_size'] and sha(raw)==e['candidate_sha256']
 assert e['transformation']=='identity' and e['candidate_sha256']==e['raw_sha256']
 rows.append({'path':str(p),'size':len(raw),'sha256':sha(raw)})
assert len(rows)==98 and len({r['path'] for r in rows})==98
maps=json.loads((P/'FULL_GIT_INPUTS.json').read_bytes())['maps'];cache={};fixed={}
for m in maps:
 actual={}
 for line in git('ls-tree','-r','-z',m['head']).split(b'\0'):
  if not line:continue
  h,p=line.split(b'\t',1);p=p.decode();mode,kind,blob=h.decode().split()
  if p.startswith('progress/'):continue
  actual[p]=(mode,kind,blob)
 assert len(actual)==m['count']==len(m['entries'])
 assert len({e['path'] for e in m['entries']})==m['count']
 assert git('rev-parse',m['head']+'^{tree}').decode().strip()==m['tree']
 for e in m['entries']:
  assert actual[e['path']]==(e['mode'],e['type'],e['blob'])
  if e['blob'] not in cache:cache[e['blob']]=git('cat-file','blob',e['blob'])
  b=cache[e['blob']]; assert len(b)==e['size'] and sha(b)==e['sha256']
 fixed[m['head']]=m
assert len(maps)==7 and sum(m['count'] for m in maps)==10760 and len(cache)==1526
base={e['path']:e for e in fixed[BASE]['entries']};final={e['path']:e for e in fixed[FINAL]['entries']}
assert len(base)==1527 and len(final)==1541 and all(final[p]==e for p,e in base.items())
assert len(set(final)-set(base))==14
assert git('rev-parse','HEAD').decode().strip()==FINAL and not git('status','--porcelain').strip()
for e in final.values():
 b=(TREE/e['path']).read_bytes();assert b==cache[e['blob']]
stages=[]
for row in json.loads((P/'OWNER_GATE_READBACK.json').read_bytes())['stage_rows']:
 s=row['stage']; before=json.loads((P/s/'before.json').read_bytes());after=json.loads((P/s/'after.json').read_bytes())
 assert before==after==fixed[row['head']]
 receipt=json.loads((P/s/'receipt.json').read_bytes()); command=json.loads((P/s/'command.json').read_bytes());log=(P/s/'run.log').read_bytes()
 assert receipt['head']==command['source_head']==row['head'] and receipt['input_count']==before['count']
 assert receipt['log_sha256']==sha(log)==row['log_sha256'] and receipt['log_size']==len(log)
 assert receipt['runner_sha256']==command['runner_sha256']==sha((P/'run_stage.py').read_bytes())
 for key in receipt:assert receipt[key]==row[key]
 if s.endswith('-final'): assert row['head']==FINAL and receipt['command_exit_code']==receipt['wrapper_exit_code']==0
 stages.append({'stage':s,'receipt':receipt,'argv':command['argv'],'log_sha256':sha(log),'log_size':len(log)})
assert len(stages)==15 and sum(s['receipt']['input_count']*2 for s in stages)==46204
assert b'68 passed, 1 warning' in (P/'focused-final/run.log').read_bytes()
assert b'186 passed, 2 warnings' in (P/'related-final/run.log').read_bytes()
for a,b,n in [('5364926fc40171a0bad19b04c851eac0b7fce0b9','4500432d2f119da2a8e6dd41024ab9d94db9feed','first-red-green.py'),('8a0f19eccc3cd93689fd3223eb5be31ac06ee048','387916827f855f5973656ed03c179ac520d267bf','typed-red-green.py')]:
 raw=(P/'source-original-tests'/n).read_bytes();assert raw==git('show',a+':tests/unit/test_codex_turn_protocol_catalog.py')==git('show',b+':tests/unit/test_codex_turn_protocol_catalog.py')
put('READBACK.json',{'role':'root independent fixed Git, exact seal and original gate verification; no rerun','final':FINAL,'base':BASE,'candidate_count':98,'candidate_bytes':sum(r['size'] for r in rows),'candidate_rows':rows,'source_maps':7,'source_bindings':10760,'distinct_blobs':1526,'stage_count':15,'stage_maps':30,'stage_bindings':46204,'unchanged_old_inputs':1527,'final_inputs':1541,'all_actual_live_git_exact_clean':True,'stages':stages,'source_review':{'standards_P1_P2':0,'spec_P1_P2':0,'modules_and_final_test_read':True,'sole_norm_sha256':'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'},'limits':['selected9 internal source shapes and nonsecret manual historical projection only','No raw private source receipt upload/current CLI or actual model qualification','No production proof/protocol/runtime registration','68focused and186related overlap prior30; not additive coverage','whole changed-backend suite and native NOT_RUN; historical6671 CI separate','Original RED/typed FAIL/Ruff FAIL/mypy invocation FAIL and intentional warning retained','no model/tool/network calls made by this verification']})
print(json.dumps({'status':'PASS','source':FINAL,'candidates':98,'inputs':1541,'stages':15,'readback_sha256':sha((OUT/'READBACK.json').read_bytes())}))
