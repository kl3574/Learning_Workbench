import datetime
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

B = Path('$HOME/.cache/learning-workbench-acceptance')
R = B / 'm62-public-safe-oct02'
O = Path(__file__).parent
H = '3265a1f381547e6a84f6acd9ab931bcf6078ed13'
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_text())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip() == H
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=R)
spec = importlib.util.spec_from_file_location('public_package', B / 'm62-v313-pushed-progress-sync-oct03/package.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def sealed(folder, style):
    P = B / folder
    safe, outer = read(P / 'SAFE_SHARE.json'), read(P / 'PUBLIC_OUTER_ALLOWLIST.json')
    names = []
    for e in safe.get('files', safe.get('explicit_candidates', [])):
        if style == 'interrupt':
            raw, candidate = (P / e['raw_path']).read_bytes(), (P / e['candidate_path']).read_bytes()
            assert sha(raw) == e['raw']['sha256'] and len(raw) == e['raw']['bytes']
            assert candidate == raw.replace(b'$HOME', b'<LOCAL_HOME>')
            assert sha(candidate) == e['candidate']['sha256'] and len(candidate) == e['candidate']['bytes']
            name = e['candidate_path']
        elif style == 'exact':
            name = e['candidate']
            raw, candidate = (P / e['source']).read_bytes(), (P / name).read_bytes()
            assert raw == candidate and sha(raw) == e['sha256'] and len(raw) == e['bytes']
        else:
            raw = (P / e['path']).read_bytes()
            name = 'safe-share/' + e['path']
            candidate = (P / name).read_bytes()
            assert sha(raw) == e['raw_sha256'] and len(raw) == e['raw_bytes']
            assert candidate == raw.replace(b'$HOME', b'$HOME')
            assert sha(candidate) == e['public_sha256'] and len(candidate) == e['public_bytes']
        assert not m.inspect('progress/' + name, candidate)
        names.append(name)
    outer_entries = outer['files']
    if isinstance(outer_entries, dict):
        outer_entries = [{'path': name, **e} for name, e in outer_entries.items()]
    for e in outer_entries:
        name = e['path']
        raw = (P / name).read_bytes()
        assert sha(raw) == e['sha256'] and len(raw) == e['bytes']
        assert not m.inspect('progress/' + name, raw)
        names.append(name)
    return names

generic = sealed('m63-generic-approval-evidence-oct04', 'home')
generic_peer = sealed('m63-generic-approval-static-fdd3a949-oct04', 'exact')
interrupt = sealed('m63-turn-interrupt-evidence-oct04', 'interrupt')
interrupt_peer = sealed('m63-interrupt-independent-static-79a3-oct04', 'home')
assert len(generic) == 78 and len(generic_peer) == 10
assert len(interrupt) == 61 and len(interrupt_peer) == 5
G = B / 'm63-unsupported-interrupt-combined-gates-oct04'
gates = read(G / 'GATES.json')
assert gates['head'] == H and len(gates['gates']) == 6 and all(e['exit_code'] == 0 for e in gates['gates'])
assert (G / 'before.json').read_bytes() == (G / 'after.json').read_bytes()
before = read(G / 'before.json')
assert before['head'] == H and before['count'] == 1444
tree = {}
for row in subprocess.check_output(['git', 'ls-tree', '-rz', H], cwd=R).split(b'\0'):
    if not row:
        continue
    meta, name = row.split(b'\t', 1)
    if not name.startswith(b'progress/'):
        tree[name.decode()] = meta.split()[2].decode()
assert set(tree) == set(before['files'])
for name, e in before['files'].items():
    raw = (R / name).read_bytes()
    assert sha(raw) == e['sha256'] and len(raw) == e['bytes'] and e['git_blob'] == tree[name]
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == tree[name]
for e in gates['gates']:
    assert sha((G / (e['name'] + '.log')).read_bytes()) == e['log_sha256']

sync = read(B / 'm63-3265-isolated-native-Issue32-sync-oct04/READBACK.json')
readback = {'status': 'ROOT_3265_COMPLETE_INPUT_AND_EXPLICIT_SEAL_READBACK_PASS',
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'head': H, 'complete_nonprogress_git_count': 1444, 'six_static_pass': True,
    'generic_candidates_and_outer': len(generic), 'generic_peer_candidates_and_outer': len(generic_peer),
    'interrupt_candidates_and_outer': len(interrupt), 'interrupt_peer_candidates_and_outer': len(interrupt_peer),
    'boundary': 'Actual source/blob/candidate checks only; no new product tests. Whole3265 Python/native NOT_RUN; original29e complete gates are separately bound. Pure-memory closure and UI remain isolated. No sourcepush/merge/release/deploy.'}
(O / 'READBACK.json').write_text(json.dumps(readback, indent=2) + '\n')
groups = {
 'generic': [('owner-explicit', 'm63-generic-approval-evidence-oct04', generic),
     ('peer-explicit', 'm63-generic-approval-static-fdd3a949-oct04', generic_peer),
     ('root-static-and-original-verifier', 'm63-generic-approval-root-review-oct04',
       ['REVIEW.json', 'REVIEW_INITIAL_COUNT_WORDING.json', 'COUNT_WORDING_CORRECTION.json',
        'READBACK.json', 'verify.stdout', 'verify.stderr']),
     ('root-full-git-readback', 'm63-native-generic-root-readback-oct04',
       ['generic-git-readback.py', 'GENERIC_GIT_READBACK.json'])],
 'interrupt': [('owner-explicit', 'm63-turn-interrupt-evidence-oct04', interrupt),
     ('peer-explicit', 'm63-interrupt-independent-static-79a3-oct04', interrupt_peer),
     ('root-static-and-original-verifier', 'm63-turn-interrupt-root-static-79a3c0da-oct04',
       ['REVIEW.json', 'COMMIT_TASK_ID_PROCESS_CORRECTION.json', 'ORIGINAL_MIGRATION_LOCATOR_FAILURE.json',
        'owner-verify.json', 'owner-verify.stdout', 'owner-verify.stderr',
        'git-maps-readback.py', 'FINAL_MAPS_READBACK.json'])],
 'combined': [('actual-local-integration', 'm63-next-owners-canonical-integration-oct04',
       ['merge.py'] + [part + '/' + name for part in ['unsupported-approval', 'interrupt']
        for name in ['command.json', 'before.json', 'after.json', 'receipt.json', 'merge.stdout', 'merge.stderr']]),
     ('combined-six-static', G.name, ['run.py', 'before.json', 'after.json', 'GATES.json']
       + [e['name'] + '.log' for e in gates['gates']]),
     ('root-seal-and-input-readback', O.name, ['install.py', 'READBACK.json']),
     ('root-UI-and-interrupt-candidates', 'm63-ui-interrupt-candidates-root-readback-oct04', ['readback.py', 'READBACK.json'])],
 'publication': [('actual-sourcepush', 'm63-source-publication-4b5516bd-oct04',
       ['push.py', 'push.log', 'push-result.json', 'readback.json', 'fresh-readback-02.json', 'pr-body.md']),
     ('actual-PR-and-Issue-sync', 'm63-published-4b5516bd-PR56-Issue32-sync-oct04',
       ['sync.py', 'readback.json', 'pr-body.md', 'issue-body.md', 'pr-patch.invocation.json', 'issue-patch.invocation.json']),
     ('exact-CI-current-metadata', 'm63-4b-CI-current-readback-oct04', ['readback.py', 'READBACK.json']),
     ('actual-local3265-Issue-sync', 'm63-3265-isolated-native-Issue32-sync-oct04',
       ['sync.py', 'READBACK.json', 'issue-body.md', 'issue-patch.invocation.json'])]}
# Check every exact candidate before the first canonical mutation.
for group in groups.values():
    for alias, folder, names in group:
        for name in names:
            raw = (B / folder / name).read_bytes()
            safe = raw.replace(b'$HOME', b'$HOME').replace(b'$RUNNER_HOME', b'$RUNNER_HOME')
            assert not m.inspect('progress/' + alias + '/' + name, safe)
(O / 'GROUPS.json').write_text(json.dumps(groups, indent=2) + '\n')
paths = []
paths.append(m.package('M6.3-unsupported-approval-fdd-reviewed-local-integration', groups['generic'], {
    'status': 'UNSUPPORTED_APPROVAL_OWNER171_PASS_ROOT_AND_PEER_REVIEWED_LOCAL_INTEGRATION',
    'source': 'fdd3a949fc9bc6edb2d136b912f3d8d1cdba4b81',
    'scope': 'Unsupported pending/read/decline only; strict original callback/ACK/history/stop transaction. Owner171PASS/2warnings and sixstatic, root original offline verifier0 and peer static; root does not claim separate product execution. Canonical integration62b exact16ownerpaths/nonoverlap preserved.',
    'boundary': 'No approve_once/claim/accept/host execution, production registry empty. Old failures and root count-wording correction retained. WholeM6.3 unaccepted.'}))
paths.append(m.package('M6.3-turn-interrupt-79a-reviewed-local-integration', groups['interrupt'], {
    'status': 'INTERRUPT_OWNER1160_PASS_ROOT_AND_PEER_REVIEWED_LOCAL_INTEGRATION',
    'source': '79a3c0da4bef9d948bcd6a969a25ff55fd5833a0',
    'scope': 'Independent interrupt command/eventv4 plus shared Jobs request_stop; original ACK replay before CAS, sameTX stop, no cancel-key namespace collision. Owner1160PASS/2warnings and fivestatic, root original offline verifier0/all six1428maps Git-checked and peer static. Original3RED and runner/locator errors retained.',
    'process_deviation': 'Two sealed source commit messages omit task_id M6.3. Not amended; normal canonical3265 integration message includesM6.3. Root initial missed processfinding explicitly corrected.',
    'boundary': 'Original cancel route and v1/v2/v3 models retained. No actual CLI interruption, late externalprovider or wholeM6.3 acceptance.'}))
paths.append(m.package('M6.3-local3265-unsupported-interrupt-six-static-and-source-preservation', groups['combined'], {
    'status': 'LOCAL3265_SIX_STATIC_PASS_COMPLETE1444_INPUTS_EXACT_NEW_FULL_GATES_NOT_RUN',
    'source': H, 'actual': 'Normal no-force local merges4b→62b→3265; both reviewed owner path sets exact and all preexisting nonoverlap bytes unchanged. Ruff/mypy273/generator82/spec54core147declared/strict/build exit0, full1444Git beforeafter exact.',
    'routes': '130 actual/147declared/17unregistered; Web source unchanged and fullWeb not repeated here.',
    'boundary': '3265 completePython/native NOT_RUN, unpushed. 29e4085Python/2numericENVskip/1201Web/native130 do not accept later3265 or isolated UI/tool. Production proof missing,0actualmodels, physicalnumericBLOCKED, entireM6.3 incomplete.'}))
paths.append(m.package('M6.3-public4b-sourcepush-and-local3265-current-sync', groups['publication'], {
    'status': 'ACTUAL4B_SOURCEPUSH_PR_AND_ISSUE_READBACK_LOCAL3265_REMAINING_UNPUSHED',
    'public_head': '4b5516bd2a78d7b39f9b4a4c321a6d91ad4ca78f',
    'sourcepush': 'Actual push exit0; initial PR oldhead mismatch FAIL retained, freshbranch/PR exacthead verified without repeatingpush. PR56 draft/open/unmerged/basePR55e287.',
    'ci': 'Exact4b push37200167062 andPR37200168176 currentmetadata9success/3inprogress; no fullterminal/rawlogs acceptance.',
    'issue': sync,
    'boundary': 'No GitHubmerge/release/deploy. Later3265 unpushed; no actual externalmodel/CLI, numericalblocked/academicNOT_RUN/wholeM6.3 incomplete.'}))

s = m.read_state()
t = next(x for x in s['tasks'] if x['id'] == 'M6.3')
t['evidence_paths'] += paths
action = '完成隔离83d工具完整门禁及闭合读回，正常整合已验外发UI92与工具，保留中断v4/操作v5历史与原ACK；冻结新组合运行完整Python/Web/静态及native。继续独立受检产物source/stop receipt/manifest与普通Import草稿事务，核公开4b实际CI终态；生产proof缺失零真实模型、整个M6.3/AC21和M7未完成。'
s['next_action'] = t['next_action'] = action
t['source_publication_status'] = 'PUBLIC4B_VERIFIED_LOCAL3265_UNPUSHED_COMBINED_FULL_GATES_NOT_RUN'
t['candidate_implementation_commit'] = H
t['implementation_commit'] = '29e864a6157f3bb23c6ced5d1a2f34f77bf3b875'
t['last_issue_body_sha256'] = sync['issue_body_sha256']
t['last_issue_readback_at'] = sync['recorded_at']
t['remaining_contract']['runtime_registered_operations'] = 130
t['remaining_contract']['status'] = 'LOCAL3265_UNSUPPORTED_INTERRUPT_STATIC_PASS_LATEST_FULL_SOURCE29E_ONLY'
t['remaining_contract']['runtime_acceptance'] = 'LATEST_COMBINATION_FULL_GATES_NOT_RUN_REAL_PROVIDER_AND_WHOLE_M63_NOT_ACCEPTED'
s['verification']['m6_3_latest_checkpoint'] = '当前canonical3265：正常整合fddunsupported+79ainterrupt、1444完整Git exact，130实际/147声明/17未注册，六静态PASS；组合完整Python/native NOT_RUN。最后完整受测29e4085Python/2数值ENVskip/1201Web/static/native130不借给新源码。公开4b实际普通push/freshPRhead一致；原首读FAIL保留，新CI metadata9success/3running未终态。'
s['verification']['m6_3_isolated_next_owners'] = 'UI92完整1278Web/157files、214旧owner/132新related及新真实Chrome32.33s PASS；生产phase0请求，受信phase1 memory synthetic response，真实CLI/模型NOT_RUN，尚未合。原9d/3120 runtime closureP2仍OPEN历史；83d55定向/6static与独审CLOSED_STATIC，完整相关RUNNING，未合。manifest/Import仅真route404RED、实施未完成。'
s['task_sync'] = 'VERIFIED_ISSUE32_LOCAL3265_ISOLATED_NATIVE_BODY_ONLY_PUBLIC4B_UNCHANGED'
s['task_sync_readback_at'] = sync['recorded_at']
s['checkpoint']['local_resume_engineering_anchor'] = H
s['checkpoint']['previous_goal_turn'] = '公开4b实际push已fresh读回；fdd/79a正常本地整合3265与六static固定1444Git PASS，组合全量未跑。隔离UI92真实Chrome/1278WebPASS，tool83d闭合门禁进行中。旧失败/原wrapperFAIL/数值BLOCKED与真实Provider/CLI/质量NOT_RUN保留；0真实外部模型，无GitHubmerge/release/deploy。'
s['checkpoint']['working_tree'] = '3265 reviewed engineering anchor; this checkpoint only progress evidence/doc changes, public4b unchanged'
m.save(s)
lead = '# 2026-10-04 公开4b已验证；本地3265审批/中断静态通过，整体验收继续\n\n唯一规范v3.0.15 b140保持。实际公开4b普通push exit0，首读PR旧head断言FAIL保留，fresh branch/PR56 exact4b一致；没有重复push，PR56draft/open/unmerged。新CI仅当前metadata9success/3running，未全部终态、未核原joblogs。\n\n本地正常整合fdd unsupported审批与79a独立中断到3265，两组16/12来源路径逐字一致、其余原文件不变；1444完整Git输入固定六静态PASS，130实际/147声明/17未注册。新组合完整Python/native NOT_RUN、未推送。最后完整29e Python4085PASS/2数值ENVskip、1201Web/static、native130PASS及原wrapperFAIL只证旧来源。\n\n隔离UI92完整1278Web/157files、214旧owner/132新related与真实Chrome32.33s通过；四原key完整ACK丢失/刷新不自动POST、失权保留failed+complete原响应与API/Chrome重启持久化实测。生产空proof phase无模型执行，受信fixture恰1次memory响应，实际CLI/外部模型NOT_RUN；6截图有的仅长JSON局部，不称每图完整显示状态。尚未整合canonical。工具83d55定向/六static与独审CLOSED_STATIC、完整related正在运行，原9d/3120OPEN/6e5FAIL保留；未合。\n\n整体M6.3/AC21、物理Broker/受检writer停止/manifest/普通Import草稿回导及M7未完成；生产proof缺失、物理数值BLOCKED_ENVIRONMENT、来源数学教学审查NOT_RUN。本轮无真实外部模型请求，未上传key、未GitHubmerge/release/deploy。\n\n下一任务：' + action + '\n\n以下历史时点原样保留。\n\n'
for name in ['M6.3-next.md', 'M6.3-bootstrap-acceptance.md']:
    p = R / 'progress' / name
    p.write_text(lead + p.read_text())
p = R / 'progress/issues/M6.3.md'
old = p.read_text()
a, z = '<!-- engineering_progress:start -->', '<!-- engineering_progress:end -->'
assert old.count(a) == old.count(z) == 1
p.write_text(old.split(a)[0] + a + '\n' + (B / 'm63-3265-isolated-native-Issue32-sync-oct04/issue-body.md').read_text().split(a)[1].split(z)[0] + z + old.split(z)[1])
(O / 'INSTALLED_PATHS.json').write_text(json.dumps({'paths': paths, 'source': H, 'sourcepush': False}, indent=2) + '\n')
print(json.dumps({'status': 'CURRENT3265_PROGRESS_INSTALLED_LOCAL_ONLY', 'packages': len(paths)}))
