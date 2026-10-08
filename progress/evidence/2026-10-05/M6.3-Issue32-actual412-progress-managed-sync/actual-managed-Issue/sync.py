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
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip() == '412abe09c519104d9dbd2b360eed3ff4f897f829'
before = get_issue()
assert sha(before['body'].encode()) == 'fc1ef4ab7c52b42157767456c76849f2f4c170bfd958f9b2e180ea01dd7126e9'
pr = json.loads(gh('api', 'repos/kl3574/Learning_Workbench/pulls/56'))
assert pr['head']['sha'] == '1a6473dadcf71623008188f465586495ab28a204' and pr['state'] == 'open' and pr['draft'] and not pr['merged']
start, end = '<!-- engineering_progress:start -->', '<!-- engineering_progress:end -->'
assert before['body'].count(start) == before['body'].count(end) == 1
prefix, rest = before['body'].split(start)
old, suffix = rest.split(end)
current = '''
M6.3 in_progress / AC21 未完成；唯一规范 v3.0.15 b140764e，已批准受控turn/逐操作审批/产物合同继续实施。

最新本地固定组合412abe09c519104d9dbd2b360eed3ff4f897f829尚未推送。Artifact512及SSE95先在4353融合，再正常无冲突merge四个独审切片：AA表单notice、Tutor218只读观察、Artifact8f界面、Event80b读流。27disjoint路径完整候选Git mode/type/blob/size/SHA同时保留，1512工程输入同Git；1493原输入中1485未变，974个非Web/e2e输入（含564 Python）精确同4353，独审融合Standards/Spec零新增P1/P2。

4353原全Python现在实际终态4341PASS/2actual numeric BLOCKED_ENVIRONMENT SKIP/2warnings，2878.74s；9个原完整1493输入pair均封存。4353完整Web原1277PASS/1FAIL仍是FAIL。AA控制延迟save真实同测1FAIL→1PASS、原ACK仍归原actor；新412完整Web真实1359PASS/163files及七static exit0、8个完整1512输入pair一致，mypy287/生成82。Python明确是4353执行的原件，对未改后端输入引用，不冒称412重跑。新完整native已于2026-10-04T16:48:12UTC在独立412树实际启动，仍RUNNING，不能预报PASS；原配置/预算/重试策略保持，已列10原生生成输出目的地，不restore/copyback。

Artifact8f新界面27focused/1305完整Web/strict/build/spec PASS，实际Chrome+loopback HTTP owners/SQLite/IndexedDB bounded native02 PASS；6张1440/390图实际显示合成正文。完整原key/body/basis在POST前保存、实际202丢ACK后刷新零自动POST、显式同key全ACK回放、原queued与当前completed分开、普通Import预览原SHA/未审，无自动确认/Review/publish。原422f scope P2OPEN与lazy-preview LIMITED、首8f native观察FAIL保留；同scope反例1FAIL1PASS→同测2PASS，最终8f独审P2 CLOSED_STATIC。

Event80b新53focused/1331完整Web/strict/build PASS；原SSE six-variant闭合、空格换行原文、显式after_seq重连、fresh actor清显示、刷新零自动GET。限定native04真实Chrome生产组件+typedfetch+合成loopback1PASS，非production owner/CLI/model验收。初始收集/ESM/挂载/type和transport原失败各保留、挂载唯一causeUNKNOWN。独审源/55explicit candidates/6×1499输入pair零新增；已整合412。两slice数与完整组合数重叠，不相加。

新通用审批UI仍在未合入的隔离9e4ce1分支：35focused与1394完整Web/166files、strict/build/spec、新17.063s bounded Chrome/local owners场景实际PASS，1522输入exact；两明确合成memory turn和一次纯literal内存操作不代表宿主工具。原031两次完整Web各1339PASS/1FAIL（不同旧测试）保留，不能追认唯一cause。独审刚发现具名Spec P2候选：旧保存approve请求被拒/未知时，会锁住仍pending审批的后续安全decline。正在做独立真实counter RED和最窄修复，原body/key必须保留、decline从鲜读safe approval_controls明确新key，不自动改旧命令。该UI不能以既有PASS宣布验收，尚未进canonical。

Tutor218窄观察保留原准确区域/locator/5000ms，仅25ms只读采样；同DOM原1FAIL2PASS→固定6PASS（3原业务+3DOM）、native/Webstrict PASS，独审零新增并已整合。原1a Tutor CI129PASS1FAIL和唯一causeUNKNOWN保留，不用该合成机制或local绿色倒推原CI原因。

公开源码仍为1a6473（PR56 OPEN/draft/unmerged）。1a push37207897702真实5success/1browserFAIL129PASS1FAIL；PR37207899600六success/native130。12原joblogs/checkouts/PR parents/tree已核。新本地源码尚未公开、没有新CI执行/merge/release/deploy。

边界：本次0实际外部模型请求，用户key未使用/存入仓库/上传。实际生产InputProof/Broker/CLI/工具/可靠writer停止/物理资源隔离/数学来源教学质量与整个M6.3/AC21/M7仍未完成；physical numeric仍BLOCKED、无fallback。旧扩展系统安全review自动中止保持NOT_RUN，不重启或转派。

下一任务：保存412原完整native终态；按真实RED修复审批安全decline锁并独审新delta、重新固定组合适用门禁；同步精确进度与显式安全证据，再做当前tree/outgoing history审计和正常sourcepush。所有历史FAIL与各自source边界保持。
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
    'before_body_sha256':sha(before['body'].encode()),'body_sha256':sha(body.encode()),'local_candidate':'412abe09c519104d9dbd2b360eed3ff4f897f829',
    'public_pr_head':pr_after['head']['sha'],'metadata_and_unmanaged_text_unchanged':True,'write_exit_code':q.returncode,
    'boundary':'Progress-only Issue edit; no sourcepush/merge/release/deploy/model/CLI. RUNNING and source-specific FAIL retained.'}
(out/'READBACK.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
