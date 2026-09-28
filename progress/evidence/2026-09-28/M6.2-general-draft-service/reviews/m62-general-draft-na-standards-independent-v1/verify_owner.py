"""Read only: fixed Git objects plus two immutable evidence packages; no tests/DB/network."""
from pathlib import Path
import hashlib,io,json,re,subprocess
OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
REPO=ROOT/'m62-general-draft-service-active'
OWNER=ROOT/'m62-general-draft-service-na-repair-v1'
PRIOR=ROOT/'m62-general-draft-service-development-v1'
BASE='5c6d9959fee4ef7cf22fe2cca8e0f07fa524c18d'
HEAD='2035fc9bf92f1c6b38725b2936898ad49adb4c16'
def meta(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def filemeta(p):return meta(p.read_bytes())
def load(p):return json.loads(p.read_bytes())
def save(n,v):(OUT/n).write_text(json.dumps(v,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)
for root,count in [(OWNER,1063),(PRIOR,1180)]:
 m=load(root/'PRIVATE_MANIFEST.json')['members'];assert len(m)==count
 assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}==set(m)|{'PRIVATE_MANIFEST.json'}
 for name,details in m.items():assert filemeta(root/name)==details,name
assert filemeta(PRIOR/'PRIVATE_MANIFEST.json')['sha256']=='d88f0e44e1703d8e8d27fdc4d01ee2e8d04d186562ece974269946c634d63e0f'
trees={}
for head in [BASE,HEAD]:
 tree={}
 for row in git('ls-tree','-r','-z',head).split(b'\0'):
  if not row:continue
  header,name=row.split(b'\t',1);mode,kind,oid=header.decode().split();name=name.decode()
  if name.startswith('progress/'):continue
  assert kind=='blob';tree[name]=oid
 trees[head]=tree
oids=sorted({x for tree in trees.values() for x in tree.values()})
raw=subprocess.run(['git','cat-file','--batch'],cwd=REPO,input=('\n'.join(oids)+'\n').encode(),capture_output=True,check=True).stdout
stream=io.BytesIO(raw);blobs={}
for oid in oids:
 h=stream.readline().decode().split();assert h[:2]==[oid,'blob'];raw=stream.read(int(h[2]));assert stream.read(1)==b'\n';blobs[oid]=raw
assert stream.read()==b''
actual={head:{name:meta(blobs[oid]) for name,oid in tree.items()} for head,tree in trees.items()}
assert len(actual[HEAD])==1051
names=git('diff','--name-only',BASE,HEAD).decode().splitlines()
assert set(names)=={'services/api/app/application/review_service.py','tests/integration/test_draft_edit_integrity.py'}
diff=git('diff','--binary',BASE,HEAD);assert diff==(OWNER/'final-change.diff').read_bytes();(OUT/'reviewed.diff').write_bytes(diff)
pins={}
for name in names:
 raw=blobs[trees[HEAD][name]];path=OUT/'source'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);pins[name]=meta(raw)|{'git_blob':trees[HEAD][name]}
save('source-pins.json',{'base':BASE,'head':HEAD,'paths':pins})
contexts=['services/api/app/application/draft_edits.py','services/api/app/application/review_material_models.py','services/api/app/application/draft_edit_models.py','services/api/app/application/review_worker.py','services/api/app/infrastructure/review_repository.py']
save('context-pins.json',{'head':HEAD,'read_scope':'Unchanged owner paths reviewed in prior fixed Standards package; only line tracing repeated.','paths':{n:actual[HEAD][n]|{'git_blob':trees[HEAD][n]} for n in contexts}})
refs=set();rows=[];driver=filemeta(OWNER/'run.py')['sha256']
ledger=load(OWNER/'run-ledger.json');assert len(ledger)==5
for e in ledger:
 stage=e['stage'];p=OWNER/stage;r=load(p/'receipt.json');before=load(p/'inputs-before.json');after=load(p/'inputs-after.json')
 assert before==after and r['unchanged'] and not r['changed_paths'] and len(before)==r['input_count_before']==r['input_count_after']==1051
 assert r['driver_sha256']==driver and r['exit_code']==e['exit_code'] and r['actual_head']==e['actual_head']
 assert filemeta(p/'run.log')=={'bytes':r['log_bytes'],'sha256':r['log_sha256']}==e['log']
 assert filemeta(p/'receipt.json')==e['receipt'] and filemeta(p/'inputs-before.json')==e['before'] and filemeta(p/'inputs-after.json')==e['after']
 for name,d in before.items():assert filemeta(OWNER/'source-pool'/d['sha256'])==d;refs.add(d['sha256'])
 dirty=sorted(n for n in set(before)|set(actual[r['actual_head']]) if before.get(n)!=actual[r['actual_head']].get(n))
 finaldirty=sorted(n for n in set(before)|set(actual[HEAD]) if before.get(n)!=actual[HEAD].get(n))
 assert (not finaldirty)==e['matches_final_git']
 assert e['terminal'] in (p/'run.log').read_text()
 rows.append({'stage':stage,'actual_head':r['actual_head'],'exit_code':r['exit_code'],'command':r['command'],'all1051_before_after_and_CAS_verified':True,'recorded_git_mismatches':dirty,'final_git_mismatches':finaldirty,'log':e['log'],'receipt':e['receipt'],'terminal':e['terminal']})
assert len(refs)==1034 and refs=={p.name for p in (OWNER/'source-pool').iterdir()}
assert rows[0]['recorded_git_mismatches']==['tests/integration/test_draft_edit_integrity.py']
assert rows[0]['final_git_mismatches']==['services/api/app/application/review_service.py']
assert rows[1]['actual_head']==BASE and not rows[1]['final_git_mismatches']
assert all(r['actual_head']==HEAD and not r['recorded_git_mismatches'] for r in rows[2:])
assert [r['exit_code'] for r in rows]==[1,0,0,0,0]
assert 'MATHEMATICAL_REVIEW_REQUIRED' in (OWNER/'01-current-edit-na-red/run.log').read_text()
passed=[s.split(' PASSED ')[0] for s in (OWNER/'03-final-review-related/run.log').read_text().splitlines() if re.match(r'^tests/.* PASSED ',s)]
assert len(passed)==len(set(passed))==134 and len({s.split('::')[0] for s in passed})==4
assert rows[3]['command'][2:]==['services/api/app/application/review_service.py','tests/integration/test_draft_edit_integrity.py']
assert rows[4]['command'][-1]=='services/api/app' and '208 source files' in rows[4]['terminal']
save('stage-verification.json',rows)
save('VERIFY.json',{'result':'PASS','kind':'Independent raw/Git verification; not product execution','base':BASE,'candidate':HEAD,'owner_manifest':filemeta(OWNER/'PRIVATE_MANIFEST.json'),'owner_members':1063,'prior_manifest':filemeta(PRIOR/'PRIVATE_MANIFEST.json'),'prior_members_unchanged':1180,'stages':5,'CAS_blobs':1034,'final_git_inputs':1051,'stage01_test_only_change_relative_to_base':True,'stage01_product_old_and_stage02_product_final':True,'stage02_bytes_final_but_HEAD_base':True,'stage03_to05_actual_final_head_and_bytes':True,'selected_passes':134,'selected_files':4,'deselected':6,'warnings':2,'targeted_positive_and_negative_passes':3,'ruff_changed_paths':2,'mypy_source_files':208,'product_tests_run_by_reviewer':0,'network_DB_access':False})
print(json.dumps({'result':'PASS','raw_members':1063,'prior_unchanged':1180,'stages':5,'final_inputs':1051,'CAS':1034,'related_passes':134}))
