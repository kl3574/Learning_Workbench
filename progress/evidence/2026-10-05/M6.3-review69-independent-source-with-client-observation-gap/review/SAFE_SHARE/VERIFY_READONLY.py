"""Independent pure Git/source and exactly admitted documentary readback.

This script does not execute products, models, CLI, browser or network probes.
It writes only new private review artifacts, never source or old evidence.
"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-review-route-lifecycle-owner-oct05')
OWNER=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-native412-review-route-diagnosis-oct05')
OUT=Path(__file__).parent
SOURCE='d69de81045ff6c9ff2f345643f0fd412e2d108fb'
BASE='43c70d660d98904903bd607a4661b3b95710293e'
OLD='412abe09c519104d9dbd2b360eed3ff4f897f829'
SPEC='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
blobs={};trees={}
def blob(oid):
    if oid not in blobs:blobs[oid]=git('cat-file','blob',oid)
    return blobs[oid]
def tree(head):
    if head in trees:return trees[head]
    rows={}
    for item in git('ls-tree','-rz',head).split(b'\0'):
        if not item:continue
        metadata,path=item.split(b'\t',1);mode,kind,oid=metadata.decode().split();path=path.decode()
        if path.startswith('progress/'):continue
        assert kind=='blob';data=blob(oid)
        rows[path]={'mode':mode,'type':kind,'git_blob':oid,'bytes':len(data),'sha256':sha(data)}
    trees[head]=rows;return rows
def untransform(data,entry):
    """Verify candidate hash and invert only its exact declared home prefix.

    Original failed full native log and all unlisted runtime files remain unread.
    A literal $HOME in original prose is disambiguated against the fixed raw hash.
    """
    assert len(data)==entry['bytes'] and sha(data)==entry['candidate_sha256']
    expected=entry['raw_sha256']
    if entry['redaction']=='none':assert sha(data)==expected;return data
    assert entry['redaction']=='Exact <LOCAL_HOME> -> $HOME only'
    for trial in [data,data.replace(b'$HOME',b'<LOCAL_HOME>')]:
        if sha(trial)==expected:
            assert trial.replace(b'<LOCAL_HOME>',b'$HOME')==data;return trial
    parts=data.split(b'$HOME');n=len(parts)-1;assert n<=20
    for mask in range(1<<n):
        trial=parts[0]
        for i,part in enumerate(parts[1:]):trial+=(b'<LOCAL_HOME>' if mask>>i&1 else b'$HOME')+part
        if sha(trial)==expected:
            assert trial.replace(b'<LOCAL_HOME>',b'$HOME')==data;return trial
    raise AssertionError(('home transform mismatch',entry['candidate']))

def verify():
    assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('status','--porcelain').decode()==''
    assert git('show','-s','--format=%P',SOURCE).decode().strip()==BASE
    changed=git('diff','--name-only',BASE,SOURCE).decode().splitlines();assert changed==['tests/e2e/review.spec.ts']
    assert git('diff','--numstat',BASE,SOURCE).decode().strip()=='2\t2\ttests/e2e/review.spec.ts'
    before=tree(BASE);fixed=tree(SOURCE);old=tree(OLD)
    assert len(before)==len(fixed)==1522 and len(old)==1512
    assert sum(fixed.get(p)==r for p,r in before.items())==1521
    assert fixed['PRODUCT_DESIGN.md']['sha256']==before['PRODUCT_DESIGN.md']['sha256']==old['PRODUCT_DESIGN.md']['sha256']==SPEC
    path=changed[0];old_test=blob(before[path]['git_blob']);new_test=blob(fixed[path]['git_blob'])
    assert old_test==blob(old[path]['git_blob'])
    expected=old_test.replace(b"release(); await expect(page.getByRole('region', { name: '\xe5\xae\x8c\xe6\x95\xb4\xe8\xaf\x84\xe5\x88\x86\xe5\x8e\x86\xe5\x8f\xb2' }))",b"release(); await page.unrouteAll({ behavior: 'wait' }); await expect(page.getByRole('region', { name: '\xe5\xae\x8c\xe6\x95\xb4\xe8\xaf\x84\xe5\x88\x86\xe5\x8e\x86\xe5\x8f\xb2' }))")
    expected=expected.replace(b"finally { release(); await page.unroute(routePattern); await other.close() }",b"finally { release(); await page.unrouteAll({ behavior: 'wait' }); await other.close() }")
    assert new_test==expected
    explicit={'SAFE_SHARE.json':'9c644140642e5134986a89c53893a3ab4941bf237f05ecec29313057e46e858e','OUTER_ALLOWLIST.json':'d0281e3483d9c447aae2950e38ebf096939e60d3465df2e2e82c678b57f26dae'}
    for name,expected in explicit.items():assert sha((OWNER/name).read_bytes())==expected
    safe=json.loads((OWNER/'SAFE_SHARE.json').read_text());outer=json.loads((OWNER/'OUTER_ALLOWLIST.json').read_text())
    assert safe['source_head']==SOURCE and len(safe['files'])==safe['count']==68
    admitted={};raw={};entries={}
    for e in safe['files']:
        name=e['candidate'];relative=Path(name);assert relative.parts[0]=='publication-candidates' and '..' not in relative.parts and not relative.is_absolute() and name not in entries
        data=(OWNER/relative).read_bytes();raw[name]=untransform(data,e);admitted[name]=data;entries[name]=e
    for e in outer['files']:
        assert e['path'] in ['SAFE_SHARE.json','PUBLICATION_SCAN.json'];data=(OWNER/e['path']).read_bytes();assert sha(data)==e['sha256'] and len(data)==e['bytes']
    assert len(outer['files'])==2
    report='publication-candidates/diagnosis/REPORT.md';readback='publication-candidates/diagnosis/READBACK.json'
    assert sha(raw[report])=='6a2851127660e8cf06841afe3bc2ac8d04cef1af1d56d6f49af61976216144f8'
    assert sha(raw[readback])=='681f1a60f4987379082bfcb4634e34a424745ac3df222094988eb8a6626eb2c6'
    def obj(name):return json.loads(admitted['publication-candidates/'+name])
    assert raw['publication-candidates/diagnosis/source-before-review.spec.ts']==old_test
    assert raw['publication-candidates/diagnosis/source-after-review.spec.ts']==new_test
    assert raw['publication-candidates/diagnosis/source-delta.patch']==git('diff',BASE,SOURCE)
    generated=obj('original-full-native412/generated-output-changes.json')
    expected_changes=set(generated['actual_changed_paths']);assert len(expected_changes)==5
    expected_generated=set(obj('original-full-native412/generated-output-paths.json')['paths']);assert len(expected_generated)==10 and expected_changes<expected_generated
    after_changed={r['path']:r for r in generated['after']};maps=[]
    def input_map(name):
        data=obj(name);head=data['head'];records=data['files'];normal={}
        if isinstance(records,list):
            assert len(records)==len({r['path']for r in records})
            for r in records:normal[r['path']]={k:v for k,v in r.items()if k!='path'}
        else:
            for p,r in records.items():normal[p]={'mode':r['git_mode'],'type':r['git_type'],'git_blob':r['git_blob'],'bytes':r['bytes'],'sha256':r['sha256']}
        actual=tree(head);assert data['count']==len(normal)==len(actual) and set(normal)==set(actual)
        exceptions=[]
        for p,r in normal.items():
            for k in ['mode','type','git_blob']:assert r[k]==actual[p][k]
            if name=='original-full-native412/inputs-after.json' and p in expected_changes:
                assert r=={k:v for k,v in after_changed[p].items()if k!='path'} and r['matches_git'] is False and r['actual_blob']!=r['git_blob'];exceptions.append(p)
            else:
                for k in ['bytes','sha256']:assert r[k]==actual[p][k]
                if 'actual_blob' in r:assert r['actual_blob']==r['git_blob'] and r['matches_git'] is True
        if exceptions:assert set(exceptions)==expected_changes and data['all_match_git'] is False
        elif 'status' in data:assert data['status']=='' and data['all_match_git'] is True
        item={'path':name,'head':head,'count':len(normal),'raw_sha256':sha(raw['publication-candidates/'+name]),'candidate_sha256':sha(admitted['publication-candidates/'+name]),'generated_runtime_exceptions':exceptions}
        maps.append(item);return data,normal
    groups=['original-full-native412','original412-single-test-observation','controlled-static-route-order','fixed-d69-native-review'];runs=[]
    for group in groups:
        command=obj(group+'/command.json');receipt=obj(group+'/receipt.json');head=command['source_sha'];assert receipt['source_sha']==head
        assert receipt['argv']==command['argv'] and receipt['spec_sha256']==SPEC
        assert command['runner_sha256']==sha(raw['publication-candidates/'+group+'/run.py'])
        b,bfiles=input_map(group+'/inputs-before.json');a,afiles=input_map(group+'/inputs-after.json')
        assert b['head']==a['head']==head
        for name in ['before','after']:assert receipt[name+'_map_sha256']==sha(raw['publication-candidates/'+group+'/inputs-'+name+'.json'])
        assert receipt['actual_diff_sha256']==sha(raw['publication-candidates/'+group+'/actual-tracked-diff.patch'])
        changes=sorted(p for p in bfiles if bfiles[p]!=afiles[p]);assert changes==sorted(receipt['actual_generated_output_changes'])
        assert receipt['unchanged_total_inputs']==len(bfiles)-len(changes)
        assert receipt['all_non_generated_inputs_unchanged'] is True and all(bfiles[p]==afiles[p]for p in bfiles if p not in expected_generated)
        assert receipt['non_generated_input_count']==len(bfiles)-10 and receipt['inputs_count']==len(bfiles)
        log='publication-candidates/'+group+'/native.log';result={'group':group,'head':head,'argv':command['argv'],'exit_code':receipt['exit_code'],'wrapper_exit_code':receipt['wrapper_exit_code'],'native_log_sha256':receipt['native_log_sha256'],'whole_log_admitted':log in raw,'original_suite_summary':receipt['actual_suite_summary'],'elapsed_seconds':receipt['elapsed_seconds'],'map_inputs_each':len(bfiles),'generated_changes':changes}
        if log in raw:assert sha(raw[log])==receipt['native_log_sha256']
        if group=='original-full-native412':
            assert receipt['exit_code']==2 and receipt['wrapper_exit_code']==1 and len(changes)==5 and receipt['complete_inputs_unchanged'] is False
            assert len(bfiles)-len(changes)==1507 and receipt['non_generated_input_count']==1502
        else:
            assert receipt['exit_code']==receipt['wrapper_exit_code']==0 and b==a and not changes and receipt['complete_inputs_unchanged'] is True
        runs.append(result)
    stages=['web-strict','diff-check','review-strict','review-strict-type-root','review-strict-official-declaration'];static=[]
    for stage in stages:
        prefix='fixed-d69-optional-and-required-gates/'+stage
        command=obj(prefix+'/command.json');receipt=obj(prefix+'/receipt.json');assert command['command']==receipt['command'] and receipt['head']==SOURCE
        b,_=input_map(prefix+'/before.json');a,_=input_map(prefix+'/after.json');assert b==a and receipt['before_after_git_exact'] is True and receipt['complete_nonprogress_git_inputs']==1522
        log=raw['publication-candidates/'+prefix+'/run.log'];assert sha(log)==receipt['log_sha256']
        assert receipt['exit_code']==(1 if stage in ['review-strict','review-strict-type-root']else 0)
        static.append({'stage':stage,'source':SOURCE,'command':command['command'],'exit_code':receipt['exit_code'],'log_sha256':receipt['log_sha256'],'map_inputs_each':1522,'scope':'Existing Web src/vite gate' if stage=='web-strict'else 'Private bounded optional Review declaration bridge'if stage=='review-strict-official-declaration'else 'Actual command only; preserved failures stay failures'})
    assert len(maps)==18 and sum(m['count']for m in maps)==27336
    original=obj('diagnosis/ORIGINAL_FULL_READBACK.json');excerpt=raw['publication-candidates/diagnosis/original-full-failure-excerpt.raw.txt']
    assert sha(excerpt)==original['failure']['original_excerpt_sha256']
    assert original['failure']['original_full_log_sha256']==runs[0]['native_log_sha256'] and original['original_full_cause'].startswith('UNKNOWN')
    assert b'Route is already handled!'in excerpt and b'132 passed (24.1m)'in excerpt and b'1 failed'in excerpt
    mechanism=obj('controlled-static-route-order/route-order-result.json');assert mechanism['model_requests']==0 and len(mechanism['cases'])==2 and mechanism['original_full_suite_cause'].startswith('UNKNOWN')
    assert mechanism['cases'][0]['fulfill_error']=='route.fulfill: Route is already handled!' and mechanism['cases'][1]['fulfill_error'] is None
    fixedlog=admitted['publication-candidates/fixed-d69-native-review/native.log'].decode()
    assert re.search(r'3 passed \(38\.4s\)',fixedlog) and fixedlog.count('tests/e2e/review.spec.ts:')==2 and fixedlog.count('tests/e2e/draft-review.spec.ts:')==1
    singlelog=admitted['publication-candidates/original412-single-test-observation/native.log'].decode();assert '1 passed (15.2s)'in singlelog
    primary={}
    for path in ['apps/web/node_modules/playwright-core/package.json','apps/web/node_modules/playwright-core/lib/coreBundle.js','apps/web/node_modules/playwright-core/types/types.d.ts']:
        data=(ROOT/path).read_bytes();primary[path]={'bytes':len(data),'sha256':sha(data)}
    assert json.loads((ROOT/'apps/web/node_modules/playwright-core/package.json').read_text())['version']=='1.63.0'
    assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('status','--porcelain').decode()==''
    return {'read_at_utc':datetime.now(timezone.utc).isoformat(),'review_kind':'INDEPENDENT_PURE_SOURCE_AND_EXPLICIT_DOCUMENTARY_EVIDENCE_READBACK_NOT_NEW_TESTS','source_sha':SOURCE,'parent_sha':BASE,'sole_spec_sha256':SPEC,'fixed_inputs':1522,'unchanged_parent_inputs':1521,'changed_paths':changed,'source_diff_numstat':'2+/2-','source_before':before[changed[0]],'source_after':fixed[changed[0]],'all_other_product_spec_config_inputs_exact':True,'owner_explicit_outer_hashes':explicit,'owner_candidate_count':68,'owner_candidate_raw_hashes_reconstructed_home_only':True,'owner_candidates':[{'candidate':n,'raw_sha256':e['raw_sha256'],'candidate_sha256':e['candidate_sha256'],'candidate_bytes':e['bytes'],'redaction':e['redaction'],'verified':True}for n,e in entries.items()],'actual_input_maps':maps,'actual_input_map_count':18,'actual_input_entry_bindings':27336,'exact_immutable_Git_byte_bindings':27331,'original_generated_runtime_exceptions':sorted(expected_changes),'runtime_exception_boundary':'5 original full-after generated output entries checked against declared changes/patch; unselected runtime PNG/JSON bytes not reopened or visually reviewed here. All other27331 map rows exact to immutable Git bytes.','selected_original_runs':runs,'selected_static_runs':static,'controlled_mechanism':mechanism,'local_official_primary_code':primary,'local_official_version':'1.63.0','handler_wait_vs_UI_completion_boundary':'unrouteAll wait completes already-running route handlers, including fulfill, before interception update; it does not automatically prove completion of Response.json, generated API client or React late-response handling. Original count assertions observed hidden at that time and serverGET409; no broader business completion claim.','original_full_run_cause':'UNKNOWN','original_full_run_status':'FAIL132PASS1FAIL, makeexit2/wrapperexit1; unchanged by subset results','original_whole_failed_log_read':False,'original_unlisted_failure_screenshot_read':False,'new_full_d69_run':'Parent separateRUNNING not read or counted in this packet','new_product_tests_executed':False,'source_or_canonical_edited':False,'remote_publication':False,'actual_CLI':'NOT_RUN','actual_remote_provider':'NOT_RUN','whole_platform_acceptance':'NOT_CLAIMED'}

if __name__=='__main__':
    value=verify()
    for name,data in [('READBACK.json',value),('FIXED_SOURCE_INPUTS.json',{'head':SOURCE,'count':1522,'files':tree(SOURCE)})]:
        target=OUT/name;assert not target.exists();target.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:value[k]for k in ['source_sha','fixed_inputs','unchanged_parent_inputs','owner_candidate_count','actual_input_map_count','actual_input_entry_bindings','exact_immutable_Git_byte_bindings','original_full_run_status']},indent=2))
