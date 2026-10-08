创作入口新增本地 Codex 会话准备、一次批准/拒绝、受限建 thread 与当前状态读回。会话建立只保存已核验映射，三项 capability 仍为 false；刷新和同数据库 API 重启后，原 actor/key/body 可由用户显式回放，返回原 ACK，避免再次启动。

范围依据已批准的唯一 PRODUCT_DESIGN.md v3.0.14 §20.16。包含 capabilities 读取、严格 DTO/类型化客户端、前向迁移0027、持久消费/执行 owner/只读历史、浏览器命令恢复及备份副本的认证失效与历史保留。依赖 draft PR #55，基于其 feat/M6.2-candidate-review 分支；不自动合并。

实际验证：
- 固定184修订后完整Python3686 PASS/0 FAIL/0 ERROR/2物理数值环境SKIP/2既有warnings、exit0，2199.36秒；1381工程输入逐Git前后不变，root独立回读。
- 固定f321完整 Web1038 PASS/145文件，strict/build849 PASS；正式固定bd3完整 native128 PASS/0 FAIL/0 skip，1worker/0retry，无casefilter。
- 固定045真实受限零模型控制取得HTTP201/r2 ready，1CLI、0 replay starts；浏览器实际两API进程/同DB/五个原ACK字节一致。原三个v2unknown未升级或重跑。
- 原DCF整套3683 PASS/1 FAIL/2setup ERROR/2数值环境SKIP保留；仅修过时备份测试，相关65 PASS，不推断两个旧setup错误原因。原ad494/a2d9/a480失败和自动检查中止的NOT_RUN也保留。

M6.3 / AC-21 仍在实施，本PR是可审阅切片。turn、多轮、通用审批、产物、登录/导出/回导没有由建会话许可授权或验收。物理数值环境BLOCKED，Restore发布409；真实生产Provider缺完整输入计量ProofRegistry而NOT_RUN，数学/来源/教学质量和完整M7恢复分别未验。未进行模型调用、公网部署或release。

Refs #32
