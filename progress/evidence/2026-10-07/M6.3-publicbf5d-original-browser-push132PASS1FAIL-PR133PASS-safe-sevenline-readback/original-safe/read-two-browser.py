from pathlib import Path
import datetime,hashlib,json,re,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;P=B/'m63-ci-publicbf5d-original-observation-oct07'
def sha(v):return hashlib.sha256(v).hexdigest()
def put(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
latest=json.loads((P/'LATEST.json').read_bytes());raw=(P/latest['snapshot']).read_bytes();assert sha(raw)==latest['sha256'];snap=json.loads(raw);assert snap['source_head']=='bf5d2df4e7ee5156993169cdd9610fa014bdae4f' and not snap['read_errors'];put('SOURCE-SNAPSHOT.json',snap)
selected=[(e,j) for e in snap['actual_events'] for j in e.get('jobs',[]) if j['name'] in ['browser'] and j['status']=='completed'];assert len(selected)==2
ansi=re.compile(r'\x1b\[[0-9;]*[A-Za-z]');safe=[];results=[]
for e,j in selected:
 n=str(j['id']);argv=['gh','api','repos/kl3574/Learning_Workbench/actions/jobs/'+n+'/logs'];put(n+'-command.json',{'argv':argv,'source_head':snap['source_head'],'event':e['event'],'run':e['id'],'job':j,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});x=subprocess.run(argv,capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr);put(n+'-receipt.json',{'actual_exit':x.returncode,'stdout_bytes':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_bytes':len(x.stderr),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 if x.returncode:results.append({'job_id':j['id'],'name':j['name'],'event':e['event'],'download_actual_exit':x.returncode,'actual_test_counts':'NOT_READ'});continue
 if x.stdout.startswith(b'PK'):results.append({'job_id':j['id'],'name':j['name'],'event':e['event'],'download_actual_exit':0,'body_format':'ZIP_NOT_DECODED','actual_test_counts':'NOT_READ'});continue
 text=x.stdout.decode('utf-8');rows=[];counts=[];pending_checkout=False
 for i,line in enumerate(text.splitlines(),1):
  plain=ansi.sub('',line);payload=re.sub(r'^\d{4}-\d\d-\d\dT[^ ]+ +','',plain).strip();wanted=False
  if ('git log -1 --format' in payload or payload.startswith('Checking out ref')):wanted=True;pending_checkout='git log -1 --format' in payload
  elif pending_checkout and re.fullmatch('[0-9a-f]{40}',payload):wanted=True;pending_checkout=False
  elif re.search(r'(?:^|[= ])\d+ passed(?:, \d+ [a-z]+)* in \d+(?:\.\d+)?s',payload):wanted=True;counts.append({'kind':'pytest_original_footer','plain':payload})
  elif re.fullmatch(r'\d+ (?:failed|passed|skipped|flaky)(?: \([0-9.ms :]+\))?',payload):wanted=True;counts.append({'kind':'playwright_original_footer','plain':payload})
  elif re.fullmatch(r'(?:Test Files|Tests) +\d+ passed(?: +\(\d+\))?',payload):wanted=True;counts.append({'kind':'vitest_original_footer','plain':payload})
  elif re.fullmatch(r'PASS: scanned \d+ staged/tracked files against path and credential rules\. Manual provenance review remains required\.',payload):wanted=True;counts.append({'kind':'publication_scan_original_line','plain':payload})
  elif re.fullmatch(r'Success: no issues found in \d+ source files',payload) or payload=='All checks passed!':wanted=True
  if wanted:rows.append({'job_id':j['id'],'event':e['event'],'name':j['name'],'original_file':n+'.stdout','original_sha256':sha(x.stdout),'line_number':i,'text_original':line})
 safe.extend(rows);results.append({'job_id':j['id'],'name':j['name'],'event':e['event'],'download_actual_exit':0,'raw_log_bytes':len(x.stdout),'raw_log_sha256':sha(x.stdout),'actual_safe_footer_lines':counts,'safe_lines':len(rows),'scope':'Original completed job only; executionbeforeafterNOT_CAPTURED; notwholeCIacceptance'})
put('SAFE-SELECTED-LINES.json',safe);put('READBACK.json',{'source_head':snap['source_head'],'snapshot':latest,'jobs':results,'selected_original_jobs':2,'selected_safe_lines':len(safe),'raw_job_logs':'PRIVATE; no complete raw log copied','read_failures_not_retried':True,'M6_3':'NOT_ACCEPTED','model_calls_by_reader':0})
print('Two completed original browser jobs private captured; safe footer counts:',[(x['event'],x['name'],x['download_actual_exit'],x.get('actual_safe_footer_lines',[])) for x in results])
