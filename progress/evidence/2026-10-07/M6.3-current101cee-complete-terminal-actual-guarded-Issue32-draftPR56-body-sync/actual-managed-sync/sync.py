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
assert sha(i['body'].encode())=='720b2d12584b54197a5322673b8ac034f40d518f8067841eb344af51d8130eff'
assert sha(p['body'].encode())=='d8d2c71c126278a839a9b0b67a403114687df24b57d45191fc543cac27e29c96'
assert p['head']['sha']==branch['commit']['sha']==PUBLIC
assert p['draft'] and p['state']=='open' and p['merged_at'] is None
assert subprocess.run(['git','rev-parse','HEAD'],cwd=R,capture_output=True,check=True).stdout.decode().strip()=='101cee47d8e746dddac81fb6e8829069fcabff09'
assert sha((R/'PRODUCT_DESIGN.md').read_bytes())=='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
assert json.loads((B/'m63-current101-full-native-root-admission-oct07/root-receipt.json').read_bytes())['actual_exit']==0
assert json.loads((B/'m63-current101-full-native-root-admission-oct07/ROOT-READBACK.json').read_bytes())['original_native']=='133PASS20.9m/exit0 once/133successlines'
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

当前101的原完整浏览器门禁已终态并独立读回：133 PASS/0 FAIL/0 SKIP，20.9m，make与runner原退出0，只执行一次；133项/55files、1worker、retry0，原默认30s及各用例超时均未改。完整159原件、23命令四件组和166条原始行已逐字/哈希核对。4份全1564输入映射的Git/index始终精确；rawafter实际5个原生输出改写，先私有保存，再按固定101精确恢复，其余输入不变。两条证据顺序步骤exit1已保留，新readiness continuation各0，未重跑测试。Review首用例在全套中通过16.8s；旧PR超时原因仍UNKNOWN。

原完整Python `uv run --frozen --offline pytest` 已终态：4589 collected，4587 PASS、0 FAIL、0 ERROR、2 数值 BLOCKED_ENVIRONMENT skip、3 warnings，3172.43s；uv 与 wrapper 均退出0，只启动一次。56原件哈希与13份完整1564项Git/index/live映射经独立读回，最终detached与canonical闭包均在固定101精确。原阶段RESULT中的PENDING_FREEZE保留，后续独立FINAL补充真实闭包。两跳过分别为真实Authoring sealed calculator未执行、Restore evaluator未得numeric PASS；无fallback、不算物理验收。setup使用公开依赖安装网络。新安装仍有3low提示。浏览器前置原lint/typecheck/build/verify-spec回执均0，其原命令环境无HOME/CODEX_HOME覆盖；规范检查只是M0结构。

另一份独立静态捕获的四命令实际0、十份1564映射精确，但其实际覆盖HOME，违反本轮执行约束；原件和明确纠正一并保留，不升格完全合规静态验收。初始Python3.14.4准备exit2亦保留，随后采用实际公共3.12.13。进度归档的默认Git空白检查实际exit2：9份原件尾空行和1份Vite原尾空格。已独立审阅仅匹配10个确切progress归档文件的规则，已在完整门禁与最终闭包封存之后应用：仅.gitattributes改变，其余1563输入逐字与固定101相同。原规则前缀保留，实际Git属性读回证实仅10归档路径改变、所有1564非progress路径的whitespace属性值不变。原日志字节保留，秘密扫描不放宽；新的暂存默认空白检查与发布扫描尚待实际执行。

