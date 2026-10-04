"""Pure independent source/evidence readback; no product or browser execution."""
import hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-review-client-barrier-oct05')
OWNER=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-review-client-barrier-evidence-oct05/seal-22eb')
OUT=Path(__file__).parent
SOURCE='22eb3168ab9aed7d7e7d50d437919feebb75ba6d'
BASE='d69de81045ff6c9ff2f345643f0fd412e2d108fb'
SPEC='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
blobs={};trees={}
def tree(head):
    if head in trees:return trees[head]
    rows={}
    for item in git('ls-tree','-rz',head).split(b'\0'):
        if not item:continue
        meta,p=item.split(b'\t',1);path=p.decode();mode,kind,oid=meta.decode().split()
        if path.startswith('progress/'):continue
        assert kind=='blob'
        if oid not in blobs:blobs[oid]=git('cat-file','blob',oid)
        data=blobs[oid];rows[path]={'mode':mode,'type':kind,'git_blob':oid,'bytes':len(data),'sha256':sha(data)}
    trees[head]=rows;return rows
def reconstruct(data,e):
    assert len(data)==e['candidate_bytes']and sha(data)==e['candidate_sha256']
    def match(b):return len(b)==e['raw_bytes']and sha(b)==e['raw_sha256']
    if e['transformation'].startswith('identity'):
        assert match(data);return data
    assert e['transformation']=='literal home-prefix-only'
    for trial in [data,data.replace(b'${HOME}',b'<LOCAL_HOME>')]:
        if match(trial):assert trial.replace(b'<LOCAL_HOME>',b'${HOME}')==data;return trial
    parts=data.split(b'${HOME}');n=len(parts)-1;assert n<=20
    for mask in range(1<<n):
        trial=parts[0]
        for i,p in enumerate(parts[1:]):trial+=(b'<LOCAL_HOME>'if mask>>i&1 else b'${HOME}')+p
        if match(trial):assert trial.replace(b'<LOCAL_HOME>',b'${HOME}')==data;return trial
    raise AssertionError(('undeclared candidate transformation',e['candidate_path']))
