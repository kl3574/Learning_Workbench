# M6.2 候选审核前端回执

最终实现：f07f75cb59b4a33eb3ef7b7726984662a1d74ebb；基线：82ca2052de914bf8ea53cb36a9b8be2c9b64c7bf。唯一规范 PRODUCT_DESIGN.md 3.0.7。

18 个文件：新 draftReview 功能、实际 Authoring/Import 入口、Shell 临时表单关闭保护、ADR 0027 与永久原生 case。没有服务端、generated 或公共 API client 修改。

最终相关 144 PASS（27 文件，含 29 个新审核行为测试），build/lint PASS；build 保留既有 chunk 大小提示。单条真实浏览器流程 PASS（6.9 秒，case 6.4 秒），真实 Import→候选→Review Job→原 key lost ACK 回放→机器 NOT_RUN 回执→实际报告字节与下载→明确双 REJECTED+reason→刷新后旧命令只读与当前 r2 回执。无模型调用。全部 1005 工程输入前后逐字对应最终 Git。

原产品失败单列：10 表单卸载（2 RED）、12 旧页取消锁死（1 RED）、15 poll r1 覆盖 r3（1 RED），21 旧选择 timer 的额外旧 Job GET（1 RED；最终 Job 未回退）。初期 TS、jsdom Blob、native exact-label 和 fake-timer 初始化错误是夹具/操作失败，不提升为产品根因。所有原件保留。

机器数学/来源和独立教学状态不自动通过。合成人工 REJECTED 只是协议测试，不代表真实内容审批。候选 DTO 状态仍 draft，与审核回执分开。跨刷新无法证明原 actor 的未知创建/决定保留只读；新取消明确使用当前 Job/CAS 和新 key，非原 ACK 回放。

发布、状态推进、影响分析、全平台验收及真实教学质量仍未执行。本切片不关闭整个 M6.2。独立审查结论由审查者单独提供。

本公开最小包保留原日志字节，仅进行明列的精确路径及合成作者身份别名替换。报告 JSON 原字节未变。PNG 原件保留在私有证据目录并列 SHA，不在此公开包复制；运行数据库、浏览器 profile、headers、cookie 与认证凭据不在包内。fixture DOM 诊断原件仍在私有目录，本包只保留对应原失败日志与准确分类。
