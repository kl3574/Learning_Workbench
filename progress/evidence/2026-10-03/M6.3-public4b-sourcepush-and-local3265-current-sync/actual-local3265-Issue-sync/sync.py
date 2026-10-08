import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

O = Path(__file__).parent
B = O.parent
R = B / 'm62-public-safe-oct02'
H = '4b5516bd2a78d7b39f9b4a4c321a6d91ad4ca78f'
L = '3265a1f381547e6a84f6acd9ab931bcf6078ed13'
repo = 'repos/kl3574/Learning_Workbench/'
sha = lambda b: hashlib.sha256(b).hexdigest()
assert not (O / 'issue-before.json').exists()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip() == L
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=R)
def call(label, args):
    p = subprocess.run(args, capture_output=True)
    (O / (label + '.stdout')).write_bytes(p.stdout)
    (O / (label + '.stderr')).write_bytes(p.stderr)
    (O / (label + '.invocation.json')).write_text(json.dumps({'args': args, 'exit_code': p.returncode,
       'stdout_sha256': sha(p.stdout), 'stderr_sha256': sha(p.stderr)}, indent=2) + '\n')
    assert p.returncode == 0
    return json.loads(p.stdout)
pr = call('pr-before', ['gh', 'api', repo + 'pulls/56'])
issue = call('issue-before', ['gh', 'api', repo + 'issues/32'])
(O / 'pr-before.json').write_text(json.dumps(pr))
(O / 'issue-before.json').write_text(json.dumps(issue))
assert pr['head']['sha'] == H and pr['draft'] and pr['state'] == 'open' and pr['merged_at'] is None
assert sha(pr['body'].encode()) == 'd690ccc6b6c2bf8e4debfbf293cd8ae5cbfac7e413a6bdbb01b9247df00f289d'
assert sha(issue['body'].encode()) == 'daf13d9831644198305a9b10cca0a5a1d37aa7d8219f1bd0e84319b302ebce54'
pattern = r'<!-- engineering_progress:start -->.*?<!-- engineering_progress:end -->'
assert len(re.findall(pattern, issue['body'], re.S)) == 1
block = '''<!-- engineering_progress:start -->
当前 M6.3 in_progress / AC21 未完成；唯一规范 v3.0.15 b140764e，不存在待用户批准的已采纳合同阻塞。

实际公开 head 4b5516bd2a78d7b39f9b4a4c321a6d91ad4ca78f，普通 push exit0；首读 PR 旧头的断言 FAIL 与 fresh 读回一致分别保留，未重复 push。PR56 draft/open/unmerged，base PR55/e287；未 GitHub merge/release/deploy。

最后完整本地受测 source 29e864a6：1433 完整非 progress Git 输入前后一致；Python 4085 PASS / 2 实际物理数值 ENVskip / 2 warnings，Web1201/154files 与静态 PASS。原正式 native130 PASS / make0、原 wrapper1、独立补充核实际5生成路径变化分别保留，不能借给后续代码。公开4b仅终态progress，1433工程字节与29e相同。

当前 canonical 3265a1f381547e6a84f6acd9ab931bcf6078ed13：已普通本地整合 fdd unsupported 审批及79a中断，owner16/12路径分别逐字一致，其余原文件不变；1444 完整 Git 输入固定六静态 PASS、130实际/147声明/17未注册。新组合全量 Python/native NOT_RUN、未推送。fdd原171PASS、79a原1160PASS为各自来源证据；task_id提交过程偏差保留，根整合提交包含M6.3。

隔离外发 UI92c8836：完整 Web1278/157files、214原owner、132新相关、strict/build/spec PASS，1443固定输入；root与独立peer静态闭合两个真实反例。新真实Chrome run-01实际exit0/32.33s：生产空proof准备unavailable/preview503/0模型；4种写命令丢ACK、刷新0POST、显式原key完整ACK、learner与assessment安全撤销、failed+complete原响应UTF8hash、API/Chrome重启持久化通过。唯一显式memory synthetic request=1，实际外部模型/CLI均NOT_RUN；尚未整合canonical，不升级整个M6.3。

隔离pure-memory工具原9d/3120运行时绑定P2报告OPEN历史保留；3120实际222PASS仅其门禁。新4转依赖反例RED、6e5首次54FAIL/1PASS的partial结构拒绝保留；83d7窄修55定向与六静态PASS、1434固定输入，独立peer CLOSED_STATIC，完整相关门禁仍RUNNING。未合canonical，生产operation registry仍空，不称实际宿主工具。产物owner真实3route缺失RED保留；0032/manifest/实际source与stop receipt/同事务普通Import草稿回导仍实施中，不能从声明files_written0的现profile伪造产物。

公开4b新CI精确push37200167062与PR37200168176当前metadata共9job success/3仍in_progress，未读回全部终态或原joblogs，不称完整CI PASS。此前690双CI及所有旧FAIL/未知/中断/纠正原件仍保留。

阻塞与边界：生产完整输入ProofRegistry/executor不可用，真实平台Provider/CLI turn NOT_RUN；物理数值BLOCKED_ENVIRONMENT、发布409、无fallback；Broker/资源隔离/实际writer停止/来源数学教学质量未验收，整个M6.3/AC21与M7未完成。密钥未上传，本轮0实际外部模型请求。

下一任务：读回83d固定完整相关门禁与原P2闭合证据，正常整合已验UI92及工具，与已整合中断保留v4/v5历史解码和原ACK；冻结新组合完整Python/Web/静态与原native验收。并继续受检产物/普通Import草稿事务，核4b实际CI终态，收录精确候选及同步进度；不得提前报全阶段成功。
<!-- engineering_progress:end -->'''
body = re.sub(pattern, lambda _: block, issue['body'], flags=re.S)
(O / 'issue-body.md').write_text(body)
(O / 'issue-patch.json').write_text(json.dumps({'body': body}, ensure_ascii=False))
call('issue-patch', ['gh', 'api', repo + 'issues/32', '--method', 'PATCH', '--input', str(O / 'issue-patch.json')])
after = call('issue-after', ['gh', 'api', repo + 'issues/32'])
pa = call('pr-after', ['gh', 'api', repo + 'pulls/56'])
assert after['body'] == body
assert re.sub(pattern, '', after['body'], flags=re.S) == re.sub(pattern, '', issue['body'], flags=re.S)
for key in ['title', 'state', 'labels', 'assignees', 'milestone']:
    assert issue[key] == after[key]
for key in ['title', 'body', 'state', 'draft', 'merged_at', 'base', 'head']:
    assert pr[key] == pa[key]
report = {'status': 'ISSUE32_LOCAL3265_AND_ISOLATED_NATIVE_STATE_SYNC_VERIFIED',
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'issue_body_sha256': sha(body.encode()), 'local_head': L, 'public_head': H,
    'issue_outside_block_and_metadata_unchanged': True, 'pr56_unchanged': True,
    'sourcepush': False, 'boundary': 'Actual Issue32 managed-body-only sync. New source combination unaccepted/unpushed; exact4b CI metadata not fullterminal/log acceptance; production proof missing/0actualmodels/physical numeric blocked/wholeM6.3 incomplete.'}
(O / 'READBACK.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
