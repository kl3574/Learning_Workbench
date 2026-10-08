from pathlib import Path
import hashlib,json,subprocess
OUT=Path(__file__).resolve().parent
E=OUT.parent/'m63-authoring-owned-bind-collision-evidence-oct05'
T=OUT.parent/'m63-authoring-owned-bind-collision-oct05'
BASE='68a280b9cf251bbf79c2ca188ac8b4aefe7562e0'
HEAD='5fbfd5dff0fe37df61ac53d9a9a596cdd112b24b'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(T),*a])
def put(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert sha((E/'CANDIDATE_ALLOWLIST.json').read_bytes())=='d218eb05bf8a107ddf82957092acf0b5b5e0988434ba0ddafac444c0d091ec0b'
m=json.loads((E/'CANDIDATE_ALLOWLIST.json').read_bytes())
rows=[]
for e in m['admitted_candidates']:
 p=Path(e['path']);assert not p.is_absolute() and '..' not in p.parts
 b=(E/p).read_bytes();assert len(b)==e['size'] and sha(b)==e['sha256'];b.decode()
 rows.append(e)
assert len(rows)==25==len({r['path'] for r in rows})
assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain').strip()
assert git('rev-list','--parents','-n','1',HEAD).decode().split()==[HEAD,BASE]
source=json.loads((E/'SOURCE_READBACK.json').read_bytes())
assert git('rev-parse',HEAD+'^{tree}').decode().strip()==source['tree']
assert git('diff','--name-only',BASE,HEAD).decode().splitlines()==source['changed_paths']
assert len(source['changed_paths'])==4
for e in source['source']:
 b=git('show',HEAD+':'+e['path'])
 assert b==(T/e['path']).read_bytes()==(E/'fixed-source'/e['path']).read_bytes()
 assert len(b)==e['size'] and sha(b)==e['sha256'] and git('rev-parse',HEAD+':'+e['path']).decode().strip()==e['git_blob']
assert git('diff',BASE,HEAD).strip()==(E/'source-change.patch').read_bytes().strip()
assert (E/'red-source/tests/e2e/authoringRuntime.ts').read_bytes()==git('show',BASE+':tests/e2e/authoringRuntime.ts')
assert (E/'red-source/tests/e2e/ownedStartup.node.ts').read_bytes()==(E/'fixed-source/tests/e2e/ownedStartup.node.ts').read_bytes()
stages=[]
for name,code in [('RED',1),('SAME_TEST_GREEN',0),('BOUNDS_GREEN',0)]:
 command=json.loads((E/(name+'-command.json')).read_bytes());receipt=json.loads((E/(name+'-receipt.json')).read_bytes())
 assert receipt['exit_code']==code
 for stream in ('stdout','stderr'):
  b=(E/(name+'.'+stream)).read_bytes()
  assert len(b)==receipt[stream+'_size'] and sha(b)==receipt[stream+'_sha256']
 stages.append({'name':name,'command':command,'receipt':receipt})
assert b'EADDRINUSE: address already in use' in (E/'RED.stdout').read_bytes()
assert b'fail 1' in (E/'RED.stdout').read_bytes() and b'pass 1' in (E/'SAME_TEST_GREEN.stdout').read_bytes()
assert b'tests 10' in (E/'BOUNDS_GREEN.stdout').read_bytes() and b'pass 10' in (E/'BOUNDS_GREEN.stdout').read_bytes() and b'fail 0' in (E/'BOUNDS_GREEN.stdout').read_bytes()
put('READBACK.json',{'role':'root independent fixed source Spec/Standards and bounded original owned-process evidence readback',
 'source':HEAD,'base':BASE,'candidate_count':25,'candidate_rows':rows,'stages':stages,
 'whole_same_test_identical':True,'baseline_authoring_runtime_exact68a':True,'final4paths_live_git_exact_clean':True,
 'review':{'spec_P1_P2':0,'standards_P1_P2':0,'norm_sha256':'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec',
  'read_scope':'full helper, original AuthoringRuntime4path delta, both complete new Node test files, original red/samegreen/bounds logs and receipts',
  'conclusions':['only an actual closed nonzero nonsignaled owned UI child exact selected-port collision admits retry',
    'one retry shares original20s deadline; original API/general/live/HTTP/wrongport failures do not retry',
    'owned selectedportVite marker plus HTTPrequired; foreign200 is not substituted; only retained created childgroups signaled',
    'original reserve-close race remains; no collisionfree guarantee or original competitor identity claimed']},
 'acceptance':'SCOPED_SOURCE_AND_10_OWNED_NODE_BEHAVIOR_ONLY; ACTUAL_AUTHORING_SEMANTIC_TS_AND_BROWSER_PENDING_SEPARATE_NEW_GATES',
 'limits':['RED exposed copied original helper behavior; not raw68a whole gate or oldCI rerun',
 'test commands have no immutable completeGit beforeafter/selfrunner capture; source snapshots and command/log/receipt binding only',
 'actual Vite/product API/browser/semanticTS NOT_RUN in this original packet; new isolated gates pending',
 'Review/grading and original bothCI failures remain; no fullM6.3/AC21/M7 or realmodel/numeric acceptance',
 '0 source/remote mutation, model/hostprobe/unknownprocess lookup/secret reads']})
print(json.dumps({'status':'SCOPED_PASS','source':HEAD,'candidates':25,'readback_sha256':sha((OUT/'READBACK.json').read_bytes())}))
