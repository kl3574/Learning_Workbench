from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib
BASE=Path(__file__).resolve().parent;RAW=BASE.parent/'m62-publication-http-development-v1';WORK=BASE.parent/'m62-publication-http-active'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
selected=[];runs=[];tree_cache={};blobids=set()
def tree(commit):
 if commit not in tree_cache:
  rows={}
  for entry in subprocess.check_output(['git','ls-tree','-r','-z',commit],cwd=WORK).split(b'\0'):
   if not entry:continue
   meta,path=entry.split(b'\t',1);mode,kind,blob=meta.split()
   if kind==b'blob':rows[path.decode()]=(mode.decode(),blob.decode())
  tree_cache[commit]=rows
 return tree_cache[commit]
for name in ['red','generation','http','contracts','mypy','http-final','review-http','ruff','spec','web-types','web-types-final']:
 p=RAW/name;receipt=read(p/'receipt.json');logfile='run.log' if name=='generation' else 'test.log';log=(p/logfile).read_bytes();assert sha(log)==receipt['log_sha256']
 if 'log_bytes' in receipt:assert len(log)==receipt['log_bytes']
 members=['receipt.json',logfile]
 if name!='generation':
  before=read(p/'inputs-before.json');after=read(p/'inputs-after.json');assert before==after and len(before)==receipt['source_count'] and receipt['source_unchanged']
  assert receipt['all_source_matches_git_before'] and receipt['all_source_matches_git_after'] and not receipt['timeout']
  actual=tree(receipt['code_commit'])
  for row in before:
   assert actual[row['path']]==(row['git_mode'],row['git_blob_sha1']) and row['git_matches'];blobids.add(row['git_blob_sha1'])
  runs.append({'stage':name,'receipt':receipt,'before':before});members+=['inputs-before.json','inputs-after.json']
 else:runs.append({'stage':name,'receipt':receipt,'before':None})
 for n in members:
  b=(p/n).read_bytes();selected.append({'path':name+'/'+n,'bytes':len(b),'sha256':sha(b)})
for n in ['run.py','run_integrated.py','run_final.py','run_types.py','local-node-setup.json']:
 b=(RAW/n).read_bytes();selected.append({'path':n,'bytes':len(b),'sha256':sha(b)})
runners={row['sha256'] for row in selected if row['path'].startswith('run')}
for row in runs:
 if 'runner_sha256' in row['receipt']:assert row['receipt']['runner_sha256'] in runners
source_sets={label:read(BASE/label/'source-pins.json') for label in ['preliminary','final']}
for label,pins in source_sets.items():
 actual=tree(pins['head'])
 for row in pins['files']:
  data=(BASE/label/'source'/row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
  assert actual[row['path']][1]==row['git_blob'];blobids.add(row['git_blob'])
proc=subprocess.run(['git','cat-file','--batch'],input=('\n'.join(sorted(blobids))+'\n').encode(),capture_output=True,cwd=WORK,check=True);cursor=0;blobs={}
for oid in sorted(blobids):
 end=proc.stdout.index(b'\n',cursor);header=proc.stdout[cursor:end].split();size=int(header[2]);data=proc.stdout[end+1:end+size+1]
 assert header[0].decode()==oid and header[1]==b'blob' and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()==oid
 blobs[oid]={'bytes':size,'sha256':sha(data)};cursor=end+size+2
assert cursor==len(proc.stdout)
summary=[]
for row in runs:
 receipt=row['receipt'];before=row['before']
 if before is not None:
  for r in before:assert blobs[r['git_blob_sha1']]=={'bytes':r['bytes'],'sha256':r['sha256']}
 summary.append({'stage':row['stage'],'code_commit':receipt.get('code_commit',receipt.get('head_before_generation')),'exit_code':receipt['exit_code'],'input_count':len(before) if before is not None else None,'actual_git_and_before_after_verified':before is not None,'log_sha256':receipt['log_sha256']})
for label,pins in source_sets.items():
 for row in pins['files']:assert blobs[row['git_blob']]=={'bytes':row['bytes'],'sha256':row['sha256']}
old={r['path']:r for r in source_sets['preliminary']['files']};changes=[r['path'] for r in source_sets['final']['files'] if r['sha256']!=old[r['path']]['sha256']];assert changes==['tests/integration/test_draft_publication_http.py']
for label,pins in source_sets.items():
 projection=read(BASE/label/'source/packages/contracts/generated/openapi.json');previous=json.loads(subprocess.check_output(['git','show',pins['baseline']+':packages/contracts/generated/openapi.json'],cwd=WORK))
 assert projection['paths'].keys()-previous['paths'].keys()=={'/api/v1/drafts/{id}/publish'}
 assert all(v==projection['paths'][k] for k,v in previous['paths'].items())
 assert projection['components']['schemas'].keys()-previous['components']['schemas'].keys()=={'DraftPublishWrite'}
 assert all(v==projection['components']['schemas'][k] for k,v in previous['components']['schemas'].items())
 request=projection['components']['schemas']['DraftPublishWrite'];assert request['additionalProperties'] is False and set(request['required'])==set(request['properties'])=={'expected_revision','expected_content_sha256','review_receipt_id','acknowledged_warning_codes'}
setup=read(RAW/'local-node-setup.json');lock=tree(source_sets['final']['head'])['apps/web/package-lock.json'][1];assert blobs[lock]['sha256']==setup['package_lock_sha256']
(BASE/'OWNER_EVIDENCE_BINDINGS.json').write_text(json.dumps({'scope':'Only the 47 enumerated completed original run and runner/setup records. Later owner reports or package files are not claimed reviewed.','files':selected},indent=2)+'\n')
result={'verified_at':datetime.now(timezone.utc).isoformat(),'final_commit':source_sets['final']['head'],'baseline':source_sets['final']['baseline'],'independent_source_files_per_snapshot':18,'changed_scope_files':8,'delta_after_preliminary':changes,'owner_original_files_verified':len(selected),'actual_git_blobs_read':len(blobs),'fixed_gate_stages_verified':10,'generation_observation':'Original generation receipt/log hash checked separately; generation intentionally changed four artifacts and had no before/after manifests.','stages':summary,'projection':'Only one path/one closed schema added; existing paths/schemas identical at both reviewed commits.','product_tests_executed':[],'result':'PASS'}
(BASE/'VERIFY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
