from pathlib import Path
import hashlib,importlib.util,json,re
from datetime import datetime,timezone
P=Path(__file__).parent
T=P.parent/'m62-text-concept-native-oct03'
h=lambda data:hashlib.sha256(data).hexdigest()
def put(name,value):
 path=P/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
allow=['REPORT.md','SOURCE.json','COMMANDS.json','SEPARATE-EVIDENCE.json','UI-INDEPENDENT-REVIEW.md','green-inputs-before.json','green-inputs-after.json','red-input-receipt.json','capture_inputs.py','playwright-runtime-types.d.ts','tsconfig-native.json','playwright-red.config.mts','playwright-red-02.config.mts','playwright-green-01.config.mts','native-red.log','native-red-02.log','native-green-01.log','native-typecheck-01.log','native-typecheck-02.log','native-typecheck-03.log','native-typecheck-fixed.log','native-red-testcase.ts','native-red-02-testcase.ts','fixed-native-testcase.ts','native-only.patch','combined-diff-stat.txt','seal.py']
sub='text-edit-concepts-native--f176c--their-current-refs-advance/'
for prefix in ['native-red-output/','native-red-02-output/']:
 allow.extend([prefix+sub+'test-failed-1.png',prefix+sub+'error-context.md'])
allow.extend('native-green-01-output/'+sub+n for n in ['text-concepts-actual.json','text-concepts-390.png','text-concepts-1440.png'])
spec=importlib.util.spec_from_file_location('publication_scan',T/'scripts/check_publication.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
header=re.compile(rb'(?im)^\s*["\']?(authorization|proxy-authorization|cookie|set-cookie|x-csrf-token)["\']?\s*[:=]\s*[^\s,}]')
sensitive={'authorization','proxy-authorization','cookie','set-cookie','x-csrf-token','access-token','refresh-token','bootstrap-code','secret','headers','session-token'}
def json_fields(value,path=''):
 found=[]
 if isinstance(value,dict):
  for k,v in value.items():
   here=path+'/'+k
   if k.lower().replace('_','-') in sensitive:found.append(here)
   found.extend(json_fields(v,here))
 elif isinstance(value,list):
  for i,v in enumerate(value):found.extend(json_fields(v,path+'/'+str(i)))
 return found
raw_findings=[];failures=[];items=[]
for name in allow:
 raw=(P/name).read_bytes();virtual='progress/evidence/text-concept-native/'+name
 errors=mod.inspect(virtual,raw)
 if errors:raw_findings.append({'path':name,'sha256':h(raw),'rules':[i for i,v in enumerate(mod.SUSPECT) if re.search(v,raw)],'reasons':errors})
 candidate=raw
 if not name.endswith('.png'):
  candidate=re.sub(rb'<LOCAL_HOME>(?=$|/|[^A-Za-z0-9_.-])',b'<LOCAL_HOME>',candidate)
  candidate=re.sub(rb'<RUNNER_HOME>(?=$|/|[^A-Za-z0-9_.-])',b'<RUNNER_HOME>',candidate)
 fields=json_fields(json.loads(raw)) if name.endswith('.json') else []
 errs=mod.inspect(virtual,candidate)
 if errs or header.search(raw) or fields:failures.append({'path':name,'scanner':errs,'header_assignment':bool(header.search(raw)),'json_fields':fields})
 dest=P/'safe-share'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(candidate)
 items.append({'path':name,'raw_sha256':h(raw),'candidate_sha256':h(candidate),'raw_bytes':len(raw),'candidate_bytes':len(candidate)})
put('SCAN.json',{'scanner_sha256':h((T/'scripts/check_publication.py').read_bytes()),'raw_status':'FAIL' if raw_findings else 'PASS','raw_findings':raw_findings,'candidate_status':'FAIL' if failures else 'PASS','candidate_findings':failures,'scope':'Bounded repository scanner plus anchored header assignments and JSON field-name check. Paths/field names only, no matched values. Synthetic provenance and manual screenshot review separately documented.'})
assert not failures,failures
assert all(x['rules']==[5] for x in raw_findings)
put('SAFE_SHARE.json',{'scope':'Explicit private share candidate; not remote publication. Only listed files may be copied; raw originals preserved. Runtime DB/profile/tmp/output .last-run excluded.','transforms':[{'exact_prefix':'<LOCAL_HOME>','replacement':'<LOCAL_HOME>'},{'exact_prefix':'<RUNNER_HOME>','replacement':'<RUNNER_HOME>'}],'item_count':len(items),'candidate_directory':'safe-share','scan_sha256':h((P/'SCAN.json').read_bytes()),'items':items})
put('safe-share/SAFE_SHARE_MANIFEST.json',{'scope':'Exact-home-prefix-only derivative candidate with raw/candidate hashes, not publication','items':items})
raw_items=[]
for name in allow+['SCAN.json','SAFE_SHARE.json']:
 b=(P/name).read_bytes();raw_items.append({'path':name,'sha256':h(b),'bytes':len(b)})
put('MANIFEST.json',{'sealed_at':datetime.now(timezone.utc).isoformat(),'head':'814cda7f73e864af7a499c0486b4fe9bc46fccb9','status':'NATIVE_SLICE_PASS_NOT_FULL_GATE','items':raw_items})
(P/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in raw_items)+h((P/'MANIFEST.json').read_bytes())+'  MANIFEST.json\n')
assert all(h((P/x['path']).read_bytes())==x['sha256'] for x in raw_items)
assert all(h((P/'safe-share'/x['path']).read_bytes())==x['candidate_sha256'] for x in items)
for name in ['REPORT.md','MANIFEST.json','SAFE_SHARE.json','SHA256SUMS']:print(name,h((P/name).read_bytes()))
print(json.dumps({'explicit_raw_files':len(raw_items),'share_candidates':len(items),'raw_personal_path_findings':len(raw_findings),'candidate_status':'PASS'}))
