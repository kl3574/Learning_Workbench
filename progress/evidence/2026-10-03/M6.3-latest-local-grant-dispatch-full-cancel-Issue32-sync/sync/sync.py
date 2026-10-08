import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

O = Path(__file__).parent
REPO = 'kl3574/Learning_Workbench'
HEAD = '69029bc1ab355efdbb6e0fdb8a86204c59cea71a'
sha = lambda value: hashlib.sha256(value).hexdigest()
assert not (O / 'issue-before.json').exists()

def invoke(label, argv):
    result = subprocess.run(argv, capture_output=True)
    (O / (label + '.stdout')).write_bytes(result.stdout)
    (O / (label + '.stderr')).write_bytes(result.stderr)
    (O / (label + '.invocation.json')).write_text(json.dumps({
        'command': argv, 'exit_code': result.returncode,
        'stdout_sha256': sha(result.stdout), 'stderr_sha256': sha(result.stderr)
    }, indent=2) + '\n')
    return result

def read(label, endpoint):
    result = invoke(label, ['gh', 'api', 'repos/' + REPO + '/' + endpoint])
    assert result.returncode == 0
    (O / (label + '.json')).write_bytes(result.stdout)
    return json.loads(result.stdout)

identity = invoke('identity', ['gh', 'api', 'user', '--jq', '.login'])
assert identity.returncode == 0 and identity.stdout.strip() == b'kl3574'
issue = read('issue-before', 'issues/32')
pr = read('pr-before', 'pulls/56')
assert issue['state'] == 'open'
assert sha(issue['body'].encode()) == '448f124ac3d809a17b924299afa88ec2bacd026d1e0014604ac29c6b741d1bef'
assert pr['state'] == 'open' and pr['draft'] and pr['merged_at'] is None
assert pr['head']['sha'] == HEAD and pr['base']['ref'] == 'feat/M6.2-candidate-review'
assert sha(pr['body'].encode()) == 'aba2efa94c6202747c186a746eb63a8ae9f876efc3c38a56fe0c5dcde2554aaa'

