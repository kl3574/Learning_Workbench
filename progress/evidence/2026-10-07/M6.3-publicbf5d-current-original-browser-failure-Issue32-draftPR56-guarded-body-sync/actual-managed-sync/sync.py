from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

O = Path(__file__).resolve().parent
B = O.parent
R = B / 'm62-public-safe-oct02'
HEAD = 'bf5d2df4e7ee5156993169cdd9610fa014bdae4f'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def put(name, obj):
    (O / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def gh(name, *args):
    assert not (O / (name + '-receipt.json')).exists()
    argv = ['gh', *args]
    put(name + '-command.json', {'argv': argv, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    x = subprocess.run(argv, capture_output=True)
    (O / (name + '.stdout')).write_bytes(x.stdout)
    (O / (name + '.stderr')).write_bytes(x.stderr)
    put(name + '-receipt.json', {'actual_exit': x.returncode, 'stdout_bytes': len(x.stdout), 'stdout_sha256': sha(x.stdout), 'stderr_bytes': len(x.stderr), 'stderr_sha256': sha(x.stderr), 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    assert x.returncode == 0, (name, x.returncode)
    return json.loads(x.stdout)

i = gh('issue-before', 'api', 'repos/kl3574/Learning_Workbench/issues/32')
p = gh('pr-before', 'api', 'repos/kl3574/Learning_Workbench/pulls/56')
br = gh('branch-before', 'api', 'repos/kl3574/Learning_Workbench/branches/feat%2FM6.3-local-control-bootstrap')
assert sha(i['body'].encode()) == '9311fc28af019b10e512aca3f0ab36e6f4c63540db22d1e06bb1cb56a575f156'
assert sha(p['body'].encode()) == 'befb0b42412481a201a729f5eefddc28f28e10b3a17c001b7481abe8dc9d345a'
assert p['head']['sha'] == br['commit']['sha'] == HEAD
assert p['draft'] and p['state'] == 'open' and p['merged_at'] is None
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip() == HEAD
assert sha((R / 'PRODUCT_DESIGN.md').read_bytes()) == 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
watch = B / 'm63-ci-publicbf5d-original-observation-oct07'
latest = json.loads((watch / 'LATEST.json').read_bytes())
raw = (watch / latest['snapshot']).read_bytes()
assert sha(raw) == latest['sha256']
snap = json.loads(raw)
assert snap['source_head'] == HEAD and not snap['read_errors']
put('ACTUAL-CI-SNAPSHOT.json', snap)
begin, end = '<!-- engineering_progress:start -->', '<!-- engineering_progress:end -->'
assert i['body'].count(begin) == i['body'].count(end) == 1
prefix = i['body'].split(begin)[0]
suffix = i['body'].split(end)[1]
shared = i['body'].split(begin)[1].split(end)[0].strip()
lines = shared.splitlines()
matches = [n for n, line in enumerate(lines) if line.startswith('新公开bf5d的原CI已实际出现：')]
assert len(matches) == 1
status = '; '.join(e['event'] + ' run' + str(e['id']) + ' ' + e['status'] + '/' + str(e['conclusion']) + ' [' + ', '.join(j['name'] + ':' + j['status'] + '/' + str(j['conclusion']) for j in e['jobs']) + ']' for e in snap['actual_events'])
lines[matches[0]] = '新公开bf5d原CI真实回读：push37657156244 browser为132PASS/1FAIL/39.1m；PR37657163285 browser为133PASS/38.5m。两次原日志均下载actual0，7条安全checkout/footer原行已按SHA/行号逐字节绑定，完整原日志保持私有。每个事件backend1114PASS/3warnings、Web1421PASS/167files、spec-contracts962PASS/2warnings、security-publication23933扫描均来自对应原日志，不相加或沿用旧计数。元数据实际观察时间：' + snap['observed_utc'] + '；' + status + '。integration尚未由原终态日志验收；browser失败正在从指定原日志和tracked source诊断，不推定与旧079失败同因，不增加超时、不重跑或取消原CI。旧079两个原CI终态FAIL继续保留。'
shared = '\n'.join(lines)
old = '最终额外staged scope独审尚待收件，不冒称其最终通过。'
new = '旧staged scope独审最终回执仍未收件，不能称该旧回执PASS。另行新鲜bf进度/源码有限独审已完成：先发现同一P2（7个当前恢复指针仍指079），原报告保留；纠正后20项有限核验PASS、Standards/Spec均0P1/0P2，固定101门禁和bf公开指针分开，所有旧事实明确保留为previous。'
assert shared.count(old) == 1
shared = shared.replace(old, new)
shared += '\n\n生产Agent阻塞范围（本次只读源码审计）：当前注册表为空、executor=None、现有profile/request/receipt/control仅支持synthetic。真实的最终请求构造/checker、独立版本profile/receipt/executor及stop/writer owners属于仍待完成的本地工程；实际模型完整格式计数依据和强制隔离/预算/零额外外发边界需独立资格证明，不能用接口schema、Python callback、synthetic byte count或CI通过替代。用户已提供DeepSeek密钥和测试授权，不重复索要；本次根代理动作实际平台模型请求0。官方DeepSeek文档的max_tokens与唯一规范Chat max_completion_tokens存在已记录的文档合同差异，未修改规范、未试发模型、未宣称HTTP拒绝。M6.3/AC21未验收，M7todo。下一任务是收取两次原integration终态、诊断并修复具体browser失败，以及继续真实请求/运行边界工程。'
body = prefix + begin + '\n' + shared + '\n' + end + suffix
prbody = '受控turn、逐操作审批和产物回导按唯一规范持续实施。固定101本地Python4587PASS/2数值ENVskip与native133PASS已封存，源码正常推送bf。新原CI的push browser132PASS/1FAIL、PRbrowser133PASS必须分别保留；integration仍按原任务观察。生产Agent未验收。\n\n' + shared + '\nRefs #32\n'
sys.path.insert(0, str(R / 'scripts'))
from check_publication import inspect
from progress import read_state, save
assert not inspect('progress/issue-body.md', body.encode())
assert not inspect('progress/pr-body.md', prbody.encode())
for name, value in [('issue', body), ('pr', prbody)]:
    (O / (name + '-body.md')).write_text(value)
    put(name + '-patch.json', {'body': value})
gh('issue-write', 'api', '--method', 'PATCH', 'repos/kl3574/Learning_Workbench/issues/32', '--input', str(O / 'issue-patch.json'))
ia = gh('issue-after', 'api', 'repos/kl3574/Learning_Workbench/issues/32')
assert ia['body'] == body
assert {k: i[k] for k in ['number', 'title', 'state', 'labels', 'milestone', 'assignees']} == {k: ia[k] for k in ['number', 'title', 'state', 'labels', 'milestone', 'assignees']}
assert ia['body'].split(begin)[0] == prefix and ia['body'].split(end)[1] == suffix
gh('pr-write', 'api', '--method', 'PATCH', 'repos/kl3574/Learning_Workbench/pulls/56', '--input', str(O / 'pr-patch.json'))
pa = gh('pr-after', 'api', 'repos/kl3574/Learning_Workbench/pulls/56')
assert pa['body'] == prbody and pa['head']['sha'] == HEAD
assert pa['draft'] and pa['state'] == 'open' and pa['merged_at'] is None
assert pa['title'] == p['title'] and pa['base']['sha'] == p['base']['sha']
record = {'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'public_head': HEAD, 'issue_body_sha256': sha(body.encode()), 'pr_body_sha256': sha(prbody.encode()), 'scope': 'Issue32 managedregion and draftPR56 body only; metadata/unmanagedtext preserved', 'draft_open_unmerged': True, 'metadata_snapshot': latest, 'browser_original': 'push132P1F39.1m / PR133P38.5m', 'integration': 'Not yet admitted by original terminal log', 'source_push_merge_release_deploy': False, 'model_calls_by_sync': 0, 'M6_3': 'NOT_ACCEPTED', 'M7': 'todo'}
put('READBACK.json', record)
s = read_state()
t = next(x for x in s['tasks'] if x['id'] == 'M6.3')
t['last_issue_body_sha256'] = record['issue_body_sha256']
t['last_pr_body_sha256'] = record['pr_body_sha256']
t['last_issue_readback_at'] = record['recorded_utc']
s['last_pr_body_sha256'] = record['pr_body_sha256']
s['task_sync'] = 'ACTUAL_ISSUE32_DRAFTPR56_CURRENTBF_BROWSER_PUSH_FAIL_PR_PASS_ORIGINAL_INTEGRATION_OBSERVATION'
s['task_sync_readback_at'] = record['recorded_utc']
s['verification']['m6_3_publicbf_browser_original_managed_sync'] = record
save(s)
print('Actual Issue32/draftPR56 guarded body sync and exact readback succeeded; browser push FAIL preserved; no sourcepush or CI operation.')
