"""Pure fixed-source and selected original Web evidence readback; no product execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('$HOME/.cache/learning-workbench-acceptance/m63-turn-form-status-race-oct04')
BASE = ROOT.parent
PACK = Path(__file__).resolve().parent
OLD = '4353a05570afd9f2378c904b5594998de21bc474'
RED = '62d0b53101815efc1e6da336b78b1efd2c2228ae'
HEAD = 'aa85092f73aa85b53eb200039ee5b4b8ccbb63c1'
SPEC = 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
EVIDENCE = BASE / 'm63-turn-form-status-race-evidence-oct04'
TEST = 'apps/web/src/features/codex/CodexTurnPanel.test.tsx'
HOOK = 'apps/web/src/features/codex/useCodexTurns.ts'
STAGES = [('delayed-save-red',RED,1,[b'Tests  1 failed | 34 skipped (35)']),
    ('delayed-save-green',HEAD,0,[b'Tests  1 passed | 34 skipped (35)']),
    ('all-codex-regression',HEAD,0,[b'Test Files  15 passed (15)',b'Tests  296 passed (296)']),
    ('fixed-full-web',HEAD,0,[b'Test Files  157 passed (157)',b'Tests  1279 passed (1279)']),
    ('fixed-strict',HEAD,0,[]),('fixed-build',HEAD,0,[])]
PRIOR = BASE / 'm63-combined-source-independent-review-4353-oct04'
PRIOR_HASHES = {'SOURCE_STATIC_REVIEW.md':'74a726c47473658a6a86e1ce5901924e847cac784b73857b33a03fb454179420',
    'SOURCE_STATIC_REVIEW.json':'dbc11afbb0c42ebc4f1417d884a265c94431874277a294b0595ffab7a2e1d762',
    'READBACK.json':'91ba2866eef88820df8918b82673047f74164bd543a6ed137a4ed3157de5a3d8',
    'SAFE_SHARE.json':'ae2c5f172caaebd686775d06010f962c5f9c778d9075a2a2e1da23cf6ff35b94',
    'OUTER_ALLOWLIST.json':'a05bf5fe3041f2628cd3cb3936821b2f69cdd2509fe662b7a38c08b283d004b1'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def load(path):
    return json.loads(path.read_bytes())


def tree(head):
    result = {}
    for item in git('ls-tree','-r','-z',head).split(b'\0'):
        if item:
            meta,name = item.split(b'\t',1)
            if name.startswith(b'progress/'):
                continue
            mode,kind,identifier = meta.split()
            assert kind == b'blob'
            result[name.decode()] = {'mode':mode.decode(),'git_blob':identifier.decode()}
    return result


def main():
    assert git('merge-base',OLD,HEAD).decode().strip() == OLD
    assert git('rev-parse',HEAD+'^').decode().strip() == RED
    assert git('diff','--numstat',OLD,RED).decode().strip() == '32\t0\t'+TEST
    assert git('diff','--numstat',RED,HEAD).decode().strip() == '3\t2\t'+HOOK
    assert sorted(git('diff','--name-only',OLD,HEAD).decode().splitlines()) == sorted([TEST,HOOK])
    trees = {head:tree(head) for head in (OLD,RED,HEAD)}
    assert all(len(files) == 1493 for files in trees.values())
    assert set(trees[OLD]) == set(trees[HEAD])
    assert sum(trees[OLD][path] == item for path,item in trees[HEAD].items()) == 1491
    objects,offset = {},0
    unique = sorted({item['git_blob'] for files in trees.values() for item in files.values()})
    output = subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,input=('\n'.join(unique)+'\n').encode())
    for identifier in unique:
        stop = output.index(b'\n',offset)
        actual,kind,size = output[offset:stop].split()
        assert actual.decode() == identifier and kind == b'blob'
        offset = stop+1
        data = output[offset:offset+int(size)]
        objects[identifier] = {'sha256':sha(data),'bytes':len(data)}
        offset += int(size)+1
    assert offset == len(output)
    assert all(objects[files['PRODUCT_DESIGN.md']['git_blob']]['sha256'] == SPEC for files in trees.values())
    old_hook = git('show',OLD+':'+HOOK).decode()
    fixed_hook = git('show',HEAD+':'+HOOK).decode()
    condition = 'currentScope() && actorRef.current?.actor_session_id === next.actor_session_id && academic(actorRef.current) && writeAdmitted'
    fixed_block = '  const admitted = () => '+condition+'\n  const saving = writer(admitted)'
    old_block = '  const saving = writer(() => '+condition+')'
    assert fixed_hook.count(fixed_block) == 1
    reconstructed = fixed_hook.replace(fixed_block,old_block).replace('}).catch(() => { if (admitted()) setError(', '}).catch(() => { if (currentScope()) setError(')
    assert reconstructed == old_hook
    red_test = git('show',RED+':'+TEST)
    assert red_test == git('show',HEAD+':'+TEST)
    new_test = red_test.decode().split("test('late form-save failure cannot replace a fresh actor-denial notice or expose the original ACK', async () => {",1)[1].split("\ntest(",1)[0]
    assert new_test.index('await screen.findByText(/当前权限或原 actor 已变化/)') < new_test.index('await act(async () => saved.resolve())')
    assert "heldTurnCommands(workspace)[0].actor_session_id).toBe(actor)" in new_test
    assert "heldTurnCommands(workspace)[0].ack).toEqual(ack)" in new_test
    assert 'expect(port.prepare).toHaveBeenCalledOnce()' in new_test
    prior = {name:sha((PRIOR/name).read_bytes()) for name in PRIOR_HASHES}
    assert prior == PRIOR_HASHES
    assert load(PRIOR/'SOURCE_STATIC_REVIEW.json')['combined_actual_full_web']['status'] == 'FAIL'
    count,stages = 0,[]

    def original_stage(folder,head,exit_code,summaries,name):
        nonlocal count
        before,after,receipt,command = [load(folder/part) for part in ('before.json','after.json','receipt.json','command.json')]
        assert before == after and before['head'] == receipt['head'] == head
        assert receipt['exit_code'] == exit_code and receipt['before_after_git_exact']
        assert before['count'] == receipt['complete_nonprogress_git_inputs'] == 1493
        assert command['command'] == receipt['command']
        assert set(before['files']) == set(trees[head])
        for path,item in before['files'].items():
            source = trees[head][path]; actual = objects[source['git_blob']]
            assert item['git_blob'] == source['git_blob'] and item['sha256'] == actual['sha256'] and item['bytes'] == actual['bytes']
            if 'mode' in item:
                assert item['mode'] == source['mode']
            count += 1
        log = (folder/'run.log').read_bytes()
        assert sha(log) == receipt['log_sha256']
        assert all(summary in log for summary in summaries)
        if name == 'delayed-save-red':
            assert b'CodexTurnPanel.test.tsx:271' in log
        return {'path':name,'head':head,'exit_code':exit_code,'status':receipt['status'],'source_inputs':1493,
            'log_sha256':sha(log),'elapsed_seconds':receipt['elapsed_seconds'],
            'before_sha256':sha((folder/'before.json').read_bytes()),'after_sha256':sha((folder/'after.json').read_bytes()),
            'receipt_sha256':sha((folder/'receipt.json').read_bytes())}

    for name,head,exit_code,summaries in STAGES:
        stages.append(original_stage(EVIDENCE/name,head,exit_code,summaries,name))
    original_web = original_stage(BASE/'m63-4353-complete-combination-gates-oct04'/'full-web',OLD,1,
        [b'Test Files  1 failed | 156 passed (157)',b'Tests  1 failed | 1277 passed (1278)'],'original-4353-full-web')
    fixed = {path:{**item,**objects[item['git_blob']]} for path,item in sorted(trees[HEAD].items())}
    observed = git('rev-parse','HEAD').decode().strip()
    live_same = observed == HEAD and git('status','--porcelain') == b''
    if live_same:
        for path,item in fixed.items():
            assert sha((ROOT/path).read_bytes()) == item['sha256']
    result = {'recorded_at':datetime.now(timezone.utc).isoformat(),
        'status':'UI_REPAIR_STATIC_AND_ORIGINAL_GATE_READBACK_PASS','base':OLD,'red':RED,'head':HEAD,
        'sole_spec_sha256':SPEC,'changed_paths':[TEST,HOOK],'runtime_insertions':3,'runtime_deletions':2,
        'controlled_test_insertions':32,'fixed_source_inputs':1493,'unchanged_prior_inputs':1491,
        'write_guard_condition_unchanged':True,'runtime_only_catch_notification_admission_changed':True,
        'red_fixed_complete_test_file_bytes_equal':True,'controlled_denial_before_delayed_save_failure':True,
        'selected_repair_gate_pairs':6,'original_4353_web_fail_extra_pair':1,'git_map_bindings':count,
        'original_repair_stages':stages,'original_4353_full_web':original_web,
        'original_combination_open_fail_report_seals_unchanged':prior,
        'no_original_failure_log_total_event_trajectory_claim':True,
        'worktree_head_observed':observed,'worktree_equals_reviewed_fix':live_same,
        'canonical_merge_or_python_pass_claimed':False,'whole_M6_3_accepted':False,
        'product_tests_executed_by_reviewer':False,'model_cli_network_host_probes_executed':False,
        'raw_failure_logs_public':'HASH_ONLY'}
    for name,value in [('READBACK.json',result),('FIXED_SOURCE_INPUTS.json',{'head':HEAD,'count':1493,'files':fixed})]:
        path = PACK/name
        assert not path.exists()
        path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':result['status'],'fixed_inputs':1493,'unchanged_prior_inputs':1491,
        'gate_pairs':7,'git_map_bindings':count,'original_4353_web':'FAIL_RETAINED',
        'READBACK_sha256':sha((PACK/'READBACK.json').read_bytes()),
        'product_tests_executed_by_reviewer':False},sort_keys=True))


if __name__ == '__main__':
    main()
