"""Independent immutable-Git integration and original-receipt hash checks only."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
ARCHIVE=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance')
OUT=Path(__file__).parent
BASE='4353a05570afd9f2378c904b5594998de21bc474'
FIXED='412abe09c519104d9dbd2b360eed3ff4f897f829'
SPEC='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==FIXED and git('status','--porcelain')==b''
blob_cache={};trees={};evidence=[];bindings=[]
def read(path):
    data=path.read_bytes();evidence.append({'path':str(path.relative_to(ARCHIVE)),'bytes':len(data),'sha256':sha(data)});return data
def doc(path):return json.loads(read(path))
def blob(oid):
    if oid not in blob_cache:blob_cache[oid]=git('cat-file','blob',oid)
    return blob_cache[oid]
def tree(head):
    if head in trees:return trees[head]
    result={}
    for row in git('ls-tree','-rz',head).split(b'\0'):
        if not row:continue
        metadata,path=row.split(b'\t',1);mode,kind,oid=metadata.decode().split();path=path.decode()
        if path.startswith('progress/'):continue
        assert kind=='blob';data=blob(oid)
        result[path]={'mode':mode,'type':kind,'git_blob':oid,'sha256':sha(data),'bytes':len(data)}
    trees[head]=result;return result
def bind(path,head=None):
    value=doc(path);head=head or value['head'];assert value['head']==head
    expected=tree(head);files=value['files'];assert len(files)==value['count']==len(expected) and set(files)==set(expected)
    for name,rec in files.items():
        normalized={k:rec.get(k,rec.get('git_'+k)) for k in ('mode','type','git_blob','sha256','bytes')}
        assert normalized==expected[name],(path.name,name)
    bindings.append({'path':str(path.relative_to(ARCHIVE)),'head':head,'count':len(expected)})
    return value
packs=[('m63-reviewed-aa218-canonical-integration-oct05',BASE,['form-status-race','tutor-observation']),('m63-artifact8f-event80b-canonical-integration-oct05','937848134230c967d068183b6365ced0b320cc1e',['artifact-ui','event-ui'])]
all_changes={};merges=[]
for pack,start,stages in packs:
    p=ARCHIVE/pack;fusion=doc(p/'SOURCE_FUSION.json');before=bind(p/'before.json',start)
    assert fusion['before_head']==start and len(fusion['records'])==2
    current=start;original=tree(start);expected=dict(original)
    local_changes=set()
    for stage,record in zip(stages,fusion['records']):
        assert record['stage']==stage and record['previous_head']==current and record['merge_exit_code']==0
        command=doc(p/(stage+'-command.json'));assert command[:3]==['git','merge','--no-ff'] and command[3]==record['source']
        stdout=read(p/(stage+'-stdout.log'));stderr=read(p/(stage+'-stderr.log'))
        assert b'CONFLICT' not in stdout+stderr and b"Merge made by the 'ort' strategy." in stdout
        parents=git('show','-s','--format=%P',record['merged_head']).decode().strip().split();assert parents==[current,record['source']]
        names=git('diff','--name-only',record['source_base'],record['source']).decode().splitlines();assert names==record['delta_paths']
        actualsource=tree(record['source']);deltas={name:actualsource[name] for name in names}
        assert not set(names)&set(all_changes)
        all_changes.update({name:{'source':record['source'],'source_base':record['source_base'],'record':rec} for name,rec in deltas.items()})
        local_changes.update(names);expected.update(deltas)
        assert tree(record['merged_head'])==expected
        after=bind(p/(stage+'-after.json'),record['merged_head'])
        assert record['inputs']==after['count'] and record['complete_source_exact'] is True
        merges.append({'stage':stage,'source':record['source'],'source_base':record['source_base'],'previous_head':current,'merged_head':record['merged_head'],'parents':parents,'delta_paths':names,'merge_exit_code_recorded':0,'inputs':after['count'],'complete_source_exact':True,'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr)})
        current=record['merged_head']
    assert fusion['head']==current and fusion['complete_nonprogress_inputs']==len(expected)
    unchanged=sum(1 for name,rec in original.items() if expected.get(name)==rec)
    assert unchanged==fusion['original_nonoverlap_unchanged']
    assert not fusion['new_product_tests_executed'] and not fusion['source_pushed'] and not fusion['whole_M6_3_accepted']
actual=tree(FIXED);original=tree(BASE)
names=git('diff','--name-only',BASE,FIXED).decode().splitlines()
assert len(names)==27 and set(names)==set(all_changes)
assert all(name.startswith(('apps/web/','tests/e2e/')) for name in names)
assert actual=={**original,**{name:item['record'] for name,item in all_changes.items()}}
outside={name:rec for name,rec in original.items() if not name.startswith(('apps/web/','tests/e2e/'))}
outside_final={name:rec for name,rec in actual.items() if not name.startswith(('apps/web/','tests/e2e/'))}
assert outside_final==outside
unchanged=sum(1 for name,rec in original.items() if actual.get(name)==rec)
assert len(original)==1493 and len(actual)==1512 and unchanged==1485
assert actual['PRODUCT_DESIGN.md']['sha256']==SPEC
for name,rec in actual.items():
    data=(ROOT/name).read_bytes();assert len(data)==rec['bytes'] and sha(data)==rec['sha256']
gates=[]
def gate(pack,stage,head):
    p=ARCHIVE/pack/stage;c=doc(p/'command.json');r=doc(p/'receipt.json');before=bind(p/'before.json',head);after=bind(p/'after.json',head);log=read(p/'run.log')
    assert before==after and r['before_after_git_exact'] is True
    assert r['head']==head and r['complete_nonprogress_git_inputs']==len(tree(head)) and r['status']=='PASS' and r['exit_code']==0
    assert r['command']==c['command'] and r['log_sha256']==sha(log)
    counts=[line.strip() for line in log.decode().splitlines() if line.strip().startswith(('Tests  ','Test Files  ','=========== 4341','SKIPPED [1]'))]
    record={'stage':stage,'pack':pack,'head':head,'exit_code':0,'command':r['command'],'receipt_sha256':sha((p/'receipt.json').read_bytes()),'log_sha256':sha(log),'elapsed_seconds':r['elapsed_seconds'],'counts':counts,'map_count':before['count'],'boundary':r['boundary']}
    gates.append(record);return record
python=gate('m63-4353-complete-combination-gates-oct04','full-python',BASE)
assert python['log_sha256']=='9b4bd81562a796e834e0b0b16a8a732c19f3dc0d1371769ca998773b9810c94a'
assert any('4341 passed, 2 skipped, 2 warnings' in x for x in python['counts']) and len([x for x in python['counts'] if x.startswith('SKIPPED [1]')])==2
readback_path=ARCHIVE/'m63-4353-terminal-root-readback-oct05/READBACK.json';rd=doc(readback_path)
assert sha(readback_path.read_bytes())=='40a239d27b304aa2e66dac4fade170a9fbbb32e6423e14d6072b2a76ba536253'
assert rd['head']==BASE
for stage in ['full-web','static-ruff','static-mypy','static-generated','static-spec','static-diff','static-strict','static-build']:
    gate('m63-412abe-combination-gates-oct05',stage,FIXED)
assert any('Tests  1359 passed (1359)'==x for x in gates[1]['counts']) and any('Test Files  163 passed (163)'==x for x in gates[1]['counts'])
prior=[('m63-artifact-ui-final-independent-review-oct05','REVIEW.md','ac97dc65b16f9bd7815766322065c9fab052fca84985fe04f872567e484c7fc9'),('m63-turn-form-status-race-independent-review-oct04','REVIEW.md','94d863a62689cba4602f72ee6766fe3e3883913d195c090a6653124a87aad3b0'),('m63-tutor-completion-observation-independent-review-oct04','REVIEW.md','48e1553485c6f4faa94b60a9294c6f0eec7f64e1eda5553d0658d0d924601b02')]
for pack,name,expected in prior:assert sha(read(ARCHIVE/pack/name))==expected
assert git('rev-parse','HEAD').decode().strip()==FIXED and git('status','--porcelain')==b''
result={'status':'READONLY_INTEGRATION_AND_ORIGINAL_GATE_READBACK_VERIFIED','source_sha':FIXED,'base':BASE,'spec_sha256':SPEC,'new_product_execution':False,'canonical_edited':False,'changed_paths':names,'changes':all_changes,'base_inputs':1493,'fixed_inputs':1512,'unchanged_base_inputs':unchanged,'outside_web_e2e_inputs':len(outside),'outside_web_e2e_all_preserved':True,'python_related_paths_preserved':len([name for name in outside if name.endswith('.py')]),'merges':merges,'map_bindings':bindings,'map_records_checked':sum(r['count'] for r in bindings),'evidence_files':evidence,'gates':gates,'python_inheritance_qualification':'Original full Python executed at4353, not rerun at412; every nonWeb/e2e Git input is identical.2numeric environment skips remain blocked; no runtime environment equality claim. Root READBACK hash verified but its other8gate pairs were not re-audited here.','native_412':'NOT_READ_NOT_RUN_BY_THIS_REVIEW','old_seals_preserved':[{'pack':pack,'file':name,'sha256':expected} for pack,name,expected in prior]}
for name,value in [('READBACK.json',result),('FIXED_SOURCE_INPUTS.json',{'head':FIXED,'count':1512,'files':actual})]:
    p=OUT/name;assert not p.exists();p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:result[k] for k in ['status','base_inputs','fixed_inputs','unchanged_base_inputs','outside_web_e2e_inputs','python_related_paths_preserved','map_records_checked','native_412']},indent=2))
