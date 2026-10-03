import hashlib,importlib.util,json,re
from pathlib import Path
E=Path(__file__).parent
T=Path('$HOME/.cache/learning-workbench-acceptance/m63-bootstrap-full-python-source-dcfda8c2-oct03')
def record(path):
 raw=path.read_bytes();return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
names=['REVIEW.md', 'receipt.json', 'SOURCE_MANIFEST.json', 'fixed-diff.patch', 'seal.py', 'fixed-source/apps/web/src/features/authoring/AuthoringForm.tsx', 'fixed-source/apps/web/src/features/authoring/AuthoringPanel.tsx', 'fixed-source/apps/web/src/features/authoring/LocalTaskDocument.test.tsx', 'fixed-source/apps/web/src/features/authoring/LocalTaskDocument.tsx', 'fixed-source/apps/web/src/features/authoring/useAuthoring.ts']
HEAD="d973e71f45909722f26d477358aee4d5d7141056"
for name in names: assert (E/name).is_file()
manifest={'head':HEAD,'review_scope':'STATIC_ONLY; no product execution credited','count':len(names),'files':{name:record(E/name) for name in names}}
write(E/'RAW_MANIFEST.json',manifest)
scanner_path=T/'progress/evidence/2026-09-28/M6.2-general-draft-fixed-gates/publication_scanner.py'
spec=importlib.util.spec_from_file_location('scanner',scanner_path);scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
public=E/'SAFE_SHARE';public.mkdir(exist_ok=False)
raw_findings=[];findings=[];entries=[]
secret_fields={'authorization','cookie','set-cookie','x-csrf-token','csrf_token','one_time_code','access_token','refresh_token','api_key','private_key','raw_response','receipt_json','description_json'}
def json_scan(name,data):
 if not name.endswith('.json'):return []
 out=[]
 def walk(node,path):
  if isinstance(node,dict):
   for key,value in node.items():
    if key.lower() in secret_fields:out.append(path+'/'+key)
    walk(value,path+'/'+key)
  elif isinstance(node,list):
   for i,value in enumerate(node):walk(value,path+'/'+str(i))
 walk(json.loads(data),'');return out
for name in names+['RAW_MANIFEST.json']:
 raw=(E/name).read_bytes();candidate=raw.replace(b'$HOME',b'$HOME')
 (public/name).parent.mkdir(parents=True,exist_ok=True)
 (public/name).write_bytes(candidate)
 logical='progress/evidence/M6.3-local-task-document-static-d973/'+name
 raw_findings.extend({'path':name,'reason':reason} for reason in scanner.inspect(logical,raw))
 findings.extend({'path':name,'reason':reason} for reason in scanner.inspect(logical,candidate))
 findings.extend({'path':name,'field':field,'reason':'sensitive JSON field'} for field in json_scan(name,candidate))
 # Only actual header-shaped log lines, not Python source identifiers.
 if name.endswith('.log'):
  for number,line in enumerate(candidate.decode(errors='replace').splitlines(),1):
   if re.match(r'^\s*(?:authorization|cookie|set-cookie|x-csrf-token)\s*:',line,re.I):
    findings.append({'path':name,'line':number,'reason':'HTTP credential header shape'})
 entries.append({'raw_path':name,'raw':record(E/name),'candidate_path':'SAFE_SHARE/'+name,'candidate':record(public/name),
                 'transform':'exact local-home prefix to $HOME only' if raw!=candidate else 'unchanged'})
write(E/'RAW_SCAN.json',{'status':'FAIL' if raw_findings else 'PASS','findings':raw_findings,'scanner':record(scanner_path)})
write(E/'CANDIDATE_SCAN.json',{'status':'FAIL' if findings else 'PASS','findings':findings,'scanner':record(scanner_path)})
write(E/'SAFE_SHARE.json',{'source_head':HEAD,'review_scope':'STATIC_ONLY','only_explicit_entries_authorized':True,'count':len(entries),
 'transform':'Exact local-home prefix replacement only; original files unchanged. No DB/ZIP/key/runtime/cache material authorized.',
 'entries':entries})
assert not findings,[(x['path'],x.get('field',x.get('reason'))) for x in findings]
for name,facts in manifest['files'].items():assert record(E/name)==facts
for entry in entries:assert record(E/entry['raw_path'])==entry['raw'] and record(E/entry['candidate_path'])==entry['candidate']
outer=['REVIEW.md','RAW_MANIFEST.json','SAFE_SHARE.json','RAW_SCAN.json','CANDIDATE_SCAN.json','receipt.json']
(E/'SHA256SUMS').write_text(''.join(record(E/name)['sha256']+'  '+name+'\n' for name in outer))
write(E/'PUBLIC_OUTER_ALLOWLIST.json',{'scope':'Explicit outer metadata in addition to SAFE_SHARE entries; no transformations required.',
 'files':{name:record(E/name) for name in ('SAFE_SHARE.json','RAW_SCAN.json','CANDIDATE_SCAN.json','SHA256SUMS')}})
print(json.dumps({'raw_count':len(names),'candidate_count':len(entries),'raw_findings':len(raw_findings),'candidate_findings':len(findings),
 'report':record(E/'REVIEW.md'),'raw_manifest':record(E/'RAW_MANIFEST.json'),'safe_share':record(E/'SAFE_SHARE.json')}))
