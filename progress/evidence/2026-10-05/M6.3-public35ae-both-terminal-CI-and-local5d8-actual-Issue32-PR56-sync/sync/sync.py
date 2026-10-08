"""Guarded existing Issue/draft PR sync; source publication is separate."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

out = Path(__file__).parent
assert not (out / 'READBACK.json').exists()
head = '35aebd3039241abb3393300affd593f4826a4a0c'
sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
def save(name, value): (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def gh(label, *args):
    assert not (out / (label + '-command.json')).exists()
    save(label + '-command.json', {'argv': ['gh', *args], 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    result = subprocess.run(['gh', *args], capture_output=True)
    (out / (label + '.stdout')).write_bytes(result.stdout)
    (out / (label + '.stderr')).write_bytes(result.stderr)
    save(label + '-receipt.json', {'exit_code': result.returncode, 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(), 'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()})
    assert result.returncode == 0
    return json.loads(result.stdout)
assert gh('identity', 'api', 'user')['login'] == 'kl3574'
issue = gh('issue-before-api', 'api', 'repos/kl3574/Learning_Workbench/issues/32')
pr = gh('pr-before-api', 'api', 'repos/kl3574/Learning_Workbench/pulls/56')
save('issue-before.json', issue); save('pr-before.json', pr)
assert sha(issue['body']) == 'e71265947b0fd68e19bd5394aa23ac8d638aa8cb2d9071a6838180f0ac125516'
assert sha(pr['body']) == 'bd3a312c5c5639df7c7a32a83eb1ae582f3c04014c4124ebaf4797e5a5d439b6'
assert pr['head']['sha'] == head and pr['draft'] and pr['state'] == 'open' and pr['merged_at'] is None
begin, end = '<!-- engineering_progress:start -->', '<!-- engineering_progress:end -->'
assert issue['body'].count(begin) == issue['body'].count(end) == 1
managed = '''
M6.3 in_progress / AC21 尚未验收。初始任务头保留创建版本；当前唯一 PRODUCT_DESIGN.md v3.0.15，SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec。

公开分支/PR56仍35aebd3039241abb3393300affd593f4826a4a0c，draft/open/unmerged，依赖PR55。受控turn、逐操作审批、SSE/产物清单和普通Import待审回导已公开；回导没有自动人审或发布，默认完整proof/executor未注册时保持unavailable。

两原CI均真实terminalFAIL（push37226331207、pull_request37226334354，attempt1；20:10:56UTC原快照），各5SUCCESS+1browserFAIL。各backend926PASS/spec962PASS/Web1399PASS166files/21354公开扫描；各integration2467PASS/2真实numericBLOCKED_ENVIRONMENT skips/2warnings，push3176.88s、PR4230.95s。这些重叠门禁不相加。各browser132PASS1FAIL/38.4m与38.5m，首Review36总30000ms耗尽；末症状分别viewport68已closed和旧评分selector67缺失，唯一根因UNKNOWN；第二late-response真实PASS。12原完整log、各actualcheckout35ae或13ea及同tree已核。Restore与singlepublication实际numeric均BLOCKED、发布409/PUBLISH_NUMERIC_REQUIRED/未发布，CI作业成功不提升物理数值资格。

本地正常合入会话中断UI到5d8bc7ef4f34bd08e6327053e874ed062a935ae8，尚未推送：精确8Web路径、1525工程输入同受审22dade，1517原非重叠输入/旧committedprogress树及207dirty/untracked进度文件字节保持。独立一人Standards/Spec两轴0新增；原完整Web1421PASS167files、focused127PASS4files、strict/build/diff0。固定22dade原make test-e2e实际133PASS20.4m/command和wrapper0，结束20:08:38.880476UTC，logSHA4c65a40f025bf0d2a350ba95ca9751f9924836d6c60b74b5d5844bbf3298a04a；1515nongenerated不变，5原预列生成输出改变、completeunchanged=false，无restore/copyback。不是在5d8另重跑，亦不追改两原CIFAIL。

新中断受限Chrome154真实HTTP/SQLite/IDB证明原actor/sessionCAS/body/key先保存，丢200ACK后刷新0自动interruptPOST、显式原key重放、当前GET与历史ACK分离，真实412保留原命令，newactor只读旧命令；4UI interruptPOST+1明确夹具竞争POST/setup写另列，四应用seams0/bootstrap1不等于全OS监控或实际模型/CLI/tool。首轮动态raw被误重跑覆盖永久LOSS；retained run01是第二误执行setupFAIL，run02新目录PASS/实际四路径guard，不补造首raw或六guard。原前三0tests工具链FAIL、真正同整组件4FAIL→4PASS、strict2errors保留。

首Review观察-only隔离c02：原30000ms/worker/retry/oracles/第二case不变，metadata不含URL/query/ID/header/body/DOM。正确选择首次case一次1PASS15.4s；之前错误grep为0tests/NOT_RUN，首次TS7016也保留。原CI唯一原因仍UNKNOWN，观察改变调度，未复现或修复CI；safe独审及只读CI白名单补充正在完成，候选未合入/推送，不借其局部PASS为当前公开能力。

最新本地完整Python仍4353原4341PASS/2真实numericENVskip/2warnings，564Python输入连续性限定，没有新完整Python重跑。旧1a push129P1F/PR130P、412完整132P1F、480局部FAIL及旧d69OPEN保持原件/原因限定。最初35ae sourcepush git0而记录器postcheck1、首响应未保存/UNKNOWN，后来纯exacthead读回，不repush；原误静态调用、归档whitespace检查FAIL和docparserFAIL均单列。

隔离7cff备份lifespanfocused2PASS/related7PASS、独审0new仅未来有界覆盖准备，旧权限被拒/历史保留/五明确应用seams0/正常shutdown；原8162FAIL是不同oracle而非生产修复RED-GREEN。永久disabled副本queued/active、后续新调度/一般收敛/正式restore/M7/GenericApproval与Import恢复仍OPEN或NOT_RUN；M7保持todo、依赖未解锁。

本轮0实际外部模型调用，用户API key未使用、进入源码或上传。真实DeepSeek/Codex CLI模型turn、production完整InputProof/受控executor、物理Broker/host工具/资源与停止边界、物理数值隔离及来源数学教学质量、整体M6.3/AC21未验收。既有中止扩展系统探针不重启；没有GitHubmerge/release/deploy。

下一任务：完成观察-only及明确CI证据独审，归档实际终态/原失败/永久rawLOSS；固定本地已审组合、核全部当前树和待推送历史后普通sourcepush并读回新head及原CI事件，不重跑掩盖旧FAIL、不提高测试预算。继续现行规范内的不受影响实现与验收，M6.3和M7不提前关闭。
'''
prefix = issue['body'].split(begin)[0]
suffix = issue['body'].split(end)[1]
body = prefix + begin + managed + end + suffix
assert body.split(begin)[0] == prefix and body.split(end)[1] == suffix
save('issue-patch.json', {'body': body}); (out / 'issue-body.md').write_text(body)
written = gh('issue-write-api', 'api', '--method', 'PATCH', 'repos/kl3574/Learning_Workbench/issues/32', '--input', str(out / 'issue-patch.json'))
save('issue-write-response.json', written)
after = gh('issue-after-api', 'api', 'repos/kl3574/Learning_Workbench/issues/32'); save('issue-after.json', after)
assert after['body'] == body
keys = ['number', 'title', 'state', 'labels', 'milestone', 'assignees']
assert {k: issue[k] for k in keys} == {k: after[k] for k in keys}
prbody = '''本PR依照唯一PRODUCT_DESIGN.md v3.0.15实现本地受控Codex流程：冻结输入和单次外发许可、完整原actor/body/key恢复、逐操作审批/安全拒绝、只读事件与受检产物。所选产物回导为普通Import待审草稿，仍须明确确认、人审与发布。默认完整输入proof/受控executor未注册时保持unavailable。

公开仍35aebd30/draft/open/unmerged，依赖PR55。两原CI push37226331207/PR37226334354已terminalFAIL，各5SUCCESS和browser132PASS1FAIL；各integration2467PASS/2真实数值ENVskip、backend926/spec962/Web1399均PASS（重合不叠加）。首Review原总30s超时、末症状不同，唯一原因UNKNOWN；第二延迟响应PASS，12log及实际checkout35ae/PR13ea同tree已核。数值实际BLOCKED、发布409/未发布，不能因作业PASS称例题已发布。

本地已正常合入会话中断入口5d8，未推送；8Web路径，独立两轴0new，1421Web/167files、127focused、strict/build/diff及精确22dade原完整native133PASS20.4m。5生成输出变化如实保留、不restore；当前1525源同22dade且原progress字节保持。新受限真实Chrome验证原CAS/body/key持久、lostACK显式重放、独立current、412和跨actor只读；不是实际模型/CLI/工具。首轮动态日志因误重跑永久LOSS、retained run01是第二setupFAIL；后续成功不重建或消除该损失。原工具链0tests、strict2errors和旧CIFAIL都保留。

首Review诊断候选仅无正文阶段/HTTP模板耗时，保持30s/原oracles；首次正确case1PASS，原错grep0tests/TS7016分别保留、唯一CI原因仍UNKNOWN；观察改变调度、未复现或修复CI，safe独审/CI白名单补充未整合。M7备份7cff只属隔离保护覆盖准备；正式恢复、新调度、M7依赖未解锁。

4353原完整Python4341PASS/2真实ENVskip只在逐输入连续性限定下沿用，没有新全量Python重跑。真实DeepSeek/CodexCLI模型turn、物理Broker/数值、来源数学教学质量及整体M6.3/AC21未验收，本轮0实际外部模型调用，key未入仓库。当前没有GitHubmerge/release/deploy。

下一步：归档两原CI终态与新受审本地证据，核可公开当前树/历史后普通sourcepush并读回新head/新CI，不追改原FAIL。Refs #32
'''
save('pr-patch.json', {'body': prbody}); (out / 'pr-body.md').write_text(prbody)
save('pr-write-response.json', gh('pr-write-api', 'api', '--method', 'PATCH', 'repos/kl3574/Learning_Workbench/pulls/56', '--input', str(out / 'pr-patch.json')))
pafter = gh('pr-after-api', 'api', 'repos/kl3574/Learning_Workbench/pulls/56'); save('pr-after.json', pafter)
assert pafter['body'] == prbody and pafter['head']['sha'] == head and pafter['draft'] and pafter['state'] == 'open' and pafter['merged_at'] is None
save('READBACK.json', {'status': 'ACTUAL_BOTH_ORIGINAL_CI_TERMINAL_FAIL_AND_LOCAL_INTERRUPT_MERGE_SYNC',
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'public_head': head,
    'local_head': '5d8bc7ef4f34bd08e6327053e874ed062a935ae8',
    'before_issue_body_sha256': sha(issue['body']), 'issue_body_sha256': sha(body),
    'before_pr_body_sha256': sha(pr['body']), 'pr_body_sha256': sha(prbody),
    'issue_metadata_unmanaged_text_unchanged': True, 'draft_open_unmerged': True,
    'ci': 'BOTH_ORIGINAL_TERMINAL_FAIL_5SUCCESS1BROWSERFAIL_EACH2467P2ENVSKIP',
    'actual_model_calls': 0, 'source_push_github_merge_release_deploy': False})
print('Actual terminal CI failures and local reviewed interrupt merge synced; public source still35ae, no merge/release.')
