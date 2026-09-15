# M4.1 exact-source GitHub CI

本包固定观察源码提交 `5bd81576a2a0e2dbb454165eb3bcde5920493b05`，保存两个首次工作流的实际12个job记录。状态：`{"success": 12}`。各job的实际开始/结束、步骤与原日志见 `job-details.json` 和 `logs/`；浏览器实际测试数量见 `summary.json`，不能从绿色check推测数量。

`exact-source-ci.json` 保留终态check、workflow和PR47回读。该次回读的PR仍为 draft=True、state=open、merged=False；以后明确发布进度或改变review状态应记录为另一时点。

Python相关job分别执行backend(unit+security)、spec-contracts和integration，存在spec unit重叠，不能把计数直接相加并称为一次新1040全量运行。历史9a803c2全量1040PASS、早期失败native/CI以及本地5bd源码74套由各自原回执独立保存。本包不重写早期失败或代替本地验收。

`collection-index-correction.json` 记录一次采集器派生清单更新的修正：首版终态索引在12-job聚合完成前记录了旧聚合指纹。首版回执完整保留于 `historical/first-terminal-index.json`；最终索引在采集停止后重建，12个job的24项原日志/元数据逐项哈希核对。旧瞬时聚合正文已被采集器覆盖，只保留其旧指纹，不声称可重放该正文；实际CI结果未改变。

原始下载文件保持在私有采集目录。公开日志/元数据只将个人绝对路径替换为 `<CI_REPO>`、`<CI_HOME>`、`<REPO>`、`<PRIVATE_ACCEPTANCE>` 或 `<PRIVATE_HOME>`，其余正文保留；manifest分别记录原始与公开SHA256。副本中的历史嵌套哈希仍指原始对象。summary的结果行去除了ANSI控制序列以便阅读，原公开日志未删除它们。

全包执行仓库公开路径与凭据扫描并人工检查来源；不包含本地数据库、浏览器profile、截图或用户内容。本次采集没有重跑、取消、ready、merge或关闭任何CI/PR。监测节奏的一个早期49秒读回及随后60秒守卫如实记在 `monitor-notes.json`。
