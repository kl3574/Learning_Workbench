"""Bounded GET-only current PR55 and two known run snapshots."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os,json,subprocess,hashlib,datetime,re
BASE=Path(__file__).resolve().parent
REPO='kl3574/Learning_Workbench'
CURRENT='b90b4446172b39a3858a9684437920c27eda01ae'
RUNS={35692894284:CURRENT,35692897917:CURRENT}
os.umask(0o077)
ENV={k:v for k,v in os.environ.items() if k.upper() not in {'HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY'}}
ENV['GODEBUG']='http2client=0'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,value):(BASE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def get(spec):
 name,endpoint,suffix=spec;cmd=['gh','api','--method','GET',endpoint];start=now()
 try:
  r=subprocess.run(cmd,env=ENV,capture_output=True,timeout=35,check=False);code,out,err=r.returncode,r.stdout,r.stderr
 except subprocess.TimeoutExpired as e:code,out,err=124,e.stdout or b'',e.stderr or b''
 (BASE/(name+'.'+suffix)).write_bytes(out);(BASE/(name+'.stderr')).write_bytes(err)
 save(name+'.receipt.json',{'command':cmd,'started_at':start,'finished_at':now(),'exit_code':code,'timeout_seconds':35,'stdout_bytes':len(out),'stdout_sha256':sha(out),'stderr_bytes':len(err),'stderr_sha256':sha(err),'transport':{'proxy_variables_removed_case_insensitively':['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY'],'GODEBUG':'http2client=0'},'retry_count':0})
 if code:return None
 if suffix=='log':return out.decode('utf-8',errors='replace')
 try:return json.loads(out)
 except(ValueError,TypeError):return None
started=now()
specs=[('pr',f'repos/{REPO}/pulls/55','json'),('ref',f'repos/{REPO}/git/ref/heads/feat%2FM6.2-candidate-review','json')]
for run in RUNS:
 specs.extend([(f'run-{run}',f'repos/{REPO}/actions/runs/{run}','json'),(f'jobs-{run}',f'repos/{REPO}/actions/runs/{run}/jobs?filter=all&per_page=100','json')])
with ThreadPoolExecutor(max_workers=8) as pool:values=list(pool.map(get,specs))
results=dict(zip((x[0] for x in specs),values))
pr,ref=results['pr'],results['ref']
binding={'expected_current_head_sha':CURRENT,'pr_head_sha':pr['head']['sha'] if pr else None,'ref_sha':ref.get('object',{}).get('sha') if ref else None,'head_ref':pr['head']['ref'] if pr else None,'base_ref':pr['base']['ref'] if pr else None,'base_sha':pr['base']['sha'] if pr else None,'merge_commit_sha':pr.get('merge_commit_sha') if pr else None,'pr_state':pr.get('state') if pr else None,'pr_draft':pr.get('draft') if pr else None}
binding['pr_ref_match_expected']=binding['pr_head_sha']==binding['ref_sha']==CURRENT
rows=[];failed=[]
for identifier,expected in RUNS.items():
 run,jobs=results[f'run-{identifier}'],results[f'jobs-{identifier}']
 row={'id':identifier,'expected_run_head_sha':expected,'run_read_ok':run is not None,'jobs_read_ok':jobs is not None}
 if run:
  row.update({k:run.get(k) for k in ['head_sha','head_branch','event','status','conclusion','run_attempt','created_at','updated_at','html_url']});row['run_head_matches_expected']=run.get('head_sha')==expected
 row['jobs_total_count']=jobs.get('total_count') if jobs else None;row['jobs']=[]
 if jobs:
  for job in jobs.get('jobs',[]):
   entry={k:job.get(k) for k in ['id','run_id','run_attempt','name','head_sha','status','conclusion','started_at','completed_at','html_url']}
   entry['failed_steps']=[{k:s.get(k) for k in ['name','number','status','conclusion']} for s in job.get('steps',[]) if s.get('conclusion')=='failure']
   row['jobs'].append(entry)
   if job.get('status')=='completed' and (job.get('conclusion')=='failure' or job.get('name')=='browser'):failed.append(job['id'])
 rows.append(row)
print(json.dumps({'phase':'initial_snapshot','binding':binding,'runs':[{'id':r['id'],'head_sha':r.get('head_sha'),'status':r.get('status'),'conclusion':r.get('conclusion'),'jobs':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion']} for j in r['jobs']]} for r in rows],'terminal_log_reads':failed},indent=2),flush=True)
log_specs=[(f'terminal-job-{j}',f'repos/{REPO}/actions/jobs/{j}/logs','log') for j in dict.fromkeys(failed)]
with ThreadPoolExecutor(max_workers=max(1,len(log_specs))) as pool:logs=list(pool.map(get,log_specs))
parsed=[]
for spec,log in zip(log_specs,logs):
 jobid=int(spec[0].removeprefix('terminal-job-'));item={'job_id':jobid,'log_read_ok':log is not None,'actual_checkout_sha':None,'log_file':spec[0]+'.log'}
 if log is not None:
  lines=log.splitlines();checkout=[]
  for i,line in enumerate(lines):
   if 'git log -1 --format=%H' in line and i+1<len(lines):
    match=re.search(r'\b([0-9a-f]{40})\s*$',lines[i+1])
    if match:checkout.append({'command_line':i+1,'output_line':i+2,'sha':match.group(1)})
  item['checkout_observations']=checkout
  if len({x['sha'] for x in checkout})==1:item['actual_checkout_sha']=checkout[0]['sha']
  patterns={'suite_summary':r'\b\d+ (?:passed|failed|skipped)\b','failed_case':r'(?:✘\s+\d+|\s+\d+\)) .*\.spec\.ts:','failure_detail':r'Error:|Expected:|Received:|Timeout:|\bat .*\.spec\.ts:|Process completed with exit code'}
  for label,pattern in patterns.items():item[label]=[{'line':i+1,'text':line} for i,line in enumerate(lines) if re.search(pattern,line)]
 parsed.append(item)
summary={'started_at':started,'finished_at':now(),'binding':binding,'runs':rows,'terminal_job_logs':parsed,'read_failures':[k for k,v in results.items() if v is None],'scope':'Single independent GET snapshot of PR/ref and known runs/jobs, followed only by logs of completed browser or failed jobs. No retry, dispatch, polling, waiting for completion, ZIP/artifact fetch, new test run, source edit or vendor call. Metadata head fields are not job checkout proof; actual checkout only if directly printed in captured job log.'}
save('summary.json',summary)
print(json.dumps({'phase':'complete','terminal_job_logs':parsed,'read_failures':summary['read_failures'],'finished_at':summary['finished_at']},ensure_ascii=False,indent=2),flush=True)
