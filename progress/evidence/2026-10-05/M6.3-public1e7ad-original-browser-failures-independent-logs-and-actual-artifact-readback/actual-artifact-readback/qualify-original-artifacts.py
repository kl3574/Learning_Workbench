from pathlib import Path
import json,hashlib,zipfile
O=Path(__file__).resolve().parent;C=O.parent/'m63-ci-public1e7ad-observation-oct05'
def sha(b):return hashlib.sha256(b).hexdigest()
inv=json.loads((O/'ORIGINAL_ARTIFACT_INVENTORY.json').read_bytes());assert inv['original_artifact_count']==6
numeric=[];timing=[];jobs=set();artifact_rows=[]
for a in inv['records']:
 aid=a['artifact_id'];raw=(O/f'artifact-{aid}-zip-01.zip').read_bytes();assert len(raw)==a['original_zip_size'] and sha(raw)==a['original_zip_sha256']
 z=zipfile.ZipFile(O/f'artifact-{aid}-zip-01.zip');assert {n for n in z.namelist() if not n.endswith('/')}=={m['path'] for m in a['members']}
 for m in a['members']:
  b=z.read(m['path']);assert len(b)==m['size'] and sha(b)==m['sha256']
  if m['path'].endswith(('actual-publication-response.json','restore-numeric-actual.json','single-publication-actual.json')):
   d=json.loads(b);act=d['actual'];out=d.get('publishOutcome',d.get('outcome'));r=act['result'];job=act['job'];assert job['status']=='failed' and r['job_id']==job['id'] and r['outcome']=='environment_unavailable' and r['verdict']=='BLOCKED' and r['exit_code']==1 and r['assertions']==[]
   assert out['status']==409 and out['body']['error']['code']=='PUBLISH_NUMERIC_REQUIRED';jobs.add(job['id'])
   bound=d.get('bound',d.get('finalDraft'));assert bound is None or bound['state']=='draft' and bound['published_ref'] is None
   numeric.append({'run_id':a['run_id'],'artifact_id':aid,'member':m['path'],'raw_size':len(b),'raw_sha256':sha(b),'job_id':job['id'],'job_status':job['status'],'job_revision':act.get('job_revision','ABSENT'),'decision':act['decision'],'result':r,'publication_http':out['status'],'publication_error':out['body']['error']['code'],'state':bound['state'] if bound else 'ABSENT','published_ref':bound['published_ref'] if bound else 'ABSENT','actual_external_model_calls':d.get('newModelCalls',d.get('externalModelCalls','ABSENT')),'loopback_calls':d.get('loopbackCalls','ABSENT'),'physical_numeric':d.get('physicalNumeric','ABSENT')})
  if m['path'].endswith('review-history-timing.json'):
   d=json.loads(b);assert d['observed_timeout_ms']==30000 and d['retry']==0 and d['limits']=={'phases':128,'http':512} and d['dropped']=={'phases':0,'http':0}
   seq=sorted([x['sequence'] for x in d['phases']]+[x['sequence'] for x in d['http']]);assert seq==list(range(1,len(seq)+1))
   allowed={'sequence','elapsed_ms','event','route','method','status','request_elapsed_ms'}
   assert all(set(x)<=allowed for x in d['http']) and all(set(x)=={'sequence','elapsed_ms','stage'} for x in d['phases'])
   final=d['phases'][-1];assert final['stage']=='body-finally'
   path='original-review-timing-'+str(a['run_id'])+'.json';(O/path).write_bytes(b)
   timing.append({'run_id':a['run_id'],'artifact_id':aid,'member':m['path'],'original_size':len(b),'original_sha256':sha(b),'published_candidate':path,'phase_count':len(d['phases']),'HTTP_metadata_count':len(d['http']),'last_phase_before_finally':d['phases'][-2],'body_finally_elapsed_ms':final['elapsed_ms'],'limits':d['limits'],'dropped':d['dropped'],'observed_whole_test_timeout_ms':30000,'retry':0,'qualification':'Actual body-only Node monotonic marks; fixture/setup/page.request polling and React/JSON completion not captured; no cause inferred from final phase'})
 artifact_rows.append({'run_id':a['run_id'],'artifact_id':aid,'name':a['artifact_name'],'actual_zip_size':a['original_zip_size'],'actual_zip_sha256':a['original_zip_sha256'],'all_members_size_sha_exact':True,'member_count':len(a['members']),'ZIP_or_PNG_public_admission':False})
assert len(numeric)==6 and len(jobs)==4 and len(timing)==2
snapshot_path=sorted(C.glob('*-SNAPSHOT.json'))[-1];snapshot=json.loads(snapshot_path.read_bytes());steps=[]
for event in snapshot['actual_events']:
 jobs_data=json.loads((C/(f"{snapshot['sequence']:02d}-jobs-{event['id']}.stdout")).read_bytes())
 browser=next(j for j in jobs_data['jobs'] if j['name']=='browser');assert browser['conclusion']=='failure'
 retain=[s for s in browser['steps'] if s['name'].startswith('Retain ')];assert len(retain)==3 and all(s['conclusion']=='success' for s in retain)
 steps.append({'run_id':event['id'],'job_id':browser['id'],'original_conclusion':browser['conclusion'],'retention_steps':[{k:s[k] for k in ['name','number','status','conclusion','started_at','completed_at']} for s in retain]})
git=json.loads((O/'ACTUAL_FIXED_GIT_TREE_READBACK.json').read_bytes())
report={'role':'Root actual original artifact bytes/content qualification; no rerun or root-cause claim','public_head':git['public_head'],'actual_fixed_checkout_git_tree':git,'original_artifacts':artifact_rows,'original_retention_steps':steps,'numeric_records':numeric,'numeric_dto_count':6,'logical_job_descriptor_count':4,'count_limits':'Six DTOs repeat four logical Job records; not executions/process counts. Missing fields remain ABSENT, not zero. approve_once is intent, not numerical PASS.','actual_review_timing':timing,'actual_images_inspected':'Root inspected both original Review PNGs privately; no alteration/publicPNGadmission, no proof of hidden causality','failure_facts':'PR authoring definite Vite port40581 bindcollision before readiness; PR Review URLreader pollfalse; push grading revision3vs0; push Review mobile heading contextclosed; sameReview case different sites/global30sec unchanged','whole_original_runs':'Integration stillrunning at qualification snapshot; eachbrowser131PASS2FAIL and four otherjobSUCCESS do not establish whole-runPASS','snapshot':{'sequence':snapshot['sequence'],'observed_utc':snapshot['observed_utc'],'sha256':sha(snapshot_path.read_bytes())},'original_CI_before_after_working_input_maps':'NOT_CAPTURED','physical_numeric':'BLOCKED_ENVIRONMENT; no successful calculator or published content/fallback','real_provider_codex':'NOT_RUN; no sourceproof/runtime registration or realkey call','wholeM6_3_AC21_M7':'NOT_ACCEPTED','public_excluded':'All6 ZIPs/allPNG/error-context/othermemberpayloads/rawAPIidentity; only explicit metadata/numericprojection/two privacy boundedtimingJSON considered'}
(O/'ORIGINAL_ARTIFACT_CONTENT_READBACK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'artifacts':6,'numeric_DTOs':6,'logical_job_records':4,'actual_failure_upload_steps':'SUCCESS_BOTH','timings':[(x['run_id'],x['phase_count'],x['HTTP_metadata_count']) for x in timing],'same_actual_checkout_tree':git['actual_tree'],'wholeM6_3':'NOT_ACCEPTED'}))
