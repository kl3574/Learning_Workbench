from pathlib import Path
import hashlib,json,subprocess,os
O=Path(__file__).resolve().parent;B=O.parent;E=B/'m63-authoring-bind5fb-locked-acceptance-oct05'
T=B/'m63-authoring-bind5fb-locked-environment-oct05'
BASE='68a280b9cf251bbf79c2ca188ac8b4aefe7562e0';FINAL='3d4520e9a35e325e3f6062429229fbce8ca5e105'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(T),*a])
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert sha((E/'CANDIDATE_ALLOWLIST.json').read_bytes())=='5bfa42a1e0e1ea34af663bf1bd7fa99d2cf465f2b2b2c8e0d63a542ae96d49c7'
m=json.loads((E/'CANDIDATE_ALLOWLIST.json').read_bytes());rows=[]
for e in m['files']:
 p=Path(e['path']);assert p.is_relative_to(E)
 b=p.read_bytes();assert len(b)==e['size'] and sha(b)==e['sha256'];b.decode()
 rows.append({'path':str(p.relative_to(E)),'size':len(b),'sha256':sha(b)})
assert len(rows)==72==len({r['path'] for r in rows})
baseline_path=B/'m63-interrupt68a-locked-environment-and-complete-gate-oct05/complete-python/before.json'
baseline_bytes=baseline_path.read_bytes()
assert sha(baseline_bytes)=='d285fba2f543ac8668ae32b7b46ef90998200e3ae761e5ce189df2233717e2e8'
baseline=json.loads(baseline_bytes);old={e['path']:e for e in baseline['entries']}
assert baseline['head']==BASE and len(old)==1553
report=json.loads((E/'REPORT.json').read_bytes());maps={};blobs={};stages=[]
for stage in report['actual_gates']:
 name=stage['stage'];before_bytes=(E/name/'before.json').read_bytes();after_bytes=(E/name/'after.json').read_bytes()
 before=json.loads(before_bytes);command=json.loads((E/name/'command.json').read_bytes());receipt=json.loads((E/name/'receipt.json').read_bytes())
 assert before_bytes==after_bytes and receipt==stage['receipt'] and command==stage['command']
 assert len(before_bytes)==receipt['before_bytes']==receipt['after_bytes'] and sha(before_bytes)==receipt['before_sha256']==receipt['after_sha256']
 assert receipt['before_after_exact'] and receipt['source_head']==command['source_head']==before['head']
 runner=Path(command['runner']).read_bytes();assert sha(runner)==command['runner_sha256']==receipt['runner_sha256'] and len(runner)==command['runner_bytes']==receipt['runner_bytes']
 log=(E/name/'run.log').read_bytes();assert sha(log)==receipt['log_sha256'] and len(log)==receipt['log_bytes']
 head=before['head']
 if head not in maps:
  actual={}
  for row in git('ls-tree','-r','-z',head).split(b'\0'):
   if not row:continue
   meta,p=row.split(b'\t',1);p=p.decode();mode,kind,blob=meta.decode().split()
   if not p.startswith('progress/'):actual[p]=(mode,kind,blob)
  assert len(actual)==before['file_count']==len(before['files'])==1556
  assert before['tree']==git('rev-parse',head+'^{tree}').decode().strip() and before['status_porcelain']=='' and before['all_equal_git_blob_bytes']
  seen=set()
  for e in before['files']:
   p=e['path'];assert p not in seen;seen.add(p)
   assert actual[p]==(e['mode'],'blob',e['git_blob']) and e['equals_git_blob_bytes']
   if p in old and p!='tests/e2e/authoringRuntime.ts':
    # Reuse the already independently qualified immutable68a inputs; prove old mode/blob/size/SHA continuity, without rereading old payloads.
    base=old[p];assert (e['mode'],e['git_blob'],e['bytes'],e['sha256'])==(base['mode'],base['blob'],base['size'],base['sha256'])
   else:
    blob=e['git_blob']
    if blob not in blobs:blobs[blob]=git('cat-file','blob',blob)
    b=blobs[blob];assert len(b)==e['bytes'] and sha(b)==e['sha256']
  assert len(set(actual)-set(old))==3
  maps[head]=before
 else:assert before==maps[head]
 assert not command['global_timeout_modified'] and not command['retry_modified']
 stages.append({'stage':name,'command':command,'receipt':receipt})
