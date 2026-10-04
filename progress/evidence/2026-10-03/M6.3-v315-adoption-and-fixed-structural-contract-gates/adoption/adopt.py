import hashlib,json,re,subprocess
from pathlib import Path
B=Path('$HOME/.cache/learning-workbench-acceptance');R=B/'m62-public-safe-oct02';P=B/'m63-turn-contract-proposal-oct04';O=Path(__file__).parent;S=R/'PRODUCT_DESIGN.md';A=Path('$HOME/Desktop/learning/PRODUCT_DESIGN.md');sha=lambda b:hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='9dc8c1bb702459c1a1dce9e1d1c2c8e1ed0fa5ff'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=R)
assert S.read_bytes()==A.read_bytes() and sha(S.read_bytes())=='bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144'
assert not (O/'v314-original.md').exists();(O/'v314-original.md').write_bytes(S.read_bytes())
p=(P/'docs/proposals/m63-controlled-turn-approvals-artifacts.md').read_text();assert sha(p.encode())=='79bcb378cbd756651f44098648c045e0e0c711e6f2c7b32295d1bc02903e0611'
s=S.read_text()
def replace(old,new):
 global s
 assert s.count(old)==1,(old[:80],s.count(old));s=s.replace(old,new)
replace('**版本：3.0.14｜日期：2026-10-03｜','**版本：3.0.15｜日期：2026-10-04｜')
row='| 3.0.14 | M6.3 本地控制会话准备、单次明确决定、冻结许可消费及真实 thread 映射/未知结果读回（§20.16） | 已获所有者批准，待实施验收；仅空 actions、零模型/工具/学科读取/网络，不关闭AC-21或整个M6.3，不改54 core/0001/学习包3.0.0 |'
replace(row,row+'\n| 3.0.15 | M6.3 单请求受控turn、独立完整输入许可、逐操作审批与安全减权基准、不可变产物清单及普通Import草稿回导（§20.17） | 已批准4e8及同范围控制基准澄清，待实施/真实验收；无proof零外发，工具后第二模型请求停止，不代表自动连续Agent循环或整个M6.3/AC-21完成；54 core/0001/学习包3.0.0不变 |')
replace('### 20.5 上下文、搜索与资源预算\n','### 20.5 上下文、搜索与资源预算\n\n本节普通 Provider 的预算、十个 HTTP 操作与历史 wire 保持不变；Codex 的独立具名输入、许可与单请求账本限定沿 §20.17.1–20.17.2。该例外不把普通文本适配器变为 Codex profile，不授予搜索/任意网络；有限本地工具预算仍须逐操作批准，不能当作第二次外发许可。\n')
replace('本节仅补齐：本地控制准备 → 阅读冻结范围 → 单次明确决定 → 消费对应许可创建受控 thread 映射 → 当前元数据读回。','本节仅补齐 bootstrap：本地控制准备 → 阅读冻结范围 → 单次明确决定 → 消费对应许可创建受控 thread 映射 → 当前元数据读回。新的独立 turn 控制历史与当前投影沿 §20.17.3；本节许可仍只批准空 actions 的 bootstrap。')
old='''CodexSessionView = {
  id: Id, revision: Revision, status: CodexBootstrapSessionStatus,
  active_turn_id: null,
  adapter_version: nonblank safe string,
  capabilities: {approvals:false, interrupt:false, artifacts:false}
}'''
new='''CodexSessionView = {
  id: Id, revision: Revision, status: CodexBootstrapSessionStatus,
  active_turn_id: Id|null,
  adapter_version: nonblank safe string,
  capabilities: {approvals:boolean, interrupt:boolean, artifacts:boolean}
}'''
replace(old,new)
needle='| 操作 | 请求/返回 | 明确边界 |'
replace(needle,'没有新 turn 控制历史的 session 仍严格按原 initializing/r1、终态/r2、active_turn_id=null、flags全false校验。新历史的当前投影按 §20.17.3推进，旧bootstrap原JSON/hash/准备/决定/create ACK及其旧解码器逐字保留；原create ACK仍r2/false，不能从当前投影改写。\n\n'+needle)
replace('`active_turn_id` 始终 null。','只有 bootstrap 历史时 `active_turn_id` 为 null；新的真实 turn 活动槽与当前控制修订沿 §20.17.3，GET仍不产生执行。')
replace('不包含 Provider codex 外发/InputProof、多轮对话、GenericApprovalView、Codex 产物清单、登录 UI、任务导出、普通文件执行/写入、回导或发布。它们仍按 v3.0.13 的对应目标另行补齐，不由本节关闭 AC-21 或整个 M6.3。','本节 bootstrap 不包含 Provider codex 外发/InputProof、多轮对话、GenericApprovalView、Codex 产物清单、登录 UI、任务导出、普通文件执行/写入、回导或发布。已批准的受控turn/审批/产物合同另沿 §20.17；两节均不因规范采纳关闭 AC-21 或整个 M6.3。')
body=p.split('## 2. 执行单位：一次模型请求，不是无限 Agent 循环',1)[1].split('## 11. v3.0.15 采纳索引与原发现保留',1)[0]
body='## 2. 执行单位：一次模型请求，不是无限 Agent 循环'+body
body=body.replace('本提案','本节').replace('本文','本节')
body=re.sub(r'### (\d+)\.(\d+) ',lambda m:'##### 20.17.'+str(int(m[1])-1)+'.'+m[2]+' ',body)
body=re.sub(r'## (\d+)\. ',lambda m:'#### 20.17.'+str(int(m[1])-1)+' ',body)
body=body.replace('第2、3节','§20.17.1、§20.17.2')
body=re.sub(r'第([2-9]|10)节',lambda m:'§20.17.'+str(int(m[1])-1),body)
body=body.replace('本节获批仅授权合同实施','本节的批准仅授权合同实施')
addition='### 20.17 M6.3 受控turn、逐操作审批与产物回导\n\n所有者已批准固定4e8d4f79合同补充及实施；后续7820199b在同一已批准减权行为内补齐安全控制读基准，两项原P2另行静态闭合。以下是唯一规范的正式合同，批准不代表代码、真实CLI/模型或内容质量已通过。bootstrap原许可、原ACK与普通Provider历史不升级为新执行授权。\n\n'+body.strip()+'\n\n'
replace('## 21. 旧格式兼容与确定的范围边界',addition+'## 21. 旧格式兼容与确定的范围边界')
replace('| POST `/approvals/{id}/decision` | ApprovalDecision | RunSnapshot；actor、操作hash、任务版本及过期时间校验 |','| POST `/approvals/{id}/decision` | 原ApprovalDecision；Idempotency-Key | 200 GenericApprovalDecisionAck（§20.17.4）；原actor才approve_once，同workspace减权decline，真实hash/CAS/绑定 |')
replace('| POST `/codex/sessions/{id}/turns` | `{message,context_refs:ContentRef[],expected_session_revision}` | 202 `{turn_id,session_revision,job:JobRef}`；文件/命令审批通过Broker事件传递 |','| POST `/codex/sessions/{id}/turns` | CodexTurnStartWrite（§20.17.2）；Idempotency-Key | 202 CodexTurnStartAck；消费真实准备和独立新许可，ACK不证明执行/完成；旧三字段发送形状不执行 |')
replace('| POST `/codex/sessions/{id}/interrupt` | `{turn_id,expected_session_revision}` | `{id,turn_id,status:interrupt_requested|already_terminal}`；中断不证明已完成外部副作用全部撤销 |','| POST `/codex/sessions/{id}/interrupt` | 原`{turn_id,expected_session_revision}`；Idempotency-Key | 原`{id,turn_id,status:interrupt_requested|already_terminal}`；§20.17.5一次减权/零重启，中断不证明副作用全撤销 |')
replace('| POST `/codex/sessions/{id}/artifacts/import` | `{turn_id,artifact_ids:Id[],expected_manifest_sha256}` | 202 JobRef；白名单路径、哈希、大小、审查后进入草稿 |','| POST `/codex/sessions/{id}/artifacts/import` | CodexArtifactImportWrite（§20.17.6；原三字段）；Idempotency-Key | 原202 JobRef；真实不可变清单/受检副本，经Import owner原子stage，只进入预览/草稿 |')
replace('| GET `/codex/sessions/{id}` | 无 | CodexSessionView（§20.16）；当前本地受检 initializing/ready/failed/unknown 元数据；active_turn_id=null、flags全false、零执行/零写；供并发读回，不能要求客户端猜版本 |','| GET `/codex/sessions/{id}` | 无 | CodexSessionView（§20.16、§20.17.3）；当前受检bootstrap状态/真实活动turn与控制revision；旧无turn历史保持null/false，零执行/零写 |')
rows='''

| Codex受控turn补充操作（§20.17；声明不表示已注册/验收） | 请求 | 严格响应与边界 |
|---|---|---|
| POST `/codex/sessions/{id}/turn-preparations` | CodexTurnPrepareWrite；Idempotency-Key | 202 CodexTurnPreparationView；真实Job/Run/context及活动槽，零执行 |
| GET `/codex/turn-preparations/{id}` | 无 | CodexTurnPreparationView；author/学科许可，零写 |
| POST `/codex/consent-previews` | CodexOutboundPreviewWrite；Idempotency-Key | 201 CodexConsentProposalView；完整输入proof，无proof拒绝，零外发 |
| GET `/codex/consent-proposals/{id}` | 无 | CodexConsentProposalView；author/学科许可，纯读 |
| POST `/codex/consents` | CodexConsentCreateWrite；Idempotency-Key | 201 CodexConsentCreateAck；原actor明确批准，零执行 |
| GET `/codex/consents/{id}` | 无 | CodexConsentView；author/学科许可，不作为learner减权读口 |
| POST `/codex/consents/{id}/revoke` | 原`{expected_revision}`；Idempotency-Key | MutationAck；同workspace减权，基准从安全turn读回，不重置消耗 |
| GET `/codex/sessions/{id}/turns` | cursor?、limit?；默认20/最大100 | CodexTurnPage；固定创建上界/安全控制含真实approval_controls与consent_control，无学科正文 |
| GET `/codex/turns/{id}` | 无 | CodexTurnControlView；安全当前投影/真实减权CAS/hash，零写 |
| GET `/codex/turns/{id}/result` | 无 | CodexTurnResultView；author/学科许可，输出仍未审 |
| GET `/codex/turns/{id}/events` | after_seq?；省略0，沿Last-Event-ID规则 | 严格Codex本地SSE判别union（§20.17.3）；author/每批权限复核，重连零新执行 |
| GET `/approvals/{id}` | 无 | GenericApprovalView；author/学科许可，真实完整操作，不是Provider或数值批准 |
| GET `/codex/sessions/{id}/turns/{turn_id}/artifacts` | 无 | CodexArtifactManifestView；真实不可变受检清单/来源终态，author/学科许可 |
| GET `/codex/artifact-imports/{job_id}` | 无 | CodexArtifactImportView；真实聚合Job/Import子项，author/学科许可，零写 |
'''
replace('# 附录 B：核心领域模型（可抽取）',rows+'\n\n# 附录 B：核心领域模型（可抽取）')
replace('export interface CodexBrokerPort<D extends DTOMap> {','// Legacy coarse compatibility only: every call is subordinate to §20.17 checked ownership/consent.\n// prompt/approvedPaths never bypass frozen inputs, manifests or permanent once-only ledgers.\nexport interface CodexBrokerPort<D extends DTOMap> {')
replace('本机 InputProof/registry 是内部可信工程端口，不是配置或 HTTP 可提交的新授权 DTO。','Codex的受检应用/内部owner端口及独立具名许可适配沿§20.17.7，原普通Provider端口/事件/历史wire不改；粗CodexBrokerPort不能绕过真实输入、许可、操作和产物清单准入。\n\n本机 InputProof/registry 是内部可信工程端口，不是配置或 HTTP 可提交的新授权 DTO。')
replace('    那么 操作不执行；越界产物不回导；批准合法成果也只进入草稿','    那么 操作不执行；越界产物不回导；批准合法成果也只进入草稿\n    并且 按§20.17.9分列真实CLI/模型/工具、受控协议与内容质量；每turn一次模型请求，第二请求外发前停止，安全控制新页可明确decline/revoke')
S.write_text(s);A.write_bytes(S.read_bytes())
assert S.read_bytes()==A.read_bytes()
(O/'adoption-source.json').write_text(json.dumps({'status':'APPROVED_V315_NORMATIVE_TEXT_ADOPTED_NOT_YET_GATED','old_spec_sha256':'bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144','new_spec_sha256':sha(S.read_bytes()),'approved_proposal':'4e8d4f79f7090af997b48926a0a9050fe2170b7d','clarification':'7820199bb7418a1de0b9a18913be135bdd76e2bf','proposal_sha256':sha(p.encode()),'root_and_canonical_equal':True,'body':'Complete approved sections2-10, renumbered20.17.1-9; exact old-contract scope edits and14 new AppendixA operations. Original core/0001 unchanged.','boundary':'Normative contract only, no new runtime/CLI/model acceptance. No original user checkout changes.'},ensure_ascii=False,indent=2)+'\n')
print(sha(S.read_bytes()))
