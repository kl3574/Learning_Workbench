import importlib.util
from pathlib import Path

BASE = Path('$HOME/.cache/learning-workbench-acceptance')
ROOT = BASE / 'm62-public-safe-oct02'
spec = importlib.util.spec_from_file_location('progress_module', ROOT / 'scripts/progress.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
state = module.read_state()
task = next(t for t in state['tasks'] if t['id'] == 'M6.3')
assert state['spec_version'] == '3.0.14' and task['implementation_commit'] is None
task['verification'] = ('Canonical1843556e adopts approved v3.0.14 bootstrap and reviewed narrow fixes. Backenddf0 focused264PASS; actual045 HTTP201/ready r2, one restricted zero-model CLI and zero replay starts. UIa480 repairs initial false→true write admission invalidating a legitimate read; controlled RED preserved. Test-only f321 waits button readiness: completeWeb1038PASS/145files plus strict/buildPASS. Newnativea4801PASS; formalcompletebd3 native128PASS0FAIL0skip/exit0/1worker0retry with17628 tracked/1381 engineering Git-exact before/after independently verified. Browser proves two API OS processes/same DB/five original ACK byte-equal replays, not independently counted CLI starts. CompleteDCF Python3683PASS1FAIL2setupERROR2physicalnumericENVSKIP/exit1 remains sealed FAIL. Known legacy backup test oracle corrected test-onlyb51→canonical184; originalRED retained, seven relatedfiles65PASS (single included), static review no blocker. Two setup error causes UNKNOWN; bounded readonly metadata shows nonterminal persisted Jobs only. Newdetached184 exactcompletePython3688collected RUNNING, no terminal claim. Originalad494/a2d9/a480 failures and three actualv2unknown instances unchanged. FullM6.3/AC21/Broker/M7/realProvider/quality unaccepted; no sourcepush/merge/release/deploy.')
task['next_action'] = '收集固定1843556e同命令完整Python终态；不以65相关PASS替代原完整FAIL、不推断两个setup错误原因。完成新增证据与全部对象公开准入后推送独立M6.3源码分支并建立可审draft PR；继续唯一规范已定义的下一垂直切片，完整M6.3保持in_progress。'
for name in ('M6.3-bootstrap-web-and-native-actual-readback', 'M6.3-bootstrap-complete-native-bd3b', 'M6.3-bootstrap-complete-python-dcfda8c2-failure', 'M6.3-bootstrap-original-setup-errors-metadata', 'M6.3-legacy-backup-test-correction-and-review'):
    report = 'progress/evidence/2026-10-03/' + name + '/REPORT.json'
    assert (ROOT / report).is_file()
    if report not in task['evidence_paths']:
        task['evidence_paths'].append(report)
task['bootstrap_candidates'].update({
    'canonical_integration': 'dcfda8c270dff3e6db75011c50ffa7d6f5826512; original completePythonFAIL3683PASS1F2E2ENVskip retained',
    'ui_initial_read_fix': 'a48033ff9fe4beb78e5458b9806d7933d9faff66; production2-file narrow fix; newnative1PASS; controlledRED retained',
    'ui_readiness_test_only': 'f321c6f9574451c2e4d75f3be40cd9427e7bd4f5; fullWeb1038PASS/145files; line23read-result assertion unchanged',
    'canonical_full_native': 'bd3b9375b41cf9a726260e7497a7302f11c3db04; complete128PASS0FAIL0skip; all17628tracked/1381engineering Git inputs unchanged',
    'legacy_backup_test_only': 'b51de327fe74cdc476a52e061fe2e044072d2267; sevenfiles65PASS, no production/native/timeout change',
    'canonical_current_engineering': '1843556e1c01b48e60082969e78d2a82b3848b45; legacytestcherry plus testedbd3 source; exactcompletePythonRUNNING',
})
for blocker in state['blockers']:
    if blocker['code'] == 'M63_BOOTSTRAP_NATIVE_INITIAL_READ_INVALIDATED':
        blocker['status'] = 'FIXED_A480_FOCUSED_AND_NEW_NATIVE_PASS_FORMAL128_PASS'
        blocker['description'] = '原a2d9首次读取FAIL保留。受控父面板RED复现false→true初始写准入取消合法只读响应，a480窄修后新case通过且固定bd3完整native128PASS；f321只等待写按钮真实ready，完整Web1038PASS。原失败原因唯一性不作额外推断。'
    if blocker['code'] == 'M63_SESSION_BOOTSTRAP_CONSENT_CONTRACT_GAP':
        blocker['description'] = '375e55c0已批准纳入唯一v3.0.14，五个真实端点与单次许可已实施。固定045实际受限控制201/ready；新原生浏览器和API OS重启、显式回放通过，flags仍false。完整M6.3仍未验收，不是待授权阻塞。'
codes = {b['code'] for b in state['blockers']}
for blocker in (
    {'code': 'M63_DCF_COMPLETE_PYTHON_FAILURE', 'status': 'FAIL_PRESERVED_KNOWN_LEGACY_ORACLE_FIXED_NEW_FULL_GATE_RUNNING', 'description': 'DCF完整Python3683PASS/1FAIL/2setupERROR/2实际数值ENVSKIP，exit1。过时备份测试期待清空actor引用与M7保历史合同冲突，b51仅修该测试、65相关PASS；canonical184完整同命令另跑中，原门禁不升级。'},
    {'code': 'M63_DCF_SETUP_ERRORS_CAUSE_UNKNOWN', 'status': 'UNKNOWN_TWO_ORIGINAL_SETUP_ERRORS_PRESERVED', 'description': 'Provider-owner[single]与Review guards[extra_body-decision]在setup缺终态，正文未执行。精确关联后只读合成数据库状态为running r3/r2；UTC/monotonic差值已记，不足以证明租约/宿主原因。未恢复原实例或削弱租约/权限。'},
):
    assert blocker['code'] not in codes
    state['blockers'].append(blocker); task['blockers'].append(blocker['code'])
task['last_issue_body_sha256'] = 'a95b60a29050822c18155c7c25510f68bba981542f102b9228c9aeeb4d6fdcca'
task['last_issue_readback_at'] = '2026-10-03T14:20:01.650942+00:00'
state['active_task_id'] = state['next_task_id'] = 'M6.3'
state['next_action'] = task['next_action']
checkpoint = state['checkpoint']
for key in ('resume_branch', 'local_resume_branch', 'local_worktree_branch'):
    checkpoint[key] = 'feat/M6.3-local-control-bootstrap'
checkpoint['previous_goal_turn'] = task['verification']
checkpoint['working_tree'] = 'canonical1843556e整合approvedbootstrap/窄UI修复/legacy测试修正；本地证据进度更新中。固定184 detached完整Python运行中；固定bd3完整native128PASS。原用户checkout clean b895保留。M6.3源码尚未push。'
checkpoint['local_resume_engineering_anchor'] = '1843556e1c01b48e60082969e78d2a82b3848b45'
state['verification']['M6.3-bootstrap-current-complete-gates'] = task['verification']
module.save(state)
print('Current actual gates recorded; complete Python184 still RUNNING; M6.3 remains in_progress/unaccepted')
