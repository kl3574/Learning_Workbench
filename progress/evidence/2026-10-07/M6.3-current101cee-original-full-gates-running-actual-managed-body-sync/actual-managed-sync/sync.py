from pathlib import Path
import datetime,hashlib,json,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
PUBLIC='079a008cf88b37e4517cb391503a1e7393ccf374'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def gh(n,*args):
 assert not (O/(n+'-command.json')).exists()
 put(n+'-command.json',{'argv':['gh',*args],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x=subprocess.run(['gh',*args],capture_output=True)
 (O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr)
 put(n+'-receipt.json',{'exit_code':x.returncode,'stdout_bytes':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_bytes':len(x.stderr),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert x.returncode==0,(n,x.returncode);return json.loads(x.stdout)
snapraw=(B/'m63-ci-public079a008-observation-oct07/98-SNAPSHOT.json').read_bytes();snap=json.loads(snapraw)
assert sha(snapraw)=='a36d00653e16c2a9f5a5fe78dda7986d031f97c10a7441bf318e7a9e1f957013'
assert all(e['status']=='completed' and e['conclusion']=='failure' for e in snap['actual_events'])
assert gh('identity','api','user')['login']=='kl3574'
i=gh('issue-before','api','repos/kl3574/Learning_Workbench/issues/32')
p=gh('pr-before','api','repos/kl3574/Learning_Workbench/pulls/56')
branch=gh('branch-before','api','repos/kl3574/Learning_Workbench/branches/feat%2FM6.3-local-control-bootstrap')
assert sha(i['body'].encode())=='a6d4b346d9bfb975218b024782705ef9df28fa4c90c1241fd5df85369c817fe7'
assert sha(p['body'].encode())=='318d9ddea853aae89e0c60239b6de2f0b9d43c4c9f4c535022225de3ce8708ec'
assert p['head']['sha']==branch['commit']['sha']==PUBLIC
assert p['draft'] and p['state']=='open' and p['merged_at'] is None
assert subprocess.run(['git','rev-parse','HEAD'],cwd=R,capture_output=True,check=True).stdout.decode().strip()=='101cee47d8e746dddac81fb6e8829069fcabff09'
assert sha((R/'PRODUCT_DESIGN.md').read_bytes())=='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
assert json.loads((O/'NATIVE-RUNNING-ROOT-READBACK.json').read_bytes())['original_collection']=='133 tests in 55 files'
shared='''M6.3 仍在实施，AC-21 尚未验收，M7 保持 todo。唯一规范为 PRODUCT_DESIGN.md v3.0.15（SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec），包含用户已批准的受控 turn、逐操作审批和产物清单合同。

当前公开分支与草稿 PR56 已实际回读为 `079a008cf88b37e4517cb391503a1e7393ccf374`，1561 工程输入。运行源码锚点为 `d78c4d159a2831f7d5e1721a9a466ec5b3e66421`；079 的后续变更为进度证据及三个确切归档规则。原用户 b895 检出保留；没有 GitHub merge、release 或部署。

原完整本地 Python 门禁（固定079，一次实际执行）：4583 collected，4580 PASS、1 FAIL、2 数值 BLOCKED_ENVIRONMENT skip、3 warnings，3075.18s；pytest 与 wrapper 均退出1，全1561输入前后严格匹配。唯一失败为历史迁移夹具 forward_guards 的 HTTP503 vs202。原 traceback 没有打印 SQLite 异常；Broker/schema 的解释来自另外的源码与定向诊断。两数值环境 skip 保留原失败/no fallback，不算通过。

原 CI attempt1 两事件都已终态 FAILURE。独立原日志和有限原始行读回已完成，计数分别呈现，绝不相加：

- [push37632652743](https://github.com/kl3574/Learning_Workbench/actions/runs/37632652743)：5 个 job SUCCESS、1 个 integration FAIL。backend1114P/3warn，frontend1421P/167files，spec962P/2warn，publication23175路径且仍需手工来源审核；browser133P/28.6m；integration2518P/1F/2ENVskip/2warn/49m31s。
- [PR37632662238](https://github.com/kl3574/Learning_Workbench/actions/runs/37632662238)：4 个 job SUCCESS、integration 与 browser 两个 FAIL。backend1114P/3warn，frontend1421P/167files，spec962P/2warn，publication23175路径；integration2518P/1F/2ENVskip/2warn/74m57s；browser132P/1F/39.9m。

两组 integration 唯一失败均为上述 forward_guards 夹具。PR browser 的 Review 首用例在 Reader URL 谓词处耗尽整个用例的30s预算，根因仍 UNKNOWN。PR checkout e9eb82 的完整 Git tree 与079 的23175项相同；CI 执行时工作输入 before/after 明确 NOT_CAPTURED。日志下载exit0与测试成功不同，原 FAIL 不因后续局部通过而改写。

四项规范内修复已正常合入本地 `101cee47d8e746dddac81fb6e8829069fcabff09`，1564工程输入；尚未推送。原进度与用户b895检出、唯一规范均保留。另有两条确切的不可变证据空白归档规则，不改运行语义。以下是合并前的独立候选证据，不替代新组合完整门禁：

- `90c8cd4`：只修历史夹具的旧 owner 组合；升级前恢复当前 mandatory Broker，保留全部9原断言、另加3条。原同用例1F保留，修改后同用例1P、相关44P/2warn；计数重叠。独立 Standards/Spec 无阻断，生产与迁移均未改。
- `2323558`：只将锁中 source-map-js1.2.1 升至兼容补丁1.2.2。lint/typecheck/build通过，完整 Vitest1421P/167files，原 Reader 用例1P。原 audit exit1（1high/3low）与新 audit exit1（0high/3low）都保留，仍不洁净；当前数学依赖链无兼容的低风险补丁，未强制升级或改渲染语义。最初0用例的选择失败保留。
- `8bd930b`：§20.17.7 的三份备份历史测试，固定候选组合6P/2warn/19.41s，全1564输入前后相同；旧许可执行被拒绝、历史可读、关闭 worker 无伪终态。源码独立审阅与有限原件回读已完成、无阻断；未据此解锁M7。
- `5520255`：只为 Review 增加有限 setup/helper 时间与既有轮询状态码记录。原用例一次1P/19.8s，30s/retry0/worker1与业务断言不变；不记录JSON、query、header、rawURL、身份或表单值。仅诊断记录产出，未证明原PR原因已闭合；独立 Standards/Spec 源审阅无阻断；可选AST因缺本地模块未运行，额外严格E2ETS原失败及辅助声明环境通过分别保留。

已有持久 Broker 控制仍限定受检 synthetic callback、当前线程/租约和可能发送事实；22专项、473相关和Authoring5browser等旧局部证据保留，不替代当前完整门禁。更早27f/公开1e的原失败也保留。

真实 Agent 仍有工程缺口：默认空 ProofRegistry、executor=None；完整最终模型请求字节的可信 producer/checker、受限实际 App Server runtime 与停止回执未完成资格验证。当前0实际外部模型调用，用户密钥未写入源码或上传。Provider、Codex、物理数值、数学来源及教学效果分别未验收。

当前101的新完整门禁正在运行：原 `uv run --frozen --offline pytest` 实际收集4589项，只执行一次，尚未终态；原 `make test-e2e` 实际启动，全133项/55files、1worker、retry0。用例原超时保留，不推断最终通过数。新安装仍有3low依赖提示。静态检查的初次环境准备因为误用本机Python3.14.4与项目3.12约束冲突退出2，原回执保留，已用实际公共Python3.12.13继续；静态结果另行按原回执记录。

下一任务：等待固定101完整Python、全133浏览器和静态门禁的实际终态，独立读取原件与输入前后映射；根据新证据处理仍可复现的失败。公开分支仍079，当前101未推送。原两CI已结束，此次没有 rerun、cancel 或 dispatch。没有新增被自动审批拒绝的宿主探针，也没有用局部PASS宣称发布或平台验收。
'''
begin,end='<!-- engineering_progress:start -->','<!-- engineering_progress:end -->'
assert i['body'].count(begin)==i['body'].count(end)==1
prefix=i['body'].split(begin)[0];suffix=i['body'].split(end)[1]
body=prefix+begin+'\n'+shared+'\n'+end+suffix
prbody='单个受控 turn 至多一次模型请求；逐操作审批与产物回导保持人审和待审草稿边界。当前公开源的完整门禁存在真实失败；已审阅修复已正常合入本地101，新完整门禁正在运行，生产 Agent 尚未验收。\n\n'+shared+'\nRefs #32\n'
sys.path.insert(0,str(R/'scripts'));from check_publication import inspect
assert not inspect('progress/issue-body.md',body.encode()) and not inspect('progress/pr-body.md',prbody.encode())
for name,value in [('issue',body),('pr',prbody)]:
 (O/(name+'-body.md')).write_text(value);put(name+'-patch.json',{'body':value})
gh('issue-write','api','--method','PATCH','repos/kl3574/Learning_Workbench/issues/32','--input',str(O/'issue-patch.json'))
ia=gh('issue-after','api','repos/kl3574/Learning_Workbench/issues/32')
assert ia['body']==body and {k:i[k] for k in ['number','title','state','labels','milestone','assignees']}=={k:ia[k] for k in ['number','title','state','labels','milestone','assignees']}
assert ia['body'].split(begin)[0]==prefix and ia['body'].split(end)[1]==suffix
gh('pr-write','api','--method','PATCH','repos/kl3574/Learning_Workbench/pulls/56','--input',str(O/'pr-patch.json'))
pa=gh('pr-after','api','repos/kl3574/Learning_Workbench/pulls/56')
assert pa['body']==prbody and pa['head']['sha']==PUBLIC and pa['draft'] and pa['state']=='open' and pa['merged_at'] is None
assert pa['title']==p['title'] and pa['base']['sha']==p['base']['sha']
record={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'public_head':PUBLIC,
 'issue_body_sha256':sha(body.encode()),'pr_body_sha256':sha(prbody.encode()),'issue_unmanaged_metadata_preserved':True,
 'draft_open_unmerged':True,'snapshot_sequence':98,'snapshot_sha256':sha(snapraw),
 'actual_original_CI':'PUSH5SUCCESS1FAIL_PR4SUCCESS2FAIL;BOTH_FAILURE','local_candidates':'90c8/232/8bd/552_NORMALLY_INTEGRATED_LOCAL101_NOT_PUSHED',
 'local_head':'101cee47d8e746dddac81fb6e8829069fcabff09','engineering_inputs':1564,
 'new_current_gates':'Original completePython4589collected RUNNING; originalnative133/55files RUNNING; static recovery pending terminal',
 'actual_external_model_calls':0,'merge_release_deploy':False}
put('READBACK.json',record)
from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3')
t['last_issue_body_sha256']=record['issue_body_sha256'];t['last_issue_readback_at']=record['recorded_utc'];t['last_pr_body_sha256']=record['pr_body_sha256']
s['last_pr_body_sha256']=record['pr_body_sha256'];s['task_sync']='ACTUAL_ISSUE32_DRAFTPR56_PUBLIC079_ORIGINAL_FAIL_LOCAL101_INTEGRATED_NEW_FULL_GATES_RUNNING_UNPUSHED'
s['task_sync_readback_at']=record['recorded_utc'];s['task_sync_last_scope']='Issue32 managed region and draftPR56 body only; untouched metadata.'
s['verification']['m6_3_current101_running_actual_body_sync']=record;save(s)
print('Issue32 managed region and draftPR56 body exactreadback complete; originalCI failures and currentlocal101 integrated/newfull RUNNING scope stated.')
