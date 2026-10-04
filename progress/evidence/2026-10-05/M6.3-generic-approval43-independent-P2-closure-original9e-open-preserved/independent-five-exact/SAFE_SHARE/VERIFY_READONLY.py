"""Independent source-delta and explicit admitted archival evidence verification."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-generic-approval-safe-decline-oct05')
OUT=Path(__file__).parent
SOURCE='43c70d660d98904903bd607a4661b3b95710293e'
BASE='9e4ce1bab62d23cef0ef3f3354fa606ee62d090b'
RED='29fcdd0ac2bc86ee21afa54ef966073f226b70c6'
GREEN='11a7099d75d866f7e84fb5bafdd431c5058eb2c1'
MIDDLE='2d4302c790b9607949be24f084af282be7df7831'
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
assert paths==['apps/web/src/features/codex/CodexApprovalsPanel.test.tsx','apps/web/src/features/codex/CodexApprovalsPanel.tsx','apps/web/src/features/codex/useCodexApprovals.ts']
test=paths[0];production=paths[1:]
assert len(tree(BASE))==len(tree(SOURCE))==1522
assert sum(tree(SOURCE).get(name)==rec for name,rec in tree(BASE).items())==1519
assert tree(SOURCE)['PRODUCT_DESIGN.md']['sha256']==SPEC
chain=[]
for current,parent in [(RED,BASE),(GREEN,RED),(MIDDLE,GREEN),(SOURCE,MIDDLE)]:
    assert git('show','-s','--format=%P',current).decode().strip()==parent
    names=git('diff','--name-only',parent,current).decode().splitlines();chain.append({'head':current,'parent':parent,'changed_paths':names})
assert chain[0]['changed_paths']==[test] and chain[1]['changed_paths']==production
assert chain[2]['changed_paths']==chain[3]['changed_paths']==[test]
red_bytes=blob(tree(RED)[test]['git_blob']);green_bytes=blob(tree(GREEN)[test]['git_blob']);assert red_bytes==green_bytes
assert sha(red_bytes)=='89c2082821d5ecc41c9124ec6866413e8f1e5c4ee908c3098d02b211670aa73c'
for name in production:assert tree(SOURCE)[name]==tree(GREEN)[name]
old=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-generic-approval-ui-independent-review-9e-open-oct05')
preserved={name:expected for name,expected in [('REVIEW.md','2660ac4d67567d0f60a5e0df4cd156dd3df091ebf78ed300ba144bf6cf55c555'),('READBACK.json','8554207c7736a3b5f5f2ee857a9b6a662c35a9eb18a192ae3fdf2399dba28d11'),('SAFE_SHARE.json','26a1e826e3f7a42c974a8136f6ad0f9191e7f90384d996c5bfb8dc5134127c3f'),('OUTER_METADATA.json','dfc3fe36add7824b060c407cb96fb5ab032b8a701dc37056f43bd11677a143c6')]}
for name,expected in preserved.items():assert sha((old/name).read_bytes())==expected
source_result={'review_type':'PURE_SOURCE_HASH_READBACK_NOT_NEW_PRODUCT_TESTS','source_sha':SOURCE,'base':BASE,'spec_sha256':SPEC,'fixed_inputs':1522,'unchanged_base_inputs':1519,'changed_paths':paths,'production_paths':production,'chain':chain,'red_green_full_test_bytes':len(red_bytes),'red_green_full_test_sha256':sha(red_bytes),'production_green_final_exact':True,'original_9e_OPEN_and_seals_preserved':preserved,'new_product_execution':False,'canonical_source_edited':False}

# The final closure will append only explicitly admitted safe evidence checks;
# no unlisted raw logs, runtime data or unreceived RUNNING gates are read here.
def initial_source_snapshot():
    target=OUT/'SOURCE_DELTA_READBACK.json';assert not target.exists();target.write_text(json.dumps(source_result,indent=2)+'\n')
    target=OUT/'FIXED_SOURCE_INPUTS.json';assert not target.exists();target.write_text(json.dumps({'head':SOURCE,'count':1522,'files':tree(SOURCE)},indent=2)+'\n')
    print(json.dumps({'status':'SOURCE_ONLY_VERIFIED_AWAITING_EXPLICIT_SAFE_TERMINAL_EVIDENCE','inputs':1522,'changed_paths':len(paths),'unchanged_base_inputs':1519},indent=2))

EVIDENCE=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-generic-approval-safe-decline-evidence-oct05')
ADMITTED=EVIDENCE/'safe-candidates'
def reconstructed_raw(candidate,entry):
    """Invert only declared home-prefix substitutions, matched to fixed raw hash.

    The literal <LOCAL_HOME> marker may already be present in archival scripts;
    that ambiguity is resolved against the original supplied hash and size.
    No raw unlisted evidence is opened by this function.
    """
    expected=(entry['raw_sha256'],entry['raw_bytes'])
    def matched(value):return (sha(value),len(value))==expected
    if entry['transformation'] in ['identity PNG bytes','identity UTF-8 bytes (no home prefix present)']:
        assert matched(candidate);return candidate
    assert entry['transformation']=='only <LOCAL_HOME> -> <LOCAL_HOME>'
    for trial in (candidate,candidate.replace(b'<LOCAL_HOME>',b'<LOCAL_HOME>')):
        if matched(trial):
            assert trial.replace(b'<LOCAL_HOME>',b'<LOCAL_HOME>')==candidate;return trial
    parts=candidate.split(b'<LOCAL_HOME>');n=len(parts)-1
    assert n<=20,('unresolved marker ambiguity',entry['candidate_path'],n)
    for mask in range(1<<n):
        trial=parts[0]
        for i,part in enumerate(parts[1:]):trial+=(b'<LOCAL_HOME>' if mask>>i&1 else b'<LOCAL_HOME>')+part
        if matched(trial):
            assert trial.replace(b'<LOCAL_HOME>',b'<LOCAL_HOME>')==candidate;return trial
    raise AssertionError(('declared transform cannot reconstruct fixed hash',entry['candidate_path']))

def evidence_readback():
    from datetime import datetime,timezone
    import re
    explicit={
        'PUBLIC_CANDIDATES.json':'fa623e04c79b6b910a073e64d0e7d6b3ebc9fa28b0309344a3f72906f705d029',
        'REPORT.md':'fa5251c1b44b2681fde0af87efe8fad68583fd1c3db17ea0135da25e97bbe621',
        'PACKAGE_SEAL.json':'ecac858f5d588ef5c90ac997b4970daf2451e4c98fb84933b651df01ea634e3d'}
    for name,expected in explicit.items():assert sha((EVIDENCE/name).read_bytes())==expected
    public=json.loads((EVIDENCE/'PUBLIC_CANDIDATES.json').read_text())
    seal=json.loads((EVIDENCE/'PACKAGE_SEAL.json').read_text())
    assert public['source_sha']==seal['source_sha']==SOURCE and len(public['entries'])==seal['candidate_count']==93
    admitted={};original={};entries={}
    for entry in public['entries']:
        name=entry['candidate_path'];relative=Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts and name not in entries
        candidate=(ADMITTED/relative).read_bytes()
        assert len(candidate)==entry['candidate_bytes'] and sha(candidate)==entry['candidate_sha256']
        admitted[name]=candidate;original[name]=reconstructed_raw(candidate,entry);entries[name]=entry
    assert sum(name.endswith('.png') for name in entries)==seal['png_count']==10
    for name,expected in seal['outer'].items():
        if name in explicit:assert explicit[name]==expected
        else:assert sha(original['summary/'+name])==expected
    def obj(name):return json.loads(admitted[name])
    def input_map(name):
        data=obj(name);files=data['files'];head=data['head'];fixed=tree(head)
        if isinstance(files,list):
            assert len(files)==len({f['path'] for f in files})
            files={f['path']:{k:v for k,v in f.items() if k!='path'} for f in files}
        assert data['count']==len(files)==len(fixed)
        assert set(files)==set(fixed)
        for path,row in files.items():
            for k,v in fixed[path].items():assert row[k]==v,(name,path,k)
            if 'actual_blob' in row:assert row['actual_blob']==row['git_blob'] and row['matches_git'] is True
        if 'status' in data:assert data['status']==''
        return {'path':name,'head':head,'count':len(files),'candidate_sha256':sha(admitted[name]),'raw_sha256':sha(original[name])}
    full=obj('summary/FULL_GIT_MANIFESTS.json');all_head_bindings=0
    for head,rows in full['heads'].items():
        actual=tree(head);assert len(rows)==len(actual)==len({r['path'] for r in rows})
        assert {r['path']:{k:v for k,v in r.items() if k!='path'} for r in rows}==actual
        all_head_bindings+=len(rows)
    distinct={r['git_blob'] for rows in full['heads'].values() for r in rows}
    assert len(full['heads'])==full['head_count']==12 and len(distinct)==full['complete_git_blobs_read']==1517
    source_names=[name for name in entries if name.startswith('source/')]
    assert len(source_names)==11
    for name in source_names:
        path=name.removeprefix('source/');assert original[name]==blob(tree(SOURCE)[path]['git_blob'])
    base412='412abe09c519104d9dbd2b360eed3ff4f897f829'
    full_delta=git('diff','--name-only',base412,SOURCE).decode().splitlines()
    assert len(full_delta)==11 and sorted(full_delta)==sorted(n.removeprefix('source/') for n in source_names)
    assert sum(tree(SOURCE).get(p)==r for p,r in tree(base412).items())==1511
    assert original['summary/p2-delta.patch']==git('diff',BASE,SOURCE)
    assert original['summary/owner-delta.patch']==git('diff',base412,SOURCE)
    gate_bindings=obj('summary/GATE_BINDINGS.json');assert len(gate_bindings)==27
    stages=['red-safe-decline-02','green-safe-decline','closure-full-web','closure-strict','closure-build','closure-spec']
    stage_results=[];maps=[]
    for stage in stages:
        prefix='gates/'+stage+'/'
        command=obj(prefix+'command.json');receipt=obj(prefix+'receipt.json');head=command['source_sha']
        assert receipt['source_sha']==head
        for k,v in command.items():assert receipt[k]==v
        assert receipt['runner_sha256']==sha(original['summary/run.py'])
        for name,expected in command['test_sources'].items():assert tree(head)[name]['sha256']==expected
        before=input_map(prefix+'source-before.json');after=input_map(prefix+'source-after.json')
        assert before['head']==after['head']==head and admitted[prefix+'source-before.json']==admitted[prefix+'source-after.json']
        assert receipt['before_after_exact'] is True and receipt['complete_nonprogress_inputs']==1522
        maps.extend([before,after])
        binding=next(r for r in gate_bindings if r['stage']==stage)
        assert binding['receipt']==receipt
        for name,expected in binding['files'].items():
            if prefix+name in original:assert sha(original[prefix+name])==expected
        log=prefix+'run.log';result={'stage':stage,'source':head,'exit_code':receipt['exit_code'],'receipt_raw_sha256':sha(original[prefix+'receipt.json']),'log_sha256':receipt['log_sha256'],'log_admitted':log in original,'map_inputs_each':1522}
        if log in original:assert sha(original[log])==receipt['log_sha256']
        assert receipt['exit_code']==(1 if stage=='red-safe-decline-02' else 0)
        if stage=='red-safe-decline-02':
            assert head==RED;result['summary_basis']='Selected terminal receipt exit1; safe owner report/binding declares3FAIL19PASS; excluded raw failure log not read.'
        elif stage in ['green-safe-decline','closure-full-web']:
            text=admitted[log].decode();match=re.search(r'Test Files\s+(\d+) passed \(\d+\).*?Tests\s+(\d+) passed \(\d+\)',text,re.S);assert match
            result.update(files=int(match[1]),tests=int(match[2]))
            assert (result['files'],result['tests'])==((3,38) if stage=='green-safe-decline' else (166,1399))
        stage_results.append(result)
    native_bindings=obj('summary/NATIVE_BINDINGS.json');assert len(native_bindings)==4
    native_results=[]
    for stage,label,head in [('counter-red','p2_red',BASE),('counter-green','p2_green',SOURCE),('final-positive','final_positive',SOURCE)]:
        prefix='native/'+stage+'/'
        command=obj(prefix+'command.json');run=obj(prefix+'run-receipt.json')
        assert command['source_sha']==run['source_sha']==head
        for k,v in command.items():assert run[k]==v
        for name,expected in run['harness'].items():assert sha(original[prefix+name])==expected
        selected=['before.json','terminal-source.json']+(['after.json'] if stage!='counter-red' else [])
        run_maps=[input_map(prefix+n) for n in selected];assert all(r['head']==head for r in run_maps)
        assert all(obj(prefix+n)==obj(prefix+'before.json') for n in selected)
        maps.extend(run_maps)
        binding=next(r for r in native_bindings if r['label']==label);assert binding['run']==run
        for name,expected in binding['files'].items():
            if prefix+name in original:assert sha(original[prefix+name])==expected
        result={'stage':stage,'source':head,'exit_code':run['exit_code'],'run_receipt_raw_sha256':sha(original[prefix+'run-receipt.json']),'log_sha256':run['log_sha256'],'log_admitted':prefix+'run.log' in original,'map_inputs_each':1522,'maps':selected,'harness_raw_sha256':run['harness']}
        assert run['exit_code']==(1 if stage=='counter-red' else 0)
        if stage!='counter-red':
            facts=obj(prefix+'receipt.json');assert binding['facts']==facts
            assert facts['source']==head and facts['before_after_exact'] is True
            assert sha(original[prefix+'run.log'])==run['log_sha256']
            for k in ['actual_CLI','actual_remote_model','actual_tool_process']:assert facts[k]=='NOT_RUN'
            for capture in facts['screenshots']:assert sha(original[prefix+capture['file']])==capture['sha256']
            result.update(status=facts['status'],synthetic_memory_requests=facts['synthetic_memory_requests'],synthetic_literal_operations=facts['synthetic_literal_operations'])
        if stage.startswith('counter'):
            observation=obj(prefix+'counter-observation.json');assert observation['source']==head
            assert observation['actual_approve_status']==403 and observation['approval_pending']=='pending' and observation['approval_revision']==1 and observation['prior_approve_retained'] is True
            assert observation['safe_decline_enabled']==(stage=='counter-green') and observation['literal_executed'] is False and observation['synthetic_memory_requests']==1
            result['observation']=observation
        native_results.append(result)
    for name in ['native.mjs','controlled_api.py','run.py']:
        assert original['native/counter-red/'+name]==original['native/counter-green/'+name]
    total_runtime_bindings=sum(r['count'] for r in maps)
    assert len(maps)==20 and total_runtime_bindings==30440
    assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('status','--porcelain').decode()==''
    return {
        'read_at_utc':datetime.now(timezone.utc).isoformat(),'review_kind':'INDEPENDENT_PURE_SOURCE_AND_ADMITTED_ARCHIVAL_EVIDENCE_READBACK_NOT_NEW_TEST_EXECUTION',
        'source_delta':source_result,'owner_explicit_raw_seals':explicit,
        'approved_candidate_base':str(ADMITTED),'approved_candidate_count':93,'approved_png_count':10,
        'candidates':[{'candidate_path':n,'raw_sha256':e['raw_sha256'],'candidate_sha256':e['candidate_sha256'],'raw_bytes':e['raw_bytes'],'candidate_bytes':e['candidate_bytes'],'transformation':e['transformation'],'verified':True} for n,e in entries.items()],
        'full_immutable_git_heads':12,'full_immutable_git_head_input_bindings':all_head_bindings,'distinct_fixed_git_blobs':1517,
        'relative_412_owned_paths':full_delta,'relative_412_unchanged_existing_inputs':1511,
        'selected_gate_pairs':6,'selected_native_runs':3,'selected_native_successful_after_pairs':2,
        'selected_runtime_maps':maps,'selected_runtime_input_bindings':total_runtime_bindings,
        'selected_gate_results':stage_results,'selected_native_results':native_results,
        'counter_three_harness_files_red_green_full_bytes_equal':True,
        'unselected_historical_boundary':'27GATE_BINDINGS and4NATIVE_BINDINGS summary metadata read, but only6selected gate pairs and3selected native runs have admitted actual maps. Other21gate pairs and prior9epositive native not independently rebound from originals in this delta.',
        'red_failure_log_boundary':'Both component and native RED raw logs excluded and unread. Component counts3F19P come from selected safe owner qualifications/report; selected native observation/failure directly read. Receipts/log hashes preserved.',
        'manual_image_review_status':'Reviewer individually viewed all10 explicitly admitted PNGs through view_image. CounterRED pendingr1 is disabled; counterGREEN pendingr1 is enabled; positive learner safe decline is disabled after its saved decline. Mobile views are portions of long panels, not whole command/ACK evidence.',
        'manual_image_review_paths':[name for name in entries if name.endswith('.png')],
        'overall_platform_boundary':'Parent reported separate full native412FAIL132PASS1FAIL; this reviewer did not read that full run here. It is not replaced by43focused/final scoped evidence.',
        'actual_CLI':'NOT_RUN','actual_remote_provider':'NOT_RUN','actual_host_sandbox':'NOT_RUN','new_product_tests_executed':False,'remote_publication':False,'canonical_source_edited':False,
    }

if __name__=='__main__':
    readback=evidence_readback();target=OUT/'READBACK.json';assert not target.exists();target.write_text(json.dumps(readback,indent=2)+'\n')
    print(json.dumps({k:readback[k] for k in ['approved_candidate_count','approved_png_count','full_immutable_git_heads','full_immutable_git_head_input_bindings','distinct_fixed_git_blobs','selected_gate_pairs','selected_native_runs','selected_runtime_input_bindings']},indent=2))
