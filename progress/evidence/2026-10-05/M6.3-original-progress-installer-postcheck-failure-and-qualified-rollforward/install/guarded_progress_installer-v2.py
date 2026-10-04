"""Private progress installer. Default --plan writes only this private folder.

Installation requires --install, the exact HEAD and the sealed PLAN SHA.
No git mutation, source push, network request or runtime data collection exists here.
"""
from __future__ import annotations
import argparse
import copy
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

sys.dont_write_bytecode = True
os.umask(0o077)
PRIVATE = Path(__file__).resolve().parent
ROOT = PRIVATE.parent / 'm62-public-safe-oct02'
PREPARED = PRIVATE / 'prepared-02'
REVIEW = PRIVATE / 'installer-review-v2-PREPARED07'
REGISTRY = PRIVATE / 'PREPARED07.json'
HEAD = '412abe09c519104d9dbd2b360eed3ff4f897f829'
SPEC = 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
OLD_FILES = ['progress/state.json', 'progress/CURRENT.md', 'progress/M6.3-next.md', 'progress/M6.3-bootstrap-acceptance.md']
ISSUE_SHA = 'ec3c59fae7628fc7c7104fbd8cecb904d8120ace90d7843dbb2a6027a3247e63'
NATIVE_SHA = '5e426eec31979b7c9b79299cd85f3d9fb33f82cba11a06e72055faa07367af2a'
NEXT = ('保留412完整native实际132PASS/1FAIL及原因UNKNOWN；完成d69两行测试生命周期修复的独立审阅，'
        '等待root固定d69完整native实际终态，再正常整合已闭合但未合入的Generic43与受审修复、冻结新组合门禁；'
        'd69当前RUNNING与三个子集PASS不升级旧完整套件，不把1522输入隔离结果借给412。'
        '实际生产完整InputProof/Provider/Broker、物理数值环境及来源数学教学质量和整个M6.3/AC21/M7仍未验收；'
        '不重启已中止系统探针，不自动调用模型、不上传密钥。')

def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def json_bytes(value: object) -> bytes: return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()
def load(path: Path): return json.loads(path.read_bytes())
def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=ROOT, env={**os.environ, 'GIT_OPTIONAL_LOCKS':'0'})
def safe_path(base: Path, name: str) -> Path:
    p=PurePosixPath(name)
    if p.is_absolute() or not p.parts or any(x in ('..','.') for x in p.parts) or p.as_posix()!=name:
        raise ValueError('Non-canonical relative path: '+name)
    target=base.joinpath(*p.parts)
    for ancestor in [target, *target.parents]:
        if ancestor==base.parent: break
        if ancestor.is_symlink(): raise ValueError('Symlink refused: '+str(ancestor))
    return target
