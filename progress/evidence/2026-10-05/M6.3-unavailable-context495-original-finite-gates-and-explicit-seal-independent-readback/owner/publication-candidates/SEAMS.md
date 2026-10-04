# 已授权测试 seams

Root 任务明确授权真实 HTTP + SQLite owner prepare / GET / internal read/verify、完整原件 hash / byte preservation、事务回滚与当前权限检查。TDD 技能的预先 seam 确认已由这份实际任务范围满足，无新的例行用户确认。

测试模型使用独立明确的 HistoricalOnlyRuntime synthetic bootstrap fixture，不启动真实 CLI 或模型，不把其 receipt 当生产 proof。实现对 default unavailable 新准备增加 v4；生产 registry 仍空、executor=None。0 bootstrap freeze/current validity/execute、0 subprocess、0 secret read、0 model/tool/transport 为限定 seam。生产 candidate 报告由 root 独审，作者后续自身检查不称独审。
