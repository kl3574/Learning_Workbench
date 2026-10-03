from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,importlib.util,json,re,zipfile
P=Path(__file__).parent;S=P.parent/'m62-0ede-ci-terminal-oct03';B=P.parent/'m62-public-safe-oct02/progress/evidence/2026-10-03/M6.2-ci-terminal-0ede5f94';T=P.parent/'m62-text-concept-native-oct03'
h=lambda b:hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def inventory(p):return {str(q.relative_to(p)):{'sha256':h(q.read_bytes()),'bytes':q.stat().st_size} for q in sorted(p.rglob('*')) if q.is_file()}
def safe_path(root,name):
 assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
 q=root/name;assert q.is_file() and not q.is_symlink();return q
before={'archive':inventory(S),'public':inventory(B)}
manifest=load(S/'RAW_MANIFEST.json');entries=manifest['entries'];assert len(entries)==777 and len({e['path'] for e in entries})==777
assert h((S/'RAW_MANIFEST.json').read_bytes())=='fd56113c50c92bee6d28fafc31233e8928a8efdd300715bacd6063aeb7c289c5'
for e in entries:
 raw=safe_path(S,e['path']).read_bytes();assert h(raw)==e['sha256'] and len(raw)==e['bytes'],e['path']
terminal=load(S/'CI_TERMINAL.json');numeric=load(S/'NUMERIC.json')['artifacts'];assert len(terminal['runs'])==2 and len(numeric)==4
jobs_checked=[];archives=[];numbers=[];trees=[]
for run in terminal['runs']:
 source={}
 for e in run['source_api']:
  p=safe_path(S,e['path']);assert h(p.read_bytes())==e['sha256'];source[p.name.rsplit('-',1)[1].removesuffix('.json')]=load(p)
 api=source['run'];assert api['id']==run['run']
 for key in ['event','status','conclusion','run_attempt','head_sha','created_at','updated_at']:assert run[key]==api[key],key
 assert api['status']=='completed' and api['conclusion']=='success'
 job_api={j['id']:j for j in source['jobs']['jobs']};assert len(run['jobs'])==len(job_api)==6
 checkout=run['checkout']['sha'];c=load(S/str(run['run'])/('checkout-'+checkout+'.json'))
 assert c['sha']==checkout and c['tree']['sha']==run['checkout']['tree'];trees.append(c['tree']['sha'])
 for job in run['jobs']:
  j=job_api[job['id']]
  for key in ['name','status','conclusion','started_at','completed_at']:assert job[key]==j[key],key
  assert j['status']=='completed' and j['conclusion']=='success'
  raw=safe_path(S,job['raw_log']).read_bytes();assert h(raw)==job['raw_log_sha256']
  text=re.sub(r'\x1b\[[0-9;]*m','',raw.decode())
  actual=[];lines=text.splitlines()
  for i,line in enumerate(lines):
   if '[command]/usr/bin/git log -1 --format=%H' in line:
    match=re.search(r'\b([0-9a-f]{40})$',lines[i+1]);assert match;actual.append(match.group(1))
  assert actual==job['actual_checkout_shas']==[checkout]
  for fact in job['terminal_facts']:assert fact in text,fact
  for skip in job['environment_skips']:assert skip['test']+': '+skip['reason'] in text
  assert not job['failed_test_names']
  jobs_checked.append({'run':run['run'],'job':job['id'],'name':j['name'],'checkout':checkout,'status':j['conclusion'],'log_sha256':h(raw),'facts':job['terminal_facts'],'environment_skips':job['environment_skips']})
 artifacts={a['id']:a for a in source['artifacts']['artifacts']};assert len(artifacts)==len(run['artifacts'])==2
 for art in run['artifacts']:
  a=artifacts[art['artifact_id']];p=S/str(run['run'])/f"artifact-{art['artifact_id']}.raw.zip";sha=h(p.read_bytes())
  assert a['name']==art['name'] and a['digest']=='sha256:'+sha==art['metadata_digest'] and sha==art['zip_sha256'] and not a['expired']
  with zipfile.ZipFile(p) as z:
   assert z.testzip() is None
   assert set(z.namelist())=={m['path'] for m in art['members']}
   for m in art['members']:
    assert not PurePosixPath(m['path']).is_absolute() and '..' not in PurePosixPath(m['path']).parts
    data=z.read(m['path']);assert len(data)==m['bytes'] and h(data)==m['sha256']
    extracted=S/str(run['run'])/f"artifact-{art['artifact_id']}-extracted"/m['path'];assert extracted.read_bytes()==data
    d=json.loads(data)
    if not m['path'].endswith(('single-publication-actual.json','restore-numeric-actual.json')):continue
    n=next(n for n in numeric if n['artifact_id']==art['artifact_id']);assert n['run']==run['run'] and n['sha256']==h(data) and S/n['path']==extracted
    result=d['actual']['result'];outcome=d.get('outcome',d.get('publishOutcome'))
    for k in ['outcome','verdict','exit_code','assertions','output_sha256','result_sha256']:assert n[k]==result[k]
    assert result['outcome']=='environment_unavailable' and result['verdict']=='BLOCKED' and result['exit_code']==1 and result['assertions']==[] and result['output_sha256'] is None
    assert n['publication_status']==outcome['status']==409 and n['publication_error']==outcome['body']['error']['code']=='PUBLISH_NUMERIC_REQUIRED'
    assert n['external_model_calls']==d.get('externalModelCalls',d.get('newModelCalls'))==0
    numbers.append({'run':run['run'],'artifact_id':art['artifact_id'],'kind':n['kind'],'actual_sha256':h(data),'outcome':result['outcome'],'verdict':result['verdict'],'exit_code':result['exit_code'],'publication_status':409,'publication_error':'PUBLISH_NUMERIC_REQUIRED','external_model_calls':0})
  archives.append({'run':run['run'],'artifact':art['artifact_id'],'zip_sha256':sha,'member_count':len(art['members']),'digest_matches_api':True})
