"""Exact public-source progress sync; preserve unmanaged Issue text and state."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

out=Path(__file__).parent
head='35aebd3039241abb3393300affd593f4826a4a0c'
def gh(*argv):
    x=subprocess.run(['gh',*argv],capture_output=True)
    assert x.returncode==0,x.stderr.decode()
    return json.loads(x.stdout)
def sha(text):return hashlib.sha256(text.encode()).hexdigest()
def save(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
assert gh('api','user')['login']=='kl3574'
issue=gh('api','repos/kl3574/Learning_Workbench/issues/32')
assert sha(issue['body'])=='655e50225388809071c0ec1b5ad0f85df231fb08c3c3285fe19273ed6a2e171a'
pr=gh('api','repos/kl3574/Learning_Workbench/pulls/56')
assert pr['head']['sha']==head and pr['state']=='open' and pr['draft'] and pr['merged_at'] is None
save('issue-before.json',issue);save('pr-before.json',pr)
begin,end='<!-- engineering_progress:start -->','<!-- engineering_progress:end -->'
assert issue['body'].count(begin)==issue['body'].count(end)==1
prefix,rest=issue['body'].split(begin);previous,suffix=rest.split(end)
block='''
M6.3 in_progress / AC21 尚未验收。初始任务头保留创建时版本；当前唯一 spec_version=3.0.15，spec_sha256=b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec。

公开分支与PR56已真实读回35aebd3039241abb3393300affd593f4826a4a0c，draft/open/unmerged，依赖PR55。35ae归档固定5d3组合：受审Artifact512/普通Import、只读SSE95及产物/事件UI、Generic43审批和22精确Review消费观察均已正常本地整合。回导止于未审草稿，没有自动审校/发布。拒绝或未知approve保留原body/key/actor/ACK，新safe decline必须显式鲜读/独立新命令；approve仍核原actor及学科权限。

实际新组合5d3：Web1399PASS/166files、Ruff/mypy287/82generated/结构spec/strict/build/diff七static PASS，8轮1524完整Git输入before/after相同。54core/147declared134registered13missing只是结构状态。

Root固定22原make test-e2e完整133PASS/20.4m，command/wrapper exit0，结束2026-10-04T18:46:29.882884UTC，logSHA f2ea8017f0b8d7415ab6b8e99ef06ed74daccfe99852fc59b208ac3b5c8c6ec4。1514nongenerated输入不变、5原生成输出实际改变，无reset/restore/copyback。5d3及35ae的全部生产/规范/依赖/测试/config输入同22，README与精确归档attributes仅文档差异，不冒称在35ae重跑。

新22客户端屏障独审Standards/Spec0new，仅关闭本例精确JSON→有限Promise链→同步current/catch观察；不保证全部Reacteffects。实际phase只延迟一个原200，等待owned handler与JSON链后保留原隐藏断言/真实后端409。原机制同完整test bytes2FAIL→2PASS、final机制3PASS另列。原480局部1P1F、412完整132P1F与原因UNKNOWN、d69旧OPENseal及旧4353 WebFAIL/误调用静态FAIL均保留。

最新完整Python仍是4353原4341PASS/2真实numeric BLOCKED_ENVIRONMENT skip/2warnings。所有564Python与972/974原nonWeb/e2e输入逐Git相同，README/attributes两项文档例外；本轮没有重复完整Python，也不叠加重合子集计数。

公开前实际当前树21354files与938待推送历史blob规则扫描0findings，明确合成候选人工核验与两PNG读回完成；这不是通用PII/物理安全证明。git push实际exit0；原立即PR/branch一致性记录脚本exit1、首响应值未保存/原因UNKNOWN；后续独立GhAPI确认两head35ae，未repush，原失败回执保留。

新CI push37226331207、PR37226334354均真实in_progress/attempt1，当前未取得整组终态，不称CI通过。旧1a push37207897702为5success1browserFAIL/native129P1F、PR37207899600六success/native130，原12logs/checkout/tree核验与失败原因UNKNOWN不改。

M7.1仅新增942fc独立合成测试准备（工程候选未合入/推送）：focused2PASS/related21PASS/Ruff/diffPASS，原fixture布局2FAIL保留，独审0new。只证明临时CLI包手工展开、非空queued grant/completedmanifest/blob、fresh actor拒旧命令和直接GET零写/合成seams0；未进入TestClient lifespan，正式restore、后台worker恢复、Approval/Import覆盖NOT_RUN。M7仍todo，依赖未解锁。

本轮0实际外部模型请求，用户API key未使用/进入源码/上传。production完整InputProof/受控executor、真实Provider/CLI模型turn、物理Broker/hosttools/writer停止/资源限制、物理数值及来源数学教学质量与整体M6.3/AC21/M7仍未验收。物理numeric环境阻断，没有fallback；已中止扩展系统探针不重启。没有GitHubmerge/release/deploy。

下一任务：读取新35ae两CI每个job终态及原日志/实际checkout/tree，失败准确诊断/修复后重新固定验收，不追改旧失败。更新本地与公开真实回执，继续现行规范内的独立备份历史覆盖准备。
'''
body=prefix+begin+block+end+suffix
(out/'issue-body.md').write_text(body)
save('issue-patch.json',{'body':body})
written=gh('api','--method','PATCH','repos/kl3574/Learning_Workbench/issues/32','--input',str(out/'issue-patch.json'));save('issue-write-response.json',written)
after=gh('api','repos/kl3574/Learning_Workbench/issues/32');save('issue-after.json',after)
assert after['body']==body
keys=['number','title','state','labels','milestone','assignees'];assert {k:after[k] for k in keys}=={k:issue[k] for k in keys}
title='M6.3: 受控回合、逐项审批与产物草稿回导'
prbody='''本PR在唯一PRODUCT_DESIGN.md v3.0.15下增加本地受控Codex流程：冻结输入与单次外发许可、原actor/body/key命令恢复、逐操作审批及安全拒绝、只读事件与受检产物清单。所选产物只回导到普通Import待审草稿，仍需明确确认和人类审校/发布。生产完整输入证明与受控executor未注册时保持unavailable；工具默认关闭，模型/物理Broker/资源和质量验收尚未完成。

已公开35aebd30；受审运行组合5d3实际1399Web及七static PASS。Root隔离固定22原make test-e2e133PASS/20.4m、command/wrapper0；5个预列生成输出改变，其余1514输入不变。35ae的生产/测试/规范/依赖/config输入同22，README及归档attributes仅文档差异。Python沿用4353原4341PASS/2真实数值ENVskip，564Python逐Git连续；没有在35ae重跑。精确JSON/同步客户端观察有原2RED→同完整test2GREEN及独审0new，不宣称全部Reacteffects。原完整132P1F、480局部失败及旧CI失败完整保留。

新CI push37226331207、PR37226334354均in_progress，尚未取得整组终态。旧1a push129P1F/PR130P结果分别保留，原因UNKNOWN。来源数学教学质量、真实DeepSeek/CLI模型turn、物理数值/Broker和整体M6.3/AC21/M7未验收；本轮0实际外部模型调用，key未入仓库。M7合成备份仅隔离测试准备，正式恢复与后台恢复NOT_RUN。

当前draft/open/unmerged，依赖PR55。只公开明确核验的源码与合成工程证据，没有GitHubmerge/release/deploy。完整固定提交、命令、原失败、生成差异与下一任务见progress/CURRENT.md及Issue32管理区块。

Refs #32
'''
(out/'pr-body.md').write_text(prbody);save('pr-patch.json',{'title':title,'body':prbody})
written=gh('api','--method','PATCH','repos/kl3574/Learning_Workbench/pulls/56','--input',str(out/'pr-patch.json'));save('pr-write-response.json',written)
pafter=gh('api','repos/kl3574/Learning_Workbench/pulls/56');save('pr-after.json',pafter)
assert pafter['title']==title and pafter['body']==prbody and pafter['head']['sha']==head and pafter['draft'] and pafter['state']=='open' and pafter['merged_at'] is None
assert pafter['base']['ref']==pr['base']['ref'] and pafter['base']['sha']==pr['base']['sha']
save('READBACK.json',{'status':'ISSUE32_MANAGED_AND_PR56_FINAL_SCOPE_ACTUAL_WRITE_READBACK','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'public_head':head,'before_issue_body_sha256':sha(issue['body']),'issue_body_sha256':sha(body),'before_pr_body_sha256':sha(pr['body']),'pr_body_sha256':sha(prbody),'issue_metadata_and_unmanaged_text_unchanged':True,'pr_draft_open_unmerged':True,'ci':'twoexacteventin_progress_NOT_terminal','github_merge_release_deploy':False})
print('Issue32/PR56 currentpublic35ae actualwrite+readback; CI explicitlyinprogress')