下一任务：完成终态证据和有限来源审核、正常暂存提交检查，再正常推送已审阅源码并等待新原CI。公开分支仍079，本地101加确切归档规则尚未推送。原两CI已结束，没有 rerun、cancel 或 dispatch。没有新增被自动审批拒绝的宿主探针，也没有用软件PASS宣称真实Agent、发布或平台验收。
'''
begin,end='<!-- engineering_progress:start -->','<!-- engineering_progress:end -->'
assert i['body'].count(begin)==i['body'].count(end)==1
prefix=i['body'].split(begin)[0];suffix=i['body'].split(end)[1]
body=prefix+begin+'\n'+shared+'\n'+end+suffix
prbody='单个受控 turn 至多一次模型请求；逐操作审批与产物回导保持人审和待审草稿边界。当前公开源的完整门禁存在真实失败；已审阅修复已正常合入本地101，原完整Python4587P与浏览器133P已终态；数值环境仍阻塞，生产 Agent 尚未验收。\n\n'+shared+'\nRefs #32\n'
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
 'new_current_gates':'Original completePython4587PASS2numericENVskip3warn3172.43s/4589collected/uv0wrapper0; originalnative133PASS20.9m/55files/exit0 independentlyqualified; separatestaticactual0HOMEdeviation preserved',
 'actual_external_model_calls':0,'merge_release_deploy':False}
put('READBACK.json',record)
from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3')
t['last_issue_body_sha256']=record['issue_body_sha256'];t['last_issue_readback_at']=record['recorded_utc'];t['last_pr_body_sha256']=record['pr_body_sha256']
s['last_pr_body_sha256']=record['pr_body_sha256'];s['task_sync']='ACTUAL_ISSUE32_DRAFTPR56_PUBLIC079_OLD_FAIL_LOCAL101_NATIVE133PASS_PY4587PASS_TWO_NUMERIC_ENV_SKIPS_UNPUSHED'
s['task_sync_readback_at']=record['recorded_utc'];s['task_sync_last_scope']='Issue32 managed region and draftPR56 body only; untouched metadata.'
s['verification']['m6_3_current101_complete_terminal_actual_body_sync']=record
t['current_local_checkpoint']['status']='CURRENT101_ORIGINAL_FULL_PY4587PASS_TWO_NUMERIC_ENV_SKIPS_NATIVE133PASS;POST_GATE_EXACT_ARCHIVE_ATTRS_APPLIED_UNPUSHED'
previous=t['current_local_checkpoint']['python']['current1564']
f=json.loads((B/'m63-integrated-1564-complete-python-final-readback-oct07/FINAL.json').read_bytes())
assert f['source1564_before_after_exact'] and f['final_canonical1564_exact'] and f['counts']=={'passed':4587,'failed':0,'skipped':2,'warnings':3,'errors':0,'xfailed':0,'xpassed':0}
t['current_local_checkpoint']['python']['current1564']={'status':'PASS_WITH_TWO_NUMERIC_BLOCKED_ENVIRONMENT_SKIPS','source':f['source_head'],'inputs':1564,'collected':4589,'passed':4587,'failed':0,'errors':0,'skipped':2,'warnings':3,'pytest_seconds':3172.43,'actual_command_wrapper_exit':[0,0],'original_launches':1,'all1564_before_after_and_final_closure_exact':True,'original_stdout_sha256':'960f512d4d282d43c46bf109291f80769dd846d026cb5899b391b64eaa72085a','originals_manifest_sha256':'dfae73881cddf96d636f36458f0c6971e76b2089f9ce6b5df33f81c9a8cb4ba2','previous_running_record':previous,'numeric_reasons':f['original_skip_reasons'],'wholeM63':'NOT_ACCEPTED','evidence':'progress/evidence/2026-10-07/M6.3-current101cee-original-complete-Python4587PASS-numeric-ENV-skips-independent-final-closure/REPORT.json'}
t['current_acceptance_blockers']=['ProductioncompleteInputProof trustedproducer/checker and qualifiedexecutor/runtime unavailable;realmodelturnNOT_RUN','PhysicalnumericactualAuthoringcalculatornotexecuted/RestoreevaluatornoPASS;2ENVskips;no fallback','PhysicalBroker/hosttools/stop/resources and mathematicalsources/teachingacceptance incomplete;expanded rejectedhostprobesnotrestarted;M7todo']
t['next_action']='固定101原完整Python4587P/2数值ENVskip/3warn及原完整浏览器133P已封存；已在闭包后应用10确切归档规则，仅attrs差异，其余1563输入相同。完成终态证据来源审核、原暂存diff检查与发布扫描，再正常提交推送，等待新原CI。保留旧079失败、ReviewUNKNOWN、3low、静态HOME偏差；真实Agent/数值/教学未验收，M7todo。'
s['next_action']=t['next_action']
save(s)
print('Issue32 managed region and draftPR56 body exactreadback complete; originalCI failures and current101native133PASSqualified/fullPython4587PASStwoENVskips and executiondeviations stated.')
