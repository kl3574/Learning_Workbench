from pathlib import Path
import hashlib,json,subprocess
OUT=Path(__file__).resolve().parent
RAW=Path('$HOME/.cache/learning-workbench-acceptance/m63-interrupt-rpc-pairing-evidence-oct06')
SEAL=RAW/'seal-68a';P=SEAL/'publication-candidates'
TREE=Path('$HOME/.cache/learning-workbench-acceptance/m63-interrupt-rpc-pairing-oct06')
FINAL='68a280b9cf251bbf79c2ca188ac8b4aefe7562e0';BASE='27f549ff5a8fd67b0a601b67a5ba51ef35f6765f'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(TREE),*a])
def put(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert sha((SEAL/'SAFE_CANDIDATES.json').read_bytes())=='bd25199ec145f66f77bb116707c7e76eb6298fbe6adc7d46838d715a675ff3a0'
assert sha((SEAL/'READBACK.json').read_bytes())=='a6ab09839154ac5d287a18ef1986a850a8a3ad301ec94777e6a96fdb49cb9586'
manifest=json.loads((SEAL/'SAFE_CANDIDATES.json').read_bytes());rows=[];rawbytes={};transforms={}
for e in manifest['entries']:
 p=Path(e['candidate_path']);assert not p.is_absolute() and '..' not in p.parts
 b=(P/p).read_bytes();assert len(b)==e['candidate_size'] and sha(b)==e['candidate_sha256']
 t=e['transformation'];transforms[t]=transforms.get(t,0)+1
 if t=='identity':
  raw=b;qualification='candidate identity'
 elif str(p)=='REPORT.md':
  assert b.count(b'literal~\xe2\x86\x92~')==1
  raw=b.replace(b'literal~\xe2\x86\x92~',b'literal$HOME\xe2\x86\x92~')
  qualification='hash-matching reconstruction only; no historical raw report file'
 else:
  # Owner explicitly admitted only the listed transformed files in this fixed root.
  q=RAW/p;assert q.is_file();raw=q.read_bytes();qualification='explicitly admitted original actual file'
 assert len(raw)==e['raw_size'] and sha(raw)==e['raw_sha256']
 assert (raw if t=='identity' else raw.replace(b'$HOME',b'~'))==b
 rawbytes[str(p)]=raw
 rows.append({'path':str(p),'candidate_size':len(b),'candidate_sha256':sha(b),'raw_size':len(raw),'raw_sha256':sha(raw),'transformation':t,'raw_qualification':qualification})
assert len(rows)==159 and sum(r['candidate_size'] for r in rows)==31977991
assert transforms=={'literal_homeprefix_only':33,'identity':126}
maps=json.loads((P/'FULL_GIT_INPUTS.json').read_bytes())['maps'];cache={};fixed={}
for m in maps:
 actual={}
 for line in git('ls-tree','-r','-z',m['head']).split(b'\0'):
  if not line:continue
  h,p=line.split(b'\t',1);p=p.decode();mode,kind,blob=h.decode().split()
  if p.startswith('progress/'):continue
  actual[p]=(mode,kind,blob)
 assert len(actual)==m['count']==len(m['entries']) and len({e['path'] for e in m['entries']})==m['count']
 assert git('rev-parse',m['head']+'^{tree}').decode().strip()==m['tree']
 for e in m['entries']:
  assert actual[e['path']]==(e['mode'],e['type'],e['blob'])
  if e['blob'] not in cache:cache[e['blob']]=git('cat-file','blob',e['blob'])
  b=cache[e['blob']];assert len(b)==e['size'] and sha(b)==e['sha256']
 fixed[m['head']]=m
assert len(maps)==14 and sum(m['count'] for m in maps)==21719 and len(cache)==1547
base={e['path']:e for e in fixed[BASE]['entries']};final={e['path']:e for e in fixed[FINAL]['entries']}
assert len(base)==1541 and len(final)==1553 and all(final[p]==e for p,e in base.items()) and len(set(final)-set(base))==12
assert git('rev-parse','HEAD').decode().strip()==FINAL and not git('status','--porcelain').strip()
for e in final.values():assert (TREE/e['path']).read_bytes()==cache[e['blob']]
runner_sha=sha(rawbytes['run_stage.py']);assert runner_sha=='eda1b34fc2f41e82d43f548bd289cbd22273dd2c88bf537b513dce680aff97d4'
stages=[];gate=json.loads((P/'OWNER_GATE_READBACK.json').read_bytes())
final_names={'decoder-depth-green-01','related-fixed-final-01','ruff-fixed-final-01','mypy-fixed-final-01','spec-fixed-final-01','generated-fixed-final-01','diff-fixed-final-01'}
for row in gate['stage_rows']:
 s=row['stage'];before=json.loads(rawbytes[s+'/before.json']);after=json.loads(rawbytes[s+'/after.json'])
 assert before==after==fixed[row['head']]
 receipt=json.loads(rawbytes[s+'/receipt.json']);command=json.loads(rawbytes[s+'/command.json']);log=rawbytes[s+'/run.log']
 assert receipt['head']==command['source_head']==row['head'] and receipt['input_count']==before['count']
 assert receipt['log_sha256']==sha(log)==row['log_sha256'] and receipt['log_size']==len(log)
 assert receipt['runner_sha256']==command['runner_sha256']==runner_sha
 assert sha(rawbytes[s+'/command.json'])==row['command_sha256']
 assert sha(rawbytes[s+'/before.json'])==row['before_sha256'] and sha(rawbytes[s+'/after.json'])==row['after_sha256']
 for k in receipt:assert receipt[k]==row[k]
 if s in final_names:assert row['head']==FINAL and receipt['command_exit_code']==receipt['wrapper_exit_code']==0
 stages.append({'stage':s,'receipt':receipt,'argv':command['argv'],'log_sha256':sha(log),'log_size':len(log),'final_qualified':s in final_names})
assert len(stages)==27 and sum(s['receipt']['input_count']*2 for s in stages)==83840 and sum(s['final_qualified'] for s in stages)==7
assert b'2 failed, 118 passed' in rawbytes['decoder-depth-red-01/run.log']
assert b'RecursionError' in rawbytes['decoder-depth-red-01/run.log']
assert b'120 passed in 3.91s' in rawbytes['decoder-depth-green-01/run.log']
assert b'290 passed, 3 warnings' in rawbytes['related-fixed-final-01/run.log']
source=json.loads((P/'SOURCE_BINDING.json').read_bytes())
for e in source['same_test_pairs']:
 b=git('show',e['red']+':'+e['binding']['path']);assert b==git('show',e['green']+':'+e['binding']['path'])
 assert len(b)==e['binding']['size'] and sha(b)==e['binding']['sha256'] and len(b.splitlines())==e['actual_line_count']
assert len(source['same_test_pairs'])==4
put('DOC_PREFIX_CORRECTION.json',{'role':'Separate documentary correction; immutable original report retained','report_candidate_sha256':sha(rawbytes['REPORT.md'].replace(b'$HOME',b'~')),'finding':'REPORT transformation sentence was itself normalized to literal tilde arrow tilde','correction':'Only the literal personal home directory prefix was replaced by a tilde. Candidate copies are not raw command/log bytes; both hashes and sizes remain in the original manifest. Restore the specific prefix before replaying the normalized runner.','raw_report_status':'No separately saved historical raw file; one sentence is reconstructed to match the original declared raw size and SHA. This is hash-matching reconstruction, not an original file or a rerun.','product_or_gate_failure':False})
put('READBACK.json',{'role':'Root independent fixed Git, exact declared candidates, original gate bytes; no rerun','final':FINAL,'base':BASE,'candidate_count':159,'candidate_bytes':31977991,'candidate_rows':rows,'transformations':transforms,'source_maps':14,'source_bindings':21719,'distinct_blobs':1547,'stage_count':27,'stage_maps':54,'stage_bindings':83840,'unchanged_old_inputs':1541,'final_inputs':1553,'all_actual_live_git_exact_clean':True,'stages':stages,'source_review':{'standards_P1_P2':0,'spec_P1_P2':0,'prior_f81_P2':'Original open finding retained; bounded parser-valid root objects leaked RecursionError','final_P2':'Closed by one-line rejection catch and same whole502 line file: 2FAIL118PASS then120PASS','modules_prior483line_tests_and_final19line_delta_read':True,'sole_norm_sha256':'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'},'limits':['Private historical source receipt remains excluded; selected8 manually checked source projection only','No production proof/protocol/runtime registration, transport/session ownership/cleanup/filestability/model admission','Whole new1553 Python/native gate NOT_RUN; running4441 gate and current1eCI qualify older1541 source only','120 focused/290 related overlap prior catalog/preparation tests, not additive','REPORT raw reconstruction is not a historical original file; documentary correction separate','Original RED/oracle/invocation/mypy failures retained; no host probes/model/tool/network calls']})
print(json.dumps({'status':'PASS','source':FINAL,'candidates':159,'inputs':1553,'stages':27,'readback_sha256':sha((OUT/'READBACK.json').read_bytes())}))
