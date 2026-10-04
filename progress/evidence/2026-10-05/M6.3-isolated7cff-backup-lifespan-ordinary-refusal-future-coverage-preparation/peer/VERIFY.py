"""Independent read-only Git/explicit safe-evidence verification; no product execution."""
from pathlib import Path
import json,hashlib,itertools,math,subprocess,os
repo=Path('$HOME/.cache/learning-workbench-acceptance/m63-codex-restore-lifespan-oct05')
seal=Path('$HOME/.cache/learning-workbench-acceptance/m63-codex-restore-lifespan-evidence-oct05/seal-7cff')
base=seal/'publication-candidates'
head='7cffb5305321c53258f5c5601a4ca7c29b5b4801'
sha=lambda v:hashlib.sha256(v).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=repo)
def load(n):return json.loads((base/n).read_bytes())
assert git('rev-parse','HEAD').decode().strip()==head and git('status','--porcelain')==b''
manifest_raw=(seal/'SAFE_CANDIDATES.json').read_bytes()
assert sha(manifest_raw)=='6d28549fc6c02bda6dbeacf1e2ed931323667a36338856b73e8724eb851b57e8'
outer_raw=(seal/'READBACK.json').read_bytes()
assert sha(outer_raw)=='3df7058f7d3179eadf9a6b22e3a461208ae6097c4ec58b3269102527b64c222c'
manifest=json.loads(manifest_raw);assert manifest['count']==len(manifest['files'])==51
candidates=[];reconstructed={}
for item in manifest['files']:
 n=item['candidate_path'];assert not Path(n).is_absolute() and '..' not in Path(n).parts
 data=(base/n).read_bytes();data.decode('utf-8')
 assert len(data)==item['candidate_bytes'] and sha(data)==item['candidate_sha256']
 if item['transformation']=='identity UTF-8':
  raw=data;indices=[];assert len(raw)==item['raw_bytes'] and sha(raw)==item['raw_sha256']
 else:
  assert item['transformation']=='literal home-prefix-only'
  parts=data.split(b'${HOME}');nparts=len(parts)-1;k=(item['raw_bytes']-len(data))//2
  assert item['raw_bytes']-len(data)==2*k and math.comb(nparts,k)<=10000
  matches=[]
  for inds in itertools.combinations(range(nparts),k):
   chosen=set(inds);raw=parts[0]
   for i,part in enumerate(parts[1:]):raw+=(b'$HOME' if i in chosen else b'${HOME}')+part
   if sha(raw)==item['raw_sha256']:matches.append((raw,list(inds)))
  assert len(matches)==1
  raw,indices=matches[0]
  assert data==raw.replace(b'$HOME',b'${HOME}')
 reconstructed[item['candidate_path']]=raw
 candidates.append(dict(path=item['candidate_path'],bytes=len(data),sha256=sha(data),raw_sha256=sha(raw),raw_reconstructed_by_only_allowed_transform=True,replaced_token_indices=indices))
assert len({v['path'] for v in candidates})==51
heads=['942fc533ca48e1a561199fb992d80e76622948c1','816cb38b7285d14fdbf5d00fcdecdced5e1b517d',head]
assert git('rev-list','--reverse',heads[0]+'..'+head).decode().splitlines()==heads[1:]
assert git('rev-parse',head+'^').decode().strip()==heads[1]
rows={};oids=set();binding_count=0
for h in heads:
 manifest_git=load('git/'+h+'.json');assert manifest_git['head']==h
 actual={}
 for line in git('ls-tree','-rz',h).split(b'\0'):
  if not line:continue
  a,p=line.split(b'\t',1);mode,kind,oid=a.decode().split();path=p.decode()
  if kind!='blob' or path.startswith('progress/'):continue
  actual[path]=(mode,kind,oid)
 entries={v['path']:v for v in manifest_git['files']}
 assert len(entries)==len(manifest_git['files'])==manifest_git['count']==len(actual)
 for p,v in entries.items():
  assert actual[p]==(v['mode'],v['type'],v['git_blob']);oids.add(v['git_blob'])
 rows[h]=entries;binding_count+=len(entries)
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
raw,_=proc.communicate(('\n'.join(sorted(oids))+'\n').encode());assert proc.returncode==0
at=0;blobmeta={}
for oid in sorted(oids):
 end=raw.index(b'\n',at);actual,kind,size=raw[at:end].decode().split();size=int(size)
 data=raw[end+1:end+1+size];at=end+size+2
 assert actual==oid and kind=='blob' and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()==oid
 blobmeta[oid]=(len(data),sha(data))
assert at==len(raw)
for h,entries in rows.items():
 for p,v in entries.items():assert (v['bytes'],v['sha256'])==blobmeta[v['git_blob']]
