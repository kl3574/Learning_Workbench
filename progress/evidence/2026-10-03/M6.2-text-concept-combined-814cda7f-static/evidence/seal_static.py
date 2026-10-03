from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,re
P=Path(__file__).parent
T=P.parent.parent/'m62-text-concept-combined-gate-oct03'
h=lambda b:hashlib.sha256(b).hexdigest()
def put(name,data):
 q=P/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(data,indent=2)+'\n')
allow=['REPORT.md','SOURCE.json','run_gates.py','npm-ci.log','seal_static.py']
for n in ['web','strict','build','ruff','mypy','verify']:
 allow.extend(n+x for x in ['.log','-receipt.json','-before.json','-after.json'])
spec=importlib.util.spec_from_file_location('scan',T/'scripts/check_publication.py');scan=importlib.util.module_from_spec(spec);spec.loader.exec_module(scan)
header=re.compile(rb'(?im)^\s*["\']?(authorization|proxy-authorization|cookie|set-cookie|x-csrf-token)["\']?\s*[:=]\s*[^\s,}]')
raw_findings=[];failures=[];items=[]
for name in allow:
 raw=(P/name).read_bytes();virtual='progress/evidence/text-concept-combined-static/'+name;errs=scan.inspect(virtual,raw)
 if errs:raw_findings.append({'path':name,'sha256':h(raw),'rules':[i for i,v in enumerate(scan.SUSPECT) if re.search(v,raw)],'reasons':errs})
 candidate=re.sub(rb'<LOCAL_HOME>(?=$|/|[^A-Za-z0-9_.-])',b'<LOCAL_HOME>',raw)
 candidate=re.sub(rb'<RUNNER_HOME>(?=$|/|[^A-Za-z0-9_.-])',b'<RUNNER_HOME>',candidate)
 err=scan.inspect(virtual,candidate)
 if err or header.search(raw):failures.append({'path':name,'reasons':err,'header_assignment':bool(header.search(raw))})
 q=P/'safe-share'/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(candidate)
 items.append({'path':name,'raw_sha256':h(raw),'candidate_sha256':h(candidate),'raw_bytes':len(raw),'candidate_bytes':len(candidate)})
put('SCAN.json',{'scanner_sha256':h((T/'scripts/check_publication.py').read_bytes()),'raw_status':'FAIL' if raw_findings else 'PASS','raw_findings':raw_findings,'candidate_status':'FAIL' if failures else 'PASS','candidate_findings':failures})
assert not failures,failures
assert all(x['rules']==[5] for x in raw_findings)
put('SAFE_SHARE.json',{'scope':'Explicit private candidate, not published; exclude live Python output, caches and runtime files.','item_count':len(items),'transforms':[{'exact_prefix':'<LOCAL_HOME>','replacement':'<LOCAL_HOME>'},{'exact_prefix':'<RUNNER_HOME>','replacement':'<RUNNER_HOME>'}],'candidate_directory':'safe-share','scan_sha256':h((P/'SCAN.json').read_bytes()),'items':items})
put('safe-share/SAFE_SHARE_MANIFEST.json',{'scope':'Exact-home-prefix-only derivative with raw and candidate SHA256, not publication','items':items})
raw=[]
for name in allow+['SCAN.json','SAFE_SHARE.json']:
 b=(P/name).read_bytes();raw.append({'path':name,'sha256':h(b),'bytes':len(b)})
put('MANIFEST.json',{'sealed_at':datetime.now(timezone.utc).isoformat(),'head':'814cda7f73e864af7a499c0486b4fe9bc46fccb9','status':'FULL_WEB_AND_STATIC_PASS_PYTHON_STILL_RUNNING_NATIVE_NOT_RUN','items':raw})
(P/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in raw)+h((P/'MANIFEST.json').read_bytes())+'  MANIFEST.json\n')
assert all(h((P/x['path']).read_bytes())==x['sha256'] for x in raw)
for name in ['REPORT.md','MANIFEST.json','SAFE_SHARE.json','SHA256SUMS']:print(name,h((P/name).read_bytes()))
print(json.dumps({'raw_files':len(raw),'candidates':len(items),'raw_home_path_findings':len(raw_findings),'candidate_status':'PASS'}))
