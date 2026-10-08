"""Offline exact-byte audit of the newly fetched 690 artifacts and root log originals."""
from pathlib import Path
import hashlib,json,re,subprocess
E=Path(__file__).resolve().parent
R=E.parent/'m63-v315-CI-terminal-690-oct04'
T=E.parent/'m63-turn-contract-dto-oct04'
head='69029bc1ab355efdbb6e0fdb8a86204c59cea71a';merge='6692d62db971b9b46cbf118efe6f26b4e0fd3b8c'
sha=lambda b:hashlib.sha256(b).hexdigest()
def facts(p):b=p.read_bytes();return {'sha256':sha(b),'bytes':len(b)}
def write(n,v):(E/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
commits={h:json.loads((R/(h+'.commit.raw.json')).read_text()) for h in [head,merge]}
assert commits[head]['tree']['sha']==commits[merge]['tree']['sha']==subprocess.check_output(['git','rev-parse',head+'^{tree}'],cwd=T,text=True).strip()
root=json.loads((R/'receipt-02.json').read_text());assert root['head']==head and len(root['jobs'])==12
source=[]
for name in ['.github/workflows/ci.yml','tests/e2e/restore-numeric.spec.ts','tests/e2e/single-publication.spec.ts']:
 b=subprocess.check_output(['git','show',head+':'+name],cwd=T);p=E/'source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 source.append({'path':name,'git_blob':subprocess.check_output(['git','rev-parse',head+':'+name],cwd=T,text=True).strip(),**facts(p)})
logs=[];numeric=[];runs=[];uploads=[];inputs={'receipt-02.json':facts(R/'receipt-02.json')}
for h in [head,merge]:inputs[h+'.commit.raw.json']=facts(R/(h+'.commit.raw.json'))
for run in [37170415116,37170416801]:
 d=E/str(run);meta=json.loads((d/'run.json').read_text());arts=json.loads((d/'artifacts.json').read_text())['artifacts'];old=json.loads((R/(str(run)+'.raw.json')).read_text())
 assert meta['head_sha']==head and meta['status']=='completed' and meta['conclusion']=='success' and meta['run_attempt']==1
 assert old['status']=='completed' and old['conclusion']=='success' and old['headSha']==head and len(old['jobs'])==6
 assert sorted((v['name'],v['conclusion']) for v in old['jobs'])==sorted([(n,'success') for n in ['backend','browser','integration','frontend','spec-contracts','security-publication']])
 inputs[str(run)+'.raw.json']=facts(R/(str(run)+'.raw.json'))
 runs.append({'run_id':run,'event':meta['event'],'head_sha':head,'status':meta['status'],'conclusion':meta['conclusion'],'attempt':meta['run_attempt'],'url':meta['html_url'],'run_metadata':facts(d/'run.json'),'artifact_metadata':facts(d/'artifacts.json')})
 for j in [j for j in root['jobs'] if j['run_id']==run]:
  name=f'{run}-{j["job"]}-api.log';p=R/name;b=p.read_bytes();assert sha(b)==j['log_sha256'];inputs[name]=facts(p)
  lines=b.decode().splitlines();mark=next(i for i,l in enumerate(lines) if 'git log -1 --format=%H' in l);checkout=lines[mark+1].split()[-1];assert checkout==(head if meta['event']=='push' else merge)==j['checkout']
  logs.append({'run_id':run,'job_id':j['job_id'],'job':j['job'],'log_file':name,**facts(p),'checkout':checkout,'checkout_line':mark+2})
  if j['job']=='browser':
   for a in arts:
    line=next(i+1 for i,l in enumerate(lines) if f"Artifact ID {a['id']}" in l and 'successfully finalized' in l)
    digest_line=next(i+1 for i,l in enumerate(lines) if a['digest'].removeprefix('sha256:') in l)
    uploads.append({'run_id':run,'artifact_id':a['id'],'artifact_name':a['name'],'finalized_log_line':line,'digest_log_line':digest_line,'browser_log_sha256':sha(b)})
 assert len(arts)==2
 for a in arts:
  path=d/f'artifact-{a["id"]}';tr=json.loads((path/'transport-receipt.json').read_text())
  assert tr['strict_member_validation']=='PASS' and tr['archive_transport_sha256']==a['digest'].split(':')[1] and tr['archive_transport_bytes']==a['size_in_bytes']
  assert a['workflow_run']['id']==run and a['workflow_run']['head_sha']==head and not a['expired']
  vals={m['basename']:json.loads((path/m['basename']).read_text()) for m in tr['members']}
  for m in tr['members']:assert facts(path/m['basename'])=={'sha256':m['sha256'],'bytes':m['bytes']}
  if 'restore-numeric-actual.json' in vals:
   v=vals['restore-numeric-actual.json'];assert vals['actual-publication-response.json']=={k:v[k] for k in ['actual','reviewJob','publishOutcome']};kind='Restore';out=v['publishOutcome'];ack=v['decision'];assert v['newModelCalls']==0
  else:
   v=vals['single-publication-actual.json'];kind='Single';out=v['outcome'];ack=v['numericAck']
   assert v['stage']=='closed_chain' and v['physicalNumeric']=='BLOCKED' and v['published'] is None and v['finalDraft']['state']=='draft' and v['finalDraft']['published_ref'] is None and v['externalModelCalls']==0 and v['loopbackCalls']==1 and v['writes']==[]
  result=v['actual']['result']
  assert result['outcome']=='environment_unavailable' and result['verdict']=='BLOCKED' and result['exit_code']==1 and result['assertions']==[] and result['output_sha256'] is None
  assert v['actual']['job']['status']=='failed' and result['job_id']==v['actual']['job']['id']==ack['job']['id'] and result['operation_sha256']==v['actual']['operation_sha256']
  assert out['status']==409 and out['body']['error']['code']=='PUBLISH_NUMERIC_REQUIRED' and v['errors']==[]
  numeric.append({'run_id':run,'kind':kind,'artifact_id':a['id'],'archive_digest':a['digest'],'archive_bytes':a['size_in_bytes'],'members':tr['members'],'outcome':result['outcome'],'verdict':result['verdict'],'exit_code':result['exit_code'],'assertions_count':0,'output_sha256':None,'result_sha256':result['result_sha256'],'job_status':'failed','publication_status':409,'publication_error':'PUBLISH_NUMERIC_REQUIRED','external_model_calls':0,'loopback_calls':v.get('loopbackCalls'),'published':False})
write('SOURCE_BINDINGS.json',{'source_head':head,'pr_checkout':merge,'common_tree':commits[head]['tree']['sha'],'source_files':source,'inherited_root_input_hashes':inputs,'independently_read_checkout_logs':logs,'artifact_upload_log_bindings':uploads,'boundary':'Root originals read only; no raw logs copied into this package; no product execution.'})
write('AUDIT.json',{'status':'READBACK_PASS','runs':runs,'numeric':numeric,'archive_count':4,'json_count':6,'physical_numeric':'4 BLOCKED, 0 PASS; publication refused in all four','no_fallback':'The observed terminal DTOs retain failed/environment_unavailable/BLOCKED and 409; no synthetic PASS substitutes for them. This is not a universal absence-of-fallback proof.','whole_ci':'Both completed SUCCESS; actual logs bind all12 job checkouts to the same source tree. CI green is separate from physical numeric status.','no_product_execution':True,'no_remote_mutation':True,'no_zip_saved':True,'original_failures_unchanged':True})
write('COLLECTION_HISTORY.json',{'metadata_gets':4,'artifact_gets':4,'archive_files_saved':0,'collection_errors':[],'reused_method':'4ecc bounded gh api GET and memory ZIP collector; actual IDs and contents are exclusively690','original_collector_hashes':{n:facts(E.parent/'m63-4ecc-numeric-artifacts-oct04'/n) for n in ['bounded_api.py','COLLECT_ARTIFACTS.py']},'root_failed_empty_log_collection':'Preserved in root package; direct API log bytes supplied source binding.','product_execution':False,'ci_rerun':False,'credential_or_environment_read':False})
print(json.dumps({'status':'READBACK_PASS','runs':2,'actual_log_checkouts':len(logs),'artifact_uploads':len(uploads),'json_files':6,'physical_BLOCKED':4,'publication_409':4}))
