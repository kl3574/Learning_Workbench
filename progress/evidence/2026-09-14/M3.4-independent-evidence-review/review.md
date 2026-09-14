# M3.4 Learning 独立有界审阅

唯一规范为仓库 PRODUCT_DESIGN.md；审阅应用分支 feat/M3.4-review-evidence，基线 HEAD 3cf2c343849ecf29bcc80b0d589ffa5efc264047。审阅与探针发生在未提交实现上，末端源码哈希详见 receipt.json。没有更改产品源码、规范、Git、进度或公共发布内容。

## 实际发现与修复

1. **暴露时间提前过滤绕过真实事件核验。** 实际导入原创五题包，真实 Practice hint 生成服务端事件和 receipt。仅将 exposure.occurred_at 改为截止后一天，原事件仍在截止前，修前 help_witnesses 返回 none/none/空集合。应为时间歧义 unknown。根将完整 witness 验证放在时间过滤之前，只有两个可信时间都晚于截止才排除，跨截止明确 unknown。原用例最终通过。
2. **无关题过滤绕过原题事件核验。** 同一实际包给第一题真实 hint，再将暴露行的题目 ref/group 改为另一道合法题的完整 ref/group；原事件与 Practice receipt 保持第一题。修前该行被提前排除，目标题帮助返回 none/none。根改为先核验原事件、receipt、assignment，再用验证后的 ref/group 过滤。原用例最终通过。

这两项是受控 SQLite 存储损坏探针，不代表用户可通过公开 API 任意改库。探针未删除不可变触发器，未伪造真实审批或评分成功。

## 独立通过的控制

- 新提交缺少资格依据明确 EVIDENCE_PREREQUISITES_INVALID，查询没有补写 legacy。
- 实际提交后再获得 hint，冻结依据字节不变；其中不保存 help Markdown 或完整 help_json。
- 真实评分版本 1 → 签名人工复核版本 2，旧 evidence 保留；当前页先选择最新成功版本再做 skill 筛选，不混旧 evidence。GET result/evidence 的 13 张业务表整行与计数均不变。
- 实际六迁移数据库生成旧提交、评分和签名复核，再应用第七迁移；在首个历史恢复项写 evidence_refs 时注入失败，已写 event/progress/binding/evidence 全部回滚。相同 worker tick 仍解析真实 TXT 到 preview_ready，其余两历史评分继续恢复，旧 grades/audits/manual reviews 字节不变。失败项保留安全隔离记录，不伪造恢复成功。

## 真实验证范围

初次 1 FAIL / 3 PASS → 截止修复后原 4 PASS → 加晚端恢复控制 5 PASS → 关联过滤探针 1 FAIL / 5 PASS → 最终 6 PASS（2.55s，pytest exit 0）。各完整运行所记录源码的 before/after 均相同。测试后期只新增第 5/6 个场景和零写入整行断言；两项红测本身未放宽。owned test 的 Ruff PASS，exit 0。

一次外围 Python3 回执脚本在 pytest 已写日志后因 datetime.UTC 不可用而退出 1；原未附回执日志和真实错误说明保留。该次不当作完整源码锚定验收，随后完整重跑取得 final-probes-receipt.json。日志含既有第三方依赖弃用警告。

静态审阅覆盖 Learning qualification/binding models、readback、事件与 evidence 原子持久化、0007 分类与不可变约束、恢复 savepoint 与 ImportWorker 接线；相关 Assessment/Content 端口用于验证实际输入。未发现上述限定范围内其他已证实阻断。这不是所有存储任意破坏或所有权限时序的形式证明，不代替主任务完整测试、原生 UI、重启与 CI 验收。未运行新的浏览器或外部服务。

## 输入与原件边界

仅使用仓库 tests.assessment_fixtures / tests.practice_fixtures 的原创算术与数量关系合成资料；真实导入、SQLite 和 worker，非假成功 HTTP handler。真实人工复核 test helper 只建立受控本地 author 签名测试身份，不声称原标准答案获专家审核。legacy fixture 只在构造六迁移时期关闭尚不存在的 M3.4 hooks，原成绩由真正评分流程产生。

本目录为本地原始证据，可能包含运行器绝对路径；尚未执行公开脱敏或发布审查。不得直接把它视为已可公开包。
