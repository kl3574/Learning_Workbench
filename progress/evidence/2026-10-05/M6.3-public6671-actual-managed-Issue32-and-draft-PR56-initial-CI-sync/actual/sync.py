"""Sync actual source and bounded gates, preserving the unmanaged Issue text."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

base=Path('$HOME/.cache/learning-workbench-acceptance')
out=Path(__file__).parent
head='6671dd5c924edbac8ca7f479c4f51d4afec14480'
assert not (out/'READBACK.json').exists()
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def gh(label,*args):
    assert not (out/(label+'-command.json')).exists()
    save(label+'-command.json',{'argv':['gh',*args],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    r=subprocess.run(['gh',*args],capture_output=True)
    (out/(label+'.stdout')).write_bytes(r.stdout);(out/(label+'.stderr')).write_bytes(r.stderr)
    save(label+'-receipt.json',{'exit_code':r.returncode,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'stdout_sha256':sha(r.stdout),'stderr_sha256':sha(r.stderr)})
    assert r.returncode==0
    return json.loads(r.stdout)
assert gh('identity','api','user')['login']=='kl3574'
issue=gh('issue-before','api','repos/kl3574/Learning_Workbench/issues/32')
pr=gh('pr-before','api','repos/kl3574/Learning_Workbench/pulls/56')
assert sha(issue['body'].encode())=='f4085720ba43f76d07cbcc102cd3e8a8e91bbff41d8175339ca2e9f5875e92f0'
assert sha(pr['body'].encode())=='6f04008d435231c200547fac7b96c5ba7f79296b5022892a3515988cc80afb08'
assert pr['head']['sha']==head and pr['draft'] and pr['state']=='open' and pr['merged_at'] is None
snapshots=sorted((base/'m63-ci-public6671-observation-oct05').glob('*-SNAPSHOT.json'))
assert snapshots
snapshot=json.loads(snapshots[-1].read_text())
assert snapshot['source']==head
ci='；'.join(f"{r['event']} {r['id']} attempt{r['run_attempt']} {r['status']}/{r['conclusion'] or '尚无终态'}" for r in snapshot['actual_events']) or '本次原始API响应尚无匹配事件；不宣称已启动或通过'
observed=snapshot['observed_utc']
begin,end='<!-- engineering_progress:start -->','<!-- engineering_progress:end -->'
assert issue['body'].count(begin)==issue['body'].count(end)==1
managed=f'''
M6.3 in_progress，AC21尚未验收。唯一规范PRODUCT_DESIGN.md v3.0.15，SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec；初始Issue任务头保持创建时版本。

普通源码推送后branch与草稿PR56均实际读回 {head}，draft/open/unmerged，依赖PR55。实现包括冻结受控回合、逐操作审批、只读SSE与产物清单、普通Import待审回导，以及现成session interrupt合同的UI入口。中断前先持久化原actor/session CAS/body/key；刷新无自动POST，丢ACK后须显式重放；412保留原命令，当前GET与历史ACK分开。回导只产生待审草稿，没有自动人审或发布。

本地新固定48693936两个原Review用例实际2PASS（15.4s/10.7s、total29.1s，command/wrapper0，原30000ms/worker1/retry0与断言保持）；独立有限核验26候选/7maps/10675绑定0新增缺口，LOG8cdedf6526644841530bcefbbf73724d0a22c1e3887a4cc4721dd823f6198102。原bare-selector list01命令0但列3项/scope wrapper1、业务NOT_RUN，exactlist02后只有这一次组合业务运行。486完整133native未运行。原22dade Web1421/167files、focused127/4files、strict/build/diff0和完整native133PASS20.4m只按各自源码限定；当前Web/package/Node输入同22dade。原4353完整Python4341PASS/2真实numericENVskip/2warnings按564Python输入一致限定沿用，没有新全量Python/Web重跑。上述重叠门禁不相加。

新CI实际快照 {observed}：{ci}。仅记录API实际状态，完整新CI终态及日志未取得时不报PASS。首Review新增payload-free阶段/HTTP静态模板计时，保持业务断言/30s；唯一新增CI白名单行仅在既有failure条件保留review-history-timing.json，实际失败上传读回尚NOT_RUN。观察改变调度，不证明修复CI，也不证明全部JSON/React效果完成。

旧35ae两原CI37226331207/37226334354均terminalFAIL、各5SUCCESS+browser132P1F，首Review30s耗尽/唯一根因UNKNOWN、第二late-responsePASS；各integration2467PASS/2真实numericBLOCKED_ENVIRONMENT skips，12原log及实际checkout已核，后续成功不追改原失败。实际数值BLOCKED、发布409/PUBLISH_NUMERIC_REQUIRED/未发布保持。原中断首轮动态raw误重跑覆盖永久LOSS、retainedrun01 SECONDsetupFAIL、新run02仅FOURguard且boundedChromePASS保持；旧工具链0tests、TS7016/strict错误与旧oracle失败均保留。

公开前文档检查也保留原件：staged空白exit2，只增加六个精确归档路径规则，生产源码规则不变；公开扫描exit1拦住state/CURRENT十九本机目录字段，原私有bytes保留，后续仅HOME前缀转换后491暂存文件scan0、最终diff0、M0结构check0。结构检查不是业务验收；固定6671当前树/待推送历史另独立有限审核后才推送。原35ae推送git0/postcheck1及首API响应未保存/UNKNOWN继续保留。

当前production完整InputProof/profile/checker/受控执行闭包仍缺实现，默认unavailable；真实Provider/DeepSeek/Codex CLI模型turn、物理Broker/工具资源与停止边界、物理数值、来源数学教学质量及整体M6.3/AC21未验收。本轮0真实外部模型调用，用户API key未使用、入库或上传。已中止的扩展主机探针不重启，没有GitHubmerge/release/deploy。M7备份7cff只隔离保护覆盖准备；正式restore、新调度、M7依赖未解锁，M7保持todo。

下一任务：读取这两个新原CI的真实终态/完整日志及各checkout；若失败按明确有界metadata定位，不放宽30s或重跑掩盖。继续现行规范内的production受检输入和执行实现，保持真实执行/数值/质量验收边界。
'''
prefix=issue['body'].split(begin)[0];suffix=issue['body'].split(end)[1]
body=prefix+begin+managed+end+suffix
save('issue-patch.json',{'body':body});(out/'issue-body.md').write_text(body)
gh('issue-write','api','--method','PATCH','repos/kl3574/Learning_Workbench/issues/32','--input',str(out/'issue-patch.json'))
iafter=gh('issue-after','api','repos/kl3574/Learning_Workbench/issues/32')
assert iafter['body']==body
keys=['number','title','state','labels','milestone','assignees']
assert {k:issue[k] for k in keys}=={k:iafter[k] for k in keys}
assert iafter['body'].split(begin)[0]==prefix and iafter['body'].split(end)[1]==suffix
prbody=f'''本PR依照唯一规范v3.0.15实现受控Codex回合、逐操作审批、只读事件与受检产物回导。回导先成为普通Import待审草稿，再经明确确认、人审与发布。新会话中断入口先保存原actor/CAS/body/key，刷新无自动提交；丢ACK可显式原命令重放，412保留原命令，当前GET与历史ACK分开。

公开head {head}，draft/open/unmerged，依赖PR55。新原CI快照 {observed}：{ci}；尚不能以非终态报通过。新增首Review无正文时序观察及一行既有failure归档白名单，原30s/断言/worker/retry保持，不宣称修复旧CI。实际失败上传读回尚NOT_RUN。

验证：固定486两个原Review用例实际2PASS、独立绑定核验0新增，LOG8cdedf6526644841530bcefbbf73724d0a22c1e3887a4cc4721dd823f6198102。仅此子集，486全133未运行；原22dade全native133和Web1421/167files、4353Python4341/2真实numericENVskip均按输入一致限定沿用，未新重跑全套。19个明确证据包归档，491暂存文件scan0/diff0/M0结构check0；原空白exit2、路径scanexit1和声明前缀转换保留。

旧35ae双CI仍FAIL，各browser132P1F/首Review30s、唯一原因UNKNOWN，第二PASS；实际数值BLOCKED/发布409/未发布。新受限Chrome中断验证只是loopback/IDB/CAS路径；首轮动态raw被覆盖永久LOSS，成功不补造原件。production完整InputProof/profile/checker/受控执行闭包尚缺，真实DeepSeek/CodexCLI、物理Broker/数值和来源数学教学质量及整个M6.3/AC21未验收。M7仅隔离准备，依赖未解锁。本轮0真实外部模型调用，key未入库；无GitHubmerge/release/deploy。

下一步读取新原CI终态和限定失败metadata，继续现行规范内production实现，保留原失败与未验收边界。Refs #32
'''
save('pr-patch.json',{'body':prbody});(out/'pr-body.md').write_text(prbody)
gh('pr-write','api','--method','PATCH','repos/kl3574/Learning_Workbench/pulls/56','--input',str(out/'pr-patch.json'))
pafter=gh('pr-after','api','repos/kl3574/Learning_Workbench/pulls/56')
assert pafter['body']==prbody and pafter['head']['sha']==head and pafter['draft'] and pafter['state']=='open' and pafter['merged_at'] is None
assert pafter['title']==pr['title'] and pafter['base']['sha']==pr['base']['sha']
save('READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'ACTUAL_PUBLIC6671_SOURCE_BOUNDED_GATES_AND_NEW_CI_SNAPSHOT_SYNC', 'head':head,
 'issue_before_body_sha256':sha(issue['body'].encode()),'issue_body_sha256':sha(body.encode()),
 'pr_before_body_sha256':sha(pr['body'].encode()),'pr_body_sha256':sha(prbody.encode()),
 'issue_unmanaged_text_metadata_unchanged':True,'draft_open_unmerged':True,'ci_snapshot':snapshot,
 'actual_model_calls':0,'github_merge_release_deploy':False})
print('Actual public6671 and original CI snapshot synchronized; Issue unmanaged text and metadata preserved.')
