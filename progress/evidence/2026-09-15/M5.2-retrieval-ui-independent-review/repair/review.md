# 两条检索 UI finding 的独立修复复核

结论：M52-UI-B-01 与 M52-UI-B-02 在本轮固定源码和已读取的受控回归范围内闭合，未发现新增阻断。此结论是独立源码审查与 owner 原证据回读，审查者未重新执行测试、原生浏览器或完整平台门禁。

M52-UI-B-01：checkedRecord 严格解码主记录与每个冲突，仅完整命令、body、ACK、rejected 等全部语义一致时将候选视作冗余。同一 unknown 已持久时不再 CAS 重写；并发同一 ACK 的真实 CAS conflict 仍能读回。推进 ACK 时只带入已经逐项验证相同的 conflict IDs；新的或不同事实不会被批量清掉。旧 ACK 或已拒绝状态不能被未确认/未拒绝状态覆盖。不同 key/body/ACK 的反例保持拒绝并核 disk 未变；真实 DraftStore 不作通用行为放宽。

M52-UI-B-02：Panel 父链按钮及 onClick 使用本机 safe；paused 时只显示权限说明。Shell 回调重新检查 subjectLocked 和 protectLearningDialog，并仅在 openReal 实际成功返回时关闭面板，保留原 canLeave 与精确引用冲突检查。合法 course→lesson→block 命中经 checkedQuery 验证，读存储成功的对照允许精确导航，READ_FAILED 情况阻止；paused 后命中和导航入口隐藏。这里未把 Panel 的端口测试冒称完整 Shell/browser 执行，也未夸称原问题造成持久数据丢失。

证据：ui-review-findings-valid-red-06 实际 7 FAIL / 4 PASS（11 例），日志中可见相同 unknown/ACK 两写一成功一拒绝、旧等价候选读失败、不同候选 persist 未拒绝，以及 READ_FAILED 时 open 被调用一次。ui-unit-final-05 实际 23 PASS / 5 files，包含相同 SHA 的两份修复测试共 11 例；并非只凭消息报数。三份已读 receipt 的 log SHA 匹配原日志，27 个列入库存的源 before/after 相同，并逐一核 source 副本。ui-lint-08 实际仅 tsc -b apps/web/tsconfig.json，exit 0、空日志；按 TypeScript build/typecheck 记，不称 ESLint 或全门禁。

反事实 RED 的精确范围：Commands 为首轮原逻辑加可注入真实 DraftStore 参数；red-source-seam.diff 记录全部差异，不能说原 Commands 文件逐字节未改。Panel 与首轮审查副本逐字节相同；Shell 处于修后接线，Panel RED 单独证明组件 open 调用，未声称旧完整 Shell 重放。red06 与 final05 的两测试源逐字节相同且具合法 DTO；此前 owner 的无效 ID/body/lifecycle 前置失败保留在 owner 原包，不计作本报告目标 RED。

本范围不包括最终 native、视觉验收、完整 frontend/backend suite 或 M5.2 阶段通过；它们由实施者/root 独立绑定。原首轮静态报告、私有 snapshot harness 错误及源码副本均保留，未被覆盖。
