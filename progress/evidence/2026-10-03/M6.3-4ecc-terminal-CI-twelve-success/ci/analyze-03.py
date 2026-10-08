import datetime, hashlib, json, re, subprocess
from pathlib import Path
O=Path(__file__).parent
REPO='kl3574/Learning_Workbench'
HEAD='4ecc27a883782855a6e5611d7610979e4b4b05ca'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not (O/'receipt-03.json').exists()
runs=[];jobs=[]
for rid in (37165685426,37165687627):
 data=json.loads((O/f'{rid}.raw.json').read_bytes())
 assert data['headSha']==HEAD and data['status']=='completed' and data['conclusion']=='success'
 assert {j['name'] for j in data['jobs']}=={'spec-contracts','backend','frontend','integration','browser','security-publication'}
 runs.append({'id':rid,**{k:data[k] for k in ('status','conclusion','headSha','event','url')}})
 for job in data['jobs']:
  stem=f"{rid}-{job['name']}"
  if not (O/(stem+'.log')).exists():
   argv=['gh','run','view',str(rid),'--repo',REPO,'--job',str(job['databaseId']),'--log']
   result=subprocess.run(argv,capture_output=True)
   (O/(stem+'.log')).write_bytes(result.stdout);(O/(stem+'.stderr')).write_bytes(result.stderr)
   (O/(stem+'.invocation.json')).write_text(json.dumps({'command':argv,'exit_code':result.returncode,'stdout_sha256':sha(result.stdout),'stderr_sha256':sha(result.stderr)},indent=2)+'\n')
   assert result.returncode==0
  raw=(O/(stem+'.log')).read_bytes();inv=json.loads((O/(stem+'.invocation.json')).read_bytes())
  assert inv['exit_code']==0 and inv['stdout_sha256']==sha(raw) and job['conclusion']=='success' and job['status']=='completed'
  lines=[line.split('\t',2)[-1] for line in raw.decode().splitlines()]
  checkout=[]
  for index,line in enumerate(lines):
   if 'git log -1 --format=%H' in line:
    found=re.search(r'\s([0-9a-f]{40})$',lines[index+1]);assert found
    checkout.append(found.group(1))
  assert len(checkout)==1,(stem,checkout)
  counts=[line for line in lines if re.search(r'(=+.*\d+ passed|Tests\s+\d+ passed|Test Files\s+\d+ passed|\[chromium\].*local-task|\b130 passed\b|Success: no issues found)',line)]
  jobs.append({'run_id':rid,'event':data['event'],'job':job['name'],'job_id':job['databaseId'],'status':job['status'],'conclusion':job['conclusion'],'url':job['url'],'checkout':checkout[0],'log_sha256':sha(raw),'test_summary_lines':counts})
bindings=[]
for commit in sorted({j['checkout'] for j in jobs}):
 r=subprocess.run(['gh','api',f'repos/{REPO}/git/commits/{commit}'],capture_output=True)
 assert r.returncode==0
 (O/(commit+'.commit.raw.json')).write_bytes(r.stdout)
 c=json.loads(r.stdout);assert c['sha']==commit
 binding={'sha':c['sha'],'tree_sha':c['tree']['sha'],'parents':[p['sha'] for p in c['parents']]};bindings.append(binding)
 (O/(commit+'.binding.json')).write_text(json.dumps(binding,indent=2)+'\n')
assert len({b['tree_sha'] for b in bindings})==1
assert all(j['checkout']==HEAD for j in jobs if j['event']=='push')
merge=next(b for b in bindings if b['sha']!=HEAD);assert HEAD in merge['parents']
summary={'status':'BOTH_COMPLETED_SUCCESS_ALL_SIX_JOBS','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':HEAD,'runs':runs,'jobs':jobs,'commit_bindings':bindings,'boundary':'12 actual job logs and exact source/merge same-tree CI success; no upgrade of physical numeric, Provider proof, actual CLI turn, quality, M6.3 overall or release. Original e913 CI failures retained. Original local parser failure separately retained; corrected analysis uses unchanged downloaded logs.'}
(O/'receipt-03.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':summary['status'],'bindings':bindings,'jobs':[{'run':j['run_id'],'job':j['job'],'summary':j['test_summary_lines']} for j in jobs]},ensure_ascii=False))