def verify():
    assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('status','--porcelain').decode()==''
    manifest=(OWNER/'SAFE_CANDIDATES.json').read_bytes();assert sha(manifest)=='42e72ca627491e27ad1371de1a6560520a99630be7446bb9c2f2c783eedb1e6d'
    m=json.loads(manifest);assert m['source_sha']==SOURCE and m['count']==len(m['files'])==121
    data={};raw={};entries={}
    for e in m['files']:
        n=e['candidate_path'];p=Path(n);assert not p.is_absolute() and '..'not in p.parts and n not in data
        data[n]=(OWNER/'publication-candidates'/p).read_bytes();raw[n]=reconstruct(data[n],e);entries[n]=e
    assert sum(n.endswith('.png')for n in data)==m['png_count']==2
    outer=json.loads((OWNER/'READBACK.json').read_text());assert outer['safe_manifest_sha256']==sha(manifest) and outer['source_sha']==SOURCE and outer['candidate_count']==121 and outer['candidate_pngs']==2
    assert sha(raw['REPORT.md'])==outer['report_sha256']=='18c00612c48ea7f0283ec4e7bb91d1feb23f99e0d31c0162c85f497ca08cd50c'
    def obj(n):return json.loads(data[n])
    source=obj('SOURCE_BINDINGS.json');heads=source['git_heads'];assert len(heads)==8 and heads[0]==BASE and heads[-1]==SOURCE
    chain=[];git_bindings=0
    for i,head in enumerate(heads):
        fixed=tree(head);mapping=obj('git/'+head+'.json');assert mapping['head']==head and mapping['count']==len(fixed)==len(mapping['files'])
        records={r['path']:{k:v for k,v in r.items()if k!='path'}for r in mapping['files']};assert records==fixed;git_bindings+=len(fixed)
        if i:
            assert git('show','-s','--format=%P',head).decode().strip()==heads[i-1];chain.append({'head':head,'parent':heads[i-1],'changed_paths':git('diff','--name-only',heads[i-1],head).decode().splitlines()})
    assert git_bindings==source['git_bindings']==12189
    distinct={v['git_blob']for h in heads for v in tree(h).values()};assert len(distinct)==source['distinct_git_blobs']==1511
    fixed=tree(SOURCE);base=tree(BASE);changed=git('diff','--name-only',BASE,SOURCE).decode().splitlines()
    assert changed==source['changed_paths']==['tests/e2e/responseJsonBarrier.check.ts','tests/e2e/responseJsonBarrier.ts','tests/e2e/review.spec.ts']
    assert len(fixed)==1524 and len(base)==1522 and sum(fixed.get(p)==v for p,v in base.items())==source['unchanged_base_inputs']==1521
    assert fixed['PRODUCT_DESIGN.md']['sha256']==SPEC
    for p in changed:assert raw['source/'+p]==blobs[fixed[p]['git_blob']]
    assert raw['owned.patch']==git('diff',BASE,SOURCE)
    maps=[]
    def mapping(n):
        d=obj(n);fixed=tree(d['head']);rs=d['files']
        if isinstance(rs,list):
            assert len(rs)==len({r['path']for r in rs});rs={r['path']:{k:v for k,v in r.items()if k!='path'}for r in rs}
        assert d['count']==len(rs)==len(fixed) and set(rs)==set(fixed)
        for p,r in rs.items():
            for k,v in fixed[p].items():assert r[k]==v,(n,p,k)
            if 'actual_blob'in r:assert r['actual_blob']==r['git_blob']and r['matches_git']is True
        if 'status'in d:assert d['status']==''
        maps.append({'path':n,'head':d['head'],'count':len(rs),'raw_sha256':sha(raw[n]),'candidate_sha256':sha(data[n])});return d
    history=obj('STAGE_HISTORY.json');assert len(history)==21
    stages=[]
    for h in history:
        name=h['stage'];prefix='stages/'+name+'/';receipt=obj(prefix+'receipt.json');command=obj(prefix+'command.json');head=receipt['source_sha']
        assert head in heads
        for k,v in command.items():assert receipt[k]==v
        for k,v in receipt.items():assert h[k]==v
        assert receipt['runner_sha256']in [sha(raw['harness/run.py']),sha(raw['harness/run-bound.py'])]
        for p,s in receipt['test_sources'].items():assert tree(head)[p]['sha256']==s
        before=mapping(prefix+'source-before.json');after=mapping(prefix+'source-after.json');assert before==after and before['head']==head and receipt['before_after_exact']is True and before['count']==receipt['complete_nonprogress_inputs']
        if 'harness_inputs'in receipt:
            assert receipt['harness_before_after_exact']is True
            for p,s in receipt['harness_inputs'].items():assert sha(raw['harness/'+p])==s
        log='logs/'+name+'.log';log_admitted=log in raw
        if log_admitted:assert sha(raw[log])==receipt['log_sha256']
        stages.append({'stage':name,'head':head,'exit_code':receipt['exit_code'],'command':receipt['command'],'log_sha256':receipt['log_sha256'],'admitted_log':log_admitted,'map_inputs_each':before['count'],'private_harness_explicitly_bound':'harness_inputs'in receipt})
    assert len(maps)==42 and sum(r['count']for r in maps)==source['before_after_map_bindings']==64004
    red='a5c11f7ba9976fb52240e0c9cbf85219c83c9821';green='7f50da35c6ab1f9bbc668cb511551a230bcc858a';p='tests/e2e/responseJsonBarrier.check.ts'
    original=blobs[tree(red)[p]['git_blob']];assert original==blobs[tree(green)[p]['git_blob']]
    assert sha(original)==source['red_green_same_complete_test_sha256']=='9ad9d8bcb579643d2b88e51e4ff8aadb47abf77aee3f1924305c6275ea81265f'
    assert raw['historical-source/red-handler-02/responseJsonBarrier.check.ts']==raw['historical-source/green-client/responseJsonBarrier.check.ts']==original
    redlog=data['logs/red-handler-02.log'].decode();greenlog=data['logs/green-client.log'].decode()
    assert '2 failed'in redlog and '2 passed'in greenlog and 'route completion must not be mistaken for client JSON consumption'in redlog
    for name,count in [('exact-review',2),('exact-mechanism',3)]:
        assert str(count)+' passed'in data['logs/'+name+'.log'].decode()
        r=next(r for r in stages if r['stage']==name);assert r['head']==SOURCE and r['exit_code']==0
    for name in ['exact-types','exact-web-strict','exact-diff']:
        r=next(r for r in stages if r['stage']==name);assert r['head']==SOURCE and r['exit_code']==0
    phase=obj('observations/exact-review-phases.json');old_phase=obj('observations/route-phase-phases.json')
    assert [r['status']for r in phase if r['event']=='captured']==[200]
    assert [r['status']for r in old_phase if r['event']=='captured']==[200,409,409]
    assert [r['event']for r in phase]==['handler-enter','captured','other-independent-visible','fulfill-enter','fulfill-complete','handlers-drained','client-chain-observed']
    preserved=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-review-route-lifecycle-independent-review-oct05')
    prior={'REVIEW.md':'b47d840471e856064a0ea384336d91914c23632f71fa8a17089b5fdd1f7755bb','READBACK.json':'bb4a3d0314f4a145f5bddf3d3830ccb562bbcdf3f0744f12163fe677e307803b','SAFE_SHARE.json':'35637bcb6d914bf743cd56dd79f86e88a3d5bc34fa35773b0f5c2fe02f0f1276','OUTER_METADATA.json':'6906eed6fbac2fc333797f2136195b8ed96ff981d9741b3c0c90f87446d90f27'}
    for n,s in prior.items():assert sha((preserved/n).read_bytes())==s
    assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('status','--porcelain').decode()==''
    return {'read_at_utc':datetime.now(timezone.utc).isoformat(),'review_type':'PURE_SOURCE_AND_PREEXISTING_ADMITTED_EVIDENCE_READBACK_NO_NEW_TEST_EXECUTION','source_sha':SOURCE,'base':BASE,'sole_spec_sha256':SPEC,'fixed_inputs':1524,'base_inputs':1522,'unchanged_base_inputs':1521,'changed_paths':changed,'numstat':git('diff','--numstat',BASE,SOURCE).decode().splitlines(),'actual_git_chain':chain,'Git_head_count':8,'Git_input_bindings':12189,'distinct_Git_blobs':1511,'owner_explicit_SAFE_sha256':sha(manifest),'owner_explicit_READBACK_sha256':sha((OWNER/'READBACK.json').read_bytes()),'candidate_count':121,'png_count':2,'candidate_base':str(OWNER/'publication-candidates'),'candidates':[{'path':n,'raw_sha256':e['raw_sha256'],'candidate_sha256':e['candidate_sha256'],'raw_bytes':e['raw_bytes'],'candidate_bytes':e['candidate_bytes'],'transformation':e['transformation'],'verified':True}for n,e in entries.items()],'actual_stage_count':21,'actual_map_count':42,'actual_map_bindings':64004,'actual_maps':maps,'stages':stages,'RED_GREEN_full_original_test_bytes_same':True,'RED_GREEN_full_original_test_sha256':sha(original),'RED_GREEN_full_original_test_bytes':len(original),'final_test_file_not_claimed_same_as_original_RED':True,'exact_review_phases':phase,'previous_three_GET_phases':old_phase,'prior_d69_OPEN_and_seals_unchanged':prior,'initial_private_config_boundary':'Initialrun.py did not separately hash private mechanism/type config. Laterrun-bound and final5stages do; no retroactive hashes invented.','failure_log_boundary':'Only explicitly admitted inert mechanism red-handler-02 failed log read. Other failed rawlogs remain excluded; their receipt/hash/owner-qualified summaries retained.','image_visual_review':'Separate manual view of both exact admitted PNGs completed before seal; first history business case only, not late-hidden evidence.','barrier_boundary':'Finite current exact GET/json adoption chain through transport/generated-client to synchronous hook current()/catch; no all React render/effects or general async-task scheduling proof.','old412_full_failure':'FAIL/causeUNKNOWN remains separate; original full raw log not read here.','root_d69_full133PASS':'Parent-reported different fixed source, not new22full-suite evidence.','new_product_execution':False,'source_or_canonical_edited':False,'remote_publication':False,'actual_model_orCLI':'NOT_RUN','whole_M6_3_acceptance':'NOT_CLAIMED'}
if __name__=='__main__':
    result=verify()
    for n,d in [('READBACK.json',result),('FIXED_SOURCE_INPUTS.json',{'head':SOURCE,'count':1524,'files':tree(SOURCE)})]:
        target=OUT/n;assert not target.exists();target.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['fixed_inputs','unchanged_base_inputs','candidate_count','Git_input_bindings','distinct_Git_blobs','actual_stage_count','actual_map_bindings']},indent=2))
