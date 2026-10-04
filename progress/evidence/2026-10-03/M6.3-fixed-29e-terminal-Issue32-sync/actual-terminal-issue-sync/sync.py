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
assert sha(issue['body'].encode()) == 'faa98f4a5c36e14fe9039b6a4848807aa2d868de7b0f556612aebb9f255c6ddc'
assert pr['state'] == 'open' and pr['draft'] and pr['merged_at'] is None
assert pr['head']['sha'] == HEAD and pr['base']['ref'] == 'feat/M6.2-candidate-review'
assert sha(pr['body'].encode()) == 'aba2efa94c6202747c186a746eb63a8ae9f876efc3c38a56fe0c5dcde2554aaa'

block = '<!-- engineering_progress:start -->\n当前实际状态：in_progress，M6.3 / AC-21 未完成，Issue保持open。唯一规范v3.0.15 SHA256 b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec；批准4e8与782澄清已经纳入，不是待批准阻塞。\n\n公开源码仍69029bc1ab355efdbb6e0fdb8a86204c59cea71a，PR56 draft/open/unmerged、依赖PR55/e287。该固定源码push37170415116与PR37170416801各六job实际SUCCESS；12实际jobsAPI日志与push/PR checkout同tree分别封存，每组825backend/809contract/2143integration+2真实数值ENVskip/1058Web/130native。此旧CI不验收最新本地源码、模型或数学质量。\n\n当前已验收组合canonical 29e864a6157f3bb23c6ced5d1a2f34f77bf3b875（b344应用字节不变，文档检查点及.gitattributes五条精确不可变patch上下文豁免），1433完整非progress Git输入，127实际/147声明/20尚未注册，仍未推送。Provider-owned完整输入grant e399、单请求start/result调度351及新回合准备/安全取消UI b149已正常本地整合；逐owner变更路径精确，其他工程字节保留，原用户checkout b895未改。\n\n此前固定0dc454cd95e8ec82beec9e0921e53926204eec66完整Python已真实终态：4012收集、4010PASS/2实际物理数值环境SKIP/2既有依赖warnings，exit0，2373.33pytest秒，2026-10-04T10:23:13.732285Z；1417完整Git输入前后逐字不变。Ruff/mypy266/generator82/spec54core147/1109Web148files/strict/build均PASS。早先ff两完整FAIL（含配额和3939PASS7FAIL）与仅七病例修复PASS分别原样保留，不改写旧失败或推断唯一原因。0dc完整PASS不代表最新b344已经跑过组合全量；最新冻结29e静态已于2026-10-04T10:58:23.317270Z真实终态PASS：Ruff/mypy268、82generator、54core147spec、1201Web154files、strict/build全exit0，1433完整Git输入前后逐字不变。完整Python已于2026-10-04T11:41:29.253129Z真实终态：4087收集、4085PASS/2物理数值环境SKIP/2既有warnings、exit0、2604.33pytest秒，完整logSHA256 ed3b3e9abfe13013bd1ff942186c1465b0c73f380755e35066b7ec7678859d44，1433完整Git before/after逐字一致。完整native第一长TMPDIR实际130FAIL/makeexit2/155.665s保留，已读前两例Chrome SingletonSocket路径太长，不声称全部失败唯一原因；第二短TMPDIR运行8PASS/1INTERRUPTED/121NOT_RUN后发现旧套件会写已跟踪docs/ui产物，主动中止，canonical1433输入逐字未变。第三在29e等字节独立worktree使用同原make test-e2e/配置/预算/重试及短独立0700TMPDIR实际于2026-10-04T11:26:02.042917Z终态：130PASS、make exit0、1210.772s，完整logSHA256 2fce6646b473f28a170f084d9e5bcbf18d36645d1c809b03d87b1691141628f9。原外层wrapper exit1保留：预列六输出遗漏模板1440/1920两路径，other1427_unchanged=false不改写。独立追加审计核全部十个原测试生成路径，实际五个docs/ui输出改变，其余1428 tracked逐字未变、1423非生成源码/runtime字节匹配固定Git；canonical1433输入仍逐字未变/clean。隔离树实际diff原样保留，无reset/恢复/拷回；root独立查看五PNG、核29明确候选及1433Git原blob与实际diff，区分130测试PASS和wrapper原FAIL。native实际两数值receipt仍environment_unavailable/BLOCKED、发布409，无算术PASS。完整Python runner期间源码/GitHEAD保持冻结；实际终态后才解除冻结，准备收录终态并正常push。\n\ndispatch固定351：真实start/result、Provider原许可消费+Job/原ACK原子事务、leaseclaim后不可变possible-send事实、最多一次显式纯内存协议request、无proof零消费/外发、失owner终态UNKNOWN不重调度、contextv3保留原history。10files相关241PASS/2warnings及6staticexit0，1417Git输入前后不变，root/peer独立静态与68raw/53明确候选/4outer实际读回；正常合2b3。生产完整ProofRegistry与executor仍为空，协议memory测试不等实际Codex/model/host资源强制证明，真实模型请求0。\n\n回合UI三个真实P2分别修复：629 cached身份恢复表单5FAIL；db5完整JobSnapshot取消wire被错按JobRef拒绝1FAIL；94b取消ACK不核原status/revision6非法FAIL/4合法PASS。原结果、generation误报撤回、fixture仅label差异与root/peer读取schema失败及更正全部保留，不称原first countertest逐字未改。新b149完整Web1201PASS/154files、strict/build/specexit0、原合同owner214PASS/2warnings，1419完整Git前后逐blob一致；独立root+peer两轴静态closure无新增确认阻断。\n\n根实际Chrome154/b149新原生检查exit0/11.185秒：原prepare/cancel ACK丢失，POST前原actor/key/body/GETbasis已持久保存；刷新0自动POST，显式同key/fullbody重放逐字原完整JobSnapshot，完整ACK与原命令字段保存，再刷新及API OS重启仍保留；oldbootstrap记录逐字不变、1440/390无overflow并实际查看截图。仅显式syntheticbootstrap1，实际CLI/model/tools/dispatchNOT_RUN。原preflight ENOBUFS、02/03 locatorFAIL与04未核cancelACK的限定PASS及scope复制标签更正全部保留，不升级为wholeUI/M6.3验收。\n\n独立后续工作（未合canonical、未推送）：unsupported GenericApproval固定fdd3a949相关171PASS/2warnings和六staticPASS，1424Git exact，129实际路由；85raw/74SAFE/4outer原verifier根实际exit0，root+peer两轴静态无新增确认阻断。它只保留pending/read/decline/safecontrol/同TXstop，未提供approve/claim/accept或实际工具。下一执行profile仅显式有界纯内存字符串解释，生产registry仍空，首真实HTTP1FAIL/9profile-unitPASS保留；新纯内存实际literal解释器已接批准r2/claimr3/result r4，首37相关PASS，后续35focused和六staticPASS；新增unknown工具事实却completed外层turn的同字节oracle1RED→1GREEN，最终固定9d3ffb0c相关11files209PASS/2warnings与六staticPASS、mypy275、1430完整Git exact，原VERIFY root实际exit0；仅隔离支持切片，尚未合canonical/不称实际工具。生产registry仍空，不是实际shell/文件/网络工具。具名interrupt根固定cc2新测试3FAIL，确认现规范声明接口尚未注册；独立0031/v4实现已将原三项测试逐字转为3PASS，首固定26实际HTTP边界PASS；固定79a3更大门禁1160PASS/2warnings、五staticPASS与1428完整Git exact，尚未合canonical。独立root/peer静态无新增确认产品阻断；两个原commit未含M6.3的§18.4低严重流程偏差保留，后续正常集成提交写task_id，不改已封SHA。旧三模型未改，真实Jobs request_stop与独立原ACK同事务。外发七操作/四writejournal UI亦在新独立树，首新功能revoke发送前未持久化1RED已保存，四write wire→journal focusedGREEN；组件/hooks完整门禁待完成，不称旧b149产品缺陷。上述新功能都不能借既有模型/原生PASS提前声称完成。\n\n下一任务：将实际29e完整Python4085PASS/2真实数值ENVskip、1201Web/staticPASS及native130PASS（原wrapperFAIL单独保留）的明确候选收录进度，普通push并读回PR56与实际新CI；隔离树继续逐操作GenericApproval和受控工具，不以unsupported对象冒称工具完整实施。后续产物manifest和普通Import待审草稿回导仍须实现/验收；核公开候选后普通push、draftPR56 body/实际CI另读回。第二模型请求必须新turn/新完整许可。\n\n四实际690数值artifact及六JSON仍物理BLOCKED_ENVIRONMENT、发布409PUBLISH_NUMERIC_REQUIRED；生产Provider完整proof缺失与数学/来源/教学质量另未验收，非用户key认证失败。M6.3/Broker/AC21与完整M7未完成。旧UNKNOWN、原失败和自动安全审查中止的系统级扩展诊断原样保留，不重启或转派被拒诊断。\n\n没有上传密钥、GitHubmerge/release/deploy或新sourcepush。\n<!-- engineering_progress:end -->'
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
receipt = {'status': 'ISSUE32_FIXED29E_COMPLETE_GATES_TERMINAL_ORIGINAL_FAILURES_PRESERVED_SYNC_VERIFIED',
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_head': HEAD, 'issue': 32, 'issue_state': after['state'],
    'issue_body_sha256': sha(body.encode()), 'outside_block_and_metadata_unchanged': True,
    'pr56_body_and_metadata_unchanged_by_this_sync': True,
    'pr56_body_sha256': sha(pr_after['body'].encode()), 'source_push_by_this_sync': False,
    'boundary': 'Authorized body-only Issue32 update; PR56 draft/open/unmerged. Canonicalb344 reviewed dispatch351 andUIb149 normally integrated; old0dc fullPython4010PASS/2actualnumericENVskip andstatic1109WebPASS. Latestfrozen29e static1201WebPASS,fullPython4085PASS/2actualnumericENVskip;native01actual130FAIL/02INTERRUPTED8PASS/03isolated130PASS makeexit0 originalwrapperFAIL preserved and independent5generateddiff qualification; UI1201Web/214owner androotnativefullcancelACKPASS separately bound. Originals preserved; no sourcepush/GitHubmerge/release/deploy/model.'}
(O / 'readback.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False))
