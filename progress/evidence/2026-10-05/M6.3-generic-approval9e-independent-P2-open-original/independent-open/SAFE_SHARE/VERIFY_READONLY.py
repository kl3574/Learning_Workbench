"""Read immutable source and explicitly authorized receipt/map metadata only."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-generic-approval-ui-owner-oct05')
EVIDENCE=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-generic-approval-ui-evidence-oct05')
OUT=Path(__file__).parent
SOURCE='9e4ce1bab62d23cef0ef3f3354fa606ee62d090b'
BASE='412abe09c519104d9dbd2b360eed3ff4f897f829'
OLD='03151b9774744933be0b5654d48adfa19b4f704c'
OLD_BASE='8f2c884510aef987b80ae62a018c33c83d89388c'
SPEC='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
cache={};trees={}
def blob(oid):
    if oid not in cache:cache[oid]=git('cat-file','blob',oid)
    return cache[oid]
def tree(head):
    if head in trees:return trees[head]
    result={}
    for row in git('ls-tree','-rz',head).split(b'\0'):
        if not row:continue
        metadata,path=row.split(b'\t',1);mode,kind,oid=metadata.decode().split();path=path.decode()
        if path.startswith('progress/'):continue
        assert kind=='blob';data=blob(oid)
        result[path]={'mode':mode,'type':kind,'git_blob':oid,'bytes':len(data),'sha256':sha(data)}
    trees[head]=result;return result
paths=git('diff','--name-only',BASE,SOURCE).decode().splitlines()
assert len(paths)==11 and paths==git('diff','--name-only',OLD_BASE,OLD).decode().splitlines()
assert all(name.startswith('apps/web/') for name in paths)
assert tree(SOURCE)=={**tree(BASE),**{name:tree(OLD)[name] for name in paths}}
assert all(tree(SOURCE)[name]==tree(OLD)[name] for name in paths)
assert git('show','-s','--format=%P',SOURCE).decode().strip().split()==[OLD,BASE]
assert len(tree(SOURCE))==1522 and len(tree(OLD))==1514
assert sum(tree(SOURCE).get(name)==rec for name,rec in tree(BASE).items())==1511
assert tree(SOURCE)['PRODUCT_DESIGN.md']['sha256']==SPEC
selected=[];maps=[];receipts=[]
def read(path):
    data=path.read_bytes();selected.append({'path':str(path.relative_to(EVIDENCE)),'bytes':len(data),'sha256':sha(data)});return data
for stage in ['expanded-focused','full-web','full-web-02','combined-full-web','combined-strict','combined-build','combined-spec']:
    p=EVIDENCE/stage;r=json.loads(read(p/'receipt.json'));c=json.loads(read(p/'command.json'))
    before=json.loads(read(p/'source-before.json'));after=json.loads(read(p/'source-after.json'))
    assert before==after and r['before_after_exact'] is True and before['status']==''
    head=before['head'];assert head==r['source_sha']==c['source_sha']
    expected=tree(head)
    for label,value in [('before',before),('after',after)]:
        files={v['path']:v for v in value['files']};assert len(files)==value['count']==len(expected) and set(files)==set(expected)
        for name,rec in files.items():
            assert {key:rec[key] for key in ['mode','type','git_blob','bytes','sha256']}==expected[name]
            assert rec['actual_blob']==rec['git_blob'] and rec['matches_git'] is True
        maps.append({'stage':stage,'snapshot':label,'head':head,'count':len(files)})
    assert r['complete_nonprogress_inputs']==len(expected) and r['command']==c['command']
    if 'test_sources' in r:
        for name,digest in r['test_sources'].items():assert expected[name]['sha256']==digest
    receipts.append({'stage':stage,'head':head,'declared_exit_code':r['exit_code'],'declared_log_sha256':r['log_sha256'],'receipt_sha256':sha((p/'receipt.json').read_bytes()),'command':r['command'],'complete_inputs':len(expected),'qualification':'Receipt/command/maps independently read and Git-bound; raw log NOT_READ pending explicit safe candidates. Test count and full native result not independently verified here.'})
    assert r['exit_code']==(1 if stage in ['full-web','full-web-02'] else 0)
for stage in ['localtask-observation','turnpanel-observation']:
    value=json.loads(read(EVIDENCE/stage/'receipt.json'))
    receipts.append({'stage':stage,'metadata_only':True,'receipt_sha256':sha((EVIDENCE/stage/'receipt.json').read_bytes()),'qualification':'Explicit observer receipt read only; no associated source/log or failure cause admitted.'})
source_inputs={name:tree(SOURCE)[name] for name in paths}
backend_paths=['services/api/app/application/codex_approvals.py','services/api/app/application/codex_approval_models.py','services/api/app/codex_turn_dto.py','services/api/app/interfaces/codex_approval_http.py','packages/contracts/generated/codex-turn-schemas.json']
for name in backend_paths:assert tree(SOURCE)[name]==tree(BASE)[name]
result={'status':'SOURCE_REVIEW_FIXED_P2_OPEN_METADATA_READBACK_ONLY','source_sha':SOURCE,'base':BASE,'old_source':OLD,'old_base':OLD_BASE,'spec_sha256':SPEC,'input_count':1522,'old_input_count':1514,'changed_paths':paths,'unchanged_base_inputs':1511,'same_generic_implementation_at031_and9e':True,'parents':[OLD,BASE],'source_bindings':source_inputs,'backend_contract_bindings':{name:tree(SOURCE)[name] for name in backend_paths},'maps':maps,'map_records_checked':sum(r['count'] for r in maps),'receipts':receipts,'selected_metadata':selected,'raw_gate_logs_read':False,'native_read':False,'new_product_execution':False,'canonical_or_owner_source_edited':False}
for name,value in [('READBACK.json',result),('FIXED_SOURCE_INPUTS.json',{'head':SOURCE,'count':1522,'files':tree(SOURCE)})]:
    p=OUT/name;assert not p.exists();p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':result['status'],'input_count':1522,'paths':len(paths),'unchanged_base_inputs':1511,'metadata_files':len(selected),'map_records_checked':result['map_records_checked']},indent=2))
