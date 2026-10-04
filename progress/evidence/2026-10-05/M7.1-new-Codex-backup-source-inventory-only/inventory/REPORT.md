# d69 备份与恢复合同只读盘点

本报告只记录固定源码事实和可推进的本地任务，不修改规范、生产代码、测试或进度。基线为 `d69de81045ff6c9ff2f345643f0fd412e2d108fb`；唯一规范 `PRODUCT_DESIGN.md` v3.0.15，SHA-256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`。源码工作树为 `m63-review-route-lifecycle-owner-oct05`。

本轮仅阅读规范、源码、合成测试和已跟踪的任务状态；未读取真实数据库、备份、凭据或运行时目录，未执行备份/恢复/测试，未请求模型或网络。下文“已实现”仅指源码存在，不是本轮 PASS。

## 已声明合同与实际实现

| 合同 | 当前源码事实 | 本轮判定 |
|---|---|---|
| §20.4 稳定 `make backup`、SQLite WAL 一致快照 | `scripts/backup.py:23` 调用 `Database.online_backup`，仅净化独立副本；完整性、外键、blob 路径/大小/hash、压缩包 hash 读回与原子落盘均有实现 | IMPLEMENTED_SOURCE；本轮 NOT_RUN |
| §20.6 全备份含必要对象、题解和个人资料，排除密钥，含清单/schema/数量/UTC | 同一脚本包装完整数据库和全部 `content_blobs` 索引字节，带敏感性标记、迁移记录、表数量、UTC、逐文件大小/SHA；不复制任意数据目录文件。清单明确 `restore_acceptance=NOT_RUN` | IMPLEMENTED_SOURCE；不是完整恢复验收 |
| §20.4 Provider 自有降权保留原历史/hash/ACK | `provider_backup.py:14` 检查独立事务副本，删除私密 HMAC/locator，添加可校验 `provider_backup_projections`；不重写旧准备、许可、请求、回答或 ACK | IMPLEMENTED_SOURCE；新 Codex 专项备份证据不足 |
| §20.17.7 保留历史 actor/引用/可校验事实，认证不继承 | `session_backup.py:10` 保留 actor 身份与历史绑定，换成不可认证 sentinel、撤销所有旧会话，删除 bootstrap/通用幂等缓存；包装方 VACUUM 清除自由页认证材料 | IMPLEMENTED_SOURCE；不能删除历史 actor 来“安全化” |
| §20.6/附录 A 三类导出、恢复预览/CAS 提交、不覆盖原工作区、中断恢复 | 当前覆盖投影明确未注册下列 4 个导出/恢复操作，没有对应应用 DTO/HTTP handler/restore worker | NOT_IMPLEMENTED；NOT_RUN |
| M7.1 归档、purge 预览/确认及引用策略 | 同一覆盖投影另列 3 个未注册操作 | NOT_IMPLEMENTED；NOT_RUN |

未注册的 7 个操作：

```text
GET /api/v1/exports/{id}
POST /api/v1/exports
POST /api/v1/backups/restore-preview
POST /api/v1/backups/restore-commit
POST /api/v1/deletions/preview
POST /api/v1/deletions/commit
POST /api/v1/objects/{id}/archive
```

`packages/contracts/generated/runtime-route-coverage.json` 的 SHA-256 为 `5ccf701938fcc32f8aa29c3656ae42c9a3d4b6f04e018dee07b0d7de1fe164b4`。内容块历史恢复和数值恢复属于 M6.2，不能用其 `/content/.../restore` 实现代替工作区备份恢复。

## 新 Codex 私有持久状态应如何备份

现行规范已经规定这条边界（§20.17.7，规范行 1832）；无需为最小合成回读任务新增接口或规范：保存事实，拒绝继承认证和执行权。

1. `0028` turn、`0029` Provider Codex、`0030` GenericApproval、`0031` interrupt、`0032` manifest，以及 `0033–0035` Import 绑定/成员/命令都在一致数据库副本内。应原样保留它们实际创建的 JSON、SHA、原 ACK、head、全成员、跨 owner 引用及 actor 外键；不能将旧许可事件直接改成 revoked 而使历史链失配。
2. `codex_artifacts.py:67` 登记 manifest 时调用 `ArtifactRepository.register`（`artifact_repository.py:26`）；该端口先登记 `content_blobs`，因此已受检 Codex 输出字节会进入备份。实时 writer/runtime 目录和进程不是可继承的执行能力，不应为“恢复”复制任意目录。
3. `infrastructure/security.py:95` 的执行身份核验要求原 author 会话仍有效；净化后的原 actor 被撤销。`provider_codex_consents.py:219` 在派发前重核该身份；其 `:328` 当前投影另核 Provider 降权/秘密可用性。`codex_turn_worker.py:167` 先做该准入再记录开始许可。旧排队任务仍是历史事实；当前准入应阻止外部执行。
4. 工具批准与执行也经过同一原外发执行准入（`codex_operation_execution.py:28`）；新 actor 不能继承旧 approve_once（`codex_approvals.py:96`）或原 turn 开始许可（`codex_turn.py:258`）。允许仅减权 decline/revoke/stop 的权限应继续按原合同处理，不能一概禁止全部历史控制。
5. control/result/manifest GET 经当前会话、Policy 和完整 owner 读口；manifest GET 使用只读事务并复核 blob。恢复后 GET 不应重新排队或执行。原历史 ACK 与动态当前 validity 必须分别验证，不能要求动态 DTO 全字节不变，也不能把历史 active ACK 当成恢复后的当前许可。

这些是源码中的防线与已声明要求；本轮没有执行证明它们在新 Codex 备份副本上全部成立。

## 已有合成测试与明确空白

已有 `tests/unit/test_backup_command.py`、`test_session_backup.py` 和 `tests/integration/test_backup_session_history.py`、`test_backup_owner_history.py`，覆盖一致快照、secret-free、原数据不变、历史 actor、内容/评审/成绩及旧数值任务不继承批准。测试 helper `cli_backup`（`test_backup_session_history.py:37`）会实际运行 CLI，但只用临时合成资料和最小非秘密环境；它随后手工展开备份作回读，这不是产品 restore-preview/commit 流程。

`test_backup_codex_control_history.py:17` 参数化 approved/declined/ready/unknown，创建的是 v3.0.14 bootstrap 历史。其 `codex_` 前缀表比较不创建新 turn/GenericApproval/manifest/Import 的非空历史，也不包含 `provider_codex_` 前缀；因此该测试不能证明 v3.0.15 新 owner 图的备份恢复正确。现有 turn/manifest/审批测试验证原工作区的合成运行，没有调用备份 CLI。

## 可以独立推进的最小本地任务

建议在最终已固定整合源码的另一个独立 worktree 中，增加仅用临时合成资料的两项备份回读测试，不新增产品路由：

1. **已 grant 并 queued 的 turn**：复用 `make_consent_case` / `make_dispatch_case` / `queued` 的合成 seam。实际 CLI 备份后，确认此次确实非空的 turn + `provider_codex_` 原 JSON/hash/head/成员/ACK/actor 引用保留；源库/源文件不变；所有包内文件大小/hash 可核；旧 cookie 无效、新会话不能接管原 start/grant；control/current-grant GET 不写库、不重新排队、合成 executor 实际调用为零。若另外显式运行 worker 收敛，单独记录其合法终态写入，不混作 GET 零写。
2. **已完成且有受检 manifest 的 turn**：复用 `test_codex_artifact_manifest.py:13` 的 `CheckedAnswerMaterializer` 和纯内存合成返回。确认真实非空 manifest/成员/跨 owner 事实及登记 blob 字节完整保留，fresh author 可按原读权限回读旧受检结果，旧认证/许可不能恢复，质量字段保持 `mathematical/sources/independent_pedagogy=NOT_RUN`。若此用例未实际创建 GenericApproval 或 Import 记录，将其覆盖明确列为 NOT_RUN，不能用空表 hash 相同宣称已覆盖。

随后才独立添加真实 GenericApproval 已决定/待决定与 Import 绑定的合成副本案例。上述只是 §20.17.7 已有合同的局部证据；即使 PASS，也不能标记 M7.1 或完整 restore 通过。

## 合同需避免自行扩充的边界

恢复预览的附录 A（行 1958）只规定立即返回 `proposal_id/job/backup_sha256`，同时要求最终结果列冲突、版本、迁移、影响；通用 `JobSnapshot.result_refs`（行 1942）只能是 `ContentRef[]`。模块端口（行 3462–3463）也只写 proposal/warnings 和 proposalId。

这是 **SPEC_GAP 候选**：若后续完整恢复 UI 必须获得机器可核、结构化的详细 preview/proposal，则当前没有该详细读回 DTO/GET 合同，不能自行新增 `GET /backups/...`、扩充 JobSnapshot 或把 proposal/冲突伪装成 ContentRef。本轮没有据此断言所有预览实现必然阻塞；现有 Warning[] 可能承载已规定的有限摘要。应在实施具体恢复产品流程时先确定已声明形状能否满足要求，确有不足再单独记录合同冲突。它不阻塞上述两项本地合成备份回读。

## 阶段状态边界

固定 d69 的 `progress/state.json` SHA-256 为 `f3a60a0ea94171b19a8dee0507d429f60846b4a4be796021ff6e9506d6f59b27`：M6.3 为 `in_progress`、wholeM6.3/AC21 `NOT_ACCEPTED`；M7.1 为 `todo`、verification `NOT_RUN`、depends_on M6.3，已有工程准备提交 `b6340d913df252e30b920ec548e6cfd580505ec9`。该固定树的旧 next_action/测试文字是继承的历史检查点，不能冒充 root 此刻在跑的最终门禁状态。M7.1 验收尚未解锁；本报告未改进度。
