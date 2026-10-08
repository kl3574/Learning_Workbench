from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,re
P=Path(__file__).parent;T=P.parent/'m63-spec-http-independent-oct03';h=lambda b:hashlib.sha256(b).hexdigest()
def put(name,value):
 q=P/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(value,indent=2)+'\n')
allow=['REVIEW.md','SOURCE.json','run_probes.py','executed-http-probe.py','share-http-probe.py','ui-probe.tsx','PRIVATE_PROBE_FORMAT_RECEIPT.json','ruff-format-fixed.log','SETUP_DIAGNOSTIC.md','setup-early-fail.log','npm-ci.log','audit_ui.py','audit_ui-initial.py','UI_AUDIT_HARNESS_DIAGNOSTIC.md','UI_EVIDENCE_REVIEW.json','UI_PRIVATE_CONFIG_READBACK.json','ui-evidence-audit.log','seal_review.py']
for name in ['http','ui','strict','ruff']:allow.extend(name+s for s in ['.log','-receipt.json','-before.json','-after.json'])
s=importlib.util.spec_from_file_location('scan',T/'scripts/check_publication.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
header=re.compile(rb'(?im)^\s*["\']?(authorization|proxy-authorization|cookie|set-cookie|x-csrf-token)["\']?\s*[:=]\s*[^\s,}]')
findings=[];failures=[];items=[]
for name in allow:
 raw=(P/name).read_bytes();virtual='progress/evidence/M63-independent-spec/'+name;errors=m.inspect(virtual,raw)
 if errors:findings.append({'path':name,'sha256':h(raw),'rules':[i for i,v in enumerate(m.SUSPECT) if re.search(v,raw)],'reasons':errors})
 candidate=re.sub(rb'<LOCAL_HOME>(?=$|/|[^A-Za-z0-9_.-])',b'<LOCAL_HOME>',raw);candidate=re.sub(rb'<RUNNER_HOME>(?=$|/|[^A-Za-z0-9_.-])',b'<RUNNER_HOME>',candidate)
 issues=m.inspect(virtual,candidate)
 if issues or header.search(raw):failures.append({'path':name,'reasons':issues,'header_assignment':bool(header.search(raw))})
 q=P/'safe-share'/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(candidate)
 items.append({'source':name,'candidate':'safe-share/'+name,'raw_sha256':h(raw),'candidate_sha256':h(candidate),'raw_bytes':len(raw),'candidate_bytes':len(candidate),'transformation':'none' if candidate==raw else 'exact <LOCAL_HOME> to <LOCAL_HOME> and <RUNNER_HOME> to <RUNNER_HOME>'})
put('SCAN.json',{'scanner_sha256':h((T/'scripts/check_publication.py').read_bytes()),'raw_status':'FAIL' if findings else 'PASS','raw_findings':findings,'candidate_status':'FAIL' if failures else 'PASS','candidate_findings':failures,'scope':'Bounded repository scanner and anchored header assignments; no matched values disclosed.'})
assert not failures,failures
assert all(x['rules']==[5] for x in findings)
put('SAFE_SHARE.json',{'scope':'Only these explicit reviewer artifacts; all tmp/runtime/DB/cache and producer payloads excluded. Private derivative, not publication. Overall source acceptance remains held by separate security findings.','items':items})
put('safe-share/SAFE_SHARE_MANIFEST.json',{'scope':'Exact prefix-only derivative with original hashes; not product approval','items':items})
raw=[]
for name in allow+['SCAN.json','SAFE_SHARE.json']:
 b=(P/name).read_bytes();raw.append({'path':name,'sha256':h(b),'bytes':len(b)})
put('MANIFEST.json',{'sealed_at':datetime.now(timezone.utc).isoformat(),'source':'6a594a58fd99b0eb2baafe845959e9f2886f60f9','status':'SPEC_HTTP_UI_NO_NEW_BLOCKER_OVERALL_SECURITY_HOLD','items':raw})
(P/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in raw)+h((P/'MANIFEST.json').read_bytes())+'  MANIFEST.json\n')
for name in ['REVIEW.md','MANIFEST.json','SAFE_SHARE.json','SHA256SUMS']:print(name,h((P/name).read_bytes()))
print(json.dumps({'raw_items':len(raw),'share_items':len(items),'raw_personal_path_findings':len(findings),'candidate_status':'PASS'}))