assert len(jobs_checked)==12 and len(archives)==len(numbers)==4 and len(set(trees))==1
share=load(S/'SAFE_SHARE.json')['allowlist'];assert len(share)==8
whitelist=[]
for e in share:
 raw=safe_path(S,e['source']).read_bytes();candidate=safe_path(S,e['candidate']).read_bytes()
 assert h(raw)==e['raw_sha256'] and h(candidate)==e['published_sha256'] and len(candidate)==e['bytes']
 expected=raw.replace(b'<RUNNER_HOME>',b'$RUNNER_HOME').replace(b'<LOCAL_HOME>',b'$HOME')
 assert candidate==expected and e['transformation']==('none' if candidate==raw else 'exact <RUNNER_HOME> to $RUNNER_HOME and <LOCAL_HOME> to $HOME only')
 whitelist.append({'path':e['candidate'],'sha256':h(candidate),'bytes':len(candidate),'transformation':e['transformation']})
public=load(B/'manifest.json')['entries'];assert len(public)==12
allowed_sources={x['candidate'] for x in share}|{'SAFE_SHARE.json','SAFE_SCAN.json','FINAL_READBACK.json'}
assert {x['source_relative'] for x in public if 'source_relative' in x}==allowed_sources
assert {str(q.relative_to(B)) for q in B.rglob('*') if q.is_file()}=={x['file'] for x in public}|{'manifest.json'}
assert len(inventory(B))==13
for e in public:
 data=safe_path(B,e['file']).read_bytes();assert h(data)==e['published_sha256']
 if 'source_relative' in e:
  raw=safe_path(S,e['source_relative']).read_bytes();assert h(raw)==e['raw_sha256'] and data==raw and e['transformation']=='none'
report=load(B/'REPORT.json');assert report['head']==terminal['runs'][0]['head_sha'] and report['files']==11
for r in report['runs']:
 original=next(x for x in terminal['runs'] if x['run']==r['id']);assert r['event']==original['event'] and r['conclusion']==original['conclusion'] and r['actual_checkout']==original['checkout']['sha']
scan_spec=importlib.util.spec_from_file_location('scan',T/'scripts/check_publication.py');scan=importlib.util.module_from_spec(scan_spec);scan_spec.loader.exec_module(scan)
keys=re.compile(r'^(authorization|proxy[-_]authorization|cookie|set[-_]cookie|x[-_]csrf[-_]token|csrf([-_]token)?|access[-_]token|refresh[-_]token|session[-_]token|bootstrap([-_]token|[-_]code)?|password|secret|api[-_]key|private[-_]key|headers)$',re.I)
header=re.compile(rb'(?im)^\s*["\']?(authorization|proxy-authorization|cookie|set-cookie|x-csrf-token)["\']?\s*[:=]\s*[^\s,}]')
findings=[]
def fields(v,path,file):
 if isinstance(v,dict):
  for k,value in v.items():
   if keys.fullmatch(k):findings.append({'path':file,'field':path+'/'+k})
   fields(value,path+'/'+k,file)
 elif isinstance(v,list):
  for i,value in enumerate(v):fields(value,path+'/'+str(i),file)
for q in sorted(B.rglob('*')):
 if not q.is_file():continue
 rel=str(q.relative_to(B));data=q.read_bytes()
 for reason in scan.inspect('progress/evidence/CI-independent/'+rel,data):findings.append({'path':rel,'reason':reason})
 if header.search(data):findings.append({'path':rel,'rule':'header assignment'})
 if q.suffix=='.json':fields(load(q),'',rel)
assert not findings,findings
assert before=={'archive':inventory(S),'public':inventory(B)}
receipt={'reviewed_at':datetime.now(timezone.utc).isoformat(),'scope':'Independent local read-only audit of sealed original evidence and 13-file public candidate; no API, network, re-execution or source mutation.','status':'PASS_NO_CONFIRMED_BLOCKER','raw_manifest_sha256':h((S/'RAW_MANIFEST.json').read_bytes()),'raw_members_rehashed':777,'archive_files_before_after_unchanged':len(before['archive']),'actual_job_checkout_checks':jobs_checked,'common_tree':trees[0],'zip_checks':archives,'numeric_outcomes':numbers,'eight_payload_whitelist':whitelist,'public_files':before['public'],'public_payload_sources_exactly_allowed':True,'public_scan_findings':findings,'public_files_before_after_unchanged':True,'boundaries':['CI success is software checks only; all physical numeric outcomes remain BLOCKED and publication HTTP409.','Python job counts overlap and cannot be summed as one full suite.','Original CI source0ede differs from new814 concept-retention local gates.','Eight SAFE_SHARE payloads plus three explicitly checked outer metadata and two public package files only; raw-manifest hashes do not authorize raw payload publication.','No independent execution or fresh GitHub API status is claimed; this audit binds the retained originals.']}
(P/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'raw':777,'jobs':len(jobs_checked),'zip':len(archives),'numeric_blocked':len(numbers),'safe_payloads':len(share),'public_files':13,'scan_findings':len(findings),'inputs_unchanged':True,'receipt_sha256':h((P/'RECEIPT.json').read_bytes())}))
