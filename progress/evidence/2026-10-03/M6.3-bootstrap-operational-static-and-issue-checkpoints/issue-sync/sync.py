import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

OUT = Path(__file__).parent
ENDPOINT = 'repos/kl3574/Learning_Workbench/issues/32'
GUARD = '0e6860e0a37546f0b78116949676491be52f3b12a40ce3d362c93254b1fbe808'
sha = lambda value: hashlib.sha256(value).hexdigest()
assert not (OUT / 'before.json').exists()
def read(label):
    result = subprocess.run(['gh', 'api', ENDPOINT], capture_output=True)
    (OUT / (label + '.stderr')).write_bytes(result.stderr)
    assert result.returncode == 0, 'Read unavailable; no inferred current state'
    (OUT / (label + '.json')).write_bytes(result.stdout)
    return json.loads(result.stdout)
identity = subprocess.run(['gh', 'api', 'user', '--jq', '.login'], capture_output=True)
assert identity.returncode == 0 and identity.stdout.strip() == b'kl3574'
before = read('before')
body = before['body']
assert before['state'] == 'open' and sha(body.encode()) == GUARD, 'Issue changed; refuse overwrite'
block = '''<!-- engineering_progress:start -->
当前实际状态：`in_progress`；M6.3 / AC-21 未完成，Issue 保持 open。
唯一规范 v3.0.14，所有者已批准375e55c0并采纳：`bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`。本地控制切片 allowed_actions=[]、三flags=false、active_turn_id=null；不授予模型、turn、账号登录、工具或学科读取。
后端固定 `df0bc6188745cf96aed4b68e52737dab492758d4`：264相关PASS、Ruff/mypy250/结构80 PASS；107 bootstrap测试包含在264中，不相加。root独立核1365完整非progress工程输入前后逐Git及642原件/140明确候选。五个真实端点、原actor/权限/CAS/完整命令/只读历史、一次消费及owner结束恢复已实施；不是完整后端门禁。
生产固定 `04500f20fd9727d9b15da081e820bbd81a780fad` 真实受限控制：通过实际HTTP prepare→GET→approve→GET→consume取得 **201/r2 ready**；恰1固定CLI，0.963秒；原201 ACK及同数据库应用重建回放逐字一致，零新start。root独立核1364完整Git输入和实际runner绑定。ready仅是已核验本地thread映射，不是模型调用、账号授权、当前进程仍运行或完整Broker完成。这是TestClient/应用重建，尚不是浏览器或API OS重启。
profile-v3保持原三帧请求、受限配置和资源。离线固定CLI schema导出440文件逐hash读回，四个所选schema字节绑定源码；仅补全实际返回metadata与匹配thread/started通知的严格观察，不开新RPC。原三个真实v2 unknown实例未升级/重跑，v3只读回保持全部八张owner表不变。原RED/FAIL、早期WIP不可完整重建限制及脚本错误均保留。
原固定366 owner文件P2由852锁顺序修改静态闭合；31补四终态文件数量检查并由最终264 gate实际执行。它不代表完整运行时安全审计。
UI固定5d07完整Web1037/145files、strict/build PASS；root独立读回63白名单/1369工程输入。新native组合a2d9第一次0retry执行 **FAIL**：首次读取本地记录后未退出初始提示，尚未到prepare/create，浏览器thread **NOT_RUN**。原日志/截图/完整输入保留；新的受控父面板测试复现false→true初始准入取消合法只读响应，小修a480已固定并独立读代码，现按新源码重验同字节新case，不改旧测试/超时或抹掉原FAIL。
root组合 `dcfda8c270dff3e6db75011c50ffa7d6f5826512` 含后端/UI/new-native/root备份4；同提交detached完整Python收集3688项，当前 **RUNNING**，无终态PASS承诺。当前canonical已机械采纳两文件UI修复为 `7b0ee3ae7d94a0d069b873133e69b5aaf3a18c89`，1381非progress输入逐Git不变，Ruff/mypy250/结构80 PASS；后端源仍与dcf相同。
root固定c73真实备份CLI对四种合成Codex历史4PASS，1374工程输入前后逐Git；八张Codex表/原actor保留，旧cookie401，新actor不得继承旧许可/命令。不是实际Codex或完整M7.1恢复验收；私有DB/ZIP未公开。
历史ad494完整Python3633PASS/2实际数值ENVIRONMENT SKIP/1setupERROR/exit1与native126PASS/1FAIL/exit1仍为原失败记录。受控租约诊断不关闭它们。扩展安全审阅和旧native诊断因自动检查 possible cybersecurity risk 中止、NOT_RUN，未重启或转派；不称完整安全审计通过。
新M6.3源码/证据尚未push；本地分支feat/M6.3-local-control-bootstrap。PR55仍draft/open/unmerged、head e2877101，既有M6.2双CI各6/6SUCCESS不替代本阶段门禁。物理数值环境BLOCKED，生产托管Provider完整输入计量ProofRegistry未闭合，真实平台Provider NOT_RUN，非key认证失败。
下一任务：收集修复后新native、完整Web与组合完整Python实际终态，按故障证据修复/验收，再检查公开内容和全部新增对象、发布可审draft PR；无merge/release/deploy。
<!-- engineering_progress:end -->'''
pattern = r'<!-- engineering_progress:start -->.*?<!-- engineering_progress:end -->'
assert len(re.findall(pattern, body, re.S)) == 1
new = re.sub(pattern, lambda _: block, body, flags=re.S)
(OUT / 'issue-body.md').write_text(new)
(OUT / 'patch.json').write_text(json.dumps({'body': new}, ensure_ascii=False))
result = subprocess.run(['gh', 'api', ENDPOINT, '--method', 'PATCH', '--input', str(OUT / 'patch.json')], capture_output=True)
(OUT / 'patch-response.json').write_bytes(result.stdout)
(OUT / 'patch.stderr').write_bytes(result.stderr)
assert result.returncode == 0, 'Unknown patch outcome; read current state before any retry'
after = read('after')
assert after['body'] == new
assert re.sub(pattern, '', after['body'], flags=re.S) == re.sub(pattern, '', body, flags=re.S)
for field in ('title', 'state', 'labels', 'assignees', 'milestone'):
    assert before[field] == after[field], field
receipt = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'issue': 32, 'state': after['state'],
           'body_sha256': sha(new.encode()), 'metadata_and_outside_block_unchanged': True, 'sourcepush': False,
           'scope': 'Actual45 scoped201/ready independently verified; final backend264 subset PASS; first new native FAIL before prepare, fix rerun pending; completePython RUNNING. Original completeERROR/FAIL preserved.',
           'boundary': 'Authorized body-only status sync, no source publication/task closure/merge/release/deploy.'}
(OUT / 'readback.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False))
