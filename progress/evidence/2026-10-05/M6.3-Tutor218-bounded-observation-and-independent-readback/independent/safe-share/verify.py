"""Pure immutable Git and explicit safe-only original evidence readback."""
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

ROOT = Path('$HOME/.cache/learning-workbench-acceptance/m63-tutor-completion-observation-oct04')
EVIDENCE = ROOT.parent / 'm63-tutor-completion-observation-evidence-oct04'
PACK = Path(__file__).resolve().parent
BASE = '1a6473dadcf71623008188f465586495ab28a204'
RED = 'd34acd3838bd59b55c012aa72f9d373d0c7825f4'
HEAD = '21877782cc6b7861acb23fc8bc040d22fbf6c225'
SPEC = 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
PATHS = ['tests/e2e/tutor-completion.spec.ts','tests/e2e/tutor.spec.ts','tests/e2e/tutorCompletion.ts']
STAGES = [('01-old-matcher',RED,1,[b'1 failed',b'2 passed (12.6s)']),
    ('02-fixed-tutor',HEAD,0,[b'6 passed (50.9s)']),
    ('03-native-types',HEAD,0,[]),('04-web-strict',HEAD,0,[])]
DIAG = ROOT.parent / 'm63-1a-tutor-ci-diagnosis-oct04/SAFE_SHARE/REPORT.md'
DIAG_SHA = 'd86e27b758b07be0857dd160df0c14ea80012da5c267480151a4f20a31245f54'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def load(path):
    return json.loads(path.read_bytes())


def reconstructed_source(candidate, item):
    if item['source_sha256']==item['sha256']:
        return candidate
    marker=b'<LOCAL_HOME>'
    parts=candidate.split(marker)
    replacements=(item['bytes']-item['source_bytes'])//3
    assert (item['bytes']-item['source_bytes'])%3==0 and len(parts)<=13
    matches=[]
    for indices in itertools.combinations(range(len(parts)-1),replacements):
        selected=set(indices)
        result=parts[0]
        for index,part in enumerate(parts[1:]):
            result+=(b'$HOME' if index in selected else marker)+part
        if len(result)==item['source_bytes'] and sha(result)==item['source_sha256']:
            matches.append(result)
    assert len(matches)==1
    return matches[0]


def tree(head):
    result = {}
    for item in git('ls-tree','-r','-z',head).split(b'\0'):
        if item:
            meta,name=item.split(b'\t',1)
            if name.startswith(b'progress/'):
                continue
            mode,kind,identifier=meta.split()
            assert kind == b'blob'
            result[name.decode()]={'mode':mode.decode(),'git_blob':identifier.decode()}
    return result


