"""Explicit safe evidence selection; never traverse test databases or Broker state."""
import hashlib,importlib.util,json,re,subprocess
from pathlib import Path
ROOT=Path('$HOME/.cache/learning-workbench-acceptance/m63-local-session-bootstrap-implementation-oct03')
E=Path(__file__).parent
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head=='df0bc6188745cf96aed4b68e52737dab492758d4'
assert subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)==b''
def entry(path):
 raw=path.read_bytes();return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
raw=set((E/'stages').rglob('*'))|set((E/'snapshots').rglob('*'))
raw={p for p in raw if p.is_file()}
raw.update(E/name for name in ('REPORT.md','run_stage.py','run_tail_stage.py','actual_control_32.py','actual_control_33.py',
 'actual_control_34.py','actual_control_45.py','offline_schema_36.py','legacy_actual_47.py','legacy-actual-47.json',
 '37-harness-source.py','38-runtime-red-probe.py','43-harness-source.py','seal_evidence.py'))
raw.update(E/f'actual-{number}/actual.json' for number in (32,33,34,45))
raw.update(E/'offline-schema-36'/name for name in ('receipt.json','launcher.py'))
# Schema-only files are an explicit engineering source set, not a Broker copy.
raw.update((E/'offline-schema-36/broker/schemas').rglob('*.json'))
assert all(p.is_file() for p in raw)
for p in raw:
 assert p.suffix not in {'.db','.sqlite','.sqlite3','.zip','.key','.pem','.token'}
 assert 'private-workspace' not in p.parts and 'private-temp' not in p.parts
manifest={'source_head':head,'spec_sha256':'bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144',
 'scope':'explicit logs, source/input bindings, selected actual public views, ordinary probes and offline schema-only export; no runtime DB, key, global configuration or raw control responses',
 'files':{str(p.relative_to(E)):entry(p) for p in sorted(raw)}}
write(E/'RAW_MANIFEST.json',manifest)
# Select final reproducible boundaries plus every original failure/run log.
candidates={E/'REPORT.md',E/'RAW_MANIFEST.json'}
candidates.update(p for p in raw if p.parent==E and p.suffix in {'.py','.json'})
candidates.update(p for p in raw if p.is_relative_to(E/'snapshots'))
candidates.update(p for p in raw if p.is_relative_to(E/'stages') and (p.suffix=='.log' or p.name=='result.json'))
candidates.update(p for p in raw if p.is_relative_to(E/'stages/10-failed-source'))
for stage in ('20-tail-original-red','31-fixed-focused','36-offline-experimental-schemas','38-upstream-shape-red',
 '39-upstream-shape-green','45-actual-profile-v3-control','47-real-unknown-readback','48-final-focused',
 '49-final-ruff','50-final-mypy','51-final-verify'):
 for name in ('before.json','after.json'):
  p=E/'stages'/stage/name
  assert p.is_file(),p
  candidates.add(p)
candidates.add(E/'actual-45/actual.json')
candidates.update(E/'offline-schema-36'/name for name in ('receipt.json','launcher.py'))
public=E/'SAFE_SHARE';public.mkdir(exist_ok=False)
scanner_path=ROOT/'progress/evidence/2026-09-28/M6.2-general-draft-fixed-gates/publication_scanner.py'
spec=importlib.util.spec_from_file_location('publication_scanner',scanner_path)
scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
raw_findings=[];candidate_findings=[];entries=[]
secret_fields={'authorization','cookie','set-cookie','x-csrf-token','csrf_token','one_time_code','access_token','refresh_token','api_key','private_key','raw_response','receipt_json','description_json'}
def json_fields(path,data):
 if path.suffix!='.json':return []
 try:value=json.loads(data)
 except Exception:return ['invalid JSON']
 findings=[]
 def walk(node,where):
  if isinstance(node,dict):
   for key,item in node.items():
    field=str(key).lower()
    if field in secret_fields:findings.append(where+'/'+str(key))
    walk(item,where+'/'+str(key))
  elif isinstance(node,list):
   for index,item in enumerate(node):walk(item,where+'/'+str(index))
 walk(value,'')
 return findings
for p in sorted(candidates):
 name=str(p.relative_to(E));original=p.read_bytes();safe=original.replace(b'$HOME',b'$HOME')
 dest=public/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(safe)
 logical='progress/evidence/M6.3-local-bootstrap/'+name
 raw_findings.extend({'path':name,'reason':reason} for reason in scanner.inspect(logical,original))
 candidate_findings.extend({'path':name,'reason':reason} for reason in scanner.inspect(logical,safe))
 candidate_findings.extend({'path':name,'field':field,'reason':'sensitive JSON field'} for field in json_fields(p,safe))
 entries.append({'raw_path':name,'raw':entry(p),'candidate_path':'SAFE_SHARE/'+name,'candidate':entry(dest),
                 'transform':'exact $HOME -> $HOME' if safe!=original else 'unchanged'})
write(E/'RAW_SCAN.json',{'status':'FAIL' if raw_findings else 'PASS','findings':raw_findings,
 'scope':'selected candidates only; field/path/reason output, never values','scanner':entry(scanner_path)})
write(E/'CANDIDATE_SCAN.json',{'status':'FAIL' if candidate_findings else 'PASS','findings':candidate_findings,
 'scope':'explicit share candidates; credential/path patterns and exact sensitive JSON field names; not arbitrary-prose guarantee',
 'scanner':entry(scanner_path)})
write(E/'SAFE_SHARE.json',{'source_head':head,'transform':'Only exact byte prefix $HOME -> $HOME; originals unchanged',
 'only_explicit_entries_authorized':True,'count':len(entries),'entries':entries,
 'excluded':'all DB/key/ZIP/runtime state, complete private frozen operations, raw account/thread responses and nonselected offline schemas',
 'raw_manifest':entry(E/'RAW_MANIFEST.json'),'candidate_scan':entry(E/'CANDIDATE_SCAN.json')})
assert not candidate_findings,[(x['path'],x.get('field',x.get('reason'))) for x in candidate_findings]
# Validate every raw and candidate once more. Write sums last; no later edits.
for name,facts in manifest['files'].items():assert entry(E/name)==facts
for row in entries:assert entry(E/row['raw_path'])==row['raw'] and entry(E/row['candidate_path'])==row['candidate']
meta=('RAW_MANIFEST.json','SAFE_SHARE.json','RAW_SCAN.json','CANDIDATE_SCAN.json','REPORT.md')
(E/'SHA256SUMS').write_text(''.join(entry(E/name)['sha256']+'  '+name+'\n' for name in meta))
print(json.dumps({'raw_count':len(raw),'candidate_count':len(entries),'raw_findings':len(raw_findings),'candidate_findings':len(candidate_findings),
                 'report':entry(E/'REPORT.md'),'raw_manifest':entry(E/'RAW_MANIFEST.json'),'safe_share':entry(E/'SAFE_SHARE.json')}))
