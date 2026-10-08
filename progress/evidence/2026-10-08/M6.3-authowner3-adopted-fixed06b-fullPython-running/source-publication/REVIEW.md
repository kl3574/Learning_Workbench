固定 `06b2f4ccf361d081a791554c677fd858fb537243` 相对 parent `fb749cb3d858eb910b44db73007e4823e63dde7c` 的 **source publication/provenance** 增量审查：Standards、Spec 各 **0 P1 / 0 P2**。不代表 runtime、完整门禁、生产 owner/InputProof、RealAgent、release 或发布已经通过。

本次只增加/修改三个真实源路径：`provider_codex_consents.py`、`provider_codex_retained_request.py`、`scripts/codex-turn/provider_retained_auth_checks.py`。新的三份出站 blob 全部实际扫描及阅读，非引用旧25包代替新增检查；原25包不改。本固定提交仍未包含随后 root 将整理的纯 progress，也不追随未来 HEAD。

## Standards

0 P1 / 0 P2，限定公开内容、来源及父源码相容性。实际 author commit `44876a81e89e9d128a3f8a02442bb1d576e541b7` 的 parent `f955a0dc55a962f58b57b483b1a44a67cd6e3955` 与 canonical parent fb749 的全部1585工程 Git mode/blobOID 图完全相同（仅排除 literal `progress/`）。正常纳入后仅三项差异，工程1587。三源与作者最终 immutable 副本、作者 Git、06b Git、当前 index/live 字节一致，author/canonical fullPOSIX 均0664、Git100644。没有隐含 merge/source漂移；不把 Git图相等冒充作者 base 的全文件 live POSIX 扫描。

三份新增出站版本按未变的仓库 publication path/credential/personal-path 规则及 UTF-8/NUL/binary/archive/rawlog 边界扫描未命中；只提交源码，没有实际 SecretStore 版本文件、SQLite数据、运行数据、SO/二进制、日志、profile 或真实凭据。源中的 synthetic keys/materials 是显式测试定义，不是本机账户材料。扫描需人工来源审查，不保证识别任意私密 prose。

实际代码保持 private repr=False auth capture，共享比较 helper 仍区分 started-required 与 not-started-required 前置条件；新的 owner 默认 resolver/foreign 均None，显式 `_for_local_test` 才组合。prepare/verify 的异常转换为固定安全 code/message，resolver不接收私有 secret snapshot。手动检查文件位于 scripts、非标准默认测试命名，文档说明须显式 pytest及owned library，不把私有库依赖带入普通全套或偷偷增加 ENVskip。没有 main/DTO/schema/锁/原Worker/default proof/executor改动。

## Spec

0 P1 / 0 P2，限定新增内部 mechanism 与真实声明。唯一规范 v3.0.15 `PRODUCT_DESIGN.md` SHA `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`、AGENTS、依赖锁、旧core/retained六输入/runner及publication checker 与parent字节相同。本审查按唯一规范 M6.3、§20.5、内部可信端口及附录G的公开内容/验证声明边界进行。

代码只把真实SQLite源/config与具名SecretStore捕获连接到显式local-test resolver和已有genuine Rust memory owner：source/auth在同一新transaction内读取，FFI前再次核绑定/secret，返回前再核，变化拒绝不refresh；不记录新start或send。正文由真正core producer编码，而非转换synthetic PreparedCodexRequest body。完整文本历史的顺序/丢失检查是纯材料fixture，真实selected refs直接拒绝，不用空材料替换；其余metadata/native mapping/ModelInfo仍明确fixture-only机械事实。

源、作者REPORT/STATUS都明确沿用封存SO而非freshRust；本轮27 scoped PASS、旧FinalAuth4 PASS/34 deselected分列，后者receipt之后只有doc/typing及新增手动例变动，不说4项在最终三源字节上重新执行。原RED/setup/15P7F/mypy故障保留。现有durable start账本仍绑定synthetic proposal bytes，测试明确其SHA不同于新genuinebody；genuineInputProof、生产metadata/owner资格、ledger-to-handle-send、qualified loader/resource/network和默认composition均未准入。内部prepare/verify/borrow不是发送许可，不注册生产executor/proof。

root另一个owner负责唯一固定06b完整Python/native，本 reviewer未启动、观察或判定该门禁。本次不覆盖原438完整4596P6F2numericENVskip/4604exit1、旧fixed24完整结果或任何CI事件，也不借局部mechanism绿称当前完整1587 PASS。

## 有限证据

`SOURCE3-INCREMENTAL-READBACK.json` 保存实际三源身份、fullPOSIX、parent Git相容及新版本扫描；`AUTHOR-METADATA-AND-SOURCE-BOUNDARY-READBACK.json` 绑定作者六个既有metadata/report pin及AST存在性，明确不是重新读取/核hash整个203包或大库。固定三源和完整diff另保存。所有执行仅具名Git/read/hash/AST，不import模块、不load库、不运行tests/model/network/CLI/AppServer/host probe，不写canonical/作者包/remote。

自身首个author metadata checker实际1仅因把口头MANIFEST别名误当`MANIFEST.json`；原错误分类保存，限定catalog确认真实`FINAL-ARTIFACT-MANIFEST.json`后同pin读回实际0。不是候选FAIL，不改测试或候选。随后progress增量 **NOT_REVIEWED**，等待独立固定pin后另核，不能扩大本包06b结论。
