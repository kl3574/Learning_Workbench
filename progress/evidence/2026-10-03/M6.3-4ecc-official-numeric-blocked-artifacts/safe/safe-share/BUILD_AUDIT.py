"""Offline projection of the already fetched approved artifacts and browser logs."""
from pathlib import Path
import hashlib,json,re,subprocess,datetime
E=Path(__file__).resolve().parent;R=E.parent/'m62-public-safe-oct02';sha=lambda b:hashlib.sha256(b).hexdigest()
head='4ecc27a883782855a6e5611d7610979e4b4b05ca';merge='339d5a61f9be9a8306b1a6851286c765c6aeb21e';commits={x:json.loads((E/(x+'-commit.json')).read_text()) for x in [head,merge]}
assert commits[head]['tree']['sha']==commits[merge]['tree']['sha']==subprocess.check_output(['git','rev-parse',head+'^{tree}'],cwd=R,text=True).strip()
source=[]
for name in ['.github/workflows/ci.yml','tests/e2e/restore-numeric.spec.ts','tests/e2e/single-publication.spec.ts']:
 b=subprocess.check_output(['git','show',head+':'+name],cwd=R);dest=E/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
 source.append(dict(path=name,git_blob=subprocess.check_output(['git','rev-parse',head+':'+name],cwd=R,text=True).strip(),sha256=sha(b),bytes=len(b)))
runs=[];logs=[];numeric=[]
for run in [37165685426,37165687627]:
 d=E/str(run);meta=json.loads((d/'run.json').read_text());jobs=json.loads((d/'jobs.json').read_text())['jobs'];artifacts=json.loads((d/'artifacts.json').read_text())['artifacts']
 assert meta['head_sha']==head and meta['conclusion']=='success' and meta['status']=='completed' and len(jobs)==6
 assert sorted((v['name'],v['conclusion']) for v in jobs)==sorted([(n,'success') for n in ['backend','browser','integration','frontend','spec-contracts','security-publication']])
 runs.append(dict(id=run,event=meta['event'],status=meta['status'],conclusion=meta['conclusion'],head_sha=head,attempt=meta['run_attempt'],url=meta['html_url'],metadata_sha256=sha((d/'run.json').read_bytes()),metadata_captured_utc=json.loads((d/'run-invocation.json').read_text())['captured_utc'],jobs=[{k:j[k] for k in ['id','name','status','conclusion','html_url']} for j in jobs]))
 for name in ['browser']:
  p=d/'browser-private.log';b=p.read_bytes();lines=b.decode().splitlines();marker=next(i for i,l in enumerate(lines) if 'git log -1 --format=%H' in l);checkout=lines[marker+1].split()[-1];assert checkout==(head if meta['event']=='push' else merge)
  summary=next((i+1,l) for i,l in enumerate(lines) if re.search(r'\b[0-9]+ passed \(',l));passed=int(re.search(r'\b([0-9]+) passed \(',summary[1]).group(1))
  skip=[dict(line=i+1,code='BLOCKED_ENVIRONMENT',detail=l.split('BLOCKED_ENVIRONMENT:',1)[1].strip()) for i,l in enumerate(lines) if 'BLOCKED_ENVIRONMENT:' in l]
  upload=[]
  if name=='browser':
   for art in artifacts:
    n=next(i for i,l in enumerate(lines) if f"Artifact ID {art['id']}" in l and 'successfully finalized' in l)
    upload.append(dict(artifact_id=art['id'],name=art['name'],line=n+1,metadata_bytes=art['size_in_bytes']))
  logs.append(dict(origin='official job log GET; private raw log',file=str(p.relative_to(E)),sha256=sha(b),bytes=len(b),job_id=next(j['id'] for j in jobs if j['name']==name),checkout_sha=checkout,checkout_line=marker+2,tree_sha=commits[checkout]['tree']['sha'],summary_line=summary[0],passed=passed,skip_evidence=skip,artifact_uploads=upload))
 for art in artifacts:
  a=d/f'artifact-{art["id"]}';transport=json.loads((a/'transport-receipt.json').read_text());assert transport['strict_member_validation']=='PASS' and transport['archive_transport_sha256']==art['digest'].split(':')[1] and transport['archive_transport_bytes']==art['size_in_bytes']
  values={m['basename']:json.loads((a/m['basename']).read_text()) for m in transport['members']}
  if 'restore-numeric-actual.json' in values:
   v=values['restore-numeric-actual.json'];short=values['actual-publication-response.json'];assert short=={k:v[k] for k in ['actual','reviewJob','publishOutcome']};kind='Restore';out=v['publishOutcome'];ack=v['decision'];assert v['newModelCalls']==0
  else:
   v=values['single-publication-actual.json'];kind='Single';out=v['outcome'];ack=v['numericAck'];assert v['stage']=='closed_chain' and v['physicalNumeric']=='BLOCKED' and v['published'] is None and v['finalDraft']['state']=='draft' and v['finalDraft']['published_ref'] is None and v['externalModelCalls']==0 and v['loopbackCalls']==1
  result=v['actual']['result'];assert result['outcome']=='environment_unavailable' and result['verdict']=='BLOCKED' and result['exit_code']==1 and result['assertions']==[] and result['output_sha256'] is None
  assert v['actual']['job']['status']=='failed' and result['job_id']==v['actual']['job']['id']==ack['job']['id'] and result['operation_sha256']==v['actual']['operation_sha256']
  assert out['status']==409 and out['body']['error']['code']=='PUBLISH_NUMERIC_REQUIRED' and v['errors']==[]
  numeric.append(dict(run_id=run,kind=kind,artifact_id=art['id'],stage=v.get('stage','after_browser_publication_assertions'),numeric_outcome=result['outcome'],numeric_verdict=result['verdict'],exit_code=result['exit_code'],assertions_count=0,output_sha256=None,result_sha256=result['result_sha256'],job_status=v['actual']['job']['status'],publication_status=out['status'],publication_code=out['body']['error']['code'],external_model_calls=v.get('externalModelCalls',v.get('newModelCalls')),loopback_calls=v.get('loopbackCalls'),published=False,raw_files=transport['members']))
