import datetime,hashlib,importlib.util,json,subprocess
from pathlib import Path
O=Path(__file__).parent; B=O.parent;R=B/'m62-public-safe-oct02';A=B/'m63-native-formal-79acabc2-oct04';T=B/'m63-native-formal-79ac-owner-oct04'
sha=lambda b:hashlib.sha256(b).hexdigest()
def j(p):return json.loads(p.read_bytes())
spec=importlib.util.spec_from_file_location('publication_check',R/'scripts/check_publication.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
allow=j(A/'publication-candidates/allowlist.json');assert allow['count']==25 and len(allow['files'])==25
assert sha((A/'publication-candidates/allowlist.json').read_bytes())=='375fe7b3e487c6be8bfa1694863cc81fe4ed8005a74bf582cfe7852996f1d122'
for item in allow['files']:
 raw=(A/item['source']).read_bytes();cand=(A/'publication-candidates'/item['candidate']).read_bytes()
 assert sha(raw)==item['raw_sha256'] and sha(cand)==item['candidate_sha256']
 assert len(raw)==item['raw_bytes'] and len(cand)==item['candidate_bytes']
 assert cand==(raw if item['transformation']=='byte-identical PNG' else raw.replace(b'$HOME',b'<LOCAL_HOME>'))
 assert not module.inspect('progress/evidence/M6.3-native79ac/'+item['candidate'],cand)
for name,desc in j(A/'FINAL_BINDING.json')['raw_files'].items():
 raw=(A/name).read_bytes();assert sha(raw)==desc['sha256'] and len(raw)==desc['bytes']
before=j(A/'inputs-before.json');after=j(A/'inputs-after.json');head=before['head'];assert head==after['head']=='79acabc2566318f9ea099da067abd7e9c4f010a2'
assert before['count']==after['count']==1465 and before['all_match_git'] and not after['all_match_git']
tree={}
for line in filter(None,subprocess.check_output(['git','ls-tree','-r','-z',head],cwd=R).split(b'\0')):
 meta,path=line.split(b'\t',1);mode,kind,oid=meta.split();path=path.decode()
 if not path.startswith('progress/'):
  assert kind==b'blob';tree[path]=oid.decode()
assert len(tree)==1465
raw=subprocess.check_output(['git','cat-file','--batch'],cwd=R,input=('\n'.join(tree.values())+'\n').encode());offset=0;digests={}
for oid in tree.values():
 end=raw.index(b'\n',offset);header=raw[offset:end].split();size=int(header[2]);assert header[:2]==[oid.encode(),b'blob']
 data=raw[end+1:end+1+size];assert len(data)==size;digests[oid]=sha(data);offset=end+size+2
assert offset==len(raw)
first={x['path']:x for x in before['files']};last={x['path']:x for x in after['files']};assert len(first)==len(last)==1465 and set(first)==set(last)==set(tree)
changed=[]
for path,oid in tree.items():
 x,y=first[path],last[path];assert x['git_blob']==y['git_blob']==oid and x['actual_blob']==oid and x['matches_git'] and x['sha256']==digests[oid]
 data=(T/path).read_bytes();actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 assert y['sha256']==sha(data) and y['actual_blob']==actual and y['matches_git']==(actual==oid)
 if x['sha256']!=y['sha256']:changed.append(path)
generated=j(A/'generated-output-paths.json')['paths'];assert len(generated)==10 and len(set(generated))==10
assert set(changed)==set(j(A/'receipt.json')['actual_generated_output_changes']) and len(changed)==5 and set(changed)<=set(generated)
for path in generated:
 name=Path(path).name
 assert sha((A/'generated-before'/name).read_bytes())==first[path]['sha256']
 assert sha((A/'generated-after'/name).read_bytes())==last[path]['sha256']
assert sha((A/'native.log').read_bytes())=='656c0073010bb821e5c0e53cdf9ae297421b4c1e8db47a39afcc8923628cf660'
assert '130 passed (20.6m)' in (A/'native.log').read_text()
audit=j(A/'POST_RUN_AUDIT.json'); numeric=[]
for item in audit['numeric_observations']:
 data=(A/item['private_raw_source']).read_bytes();assert sha(data)==item['raw_sha256'];value=json.loads(data)
 result=value['actual']['result'];publish=value.get('publishOutcome',value.get('outcome'))
 assert result['outcome']=='environment_unavailable' and result['verdict']=='BLOCKED' and result['exit_code']==1
 assert publish['status']==409 and publish['body']['error']['code']=='PUBLISH_NUMERIC_REQUIRED'
 counter='newModelCalls' if 'newModelCalls' in value else 'externalModelCalls';assert value[counter]==0
 numeric.append({'raw_sha256':sha(data),'outcome':result['outcome'],'verdict':result['verdict'],'publish_status':409,'counter_original_field':counter,'counter_value':0})
boot=audit['bootstrap_control_observation'];data=(A/boot['private_raw_source']).read_bytes();assert sha(data)==boot['raw_sha256'];value=json.loads(data)
assert value['real_thread']=='PASS' and value['blocked_code'] is None
assert value['registrations_before_restart']==value['registrations_after_restart_and_replay']=={'sessions':1,'permits':1,'finished':1}
assert value['create_posts_before_explicit_replay']==1
report={'status':'ROOT_NATIVE79AC_130_PASS_RAW25_CANDIDATES_11_IMAGES_AND1465_INPUTS_VERIFIED',
 'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':head,'make_exit':0,'wrapper_exit':0,
 'complete_before_git_map_count':1465,'complete_after_actual_byte_readback':1465,'actual_changed_outputs':changed,
 'unchanged_total_inputs':1460,'nongenerated_source_inputs_all_unchanged':1455,'complete1465_unchanged':False,
 'candidate_count':25,'candidate_pngs_individually_viewed_by_root':11,'image_review':'1440/1920/900/390 synthetic reading/drawers/longformula localscroll/threeway conflict/native200percent and capability1440/390; no visible credentials or private content. Does not prove additional M6.3 producer UI.',
 'numeric':numeric,'bootstrap_control':{'real_thread':'PASS','raw_sha256':sha(data),'scope':'real production ready mapping/persistent readback; unique OS CLI starts/isolation not independently measured by browser; no turn/login/tool/model request'},
 'qualification':'Original author audit external_model_calls=0 for Restore derives only raw newModelCalls=0; do not present as full external network measurement. Preserve original authored audit alongside this field-name qualification.',
 'boundaries':'No new application/test/CLI/provider executions by rootreadback; no copyback/restore/stage; original synthetic fixtures. Real model turn/hosttools/physical numeric/academic quality/wholeM6.3 not accepted.',
 'source_mutation':False,'published':False}
(O/'READBACK.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'receipt_sha256':sha((O/'READBACK.json').read_bytes())}))