def main():
    assert git('merge-base',BASE,HEAD).decode().strip()==BASE
    assert git('rev-parse',HEAD+'^').decode().strip()==RED
    assert sorted(git('diff','--name-only',BASE,HEAD).decode().splitlines())==PATHS
    trees={head:tree(head) for head in (BASE,RED,HEAD)}
    assert len(trees[BASE])==1465 and len(trees[RED])==len(trees[HEAD])==1467
    assert set(trees[BASE])<=set(trees[HEAD])
    assert sum(trees[BASE][name]==trees[HEAD][name] for name in trees[BASE])==1464
    unique=sorted({item['git_blob'] for files in trees.values() for item in files.values()})
    output=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,input=('\n'.join(unique)+'\n').encode())
    objects,offset={},0
    for identifier in unique:
        stop=output.index(b'\n',offset)
        actual,kind,size=output[offset:stop].split()
        assert actual.decode()==identifier and kind==b'blob'
        offset=stop+1
        data=output[offset:offset+int(size)]
        objects[identifier]={'sha256':sha(data),'bytes':len(data)}
        offset+=int(size)+1
    assert offset==len(output)
    assert all(objects[files['PRODUCT_DESIGN.md']['git_blob']]['sha256']==SPEC for files in trees.values())
    original=git('show',BASE+':tests/e2e/tutor.spec.ts')
    fixed=git('show',HEAD+':tests/e2e/tutor.spec.ts')
    assert fixed.count(b"import { expectTutorCompletion } from './tutorCompletion'\n")==1
    reversed_source=fixed.replace(b"import { expectTutorCompletion } from './tutorCompletion'\n",b'').replace(
        "await expectTutorCompletion(tutor.getByRole('heading', { name: '真实任务状态：completed', exact: true }))".encode(),
        "await expect(tutor.getByRole('heading', { name: '真实任务状态：completed', exact: true })).toBeVisible()".encode())
    assert reversed_source==original
    helper=git('show',HEAD+':tests/e2e/tutorCompletion.ts')
    assert b"expect.poll(() => completed.isVisible(), { timeout: 5000, intervals: [25] }).toBe(true)" in helper
    assert b'catch' not in helper and b'request' not in helper and b'click' not in helper
    assert git('show',RED+':tests/e2e/tutor-completion.spec.ts')==git('show',HEAD+':tests/e2e/tutor-completion.spec.ts')
    outer=load(EVIDENCE/'OUTER_METADATA.json')
    assert len(outer['files'])==5
    for item in outer['files']:
        data=(EVIDENCE/item['path']).read_bytes()
        assert sha(data)==item['sha256'] and len(data)==item['bytes']
    raw_manifest=load(EVIDENCE/'RAW_MANIFEST.json')
    raw_descriptors={item['path']:item for item in raw_manifest['files']}
    manifest=load(EVIDENCE/'SAFE_SHARE.json')
    assert len(manifest['entries'])==29
    raw,reviewed={},[]
    for item in manifest['entries']:
        candidate=(EVIDENCE/item['candidate']).read_bytes()
        assert sha(candidate)==item['sha256'] and len(candidate)==item['bytes']
        original=reconstructed_source(candidate,item)
        assert sha(original)==item['source_sha256'] and len(original)==item['source_bytes']
        assert original.replace(b'$HOME',b'<LOCAL_HOME>')==candidate
        descriptor=raw_descriptors[item['source']]
        assert descriptor['sha256']==item['source_sha256'] and descriptor['bytes']==item['source_bytes']
        raw[item['source']]=original
        reviewed.append({'source':item['source'],'candidate':item['candidate'],'sha256':sha(candidate),
            'original_sha256':sha(original),'bytes':len(candidate),
            'original_bytes_reconstructed_by_declared_transform':True})
    assert sha(raw['REPORT.md'])=='04bbc4dcdd45d751810543507d360864fe368751511d2ed98fb3c8ef80e8affe'
    binding=json.loads(raw['SOURCE_BINDING.json'])
    assert binding['base']==BASE and binding['red']==RED and binding['fixed']==HEAD
    assert sorted(binding['changed_paths'])==PATHS
    for item in binding['source_files']:
        assert sha(git('show',item['commit']+':'+item['path']))==item['sha256']
    stages,total=[],0
    for name,head,exit_code,summaries in STAGES:
        before=json.loads(raw[name+'/inputs-before.json'])
        after=json.loads(raw[name+'/inputs-after.json'])
        receipt=json.loads(raw[name+'/receipt.json'])
        assert before==after and receipt['head']==head and receipt['exit_code']==exit_code
        assert receipt['source_equal'] and receipt['input_count']==len(before)==1467
        assert set(before)==set(trees[head])
        for path,item in before.items():
            source=trees[head][path];value=objects[source['git_blob']]
            assert item['git_blob']==source['git_blob'] and item['sha256']==value['sha256'] and item['bytes']==value['bytes']
            total+=1
        assert sha(raw[name+'/runner.py'])==receipt['runner_sha256']
        if 'config_sha256' in receipt:
            assert sha(raw[name+'/playwright.config.ts'])==receipt['config_sha256']
            assert b'workers:1,retries:0' in raw[name+'/playwright.config.ts'] and b'timeout:30000' in raw[name+'/playwright.config.ts']
        if 'native_tsconfig_sha256' in receipt:
            assert sha(raw['native-tsconfig.json'])==receipt['native_tsconfig_sha256']
        log=raw[name+'/run.log']
        assert sha(log)==receipt['log_sha256'] and all(part in log for part in summaries)
        stages.append({'path':name,'head':head,'exit_code':exit_code,'input_count':1467,
            'command':receipt['command'],'log_sha256':sha(log),'seconds':receipt['seconds'],
            'runner_sha256':receipt['runner_sha256'],'config_sha256':receipt.get('config_sha256'),
            'receipt_original_sha256':sha(raw[name+'/receipt.json']),
            'before_original_sha256':sha(raw[name+'/inputs-before.json']),
            'after_original_sha256':sha(raw[name+'/inputs-after.json'])})
    diagnostic=DIAG.read_bytes()
    assert len(diagnostic)==7542 and sha(diagnostic)==DIAG_SHA
    source_inputs={name:{**item,**objects[item['git_blob']]} for name,item in sorted(trees[HEAD].items())}
    observed=git('rev-parse','HEAD').decode().strip()
    live_same=observed==HEAD and git('status','--porcelain')==b''
    if live_same:
        for path,item in source_inputs.items():
            assert sha((ROOT/path).read_bytes())==item['sha256']
    result={'recorded_at':datetime.now(timezone.utc).isoformat(),
        'status':'TUTOR_OBSERVATION_STATIC_AND_SAFE_ORIGINAL_GATE_READBACK_PASS',
        'base':BASE,'red':RED,'head':HEAD,'sole_spec_sha256':SPEC,'changed_paths':PATHS,
        'fixed_source_inputs':1467,'old_nonoverlap_unchanged':1464,
        'product_source_changed':False,'original_tutor_bytes_equal_after_import_assertion_reversal':True,
        'original_exact_locator_and_5000ms_budget_preserved':True,
        'new_dom_test_red_fixed_bytes_equal':True,'safe_candidates_verified':29,'outer_metadata_verified':5,
        'excluded_raw_files_read':False,'raw_manifest_descriptor_count_only':len(raw_descriptors),
        'safe_home_only_transform_equivalence_verified':True,'reviewed_safe_candidates':reviewed,
        'selected_original_gate_pairs':4,'git_map_bindings':total,'original_stages':stages,
        'old_ci_diagnosis_approved_candidate_sha256':DIAG_SHA,'old_ci_failure_status':'FAIL_RETAINED',
        'old_ci_unique_cause':'UNKNOWN; synthetic matcher timing is not original CI replay',
        'private_harness_before_input_map_claimed':False,
        'worktree_head_observed':observed,'worktree_equals_reviewed_source':live_same,
        'product_tests_executed_by_reviewer':False,'model_cli_network_host_probes_executed':False,
        'canonical_integration_claimed':False,'remote_ci_rerun_claimed':False,'whole_M6_3_accepted':False}
    for name,value in [('READBACK.json',result),('FIXED_SOURCE_INPUTS.json',{'head':HEAD,'count':1467,'files':source_inputs})]:
        path=PACK/name
        assert not path.exists()
        path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':result['status'],'fixed_inputs':1467,'git_map_bindings':total,
        'safe_candidates':29,'outer_metadata':5,'gate_pairs':4,'product_tests_executed_by_reviewer':False,
        'READBACK_sha256':sha((PACK/'READBACK.json').read_bytes())},sort_keys=True))


if __name__ == '__main__':
    main()