(E/'SOURCE_BINDINGS.json').write_text(json.dumps(dict(head_sha=head,push_checkout=head,pr_checkout=merge,common_tree=commits[head]['tree']['sha'],official_commit_metadata=[dict(sha=x,tree=commits[x]['tree']['sha'],parents=[p['sha'] for p in commits[x]['parents']],raw_metadata_sha256=sha((E/(x+'-commit.json')).read_bytes())) for x in [head,merge]],source_files=source,actual_checkout_logs_verified=2,remaining_job_checkouts='not independently read; job terminal statuses from official metadata only',log_directory='.',logs=logs),ensure_ascii=False,indent=2)+'\n')
(E/'AUDIT.json').write_text(json.dumps(dict(status='READBACK_PASS',whole_ci='SUCCESS in both runs; numeric and publication facts are reported separately',runs=runs,numeric=numeric,physical_numeric='BLOCKED, four actual executions; zero PASS',cli_availability='NOT_ATTESTED by these three allowed JSON basenames; browser green does not establish installed/supported/ready CLI',external_model_calls=0,collection_only=True),ensure_ascii=False,indent=2)+'\n')
(E/'COLLECTION_HISTORY.json').write_text(json.dumps(dict(metadata='Six gh api GETs saved exact stdout and invocation receipts; no auth/env print or account query.',artifacts='Saved producer COLLECT_ARTIFACTS.py executed once. Four bounded GET archive transports, six approved JSON dictionaries, no ZIP archive persisted.',commits='Two official Git commit GETs and two exact successful browser job log GETs; no Git fetch/worktree mutation.',collection_errors=[],no_product_execution=True,no_ci_rerun=True,no_remote_mutation=True),indent=2)+'\n')
print(json.dumps(dict(status='READBACK_PASS',runs=2,jobs=12,backend_failures=0,artifacts=4,json_files=6,actual_checkout_logs=2,tree_equal=True,physical_numeric_blocked=4,publication_409=4)))
