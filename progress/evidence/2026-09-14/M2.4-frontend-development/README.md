# M2.4 前端开发证据

本目录保留冻结前端的开发验证，包括失败历史。最终开发回归为 118 个 unit、6 个真实 Reader native、TypeScript/lint/build 通过。构建的 MathJax 包体积警告保留。

`frontend-freeze.json` 保存原冻结源码 manifest 与原 aggregate SHA；`manifest.json` 分别记录临时原始文件哈希和公开脱敏副本哈希，不能互换。`commands-and-results.json` 给出已实际执行的命令、完成状态、范围和限制。

个人/本机 checkout 路径转换为占位符，已知日志链接改为公开副本，终端 ANSI 控制符移除；测试结果与先前源码哈希不改写。仅复制合成界面 PNG，不复制 profile、数据库、DOM dump 或导入原件。图片及逐张视觉审查在 `docs/ui/M2.4/`。

这是开发证据，不是最终精确提交的 39 个 native 验收门禁，也不表示公开发布成功。父代理独立维护提交及阶段验收。
