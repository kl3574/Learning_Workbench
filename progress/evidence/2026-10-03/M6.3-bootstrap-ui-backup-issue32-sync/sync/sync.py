import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

base = Path('$HOME/.cache/learning-workbench-acceptance')
root = base / 'm62-public-safe-oct02'
dest = Path(__file__).parent
endpoint = 'repos/kl3574/Learning_Workbench/issues/32'
assert not (dest / 'before.json').exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
def read(name):
    result = subprocess.run(['gh', 'api', endpoint], capture_output=True)
    (dest / (name + '.stderr')).write_bytes(result.stderr)
    assert result.returncode == 0, 'Issue read unavailable; no inferred state'
    (dest / (name + '.json')).write_bytes(result.stdout)
    return json.loads(result.stdout)

identity = subprocess.run(['gh', 'api', 'user', '--jq', '.login'], capture_output=True)
assert identity.returncode == 0 and identity.stdout.strip() == b'kl3574'
before = read('before')
body = before['body']
assert before['state'] == 'open'
assert sha(body.encode()) == '175aed0a0deac1b446da56935033fb8a13892c81c9ae7f5630b4bb64cb626496', 'Remote changed; no update'
state = json.loads((root / 'progress/state.json').read_text())
block = '\n'.join(['<!-- engineering_progress:start -->', '当前实际状态：`in_progress`；M6.3 未完成，Issue 保持 open。', '唯一规范 v3.0.14（所有者已批准）：`bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`；新增本地会话合同仅 allowed_actions=[]、三 flags=false、active_turn_id=null，无模型/turn/tool/教材读取授权。', '隔离后端 `366d7b862379b3f3fa27808b04dbbd1b2694a6bc` 已实际注册三准备端点及原两 session 端点；它是中间候选，**NOT_ACCEPTED**。冻结部署闭包、输出预算、并发/恢复与真实受限控制验收仍在实施。独立静态审阅确认一项 P2：准入/原ACK回放前创建未登记 owner 文件，作者 WIP 调整尚待固定复核。', '隔离 UI 实现 `356a9ade7b0136f93cad5d3cbd5170afd178c991`，生成传输及完整 Web 固定 `5d07c43851c84e4e1d8df12d7de52500293c1c3b`：**1037 PASS /145 files，strict/noUnused PASS，build849 modules PASS**。root 独立核63原件/白名单及1369前后工程输入逐Git一致。原actor晚到ACK可由同工作区合法读者显式仅本地保存，零POST/零执行权限继承；工作区晚到读取已受控修复。', 'root 独立组合固定 `c73cbcbb9b95205986373706205dfafcdce709b7`：真实备份 CLI 对四种合成 Codex 历史 **4 PASS**，1374工程输入前后逐Git一致；八张Codex表与原actor保留、源表/文件不变、旧cookie401，新actor不能消费旧许可或决定。无真实Codex进程/thread/model；不是完整M7.1恢复验收。私有DB/ZIP/认证材料未公开。', '新的真实 Codex thread 与新 bootstrap native 当前 **NOT_RUN**；capabilities、协议模拟、UI测试及 fake thread ID 都不代替真实上游。ready 只有唯一实际受检映射落盘后才返回；未知结果不得第二次start，不能降低隔离或伪造201。', '历史固定 `ad49490e78c21174349595da8090c6c2b445bce9` 完整 Python **3633 PASS、2实际数值ENVIRONMENT SKIP、1setup ERROR、exit1**；native **126 PASS、1 FAIL、exit1**。完整原失败与日志/source绑定保留。受控租约诊断证明既有安全拒绝与fresh-owner一次派发恢复，未确立生产缺陷或历史宿主时序原因；原native初始会话HTTP未保留，具体原因UNKNOWN。', '扩展安全审阅和旧native UI诊断因自动安全检查 possible cybersecurity risk 中止，**NOT_RUN**，未重启/转派，不称完整安全审查通过。', '本阶段新代码/证据尚未source push；已封存本地进度。GitHub PR55仍draft/open/unmerged、head e2877101；既有M6.2双CI各6/6SUCCESS不代替本M6.3门禁。', '物理数值环境BLOCKED；托管完整输入计量ProofRegistry未闭合，真实平台Provider NOT_RUN，非key认证失败。', '下一任务：固定并独审后端修订，按已批准范围验真实零模型受限thread；整合UI和备份回归，执行新native及适用完整门禁，再检查公开对象并发布可审draft PR。无merge/release/deploy。', '<!-- engineering_progress:end -->'])
pattern = r'<!-- engineering_progress:start -->.*?<!-- engineering_progress:end -->'
assert len(re.findall(pattern, body, re.S)) == 1
new = re.sub(pattern, lambda match: block, body, flags=re.S)
(dest / 'issue-body.md').write_text(new)
(dest / 'patch.json').write_text(json.dumps({'body': new}, ensure_ascii=False))
result = subprocess.run(['gh', 'api', endpoint, '--method', 'PATCH', '--input', str(dest / 'patch.json')], capture_output=True)
(dest / 'patch-response.json').write_bytes(result.stdout)
(dest / 'patch.stderr').write_bytes(result.stderr)
assert result.returncode == 0, 'Unknown mutation outcome; read before any retry'
after = read('after')
assert after['body'] == new
assert re.sub(pattern, '', after['body'], flags=re.S) == re.sub(pattern, '', body, flags=re.S)
for field in ['title', 'state', 'labels', 'assignees', 'milestone']:
    assert after[field] == before[field], field
receipt = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'issue': 32,
           'state': after['state'], 'body_sha256': sha(new.encode()),
           'metadata_and_outside_block_unchanged': True, 'sourcepush': False,
           'full_gates': 'ad494 Python ERROR / native FAIL; original terminal retained',
           'approved_new_slice': 'v3.0.14 backend intermediate/UI1037PASS/rootbackup4PASS; actual session/native NOT_RUN',
           'boundary': 'Authorized body-only status update. No model/test rerun, source push, task closure, merge, release or deployment.'}
(dest / 'readback.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
