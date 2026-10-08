import datetime,hashlib,json,subprocess,sys
from pathlib import Path
b=Path('$HOME/.cache/learning-workbench-acceptance');e=b/'m63-production-preparation-closure-evidence-oct05';s=e/'seal-495';c=s/'publication-candidates';r=b/'m63-production-preparation-closure-oct05';o=Path(__file__).parent
sys.path.insert(0,str(r/'scripts'))
from check_publication import inspect
def sha(x):return hashlib.sha256(x).hexdigest()
def git(*x):return subprocess.check_output(['git',*x],cwd=r)
raw=(s/'SAFE_CANDIDATES.json').read_bytes();assert sha(raw)=='2c5a06ce18c783c032a4bf6cef07bd460578ec0614760176eb1199e6b76820d0'
m=json.loads(raw);assert m['candidate_count']==len(m['entries'])==116
receipt=(s/'READBACK.json').read_bytes();assert sha(receipt)=='8c9e90d02c1c843c2b810a96157458be378600af3dbb5fdf81f91a20abc00a96'
rows=[];cache={}
for item in m['entries']:
 name=item['candidate_path'];assert name and not Path(name).is_absolute() and '..' not in Path(name).parts
 data=(c/name).read_bytes();assert len(data)==item['candidate_size'] and sha(data)==item['candidate_sha256']
 assert not inspect('progress/evidence/seal/'+name,data.replace(b'$HOME',b'$HOME').replace(b'$RUNNER_HOME',b'$RUNNER_HOME'))
 if item['transformation']=='identity':assert item['raw_sha256']==sha(data) and item['raw_size']==len(data)
 elif name=='first-behavior-red/bounded-failure-excerpt.log':assert item['transformation']!='identity'
 else:raise AssertionError('Unexpected transformation')
 cache[name]=data;rows.append({'path':name,'sha256':sha(data),'size':len(data)})
assert sum(x['size'] for x in rows)==20274525
# Exact immutable Git maps, including all prior fixed stages. Only selected nonprogress blobs.
full=json.loads(cache['FULL_GIT_INPUTS_V2.json']);maps={v['head']:v for v in full['maps']};blobs={};bindings=0
for head,v in maps.items():
 expected={}
 for row in git('ls-tree','-rz',head).split(b'\0'):
  if row:
   h,p=row.split(b'\t',1);p=p.decode();mode,typ,blob=h.decode().split()
   if not p.startswith('progress/'):expected[p]=(mode,typ,blob)
 assert {x['path']:(x['mode'],x['type'],x['blob']) for x in v['entries']}==expected
 for x in v['entries']:
  blob=x['blob']
  if blob not in blobs:
   body=git('cat-file','blob',blob);blobs[blob]=(len(body),sha(body))
  assert (x['size'],x['sha256'])==blobs[blob]
 bindings+=len(v['entries'])
assert bindings==10686 and len(blobs)==1516
stages=[x.removesuffix('/command.json') for x in cache if x.endswith('/command.json')];stagebindings=0
for name in stages:
 cmd=json.loads(cache[name+'/command.json']);rec=json.loads(cache[name+'/receipt.json']);a=json.loads(cache[name+'/before.json']);z=json.loads(cache[name+'/after.json'])
 assert a==z==maps[a['head']] and a['head']==cmd['source_head']==rec['head'] and rec['before_after_complete_exact']
 assert rec['input_count']==a['count'] and cmd['runner_sha256']==rec['runner_sha256']==sha(cache['run_stage.py'])
 expected_exit=1 if name in ['first-behavior-red','mypy-01','ruff-final'] else 0
 assert rec['command_exit_code']==rec['wrapper_exit_code']==expected_exit
 if name!='first-behavior-red':assert sha(cache[name+'/run.log'])==rec['log_sha256'] and len(cache[name+'/run.log'])==rec['log_size']
 else:assert rec['log_sha256']=='0e4ec41712b3d58bde8df982458c02ea515cb85c4a96191c65d6f87eeb89cc68'
 stagebindings+=len(a['entries'])+len(z['entries'])
assert len(stages)==19 and stagebindings==58024
correction=(e/'DOC_SCOPE_CORRECTION.json').read_bytes();assert len(correction)==1351 and sha(correction)=='6f952677f878fe01f2028987bf7132fc00500c6320ed7415ac27878867b402ab'
assert not inspect('progress/evidence/DOC_SCOPE_CORRECTION.json',correction.replace(b'$HOME',b'$HOME'))
# The six final-source copies are separately equal to immutable Git. No raw RED fixture reread.
for name,data in cache.items():
 if name.startswith('source/'):
  assert git('show',m['final']+':'+name.removeprefix('source/'))==data
report={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':m['final'],
 'scope':'Independent root readback of exactly116 named candidates/two outer metadata/one explicit correction; no recursive private directory or new product test',
 'candidate_count':116,'candidate_total_bytes':20274525,'all_exact_sha_size':True,'source_maps':7,'source_bindings':10686,'source_distinct_blobs':1516,
 'original_stages':19,'stage_maps':38,'stage_bindings':58024,'all_original_receipts_and_admitted_logs_exact':True,
 'report_semantic_review':'Owner role explicit, full495finitegate accurate, setup/fenced phase/legacy codec limits explicit, original pytestRED/mypy/Ruff FAIL retained; fullrawRED excluded, excerpt cannotprovewholelog. No fullPython/native/production qualification promotion.',
 'documentary_finding':'Owner REPORT Ruff row says new6paths; actual command ruff check . is projectwide. Immutable original retained; DOC_SCOPE_CORRECTION exactseparate clarifies scope; source or gate unaffected.',
 'correction_sha256':sha(correction),'owner_report_sha256':sha(cache['REPORT.md']),'owner_manifest_sha256':sha(raw),'owner_readback_sha256':sha(receipt),
 'source_findings':[],'remaining_material_binding_gaps':[],'qualification':'QUALIFIED_EXPLICIT_CANDIDATES_WITH_DOCUMENTARY_CORRECTION_REQUIRED_ALONGSIDE_ORIGINAL_REPORT',
 'raw_full_RED_identity':'Original raw digest receipt only inthisseal qualification; independently previouslybound privately; no new raw fixture read',
 'realCLI_model_hostprobe_newtests':'NOT_RUN','whole_M6_3_AC21_M7':'NOT_ACCEPTED','remote_mutation':False,'source_changed':False}
(o/'PUBLICATION_READBACK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'qualified_candidates':116,'stage_bindings':58024,'source_bindings':10686,'correction':True,'source_findings':0}))
