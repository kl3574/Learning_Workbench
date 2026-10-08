"""Read only 50 admitted Web text candidates and immutable Git, no product execution."""
from pathlib import Path
import json,hashlib,itertools,subprocess
repo=Path('$HOME/.cache/learning-workbench-acceptance/m63-session-interrupt-ui-oct05')
p=Path('$HOME/.cache/learning-workbench-acceptance/m63-session-interrupt-ui-evidence-oct05/seal-22dade')
b=p/'publication-candidates';head='22dade7996f13634202250ef5e1c05dc976214a5'
sha=lambda v:hashlib.sha256(v).hexdigest()
git=lambda *a:subprocess.check_output(['git',*a],cwd=repo)
mr=(p/'SAFE_CANDIDATES.json').read_bytes();outer=(p/'READBACK.json').read_bytes()
assert sha(mr)=='bd58daa47fc06dc13a23951c8f029567d0b0d56f25a8cab37d58c89f79b84b60'
assert sha(outer)=='b81b2c5b3e9a1d353de3eb2eb90657a64fdc3a736f17f1ded2704cc90cce6eef'
m=json.loads(mr);assert m['source']==head and len(m['files'])==50
payloads={};raws={};candidates=[]
for e in m['files']:
 n=e['candidate_path'];assert not Path(n).is_absolute() and '..' not in Path(n).parts and n not in payloads
 data=(b/n).read_bytes();data.decode('utf-8');assert len(data)==e['bytes'] and sha(data)==e['sha256']
 raw=data
 if sha(raw)!=e['raw_sha256']:
  raw=data.replace(b'${HOME}',b'$HOME')
  if sha(raw)!=e['raw_sha256']:
   parts=data.split(b'${HOME}');num=len(parts)-1;matches=[]
   for kept in range(min(num,4)+1):
    for keep in itertools.combinations(range(num),kept):
     inds=set(keep);v=parts[0]
     for i,part in enumerate(parts[1:]):v+=(b'${HOME}' if i in inds else b'$HOME')+part
     if sha(v)==e['raw_sha256']:matches.append(v)
   assert len(matches)==1,n;raw=matches[0]
  assert raw.replace(b'$HOME',b'${HOME}')==data
 assert sha(raw)==e['raw_sha256']
 payloads[n]=data;raws[n]=raw;candidates.append(dict(path=n,bytes=len(data),sha256=sha(data),advertised_raw_sha256=sha(raw),only_allowed_transform=True))
history=json.loads(payloads['STAGE_READBACK.json']);stages=history['stages'];assert len(stages)==11
heads=sorted(set(st['head'] for st in stages));rows={};oids=set()
for h in heads:
 entries={}
 for line in git('ls-tree','-rz',h).split(b'\0'):
  if not line:continue
  meta,path=line.split(b'\t',1);mode,kind,oid=meta.decode().split();path=path.decode()
  if path.startswith('progress/'):continue
  assert kind=='blob';entries[path]=dict(mode=mode,type=kind,git_blob=oid);oids.add(oid)
 rows[h]=entries
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
v,_=proc.communicate(('\n'.join(sorted(oids))+'\n').encode());assert proc.returncode==0
at=0;blob={}
for oid in sorted(oids):
 end=v.index(b'\n',at);actual,kind,size=v[at:end].decode().split();size=int(size);data=v[end+1:end+1+size];at=end+size+2
 assert actual==oid and kind=='blob' and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()==oid
 blob[oid]=dict(size=size,sha256=sha(data))
assert at==len(v)
for entries in rows.values():
 for item in entries.values():item.update(blob[item['git_blob']])
mapcount=0;bindings=0;summary=[]
for st in stages:
 name=st['stage'];rec=json.loads(payloads[name+'/receipt.json']);before=json.loads(payloads[name+'/before.json']);after=json.loads(payloads[name+'/after.json']);ref=rows[st['head']]
 assert before==after and rec['head']==st['head'] and rec['inputs']==len(before)==len(ref)==1525 and rec['before_after_git_exact']
 for snap in [before,after]:
  assert set(snap)==set(ref)
  for path,v in snap.items():assert v['git_exact'] and all(v[k]==ref[path][k] for k in ['mode','type','git_blob','size','sha256'])
  bindings+=len(snap);mapcount+=1
 assert rec['exit_code']==st['exit_code'] and rec['log_sha256']==st['log_sha256']
 assert rec['started_utc']==st['start'] and rec['ended_utc']==st['end']
 assert 'runner_sha256' not in rec
 log=name+'/run.log';checked=log in raws
 if checked:assert sha(raws[log])==rec['log_sha256']
 else:
  bounded=json.loads(payloads[name+'/bounded-failure-summary.json']);assert bounded['raw_log_sha256']==rec['log_sha256'] and bounded['head']==rec['head']
 summary.append(dict(stage=name,head=st['head'],exit_code=rec['exit_code'],status=st['test_status'],raw_log_sha256=rec['log_sha256'],raw_log_reconstructed_from_admitted_candidate=checked,before_after_exact=True,bindings=3050,historical_runner_sha256='NOT_CAPTURED'))
assert mapcount==22 and bindings==33550 and len(blob)==1515
path='apps/web/src/features/codex/CodexTurnInterruptPanel.test.tsx'
red=git('show','af20b3fe90228d8f522b050a13084785eaa98af8:'+path);green=git('show','68420d379b69c0368305adab057432d21c1e56fb:'+path);final=git('show',head+':'+path)
assert red==green and sha(red)=='095e267d26a78188f46f9ccf3d49d4000cc0983f8bae7c78a657a0a58197079f' and final!=green
assert sha(raws['run.py'])==history['current_runner_sha256']
assert history['historical_runner_hash_not_reconstructed']
assert git('rev-parse','HEAD').decode().strip()==head and git('status','--porcelain')==b''
result=dict(source=head,owner_safe_sha256=sha(mr),owner_outer_sha256=sha(outer),candidate_count=50,outer_count=2,candidates=candidates,git_heads=heads,distinct_git_blobs=len(blob),complete_git_bindings=sum(len(v) for v in rows.values()),historical_maps=mapcount,historical_map_bindings=bindings,all_mode_type_blob_size_sha_exact=True,stages=summary,same_complete_red_green_component_sha256=sha(red),final_component_sha256=sha(final),original_actual_four_fail='Bounded admitted summary+exit1; excluded retained raw DOM not read/reconstructed.',three_toolchain_failures='0 tests, actual admitted logs; not behavior RED.',strict_first='Actual two TypeScript diagnostics, retained; fixed22 strict exit0.',current_runner_sha256=sha(raws['run.py']),historical_runner_sha256='NOT_CAPTURED / NOT_RECONSTRUCTED',full_native='RUNNING separate root packet, not admitted/counted',public_ci='Root-reported firstReview132P1F UNKNOWN, original CI not independently read in this packet.',new_product_test_execution=False)
print(json.dumps(result,ensure_ascii=False,indent=2))
