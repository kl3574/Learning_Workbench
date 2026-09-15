# M4.2 路线草稿日志独立复审公开派生证据

本包记录固定 shared 源 `e24982ac1da83e32b3a993d8dfc01d29827f4365422139d31686f62edb06d419` 的独立静态复审、两个隔离反例各自的 RED→GREEN，以及实际回读的 owner 日志。结论和范围见 final-review.md。不是 M4.2 阶段通过、完整测试全通过或原生浏览器通过。

独立执行仅四次 JSDOM/fake-indexeddb 单例：实际生产 DraftStore、两个 store 实例、hash 固定 shared hook、合成 envelope。每个最终 GREEN 的 harness 字节与其原 RED 相同，只替换固定的 shared 源。原失败和所有原字节在私有 acceptance cache 保留；没有 browser/network/API 操作或 repo 源修改。owner-readback 是他人实际运行后由本审查者读回并核 hash 的证据，不能冒称由审查者重跑。

manifest.json 每个 payload 同时记录原 SHA/字节数、公开 SHA/字节数、原位置标签与转换类型。公开派生仅将实际 repo 绝对目录归一化为 `<REPO>`，将 acceptance cache 绝对目录归一化为 `<ACCEPTANCE_CACHE>`；不改时间、退出码、测试断言、源 hash 或运行结果。原运行 receipt 内 stdout/input/source hash 保留原义，关联公开变体请查 manifest，不能拿 raw stdout hash 验证已经归一化的公开日志。raw_inspect_findings 是原材料因个人路径被公开扫描拒绝的事实，原件未覆盖；公开派生另经实际 inspect 检查。

原日志中的诊断 artifact/source 路径是原运行位置标签，只有 manifest.path 才是本包 payload 路径。本包未复制原 run05/run06 的截图或完整 native artifacts；也没有把仅读新 native 测试源码当作已执行。final-sources 是复审所见源字节快照。独立 harness 目录不携带 node_modules，复现需采用仓库锁定的已安装测试工具链；本包没有安装/联网步骤的执行证明。

owner 的 24 focused PASS 绑定 a70aecb；最终 e24982ac 的 whole unit 原记录为 284 PASS / 1 FAIL，唯一失败属于另一个 owner 的初次工作台恢复新增 RED，不能称为全 PASS。最终 e24982ac 的两个独立 GREEN 与 lint 证据分别记录。ADR0015 只核了 shared journal 描述；另一 owner 的 bootstrap 实现不在本独立审范围。