block = '<!-- engineering_progress:start -->\n当前实际状态：in_progress，M6.3 / AC-21 未完成，Issue保持open。唯一规范v3.0.15 SHA256 b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec；批准4e8与782澄清已经纳入，不是待批准阻塞。\n\n公开源码仍69029bc1ab355efdbb6e0fdb8a86204c59cea71a，PR56 draft/open/unmerged、依赖PR55/e287。该固定源码push37170415116与PR37170416801各六job实际SUCCESS；12实际jobsAPI日志与push/PR checkout同tree分别封存，每组825backend/809contract/2143integration+2真实数值ENVskip/1058Web/130native。此旧CI不验收最新本地源码、模型或数学质量。\n\n当前canonical b34428ab5e9d99c5e04c886af445be73490171f2，1433完整非progress Git输入，127实际/147声明/20尚未注册，仍未推送。Provider-owned完整输入grant e399、单请求start/result调度351及新回合准备/安全取消UI b149已正常本地整合；逐owner变更路径精确，其他工程字节保留，原用户checkout b895未改。\n\n此前固定0dc454cd95e8ec82beec9e0921e53926204eec66完整Python已真实终态：4012收集、4010PASS/2实际物理数值环境SKIP/2既有依赖warnings，exit0，2373.33pytest秒，2026-10-04T10:23:13.732285Z；1417完整Git输入前后逐字不变。Ruff/mypy266/generator82/spec54core147/1109Web148files/strict/build均PASS。早先ff两完整FAIL（含配额和3939PASS7FAIL）与仅七病例修复PASS分别原样保留，不改写旧失败或推断唯一原因。0dc完整PASS不代表最新b344已经跑过组合全量；当前最新组合NOT_RUN。\n\ndispatch固定351：真实start/result、Provider原许可消费+Job/原ACK原子事务、leaseclaim后不可变possible-send事实、最多一次显式纯内存协议request、无proof零消费/外发、失owner终态UNKNOWN不重调度、contextv3保留原history。10files相关241PASS/2warnings及6staticexit0，1417Git输入前后不变，root/peer独立静态与68raw/53明确候选/4outer实际读回；正常合2b3。生产完整ProofRegistry与executor仍为空，协议memory测试不等实际Codex/model/host资源强制证明，真实模型请求0。\n\n回合UI三个真实P2分别修复：629 cached身份恢复表单5FAIL；db5完整JobSnapshot取消wire被错按JobRef拒绝1FAIL；94b取消ACK不核原status/revision6非法FAIL/4合法PASS。原结果、generation误报撤回、fixture仅label差异与root/peer读取schema失败及更正全部保留，不称原first countertest逐字未改。新b149完整Web1201PASS/154files、strict/build/specexit0、原合同owner214PASS/2warnings，1419完整Git前后逐blob一致；独立root+peer两轴静态closure无新增确认阻断。\n\n根实际Chrome154/b149新原生检查exit0/11.185秒：原prepare/cancel ACK丢失，POST前原actor/key/body/GETbasis已持久保存；刷新0自动POST，显式同key/fullbody重放逐字原完整JobSnapshot，完整ACK与原命令字段保存，再刷新及API OS重启仍保留；oldbootstrap记录逐字不变、1440/390无overflow并实际查看截图。仅显式syntheticbootstrap1，实际CLI/model/tools/dispatchNOT_RUN。原preflight ENOBUFS、02/03 locatorFAIL与04未核cancelACK的限定PASS及scope复制标签更正全部保留，不升级为wholeUI/M6.3验收。\n\n下一任务：封存本次进度/证据并冻结最新组合，运行完整Python/Web/静态门禁、按真实终态处理；隔离树继续逐操作GenericApproval和受控工具，不以unsupported对象冒称工具完整实施。后续产物manifest和普通Import待审草稿回导仍须实现/验收；核公开候选后普通push、draftPR56 body/实际CI另读回。第二模型请求必须新turn/新完整许可。\n\n四实际690数值artifact及六JSON仍物理BLOCKED_ENVIRONMENT、发布409PUBLISH_NUMERIC_REQUIRED；生产Provider完整proof缺失与数学/来源/教学质量另未验收，非用户key认证失败。M6.3/Broker/AC21与完整M7未完成。旧UNKNOWN、原失败和自动安全审查中止的系统级扩展诊断原样保留，不重启或转派被拒诊断。\n\n没有上传密钥、GitHubmerge/release/deploy或新sourcepush。\n<!-- engineering_progress:end -->'
pattern = r'<!-- engineering_progress:start -->.*?<!-- engineering_progress:end -->'
assert len(re.findall(pattern, issue['body'], re.S)) == 1
body = re.sub(pattern, lambda _: block, issue['body'], flags=re.S)
(O / 'issue-body.md').write_text(body)
(O / 'patch.json').write_text(json.dumps({'body': body}, ensure_ascii=False))
result = invoke('issue-patch', ['gh', 'api', 'repos/' + REPO + '/issues/32',
    '--method', 'PATCH', '--input', str(O / 'patch.json')])
after = read('issue-after', 'issues/32')
assert after['body'] == body, 'Unknown outcome; inspect actual state before retry'
assert result.returncode == 0
assert re.sub(pattern, '', issue['body'], flags=re.S) == re.sub(pattern, '', after['body'], flags=re.S)
for field in ('title', 'state', 'labels', 'assignees', 'milestone'):
    assert issue[field] == after[field], field
pr_after = read('pr-after', 'pulls/56')
for field in ('title', 'state', 'draft', 'merged_at', 'body', 'labels', 'assignees', 'milestone'):
    assert pr[field] == pr_after[field], field
assert pr_after['head']['sha'] == HEAD and pr_after['base']['ref'] == pr['base']['ref']
receipt = {'status': 'ISSUE32_FIXED_0DC_TERMINAL_DISPATCH_AND_FULL_CANCEL_UI_LOCAL_SYNC_VERIFIED',
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_head': HEAD, 'issue': 32, 'issue_state': after['state'],
    'issue_body_sha256': sha(body.encode()), 'outside_block_and_metadata_unchanged': True,
    'pr56_body_and_metadata_unchanged_by_this_sync': True,
    'pr56_body_sha256': sha(pr_after['body'].encode()), 'source_push_by_this_sync': False,
    'boundary': 'Authorized body-only Issue32 update; PR56 draft/open/unmerged. Canonicalb344 reviewed dispatch351 andUIb149 normally integrated; old0dc fullPython4010PASS/2actualnumericENVskip andstatic1109WebPASS. Latestb344 fullcombinedNOT_RUN; UI1201Web/214owner androotnativefullcancelACKPASS separately bound. Originals preserved; no sourcepush/GitHubmerge/release/deploy/model.'}
(O / 'readback.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False))
