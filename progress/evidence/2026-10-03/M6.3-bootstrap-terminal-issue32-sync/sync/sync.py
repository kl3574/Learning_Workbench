import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

OUT = Path(__file__).parent
ENDPOINT = 'repos/kl3574/Learning_Workbench/issues/32'
GUARD = '47813ad57e501b13c040d96e774454fb900b6ffc870e771088244e15a166c3e5'
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
block = '<!-- engineering_progress:start -->\n当前实际状态：`in_progress`，M6.3 / AC-21 未完成，Issue保持open。唯一规范v3.0.14（已批准375e55c0），SHA256 `bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`。本地会话切片只建立受限thread映射，allowed_actions=[]、三capability=false、active_turn_id=null。\n\n后端固定df0 focused264PASS（其中bootstrap107，不相加）、Ruff/mypy250/结构80PASS；root核1365完整工程输入逐Git/前后不变及642原件/140明确候选。五个真实端点、原actor/权限/CAS/完整历史/一次消费/owner恢复已实施；完整阶段验收仍待后续。\n\n实际固定045受限控制：真实HTTP prepare→GET→approve→GET→consume取得201/r2 ready，恰1固定CLI，0.963秒；原201ACK及同DB应用重建回放逐字相同、零新start。profile-v3保留三帧/预算/限制，四个所选schema逐字绑定离线440文件。无模型、turn、账号登录、工具、网络或学科读取。三个原真实v2unknown保持unknown、不升级或重跑。原owner文件P2已由852/31静态修复及终态文件数量回归实际闭合，不称完整隔离安全审计。\n\nUI初始false→true写准入取消合法只读响应，受控RED复现后a480仅两文件窄修；原a2d9新nativeFAIL（准备/创建/thread NOT_RUN）和日志/截图保留。a480新native1PASS，实际browser/IndexedDB/两API OS进程/同DB贯通，五个显式原命令ACK回放字节相同，登记session/permit/finish保持1/1/1。浏览器证据不独立计OS CLI启动。\n\n原a480完整Web1037PASS/1FAIL保留；f321仅在新回归等待写按钮实际ready，读取断言、production/native不改。f321完整Web1038PASS/145files、strict/build849PASS，17161 tracked/1376工程输入逐Git前后不变。\n\n正式固定bd3完整native：128PASS、0FAIL、0skip、exit0、1worker/0retry、无casefilter，18.1分钟；root独立核230原件hash/23明确候选、17628 tracked/1381工程输入逐Git前后不变。Authoring/Restore实际数值environment_unavailable、Job failed、verdict BLOCKED；Restore发布409。浏览器安全路径PASS不升级物理运行。\n\n固定dcf正式完整Python：3688收集，3683PASS/1FAIL/2setupERROR/2物理数值环境SKIP、exit1，原完整失败封存。旧备份测试期待清空reviewer actor引用与现行M7保历史合同冲突；b51仅修测试并cherry到当前canonical1843556e，原RED1FAIL、新single1PASS（包含在七文件65PASS中）、Ruff及独立静态审阅通过。没有生产/native/timeout/租约修改，65相关PASS不替代整套FAIL。\n\n两个原setup ERROR（Provider owner single、Review guards extra_body-decision）原因UNKNOWN，正文未执行。先核源/收集/allocator/独占basetemp关联，再只读合成DB非秘密状态时间计数，观察authoring running r3/import running r2；不能推断租约丢失、UTC差值或宿主原因，不恢复/改写原实例。修订后固定184的同命令完整Python3688收集已终态：3686PASS/0FAIL/0ERROR/2物理数值环境SKIP/2既有warnings、exit0，2199.36秒。1381工程输入逐Git前后不变；root独立核全部输入/runner/log及11原件/12明确候选。无筛选/超时修改；新PASS不解释两个原setup原因。\n\nroot固定c73备份CLI四种合成Codex历史4PASS，1374工程输入逐Git，原actor/八表保留，旧cookie401、新actor不继承旧许可。它与legacy65回归不是完整M7.1真实恢复验收；私有DB/ZIP不分享。\n\n原ad494完整Python3633PASS2ENVskip1setupERROR/exit1、native126PASS1FAIL/exit1均保留。自动检查 possible cybersecurity risk 中止的扩展安全审阅和旧native诊断为NOT_RUN，未重启或转派。完整M6.3/Broker、turn、多轮/通用审批/产物/登录/导出/工具/回导与发布尚未完成；生产托管Provider缺完整输入计量ProofRegistry，真实平台Provider NOT_RUN，非key认证失败；数学/来源/教学分别未验。\n\nM6.3源码尚未push，独立本地分支feat/M6.3-local-control-bootstrap；原用户checkout clean b895保留。PR55仍draft/open/unmerged、head e2877101，既有M6.2两次CI各6/6SUCCESS不代替本阶段门禁。新证据已按明确白名单/仅个人home前缀转换封包；后续全部新增对象还需新公开准入。\n\n下一任务：核全部公开对象，推送独立M6.3分支并建立可审draft PR、读回对应SHA的CI；并行实施§6.6仅四当前输入Markdown需求下载的客户端fallback（局部RED保留，GREEN尚待固定独审）。该下载不创建Job/许可、不附教材/来源、零模型/工具，不证明R23生成集成。无merge/release/deploy。\n<!-- engineering_progress:end -->'
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
           'scope': 'Actual045 scoped control PASS; fullWeb1038 PASS; formalbd3 native128 PASS; DCF completePython FAIL1F2E2ENVskip retained; legacytest-only corrected65PASS; new184 completePython3686PASS0F0E2ENVskip/exit0 independently verified; stage unaccepted.',
           'boundary': 'Authorized body-only status sync, no source publication/task closure/merge/release/deploy.'}
(OUT / 'readback.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False))