changed=git('diff','--name-only',heads[0],head).decode().splitlines()
assert changed==['tests/integration/test_backup_codex_lifespan.py']
assert git('diff','--binary',heads[0],head,'--',*changed)==reconstructed['owned.patch']
assert git('diff',heads[1],head,'--',*changed)==reconstructed['expectation-correction.patch']
assert all(v==rows[head][p] for p,v in rows[heads[0]].items())
assert git('show',head+':'+changed[0])==reconstructed['source/'+changed[0]]
assert git('show',heads[1]+':'+changed[0])==reconstructed['original-source/816-test_backup_codex_lifespan.py']
assert rows[head]['PRODUCT_DESIGN.md']['sha256']=='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
live_bindings=0
for p,v in rows[head].items():
 f=repo/p;data=os.readlink(f).encode() if v['mode']=='120000' else f.read_bytes()
 assert len(data)==v['bytes'] and sha(data)==v['sha256']
 assert (f.is_symlink() if v['mode']=='120000' else not f.is_symlink())
 if v['mode']!='120000':assert bool(f.stat().st_mode&0o111)==(v['mode']=='100755')
 live_bindings+=1
history=load('STAGE_HISTORY.json');assert len(history)==7
stages=[];run_hash=sha(reconstructed['harness/run.py']);map_bindings=0
for stage in history:
 name=stage['stage'];rec=load('stages/'+name+'/receipt.json');cmd=load('stages/'+name+'/command.json')
 assert {k:rec[k] for k in cmd}==cmd
 assert rec=={k:v for k,v in stage.items() if k!='stage'}
 assert rec['runner_sha256']==run_hash
 before=load('stages/'+name+'/source-before.json');after=load('stages/'+name+'/source-after.json')
 assert before==after and before['status']=='' and before['head']==rec['source_sha']
 ref=rows[rec['source_sha']]
 assert before['count']==len(before['files'])==len(ref)==rec['complete_nonprogress_inputs']
 for snap in [before,after]:
  seen=set()
  for v in snap['files']:
   assert v['path'] not in seen;seen.add(v['path']);rv=ref[v['path']]
   assert all(v[k]==rv[k] for k in ['mode','type','git_blob','bytes','sha256'])
   assert v['matches_git'] and v['actual_blob']==v['git_blob'];map_bindings+=1
  assert seen==set(ref)
 for p,hv in rec['test_sources'].items():assert ref[p]['sha256']==hv
 log='logs/'+name+'.log'
 checked_log=log in reconstructed
 if checked_log:assert sha(reconstructed[log])==rec['log_sha256']
 stages.append(dict(stage=name,source_sha=rec['source_sha'],exit_code=rec['exit_code'],elapsed_seconds=rec['elapsed_seconds'],finished_at=rec['finished_at'],log_sha256=rec['log_sha256'],log_candidate_independently_read=checked_log,before_after_exact=True,count=len(ref),runner_sha256=run_hash))
assert binding_count==4571 and len(blobmeta)==1506 and map_bindings==21336
observations=[]
for n in ['observations/focused-02-0.json','observations/focused-02-1.json','observations/related-01-0.json','observations/related-01-1.json']:
 ob=load(n)
 assert ob['entered_lifespan'] and ob['contract_assertions_completed'] and ob['alive_before_shutdown'] and not ob['alive_after_context']
 assert ob['forbidden_calls']=={'codex_model':0,'ordinary_provider':0,'tool':0,'process':0,'bootstrap':0}
 assert ob['source_synthetic_model_calls']==ob['fresh_bootstrap_calls']==0
 assert len(ob['worker_observations'])>=2 and ob['worker_observations'][0]['prior_loop_error'] is None
 assert all(v['error']=='ApiError' and v['code']=='PROVIDER_BACKUP_DISABLED' for v in ob['worker_observations'])
 assert all(v['prior_loop_error']=='PROVIDER_BACKUP_DISABLED' for v in ob['worker_observations'][1:])
 observations.append(dict(candidate=n,registration=ob['registration'],iterations=len(ob['worker_observations']),alive_before_shutdown=True,alive_after_context=False,forbidden_calls=ob['forbidden_calls'],assertions_completed=True))
result=dict(review='Independent source/evidence verification only; no new product/test execution',head=head,base=heads[0],parent=heads[1],changed_paths=changed,added_lines=213,base_inputs=len(rows[heads[0]]),final_inputs=len(rows[head]),unchanged_base_inputs=len(rows[heads[0]]),git_heads=heads,git_bindings=binding_count,distinct_blobs=len(blobmeta),all_mode_type_blob_size_sha_exact=True,live_inputs_exact=live_bindings,stage_count=len(stages),stage_map_bindings=map_bindings,stages=stages,observations=observations,owner_candidate_count=51,owner_outer_count=2,candidates=candidates,owner_safe_sha256=sha(manifest_raw),owner_outer_readback_sha256=sha(outer_raw),bounds=['Original focused-01 raw failed log not admitted/read; 2FAIL count from admitted bounded summary+receipt only.','Static-01/diff-01 logs not admitted/read; exit codes from exact admitted receipts only.','All successful candidate logs hashed against original receipt via allowed home-prefix transform reconstruction.','Original 816 and final 7cff are different test oracles; no production fix or same-test RED-GREEN.','Permanent disabled queued/active turn, new scheduling, general convergence and M7 restore workflow remain OPEN_EVIDENCE/NOT_RUN.','Only five explicit application seams have zero counters; no global OS/network monitoring claim.'])
print(json.dumps(result,ensure_ascii=False,indent=2))
