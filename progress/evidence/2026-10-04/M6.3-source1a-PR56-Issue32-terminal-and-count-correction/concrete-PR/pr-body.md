本 PR 在唯一 PRODUCT_DESIGN.md v3.0.15 下实现受控本地 turn：冻结完整输入、明确单次外发许可、真实幂等开始与安全控制读回，加入逐项审批拒绝、会话中断及显式受限内存操作。前端保留原 body/key/actor 的命令，刷新或丢 ACK 后仅在明确操作时重放，并保护失权与晚到回答。每 turn 最多一次模型请求；生产完整输入证明/executor 仍不可用，工具注册表默认空。

固定 79ac 的完整本地验证：Python 4211 PASS、2 项实际数值环境阻塞 skip；Web 1278 PASS，Ruff/mypy/生成合同/结构/strict TS/build 通过。原 make test-e2e 130 PASS，make 与 wrapper exit0；5 个预列生成输出实际变化，完整映射与原件保留。Python/static 的1465完整工程输入不变；原生十个预列输出之外1455输入不变。1a仅进度与明确证据路径，工程字节与79ac一致。

旧公开4b两组12个CI job终态成功且原日志/实际checkout tree已核；新1a的push37207897702、PR37207899600当前仅in_progress。数值publish409仍是环境阻断后的拒绝，未算发布成功。实际CLI模型/DeepSeek/平台Provider、物理Broker与质量验收未完成；本次实际外部模型请求0，密钥未存入源码或上传。

Artifact/普通Import回导、Codex SSE和产物UI在独立树继续，尚未纳入本PR公开源码；Artifact独审两项P2仍待闭合。M6.3/AC21保持in_progress，此PR为draft/open/unmerged，依赖PR55；无GitHub merge/release/deploy。
