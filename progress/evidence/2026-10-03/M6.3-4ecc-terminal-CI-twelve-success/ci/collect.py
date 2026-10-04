import concurrent.futures, datetime, hashlib, json, re, subprocess
from pathlib import Path
O=Path(__file__).parent
HEAD='4ecc27a883782855a6e5611d7610979e4b4b05ca'
REPO='kl3574/Learning_Workbench'
sha=lambda b: hashlib.sha256(b).hexdigest()
assert not (O/'receipt.json').exists()
runs=[]
for rid in (37165685426,37165687627):
 r=subprocess.run(['gh','run','view',str(rid),'--repo',REPO,'--json','status,conclusion,headSha,event,jobs,url'],capture_output=True)
 (O/f'{rid}.raw.json').write_bytes(r.stdout);(O/f'{rid}.stderr').write_bytes(r.stderr)
 assert r.returncode==0
 data=json.loads(r.stdout)
 assert data['headSha']==HEAD and data['status']=='completed' and data['conclusion']=='success'
 assert {j['name'] for j in data['jobs']}=={'spec-contracts','backend','frontend','integration','browser','security-publication'}
 assert all(j['status']=='completed' and j['conclusion']=='success' for j in data['jobs'])
 runs.append((rid,data))
def collect(item):
 rid,event,job=item
 argv=['gh','run','view',str(rid),'--repo',REPO,'--job',str(job['databaseId']),'--log']
 r=subprocess.run(argv,capture_output=True)
 stem=f"{rid}-{job['name']}"
 (O/(stem+'.log')).write_bytes(r.stdout);(O/(stem+'.stderr')).write_bytes(r.stderr)
 receipt={'command':argv,'exit_code':r.returncode,'stdout_sha256':sha(r.stdout),'stderr_sha256':sha(r.stderr)}
 (O/(stem+'.invocation.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 assert r.returncode==0
 text=r.stdout.decode()
 lines=text.splitlines()
 checkout=[]
 for index,line in enumerate(lines):
  if 'git log -1 --format=%H' in line:
   checkout += re.findall(r'\b[0-9a-f]{40}\b',lines[index+1])
 assert len(checkout)==1,(stem,checkout)
 counts=[line for line in lines if re.search(r'(=+.*\d+ passed|Tests\s+\d+ passed|Test Files\s+\d+ passed|\[chromium\].*local-task|\b130 passed\b|Success: no issues found)',line)]
 return {'run_id':rid,'event':event,'job':job['name'],'job_id':job['databaseId'],'status':job['status'],'conclusion':job['conclusion'],'url':job['url'],'checkout':checkout[0],'log_sha256':sha(r.stdout),'test_summary_lines':counts}
items=[(rid,data['event'],j) for rid,data in runs for j in data['jobs']]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 jobs=list(pool.map(collect,items))
commits={j['checkout'] for j in jobs}
for commit in commits:
 r=subprocess.run(['gh','api',f'repos/{REPO}/git/commits/{commit}'],capture_output=True)
 (O/(commit+'.commit.raw.json')).write_bytes(r.stdout)
 assert r.returncode==0
 c=json.loads(r.stdout)
 assert c['sha']==commit
 (O/(commit+'.binding.json')).write_text(json.dumps({'sha':c['sha'],'tree_sha':c['tree']['sha'],'parents':[p['sha'] for p in c['parents']]},indent=2)+'\n')
bindings=[json.loads((O/(c+'.binding.json')).read_text()) for c in sorted(commits)]
assert len({b['tree_sha'] for b in bindings})==1
summary={'status':'BOTH_COMPLETED_SUCCESS_ALL_SIX_JOBS','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':HEAD,'runs':[{'id':rid,**{k:data[k] for k in ('status','conclusion','headSha','event','url')}} for rid,data in runs],'jobs':jobs,'commit_bindings':bindings,'boundary':'Exact source/merge tree CI success; does not upgrade physical numeric, Provider proof, actual CLI turn, academic quality, M6.3 overall or release. Original e913 CI failures retained.'}
(O/'receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':summary['status'],'jobs':[{'run':j['run_id'],'job':j['job'],'checkout':j['checkout'],'summary':j['test_summary_lines']} for j in jobs]},ensure_ascii=False))
