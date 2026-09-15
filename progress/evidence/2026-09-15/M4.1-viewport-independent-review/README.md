# M4.1 Reader 视口修复：独立审查与焦点边界

本包保存一次独立静态审查、由实施者执行的单元失败与修复记录，以及修复后的独立复核。所有测试使用 jsdom 控制几何；这里没有新的浏览器测试、Native 验收或 M4.1 完成结论。

## 已核验的顺序

1. 初版 wrapper/helper 的 10 个单元用例通过；app lint 命令通过。此 lint 实际运行 `tsc --noEmit --noUnusedLocals --noUnusedParameters`。
2. 独立静态审查指出：面板插入后完整补偿可能把同一已聚焦控件推到新 Reader 上边界之外。原 finding 在 `reviews/review.json` 保留原状态和静态推导边界。
3. 加入一个焦点用例与对应几何计算后，同一文件共 11 例，初版 helper 得到 **10 PASS / 1 FAIL**，失败为 `expected 200 to be greater than or equal to 493`。
4. 测试文件保持不变，只修复 helper 的补偿上限后，**同 11 例 PASS**。修复 helper 的 SHA256 为 `7889f23146384733a9ac7dd5cec6e6b37b0b5117e59f9c62b9e4dd6b7e72a4aa`。独立复核读取了原始日志并核对哈希，没有重跑测试。

## 源码来源

- `archived/before-PreserveReaderViewport.tsx.txt` 和 `archived/before-Shell.tsx.txt` 是实际存档的初版源码。
- `archived/before-PreserveReaderViewport.test.tsx.txt` 是焦点修复前实际存档的 **11 例**测试源码；RED 与 GREEN 共用该正文，SHA256 为 `489303303e5fee0db33a4f143b16af5288259f4255d11b5541777b12a62d4364`。
- `archived/initial-PreserveReaderViewport.test.tsx.txt` 是 root 从后续源码移除两个新增块后重建的 **10 例**正文，严格匹配已记录的预运行 SHA256 `4187676eb572f23377c052774808133291790022d555a064d49e14115ad799c8`；不把这次重建称为 root 当时复制的原文件。
- `archived/after-PreserveReaderViewport.tsx.txt` 是本次打包时读取并核对上述修复哈希的正文。所有源码只作 `.txt` 归档，不参与测试发现或工程编译。
- `source-hashes/before.json` 与 `after.json` 是实施者保存的边界哈希。`record_check` 的 tracked diff 不能单独绑定当时未跟踪的 helper/test；需要结合这些源码正文与哈希，不能把 receipts 中的 fbc388c 基线提交当作已包含新修复的源码提交。

## 证据与公开处理

`manifest.json` 为每项输入分别记录原始 SHA256、公开 SHA256、来源和转换。公开审查副本仅把个人绝对路径替换为 `<REPO>` 或 `<PRIVATE_ACCEPTANCE>`；原始审查 JSON 未改。副本内部历史哈希仍指原始对象，不能拿它们要求脱敏后的字节相等。四项原命令回执及日志保持正文不变；其原相对 output_path 保留，当前打包位置见 manifest。

原审查引用的浏览器控制诊断按原哈希定位，由其他证据包单独保存。本包不包含该诊断的运行输出、DOM、数据库、浏览器 profile 或截图。修复后的 74 例 Native 套件与真实 412 焦点用例由后续独立验收记录证明；本包不宣称其通过。

## 修复边界

焦点上限保护旧视口内可见的同一聚焦控件，保留对象身份、同节点、子恢复、尺寸和焦点变化守卫；没有直接改动 Workbench CAS 或原 onScroll 保存路径。比剩余视口更高的控件无法因这一上限获得完整可见性。真实浏览器裁切、光标可见性、滚动事件与持久化不能从 jsdom 模拟几何推出。
