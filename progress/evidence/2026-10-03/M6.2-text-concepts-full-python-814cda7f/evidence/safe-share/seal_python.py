from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,re,shutil,subprocess
E=Path(__file__).parent;P=E/'PYTHON';T=E.parent/'m62-text-concept-combined-gate-oct03'
h=lambda b:hashlib.sha256(b).hexdigest()
receipt=json.loads((E/'python-receipt.json').read_bytes())
assert receipt['exit_code']==0 and receipt['inputs_unchanged'] and receipt['count']==1321
before=json.loads((E/'python-before.json').read_bytes());after=json.loads((E/'python-after.json').read_bytes());assert before==after
log=(E/'python.log').read_text();clean=re.sub(r'\x1b\[[0-9;]*m','',log)
summary=[x for x in clean.splitlines() if re.search(r'\b\d+ passed\b',x)][-1]
assert not re.search(r'\b\d+ (?:failed|errors?)\b',summary)
assert not subprocess.check_output(['git','status','--porcelain'],cwd=T)
P.mkdir()
for name in ['python.log','python-receipt.json','python-before.json','python-after.json','run_gates.py','seal_python.py']:shutil.copyfile(E/name,P/name)
(P/'REPORT.md').write_text('''# Fixed concept-retention combination: complete Python gate

Fixed source 814cda7f73e864af7a499c0486b4fe9bc46fccb9, clean isolated detached tree m62-text-concept-combined-gate-oct03. Sole v3.0.13 remains SHA256 949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05. No product source changed during this run.

Actual complete pytest result:

`'''+summary.strip('= ').strip()+'''`

The exact command, UTC start/end, process duration and exit code are in python-receipt.json. This is the repository's full pytest collection (3582 items), using frozen installed dependencies, --tb=short, an independent cache and fresh private basetemp. Original warnings and skip reason are retained at the end of python.log. A skipped physical-runtime test is not a physical execution PASS; synthetic protocol tests do not establish content or academic quality.

All **1321 Git-tracked non-progress engineering inputs** matched fixed Git bytes before and after; all before/after receipts are equal. The actual private run_gates.py bytes are also bound. Exclusions are progress/, ignored installed tools, runtime/temp files, caches and build outputs. No selected production subtree was substituted for this complete scope. No DB, browser profile, credentials, headers, raw session or environment is part of this package.

The 16 new concepts HTTP cases, five original V2 and seven V1 representation checks are included in this full collection, not added again to the total. Earlier 280 focused and 53 independent backend tests remain separate source-bound executions. Exact old-record canonical/hash/ACK rendering is not reopening an old captured database.

Complete Web 961 PASS, strict/build/Ruff/mypy/verify gates on this same fixed source are sealed separately under STATIC. The single native case is separately sealed at 814cda7f; root independently owns the full native run. Neither result is silently incorporated into this Python count. No remote publication or full M6.2 acceptance is asserted here.

Sharing is restricted to the explicit SAFE_SHARE list. Only exact local-home prefixes are converted in the private derivative; originals and hashes are retained. Repository path/credential and anchored header checks supplement the synthetic provenance and do not guarantee arbitrary prose classification.
''')
def put(name,data):
 q=P/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(data,indent=2)+'\n')
allow=['REPORT.md','python.log','python-receipt.json','python-before.json','python-after.json','run_gates.py','seal_python.py']
spec=importlib.util.spec_from_file_location('scan',T/'scripts/check_publication.py');scan=importlib.util.module_from_spec(spec);spec.loader.exec_module(scan)
header=re.compile(rb'(?im)^\s*["\']?(authorization|proxy-authorization|cookie|set-cookie|x-csrf-token)["\']?\s*[:=]\s*[^\s,}]')
raw_findings=[];failures=[];items=[]
for name in allow:
 raw=(P/name).read_bytes();virtual='progress/evidence/text-concept-combined-python/'+name;errs=scan.inspect(virtual,raw)
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
put('SAFE_SHARE.json',{'scope':'Explicit private candidate, not published; excludes caches/runtime/test DBs.','item_count':len(items),'transforms':[{'exact_prefix':'<LOCAL_HOME>','replacement':'<LOCAL_HOME>'},{'exact_prefix':'<RUNNER_HOME>','replacement':'<RUNNER_HOME>'}],'candidate_directory':'safe-share','scan_sha256':h((P/'SCAN.json').read_bytes()),'items':items})
put('safe-share/SAFE_SHARE_MANIFEST.json',{'scope':'Exact-home-prefix-only derivative with raw and candidate SHA256, not publication','items':items})
raw=[]
for name in allow+['SCAN.json','SAFE_SHARE.json']:
 b=(P/name).read_bytes();raw.append({'path':name,'sha256':h(b),'bytes':len(b)})
put('MANIFEST.json',{'sealed_at':datetime.now(timezone.utc).isoformat(),'head':receipt['head'],'status':'FULL_PYTHON_EXIT_ZERO_WITH_ORIGINAL_SKIP_AND_WARNING_SCOPE','summary':summary.strip('= ').strip(),'items':raw})
(P/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in raw)+h((P/'MANIFEST.json').read_bytes())+'  MANIFEST.json\n')
assert all(h((P/x['path']).read_bytes())==x['sha256'] for x in raw)
for name in ['REPORT.md','MANIFEST.json','SAFE_SHARE.json','SHA256SUMS']:print(name,h((P/name).read_bytes()))
print(json.dumps({'raw_files':len(raw),'candidates':len(items),'raw_home_path_findings':len(raw_findings),'candidate_status':'PASS','summary':summary.strip('= ').strip()}))