assert len(stages)==12 and len(maps)==3
assert git('rev-parse','HEAD').decode().strip()==FINAL and not git('status','--porcelain').strip()
for e in maps[FINAL]['files']:
 p=T/e['path'];b=os.readlink(p).encode() if e['mode']=='120000' else p.read_bytes()
 assert len(b)==e['bytes'] and sha(b)==e['sha256']
for name in ['final-semantic','final-build','final-list','short-tmp-browser']:
 r=next(s['receipt'] for s in stages if s['stage']==name);assert r['exit_code']==0 and r['source_head']==FINAL
assert b'Total: 5 tests in 2 files' in (E/'final-list/run.log').read_bytes()
assert b'5 passed (1.1m)' in (E/'short-tmp-browser/run.log').read_bytes()
assert b'5 failed' in (E/'final-browser/run.log').read_bytes() and b'Socket path too long' in (E/'final-browser/run.log').read_bytes()
oldgate=next(s for s in stages if s['stage']=='final-browser');newgate=next(s for s in stages if s['stage']=='short-tmp-browser')
assert oldgate['command']['argv']==newgate['command']['argv'] and oldgate['receipt']['source_head']==newgate['receipt']['source_head']==FINAL
assert oldgate['command']['environment']['TMPDIR']!=newgate['command']['environment']['TMPDIR']
original=json.loads((B/'m63-authoring5fb-root-independent-oct05/READBACK.json').read_bytes())
assert original['source']=='5fbfd5dff0fe37df61ac53d9a9a596cdd112b24b'
assert git('diff','--name-only',original['source'],FINAL).decode().splitlines()==['tests/e2e/authoringRuntime.ts']
for name in ['ownedStartup.ts','ownedStartup.node.ts','ownedStartupBounds.node.ts']:
 assert (E/'fixed-source'/name).read_bytes()==(B/'m63-authoring-owned-bind-collision-evidence-oct05/fixed-source/tests/e2e'/name).read_bytes()
put('READBACK.json',{'role':'root independent fixedsource Spec/Standards and exact actual12stage qualification; no test rerun',
 'fixed_source':FINAL,'base':BASE,'candidate_count':72,'candidate_rows':rows,'actual_stages':stages,'complete_engineering_inputs':1556,
 'stage_map_bindings':12*2*1556,'source_git_maps':3,'source_git_bindings':3*1556,'old1552engineering_inputs_mode_blob_size_sha_continuity':True,
 'baseline_reused':'Prior independently qualified immutable68a1553 map d285f...; old payloads not separately re-read. Changed/new Git blobs checked directly; all live1556 files size/SHA exact.',
 'source_review':{'standards_P1_P2':0,'spec_P1_P2':0,'sole_norm_sha256':'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec',
 'scope':'Full5fb helper/runtime delta/both Node tests independently read earlier; final1006B Playwright typedCJSdefault delta independently read,3otherhelper byteexact; no contract/API/CI/dependency changes'},
 'original_failures_retained':['5fbstrictTS7016','5fblistwriteerrno122; underlyingquota cause notestablished','7clistnamedCJSexpectSyntaxError;0tests','3dactualfirstsuite5FAILChromeSocketpathTooLong;originaltmpdir correction only'],
 'qualified':'finalstrict4harness semantic0/originalappbuild0/actual5case2filelist0/actualnormalViteAPIandexisting5browsercases5PASS; global30s/case90or120s/retry0/oneworker unchanged',
 'limits':['original5fb10ownedNode behavior and3d5actualbrowsercases are separate overlapping scope, not15 independentfull cases',
 'no actualVite collision injected; ordinaryVite marker+HTTP qualified, originalCIcompetitorUNKNOWN',
 'whole133native/3dwholePython/newCI/Reviewgrading/physicalnumeric/wholeM6.3/AC21/M7 NOT_ACCEPTED',
 'runtime/DB/cache/profile/PNG/ZIP/payload notread/admitted;0model/remote/hostprobe/unknownprocessscanorkill']})
print(json.dumps({'status':'SCOPED_PASS','source':FINAL,'candidates':72,'stages':12,'readback_sha256':sha((O/'READBACK.json').read_bytes())}))
