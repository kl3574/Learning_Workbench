"""Independent archival hash/source readback only. No application execution."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess

ROOT = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-artifact-ui-4353-owner-oct04')
EVIDENCE = Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-artifact-ui-evidence-oct04')
OUT = Path(__file__).parent
FIXED = '8f2c884510aef987b80ae62a018c33c83d89388c'
BASE = '4353a05570afd9f2378c904b5594998de21bc474'
SPEC = 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
def digest(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
assert git('rev-parse', 'HEAD').decode().strip() == FIXED
assert git('status', '--porcelain') == b''
entries = json.loads((EVIDENCE/'publication-candidates/allowlist.json').read_bytes())['files']
assert len(entries) == 128 and len({e['candidate'] for e in entries}) == 128
raw, candidates = {}, []
def reconstruct(data, e):
    if digest(data) == e['raw_sha256']:
        assert len(data) == e['raw_bytes']; return data
    marker, original = b'<LOCAL_HOME>', b'<LOCAL_HOME>'
    restored = data.replace(marker, original)
    if digest(restored) == e['raw_sha256']:
        assert len(restored) == e['raw_bytes']; return restored
    parts = data.split(marker); n = len(parts)-1
    assert n <= 16, ('ambiguous inverse requires explicit review', e['candidate'], n)
    for selected in itertools.product([False, True], repeat=n):
        restored = parts[0]
        for i, choice in enumerate(selected): restored += (original if choice else marker)+parts[i+1]
        if digest(restored) == e['raw_sha256'] and len(restored) == e['raw_bytes']: return restored
    raise AssertionError(('home-prefix transformation mismatch', e['candidate']))
for e in entries:
    name=e['candidate']; p=EVIDENCE/'publication-candidates'/name
    assert p.resolve().is_relative_to((EVIDENCE/'publication-candidates').resolve())
    data=p.read_bytes(); assert len(data)==e['candidate_bytes'] and digest(data)==e['candidate_sha256']
    raw[name]=reconstruct(data,e)
    assert raw[name].replace(b'<LOCAL_HOME>', b'<LOCAL_HOME>') == data or raw[name] == data
    candidates.append({'candidate':name,'raw_sha256':digest(raw[name]),'candidate_sha256':digest(data),'raw_bytes':len(raw[name]),'candidate_bytes':len(data)})
def doc(name): return json.loads(raw[name])
blob_cache={}
def blob(oid):
    if oid not in blob_cache: blob_cache[oid]=git('cat-file','blob',oid)
    return blob_cache[oid]
trees={}
def tree(head):
    if head in trees: return trees[head]
    result={}
    for row in git('ls-tree','-rz',head).split(b'\0'):
        if not row: continue
        metadata,path=row.split(b'\t',1); mode,kind,oid=metadata.decode().split(); path=path.decode()
        if path.startswith('progress/'): continue
        assert kind=='blob'
        data=blob(oid)
        result[path]={'mode':mode,'type':kind,'git_blob':oid,'sha256':digest(data),'bytes':len(data)}
    trees[head]=result; return result
map_bindings=[]
def bind(label, value, head=None):
    head=head or value.get('head'); actual=tree(head)
    files=value['files']; files={v['path']:v for v in files} if isinstance(files,list) else files
    assert value['count']==len(files)==len(actual)
    assert set(files)==set(actual)
    for name,rec in files.items():
        for key,expected in actual[name].items():
            if key in rec: assert rec[key]==expected,(label,name,key)
        assert rec['sha256']==actual[name]['sha256']
        if 'bytes' in rec: assert rec['bytes']==actual[name]['bytes']
        assert rec.get('git_blob',rec.get('oid'))==actual[name]['git_blob']
        if 'actual_blob' in rec: assert rec['actual_blob']==rec['git_blob'] and rec['matches_git'] is True
        if 'actual_sha256' in rec: assert rec['actual_sha256']==rec['sha256'] and rec['matches_before'] is True
    if 'status' in value: assert value['status']==''
    map_bindings.append({'label':label,'head':head,'count':len(actual),'record_fields':list(next(iter(files.values()))),'qualification':'Record-present fields bound to Git; full mode/type/blob/size/SHA bound separately by FULL_GIT_MANIFESTS.'})
full=doc('FULL_GIT_MANIFESTS.json')
assert len(full['heads'])==8
for head,m in full['heads'].items(): bind('FULL_GIT_MANIFESTS:'+head,m,head)
assert len(blob_cache)==full['unique_checked_git_blobs']==1499
formal=[]
runner_names={'wire-red-01':'run.py','wire-green-01':'run.py'}
stages=sorted({name.split('/')[0] for name in raw if name.endswith('/source-before.json')})
assert len(stages)==14
for stage in stages:
    before=doc(stage+'/source-before.json'); after=doc(stage+'/source-after.json'); r=doc(stage+'/receipt.json'); c=doc(stage+'/command.json')
    assert before==after and r['before_after_exact'] is True
    assert before['head']==r['source_sha']==c['source_sha']
    bind(stage+':before',before); bind(stage+':after',after)
    assert r['complete_nonprogress_inputs']==before['count']
    assert digest(raw[stage+'/run.log'])==r['log_sha256']
    assert c['command']==r['command'] and c['runner_sha256']==r['runner_sha256']
    runners=[name for name in ('run.py','run-v2.py','run-v3.py') if digest(raw[name])==r['runner_sha256']]
    assert len(runners)==1
    if 'test_sources' in r:
        for name,sha in r['test_sources'].items(): assert tree(r['source_sha'])[name]['sha256']==sha
    else:
        assert tree(r['source_sha'])['apps/web/src/features/codex/artifactWire.test.ts']['sha256']==r['test_sha256']
    log=raw[stage+'/run.log'].decode()
    counts=re.findall(r'(?:Tests|Test Files)\s+[^\n]+',log)
    formal.append({'stage':stage,'head':r['source_sha'],'exit_code':r['exit_code'],'count':before['count'],'log_sha256':r['log_sha256'],'elapsed_seconds':r['elapsed_seconds'],'counts':counts,'runner':runners[0]})
    if stage.endswith('-02'): assert r['source_sha']==FIXED and r['exit_code']==0
for stage in ('scope-red-01','scope-green-01'):
    assert raw[stage+'/ArtifactImportNavigation.test.tsx']==blob(tree(doc(stage+'/receipt.json')['source_sha'])['apps/web/src/features/codex/ArtifactImportNavigation.test.tsx']['git_blob'])
assert raw['scope-red-01/ArtifactImportNavigation.test.tsx']==raw['scope-green-01/ArtifactImportNavigation.test.tsx']
assert tree(doc('wire-red-01/receipt.json')['source_sha'])['apps/web/src/features/codex/artifactWire.test.ts']['sha256']==tree(doc('wire-green-01/receipt.json')['source_sha'])['apps/web/src/features/codex/artifactWire.test.ts']['sha256']
native=[]
for name in ('native-422f-limited','native-8f-final'):
    before=doc(name+'/before.json'); after=doc(name+'/after.json'); assert before==after
    bind(name+':before',before); bind(name+':after',after)
    if name=='native-8f-final': bind(name+':terminal-source',doc(name+'/terminal-source.json'))
    c=doc(name+'/command.json'); r=doc(name+'/receipt.json'); t=doc(name+'/terminal.json')
    assert c['source_sha']==r['source']==before['head']
    assert t['exit_code']==0 and digest(raw[name+'/run.log'])==t['log_sha256']
    for filename,sha in c['harnesses'].items(): assert digest(raw[name+'/'+filename])==sha
    assert r['before_after_exact'] is True and r['complete_nonprogress_inputs']==before['count']
    native.append({'stage':name,'head':before['head'],'exit_code':t['exit_code'],'status':r['status'],'log_sha256':t['log_sha256'],'actual_CLI':r['actual_CLI'],'actual_remote_model':r['actual_remote_model'],'actual_tool_process':r['actual_tool_process']})
fail='native-8f-fail'; bind(fail+':before',doc(fail+'/before.json')); bind(fail+':supplemental_after',doc(fail+'/SUPPLEMENTAL_AFTER.json'))
c=doc(fail+'/command.json'); t=doc(fail+'/terminal.json'); failure=doc(fail+'/failure.json')
assert c['source_sha']==FIXED and failure['source']==FIXED and t['exit_code']==1
assert digest(raw[fail+'/run.log'])==t['log_sha256']
for filename,sha in c['harnesses'].items(): assert digest(raw[fail+'/'+filename])==sha
native.append({'stage':fail,'head':FIXED,'exit_code':1,'log_sha256':t['log_sha256'],'qualification':'Original FAIL preserved; supplemental map is later and not original after map. Observation failure only; no product cause established.'})
pngs=[e for e in candidates if e['candidate'].endswith('.png')]
assert len(pngs)==6
for image in doc('native-8f-final/receipt.json')['screenshots']:
    assert digest(raw['native-8f-final/'+image['file']])==image['sha256']
    assert image['geometry']['scroll']<=image['geometry']['client']+1 and image['geometry']['document']<=image['geometry']['viewport']
changed=git('diff','--name-only',BASE,FIXED).decode().splitlines(); assert len(changed)==15
for name in changed: assert raw['source/'+name]==blob(tree(FIXED)[name]['git_blob'])
assert tree(FIXED)['PRODUCT_DESIGN.md']['sha256']==SPEC
assert len(tree(FIXED))==1504 and sum(1 for name,rec in tree(BASE).items() if tree(FIXED).get(name)==rec)==1489
binding=doc('FINAL_BINDING.json')
assert binding['changed_paths']==changed and binding['source_sha']==FIXED and binding['spec_sha256']==SPEC
assert binding['complete_nonprogress_inputs']==1504 and binding['unchanged_base_inputs']==1489
assert digest(raw['FULL_GIT_MANIFESTS.json'])==binding['git_manifest_sha256']
for r in binding['records']:
    assert r['stage'] in stages
    for filename,rec in r['artifacts'].items():
        data=raw[r['stage']+'/'+filename]; assert rec['bytes']==len(data) and rec['sha256']==digest(data)
old=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-artifact-ui-root-review-422f-oct05')
preserved={name:{'bytes':len((old/name).read_bytes()),'sha256':digest((old/name).read_bytes())} for name in ('REVIEW.md','READBACK.json','FIXED_SOURCE_INPUTS.json')}
live=tree(FIXED)
for name,rec in live.items():
    data=(ROOT/name).read_bytes(); assert len(data)==rec['bytes'] and digest(data)==rec['sha256']
assert git('status','--porcelain')==b''
result={'review_type':'READONLY_ARCHIVAL_SOURCE_AND_HASH_READBACK_NOT_NEW_PRODUCT_TESTS','source_sha':FIXED,'base':BASE,'spec_sha256':SPEC,'changed_paths':changed,'input_count':1504,'unchanged_base_inputs':1489,'allowlist_count':128,'image_count':6,'candidate_bindings':candidates,'map_bindings':map_bindings,'total_map_bindings':sum(x['count'] for x in map_bindings),'unique_git_blobs':len(blob_cache),'formal_receipts':formal,'native_receipts':native,'original_root_422f_preserved':preserved,'status':'READBACK_VERIFIED'}
for filename,value in [('READBACK.json',result),('FIXED_SOURCE_INPUTS.json',{'head':FIXED,'count':1504,'files':live})]:
    p=OUT/filename; assert not p.exists(); p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('candidate_bindings','map_bindings')},ensure_ascii=False,indent=2))