def exclusive(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(data); handle.flush(); os.fsync(handle.fileno())
    assert path.read_bytes()==data
def check_base():
    assert git('rev-parse','HEAD').decode().strip()==HEAD, 'Expected clean412 HEAD changed'
    assert git('status','--porcelain','--untracked-files=all')==b'', 'Canonical must be completely clean'
    assert sha((ROOT/'PRODUCT_DESIGN.md').read_bytes())==SPEC
    assert not (ROOT/'progress/state.tmp').exists(), 'Refuse existing progress save temporary'
    for name in OLD_FILES: assert safe_path(ROOT,name).is_file()
def progress_api():
    sys.path.insert(0,str(ROOT))
    spec=importlib.util.spec_from_file_location('guarded_progress_api',ROOT/'scripts/progress.py')
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.ROOT==ROOT and module.STATE==ROOT/'progress/state.json'
    return module

def packet_inventory():
    prepared=load(REGISTRY)
    reports=prepared['evidence_paths']
    assert reports and len(set(reports))==len(reports) and prepared['canonical_modified'] is False
    inventory=[]
    for report in reports:
        assert report.startswith('progress/evidence/2026-10-05/M6.3-') and report.endswith('/REPORT.json')
        packet=PurePosixPath(report).parent.as_posix()
        src=safe_path(PREPARED,packet); dest=safe_path(ROOT,packet)
        assert src.is_dir() and not os.path.lexists(dest), 'Refuse existing destination: '+packet
        manifest=safe_path(src,'manifest.json'); entries=load(manifest)['entries']
        names=[e['file'] for e in entries]
        assert 'REPORT.json' in names and 'manifest.json' not in names
        descriptors={}
        for entry in entries:
            if entry['file'] in descriptors: assert entry==descriptors[entry['file']], 'Conflicting duplicate descriptor'
            descriptors[entry['file']]=entry
        for entry in entries:
            path=safe_path(src,entry['file']); data=path.read_bytes()
            assert sha(data)==entry['published_sha256'], 'Prepared published SHA mismatch: '+str(path)
        expected=set(names)|{'manifest.json'}
        actual=set()
        for path in src.rglob('*'):
            assert not path.is_symlink(), 'Unexpected symlink in admitted packet'
            if path.is_file(): actual.add(path.relative_to(src).as_posix())
        assert actual==expected, 'Unlisted packet contents refused: '+packet
        for name in sorted(expected):
            data=safe_path(src,name).read_bytes()
            inventory.append({'path':packet+'/'+name,'sha256':sha(data),'bytes':len(data)})
    issue_reports=[r for r in reports if '/M6.3-Issue32-actual412-progress-managed-sync/' in r]
    assert len(issue_reports)==1
    issue=PREPARED/PurePosixPath(issue_reports[0]).parent/'actual-managed-Issue/READBACK.json'
    fact=load(issue)
    assert fact['body_sha256']==ISSUE_SHA and fact['recorded_at']=='2026-10-04T17:03:10.840639+00:00'
    assert fact['public_pr_head']=='1a6473dadcf71623008188f465586495ab28a204'
    return reports, inventory

def propose(old: dict, reports: list[str]) -> dict:
    state=copy.deepcopy(old)
    assert state['project']=='Learning_Workbench' and state['spec_version']=='3.0.15' and state['spec_sha256']==SPEC
    task=next(t for t in state['tasks'] if t['id']=='M6.3')
    assert task['status']=='in_progress'
    root_updates={'implementation':'IN_PROGRESS','active_task_id':'M6.3','next_task_id':'M6.3','next_action':NEXT,
        'task_sync':'VERIFIED_ISSUE32_MANAGED412_BODY_ORIGINAL_NATIVE_RUNNING_SNAPSHOT_CURRENT_NATIVE_FAIL_LOCAL_ONLY',
        'task_sync_readback_at':'2026-10-04T17:03:10.840639+00:00',
        'task_sync_last_scope':'Actual Issue32 managed block only at17:03:10.840639UTC; bodyec3c59; publicPRhead1a. That historical remote body still recorded nativeRUNNING; current local132P1F is not falsely claimed remotely synchronized.'}
    checkpoint={'source_head':HEAD,'status':'LOCAL_COMBINATION_WEB_STATIC_PASS_FULL_NATIVE_FAILED_UNPUBLISHED',
        'python':{'source_head':'4353a05570afd9f2378c904b5594998de21bc474','passed':4341,'numeric_environment_skips':2,
            'qualification':'Original4353 actual result.974 nonWeb/e2e inputs, including564Python, remain byte-equal at412; no claim Python rerun at412.'},
        'web':{'source_head':HEAD,'passed':1359,'static_passed':7},
        'native':{'source_head':HEAD,'status':'FAIL','passed':132,'failed':1,'elapsed_reported':'24.1m',
            'log_sha256':NATIVE_SHA,'provenance':'Root terminal safe packet explicitly listed by PREPARED07; original full raw failed log remains private, only admitted limited excerpt/hash copied.',
            'input_boundary':'1512 complete inputs;5 original generated outputs actually changed;1502 non-generated inputs unchanged. Original diffs preserved; no reset/restore/copyback.','cause':'NOT_DETERMINED'},
        'generic_approval':{'source_head':'43c70d660d98904903bd607a4661b3b95710293e','status':'INDEPENDENT_CLOSED_STATIC_UNMERGED',
            'inputs':1522,'web_passed':1399,'qualification':'Original9e P2OPEN retained; final43 owner tests/native and root exact candidate readback remain isolated. Only the registry-explicit admitted documents are copied; final independent Standards/Spec review reports zero new findings and P2 CLOSED_STATIC, still unmerged.'},
        'd69_test_repair':{'source_head':'d69de81045ff6c9ff2f345643f0fd412e2d108fb','parent':'43c70d660d98904903bd607a4661b3b95710293e','status':'TWO_LINE_TEST_ONLY_INDEPENDENT_REVIEW_PENDING_UNMERGED','subset_passed':3,'full_native':'RUNNING','full_native_started_at':'2026-10-04T17:37:16.347494+00:00','qualification':'No terminal claim; original412 fullFAIL and causeUNKNOWN retained. Controlled lifecycle mechanism and later original single-case PASS do not establish unique historical cause.'},
        'publication_head':'1a6473dadcf71623008188f465586495ab28a204','public_pr':'draft/open/unmerged',
        'whole_M6_3':'in_progress/not_accepted','evidence_paths':reports}
    task_updates={'status':'in_progress','verification':'4353_PYTHON4341_PASS_2_NUMERIC_ENV_SKIP_974_NONWEB_CONTINUITY_QUALIFIED;412_WEB1359_STATIC7_PASS_NATIVE132_PASS_1_FAIL;GENERIC43_CLOSED_STATIC_UNMERGED_D69_FULL_NATIVE_RUNNING;wholeM6.3/AC21_NOT_ACCEPTED',
        'next_action':NEXT,'candidate_implementation_commit':HEAD,
        'source_publication_status':'PUBLIC1A_UNCHANGED_LOCAL412_UNPUBLISHED_NATIVE_FAILED_GENERIC43_UNMERGED',
        'last_issue_body_sha256':ISSUE_SHA,'last_issue_readback_at':'2026-10-04T17:03:10.840639+00:00',
        'current_acceptance_blockers':['Production complete-input proof/executor unavailable; actual provider/model turn not accepted',
            'Physical numeric BLOCKED_ENVIRONMENT; no fallback',
            'Original412 complete native132PASS1FAIL; explicit terminal safe packet admitted, causeUNKNOWN; d69 complete rerun RUNNING separately',
            'Generic43 independent P2 CLOSED_STATIC and unmerged; d69 two-line test repair independent review pending before integration',
            'Physical Broker/host tools/writer-stop/resources and academic source/mathematical/teaching acceptance pending',
            'Interrupted extended system review retained; not restarted or declared resolved'],
        'current_local_checkpoint':checkpoint,
        'artifact_pending_integration':{'status':'INTEGRATED_LOCALLY_IN4353_AND412_UNPUBLISHED','source_head':'51205a75c401911d98d54a42387fbaa43583da7f','previous_record':'preserved in checkpoint history','whole_platform':'NOT_ACCEPTED'},
        'sse_pending_integration':{'status':'REVIEWED_SSE95_AND_FRONTEND80_LOCALLY_INTEGRATED_IN412_UNPUBLISHED','previous_record':'preserved in checkpoint history','whole_platform':'NOT_ACCEPTED'}}
    history=state.setdefault('checkpoint_history',[])
    marker='M6.3-412-progress-v2-packets-2026-10-05'
    assert not any(v.get('id')==marker for v in history), 'Checkpoint already installed'
    history.append({'id':marker,'previous_verification_current_fields':{k:copy.deepcopy(old['verification'][k]) for k in ['unit','contract','integration','spec_checks','browser_native','real_codex','real_provider']},
        'previous_checkpoint':copy.deepcopy(old['checkpoint']), 'previous_root_values':{k:copy.deepcopy(state.get(k)) for k in root_updates},
        'previous_task_values':{k:copy.deepcopy(task.get(k)) for k in task_updates},
        'previous_task_evidence_paths':copy.deepcopy(task['evidence_paths']),
        'qualification':'Prior records retained verbatim as values; full original state/CURRENT/next/bootstrap bytes are privately hash-backed before installation.'})
    state.update(root_updates); task.update(task_updates)
    current_verification = {
        'unit':'当前源码412；完整Python实际在4353为4341PASS/2真实numeric BLOCKED_ENVIRONMENT skip。974个非Web/e2e输入（含564Python）在412逐字连续；这是4353完整结果的明确适用范围，不是412重新运行。',
        'contract':'当前412沿用4353完整Python聚合4341PASS/2actual numeric ENVskip及974非Web/e2e输入连续性；未声明另一个独立contract子集计数，不能与聚合相加。',
        'integration':'当前412沿用4353完整Python聚合4341PASS/2actual numeric ENVskip及974非Web/e2e输入连续性；未声明另一个独立integration子集计数。物理numeric仍环境阻断，无回退。',
        'spec_checks':'当前412、唯一v3.0.15/b140：82 generated artifacts、54core、147declared/134implemented/13missing，结构门禁PASS。412实际1359Web及七static PASS；结构检查不是整个M6.3/AC21验收。',
        'browser_native':'FAIL：固定412原完整make test-e2e实际132PASS/1FAIL、24.1m，logSHA'+NATIVE_SHA+'；5个原生成输出改变、1502非生成输入逐字不变，无reset/restore/copyback。历史原因UNKNOWN；后来原单case1PASS和d69三个子集PASS不升级该套件。d69完整重跑另记RUNNING。',
        'real_codex':'PHYSICAL_CODEX_MODEL_OR_TOOL_TURN_NOT_RUN：当前412未建立真实CLI模型回合或物理host工具执行验收。历史仅受限bootstrap控制记录与显式synthetic memory结果分别保留，不升级为完整Broker/资源/安全验收。',
        'real_provider':'PLATFORM_PROVIDER_NOT_RUN：生产完整请求ProofRegistry/executor没有符合要求的注册证明；本次未使用实际Provider/key。历史直连成功描述及其缺少可独立核验原HTTP回执的限定，完整保存在checkpoint_history.previous_verification_current_fields.real_provider，不据此声称当前平台Provider通过。',
    }
    state['verification'].update(current_verification)
    branch=git('branch','--show-current').decode().strip()
    assert branch=='feat/M6.3-local-control-bootstrap'
    state['checkpoint'].update({
        'reason':'Current local412 qualified Python continuity/Web/static PASS with original complete nativeFAIL; wholeM6.3 remains in_progress.',
        'next_task_id':'M6.3','next_action':NEXT,'resume_branch':branch,'resume_base_code_commit':HEAD,
        'local_worktree_branch':branch,'local_resume_branch':branch,
        'local_resume_tree':'$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02',
        'local_resume_engineering_anchor':HEAD,'local_candidate_code_commit':HEAD,
        'publication_head':'1a6473dadcf71623008188f465586495ab28a204',
        'working_tree':'Local412 unpublished; Artifact512/SSE95/AA/218/8f/80 integrated. Generic43 independent CLOSED_STATIC unmerged; d69 test-only review pending/full nativeRUNNING. WholeM6.3 in_progress.',
        'previous_goal_turn':'4353 completePython4341PASS2actualnumericENVskip qualified by974nonWeb/e2e continuity;412 Web1359/static7PASS/fullnative132P1FAIL with5generatedchanges/1502non-generatedexact. Public1a unchanged; no newactualCI/sourcepush.',
    })
    assert all(p not in task['evidence_paths'] for p in reports)
    task['evidence_paths'].extend(reports)
    assert task['evidence_paths'][:-len(reports)]==next(t for t in old['tasks'] if t['id']=='M6.3')['evidence_paths']
    key='m6_3_412_current_local_checkpoint_v2_2026_10_05'
    assert key not in state['verification']
    state['verification'][key]=copy.deepcopy(checkpoint)
    code='M63_412_COMPLETE_NATIVE_FAILED'
    assert not any(b['code']==code for b in state['blockers'])
    state['blockers'].append({'code':code,'status':'ACTUAL_FULL_SUITE_FAIL_TERMINAL_SAFE_PACKET_RETAINED_D69_RERUN_RUNNING',
        'description':'固定412原完整native132PASS1FAIL/24.1m；logSHA'+NATIVE_SHA+'。原5生成输出变化与1502非生成输入一致性保留；原因未确立，不能借1359Web、旧套件或隔离43PASS关闭。'})
    assert code not in task['blockers']; task['blockers'].append(code)
    # Existing verification records, unrelated tasks, repository and old blockers are untouched.
    assert all(state['verification'][k]==v for k,v in old['verification'].items() if k not in current_verification)
    assert history[-1]['previous_verification_current_fields']=={k:old['verification'][k] for k in current_verification}
    assert history[-1]['previous_checkpoint']==old['checkpoint']
    assert state['blockers'][:-1]==old['blockers'] and state['repository']==old['repository']
    assert [t for t in state['tasks'] if t['id']!='M6.3']==[t for t in old['tasks'] if t['id']!='M6.3']
    return state

def intro(reports: list[str]) -> bytes:
    text=f'''# 2026-10-05 本地412已整合受审界面；完整native终态失败，Generic43独审闭合尚未整合

唯一v3.0.15规范SHA `{SPEC}`。canonical固定 `{HEAD}`；公开PR56仍是1a6473dadcf71623008188f465586495ab28a204，draft/open/unmerged，本地412未发布。Artifact512、只读SSE95及已审AA/218/8f/80已正常本地整合；旧失败/审阅原记录不改。

4353完整Python实际4341PASS/2真实数值ENVskip；412的974个非Web/e2e输入（含564Python）逐字同4353，沿用只限该输入连续性，不冒充412重跑Python。412实际1359Web及七static PASS。Root现已报告原完整native132PASS/1FAIL、24.1m，logSHA `{NATIVE_SHA}`；5个原生成输出实际变化、1502非生成输入不变，原差异保留，没有restore/reset/copyback。失败具体原因未确立。PREPARED07已明确纳入root终态安全包的限定片段/hash；不复制完整native失败原日志、DB或profile。旧包RUNNING只是原时点，不覆盖当前FAIL。

Generic43在隔离1522输入树完成1399Web/strict/build/spec与限定合成native；原9e安全拒绝P2 OPEN及真实RED保留。final43已独立Standards/Spec零新增、P2 CLOSED_STATIC，仍未合入412，不能借其PASS关闭412完整native失败或宣称全平台审批/物理操作完成。d69父43只有两行测试生命周期修复，三个子集PASS，独审pending；root固定d69完整native于2026-10-04T17:37:16.347494UTC启动、当前RUNNING，无终态声称。

Issue32管理区块实际读回于2026-10-04T17:03:10.840639UTC，bodySHA `{ISSUE_SHA}`；该原远端快照仍记录native RUNNING。这里不谎称后来FAIL已同步到远端。没有sourcepush、stage、commit、GitHubmerge/release/deploy或实钥使用。

下一任务：{NEXT}

本次新增原时点证据包：
'''
    text+=''.join('- `'+p+'`\n' for p in reports)
    text+='\n以下历史时点原文字节保留。\n\n'
    return text.encode()

def plan():
    check_base(); reports, inventory=packet_inventory(); api=progress_api(); original=api.read_state()
    proposed=propose(original,reports)
    REVIEW.mkdir(mode=0o700)
    backups={}
    for name in OLD_FILES:
        data=(ROOT/name).read_bytes(); exclusive(REVIEW/'before'/name,data)
        backups[name]={'sha256':sha(data),'bytes':len(data)}
    shadow=REVIEW/'proposed'; (shadow/'progress').mkdir(parents=True)
    api.STATE=shadow/'progress/state.json'; api.save(proposed)
    for name in OLD_FILES[2:]: exclusive(shadow/name,intro(reports)+(ROOT/name).read_bytes())
    for name in OLD_FILES:
        a=(ROOT/name).read_text().splitlines(keepends=True); b=(shadow/name).read_text().splitlines(keepends=True)
        exclusive(REVIEW/'diffs'/(Path(name).name+'.diff'),''.join(difflib.unified_diff(a,b,fromfile=name+' before',tofile=name+' proposed')).encode())
    result={'status':'PREPARED_NOT_INSTALLED','expected_head':HEAD,'spec_sha256':SPEC,
        'installer_sha256':sha(Path(__file__).read_bytes()),'registry_sha256':sha(REGISTRY.read_bytes()),'registry':REGISTRY.name,
        'progress_api_sha256':sha((ROOT/'scripts/progress.py').read_bytes()),'originals':backups,
        'reports':reports,'packet_files':inventory,'packet_count':len(reports),'packet_file_count':len(inventory),
        'proposed':{n:sha((shadow/n).read_bytes()) for n in OLD_FILES},
        'timestamp_boundary':'Actual installation calls progress.save; only updated_at/CURRENT generated timestamp differs from the reviewed proposal.',
        'write_boundary':'Explicit packet files plus4 progress documents only. No .gitattributes/source/Git metadata/index/stage/commit/push. All existing evidence/history retained.'}
    exclusive(REVIEW/'PLAN.json',json_bytes(result)); check_base()
    print(json.dumps({'status':result['status'],'plan':str(REVIEW/'PLAN.json'),'sha256':sha((REVIEW/'PLAN.json').read_bytes()),'packets':len(reports),'files':len(inventory),'canonical_modified':False}))

def install(expected: str, plan_sha: str):
    assert expected==HEAD and sha((REVIEW/'PLAN.json').read_bytes())==plan_sha, 'Explicit reviewed plan/HEAD required'
    record=load(REVIEW/'PLAN.json'); check_base()
    assert record['registry']==REGISTRY.name
    assert sha(Path(__file__).read_bytes())==record['installer_sha256']
    assert sha((REGISTRY).read_bytes())==record['registry_sha256']
    assert sha((ROOT/'scripts/progress.py').read_bytes())==record['progress_api_sha256']
    reports,inventory=packet_inventory(); assert inventory==record['packet_files'] and reports==record['reports']
    for name,entry in record['originals'].items():
        assert sha((ROOT/name).read_bytes())==entry['sha256']
        assert (REVIEW/'before'/name).read_bytes()==(ROOT/name).read_bytes()
    api=progress_api(); original=api.read_state(); new=propose(original,reports)
    reviewed=load(REVIEW/'proposed/progress/state.json')
    reviewed.pop('updated_at'); compare=copy.deepcopy(new); compare.pop('updated_at')
    assert reviewed==compare, 'Proposed semantic delta drift'
    for name in OLD_FILES:
        assert sha((REVIEW/'proposed'/name).read_bytes())==record['proposed'][name]
    backup=PRIVATE/REVIEW.name.replace('installer-review-','installer-execution-',1); backup.mkdir(mode=0o700)
    for name in OLD_FILES: exclusive(backup/'before'/name,(ROOT/name).read_bytes())
    exclusive(backup/'BEFORE.json',json_bytes({'head':HEAD,'plan_sha256':plan_sha,'files':record['originals']}))
    for name,entry in record['originals'].items(): assert sha((backup/'before'/name).read_bytes())==entry['sha256']
    # Second guard after backup and before the first canonical write.
    check_base(); assert api.read_state()==original
    copied=[]
    try:
        for report in reports:
            safe_path(ROOT,PurePosixPath(report).parent.as_posix()).mkdir(parents=True,exist_ok=False)
        for entry in inventory:
            data=safe_path(PREPARED,entry['path']).read_bytes(); assert sha(data)==entry['sha256']
            exclusive(safe_path(ROOT,entry['path']),data); copied.append(entry['path'])
        for entry in inventory: assert sha((ROOT/entry['path']).read_bytes())==entry['sha256']
        assert git('rev-parse','HEAD').decode().strip()==HEAD and api.read_state()==original
        assert git('diff','--name-only')==b'' and git('diff','--cached','--name-only')==b''
        # Use the actual install timestamp through the repository save/render API.
        api.save(new)
        for name in OLD_FILES[2:]:
            assert sha((ROOT/name).read_bytes())==record['originals'][name]['sha256']
            (ROOT/name).write_bytes((REVIEW/'proposed'/name).read_bytes())
        actual=api.read_state(); expected_state=copy.deepcopy(new)
        assert actual==expected_state and actual['spec_sha256']==SPEC
        assert git('rev-parse','HEAD').decode().strip()==HEAD and git('diff','--cached','--name-only')==b''
        changed=set(git('diff','--name-only').decode().splitlines()); assert changed==set(OLD_FILES)
        untracked=set(git('ls-files','--others','--exclude-standard').decode().splitlines())
        assert untracked=={e['path'] for e in inventory}, 'Unexpected canonical untracked path'
        for name in OLD_FILES: exclusive(backup/'after'/name,(ROOT/name).read_bytes())
        exclusive(backup/'RESULT.json',json_bytes({'status':'INSTALLED_UNSTAGED_UNCOMMITTED_LOCAL_ONLY','head':HEAD,'plan_sha256':plan_sha,'copied':copied,'after':{n:sha((ROOT/n).read_bytes()) for n in OLD_FILES},'history_preserved':True}))
        print('INSTALLED_UNSTAGED_UNCOMMITTED_LOCAL_ONLY')
    except BaseException as error:
        exclusive(backup/'PARTIAL_FAILURE.json',json_bytes({'status':'PARTIAL_PRESERVED_NO_ROLLBACK','error_type':type(error).__name__,'copied':copied,'boundary':'No reset/restore/overwrite/retry. Inspect exact private backup and canonical diff before any recovery.'}))
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(); mode.add_argument('--plan',action='store_true'); mode.add_argument('--install',action='store_true')
    p.add_argument('--expected-head'); p.add_argument('--plan-sha256'); p.add_argument('--registry',default='PREPARED07.json'); p.add_argument('--review-name'); args=p.parse_args()
    if not __debug__: raise RuntimeError('Optimized Python disables guards and is refused')
    assert Path(args.registry).name==args.registry and args.registry.startswith('PREPARED') and args.registry.endswith('.json')
    REGISTRY=safe_path(PRIVATE,args.registry)
    review_name=args.review_name or 'installer-review-v2-'+REGISTRY.stem
    assert Path(review_name).name==review_name and review_name.startswith('installer-review-')
    REVIEW=safe_path(PRIVATE,review_name)
    if args.install:
        assert args.expected_head and args.plan_sha256
        install(args.expected_head,args.plan_sha256)
    else:
        assert not args.expected_head and not args.plan_sha256
        plan()
