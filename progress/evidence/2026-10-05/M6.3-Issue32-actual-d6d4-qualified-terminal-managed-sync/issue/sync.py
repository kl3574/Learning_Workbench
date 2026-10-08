"""Update only the managed Issue block with the actual local combination state."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

out = Path(__file__).parent
root = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
def gh(*args):
    return subprocess.check_output(['gh', *args], cwd=root)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def get_issue():
    return json.loads(gh('api', 'repos/kl3574/Learning_Workbench/issues/32'))
def meta(issue):
    return {k: issue[k] for k in ('number', 'title', 'state', 'labels', 'milestone', 'assignees')}
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip() == 'd6d4d9b98316d7f3790eb60e5d1bb4aca67450d1'
assert json.loads(gh('api', 'user'))['login'] == 'kl3574'
before = get_issue()
assert sha(before['body'].encode()) == 'ec3c59fae7628fc7c7104fbd8cecb904d8120ace90d7843dbb2a6027a3247e63'
pr = json.loads(gh('api', 'repos/kl3574/Learning_Workbench/pulls/56'))
assert pr['head']['sha'] == '1a6473dadcf71623008188f465586495ab28a204' and pr['state'] == 'open' and pr['draft'] and not pr['merged']
start, end = '<!-- engineering_progress:start -->', '<!-- engineering_progress:end -->'
assert before['body'].count(start) == before['body'].count(end) == 1
prefix, rest = before['body'].split(start)
old, suffix = rest.split(end)
current = '''
M6.3 in_progress / AC21 尚未验收；唯一规范 v3.0.15 b140764e，用户批准的受控turn、单次模型、逐操作审批及产物待审回导范围继续实施。

最新本地组合 d6d4d9b98316d7f3790eb60e5d1bb4aca67450d1 尚未推送。已正常整合 Artifact512/SSE95、AA表单notice、Tutor218只读观察、Artifact8f产物界面、Event80b读流、Generic43审批界面和Review69两行测试生命周期修复。13组明确安全证据已保存并本地提交；进度主字段已更新，旧状态/失败/完整原件保持。普通源码merge保存12候选路径以及全部原progress Git字节；1521/1522工程输入与d69相同，唯一例外为5个精确档案的.gitattributes空白规则，不改运行代码。

实际完整门禁：d6d4 Web1399PASS/166files，Ruff/mypy287/生成82/spec/strict/build/diff各exit0；spec结构54core/147declared134implemented13missing不等于平台验收。两次额外错参数静态调用（不存在worker路径、误将--check传给extract）实际FAIL保留，新正确原规范命令分别PASS，无源码改动、不把原件追改为绿。10个实际完整1522工程输入before/after pairs均exact。

独立树固定d69完整make test-e2e实际133PASS/20.1m/exit0且wrapper0，start2026-10-04T17:37:16.347494UTC、end17:57:22.351345UTC，logSHA ad3c0608c6ab60b88071ceaf8a7c9cac95db2df7e82e3f50cb999beb474194f7。原10生成目的地中5个输出实际改变，1512非生成输入不变，无reset/restore/copyback。它是d69执行的原件，结合上述运行输入连续性用于本地组合；不冒称在d6d4重复运行。原412完整132PASS1FAIL/24.1m及route.fulfill alreadyhandled原因UNKNOWN保持FAIL；原4353完整Web1277PASS1FAIL也保留。

4353完整Python原实际4341PASS/2真实numeric BLOCKED_ENVIRONMENT skip/2warnings仍是最新全Python执行；当前所有Python/后端输入与4353保持，本地非Web/e2e仅documentary attributes例外。没有把隔离UI结果或新native数字冒充新全Python重跑；slice和whole counts重叠不相加。

Generic43独审Standards/Spec零新增，SAFE_DECLINE_BLOCKED_BY_PRIOR_APPROVE_COMMAND仅对修复source CLOSED_STATIC：原approve真实403/503被拒或unknown仍保留整条原body/key/ACK，新explicit decline从鲜读safe controls建立新key；approve_once仍受ANY旧command防重和原actor/学科权限。组件同完整测试3FAIL→38focusedPASS；原9e与43实际403的相同3harness字节反例RED→GREEN。限定Chrome/local HTTP owners/SQLite/IndexedDB两明确synthetic memory turn/1纯literal操作（host_actions/provider_requests/files_written=0）通过，不是实际远程模型/CLI/host工具。原9eOPEN四seal和031两wholeFAIL不改。

Review69独审窄source零新增，handler结束时两个hidden断言+server409与actual3subset（2Review+1draft-review）分列。客户端JSON/生成client/hook/React完成的既有证据缺口仍OPEN_EVIDENCE，不由unrouteAll(wait)或完整133绿色关闭；另树正在做精确透明消费观察与因果屏障，首真实Chrome+loopback+actual client机制反例2FAIL已保留，尚未合入或验收。原412完整失败没有时序记录，机制counter不证明原唯一原因。

公开源码仍1a6473，PR56 open/draft/unmerged。原1a push37207897702为5success1browserFAIL/native129P1F，PR37207899600六success/native130；12原joblogs及checkout/tree已核。尚无本次源码push或新CI，不称main发布、GitHubmerge/release/deploy。

边界：本次0真实外部模型请求，用户key未使用/进入仓库/上传。生产完整input proof/Provider/Broker/实际CLI、物理工具和writer停止/资源封闭验收尚未完成；物理numeric仍BLOCKED_ENVIRONMENT，无fallback；来源/数学/教学质量及整体M6.3/AC21/M7仍未验收。原扩展系统探针自动中止保持NOT_RUN、不重启或转派。

下一任务：完成精确客户端消费屏障的实际反例/固定源码/独立复核并保留d69原完整133结果；保存最新组合明确候选与当前主记录，做当前tree及outgoing history审计后正常sourcepush并按实际CI终态回读。M7.1新Codex备份范围仅只读盘点，验收未解锁。
'''
body = prefix + start + current + end + suffix
(out/'issue-before.json').write_text(json.dumps(before, indent=2)+'\n')
(out/'issue-body-before.md').write_text(before['body'])
(out/'issue-body.md').write_text(body)
(out/'patch.json').write_text(json.dumps({'body': body}, ensure_ascii=False)+'\n')
q = subprocess.run(['gh','api','--method','PATCH','repos/kl3574/Learning_Workbench/issues/32','--input',str(out/'patch.json')],cwd=root,capture_output=True)
(out/'write.stdout').write_bytes(q.stdout);(out/'write.stderr').write_bytes(q.stderr)
assert q.returncode == 0, q.returncode
after = get_issue(); assert after['body'] == body and meta(after) == meta(before)
pr_after = json.loads(gh('api','repos/kl3574/Learning_Workbench/pulls/56'))
assert pr_after['head']['sha'] == pr['head']['sha'] and pr_after['draft'] and not pr_after['merged']
(out/'issue-after.json').write_text(json.dumps(after,indent=2)+'\n')
receipt = {'status':'ISSUE32_MANAGED_PROGRESS_ACTUALLY_UPDATED_AND_READBACK_VERIFIED','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'before_body_sha256':sha(before['body'].encode()),'body_sha256':sha(body.encode()),'local_candidate':'d6d4d9b98316d7f3790eb60e5d1bb4aca67450d1',
    'public_pr_head':pr_after['head']['sha'],'metadata_and_unmanaged_text_unchanged':True,'write_exit_code':q.returncode,
    'boundary':'Progress-only Issue edit; fixed-source PASS, originalFAIL and OPEN_EVIDENCE separately retained. No sourcepush/GitHubmerge/release/deploy/model/CLI.'}
(out/'READBACK.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
