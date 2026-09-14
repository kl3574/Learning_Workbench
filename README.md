# 知径 Learning Workbench

本机优先的学习工作台。唯一产品与工程规范是完整的 [PRODUCT_DESIGN.md](PRODUCT_DESIGN.md)，实际阶段、阻塞和下一任务见 [progress/CURRENT.md](progress/CURRENT.md)。

公开仓库：[kl3574/Learning_Workbench](https://github.com/kl3574/Learning_Workbench)。M0—M7 及 E1 已用稳定任务 ID 建立 Issues/Milestones。实现走分支和 PR；没有审查合并的代码不表示 main 已交付。

## 本机安装与启动

当前目标为 Linux x86_64，需 Git、curl、make 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。Python 3.12.13、Node 24.21.0 和应用依赖精确锁定；setup 不更改系统默认 Python/Node。

```bash
make setup
make dev
```

启动器打开本机浏览器，通过 URL fragment 传递短效一次性凭证；页面使用后清除。该启动链接含临时秘密，不要复制到 Issue 或日志。已有会话直接访问页面；会话过期后重新运行启动器。开发页面默认 http://127.0.0.1:5173，API 默认 127.0.0.1:8765，仅监听本机。

```bash
make build
make start
```

生产构建在 http://127.0.0.1:8765 同源运行。数据默认位于 XDG 用户数据目录下的 learning-workbench，可用 LEARNING_DATA_DIR 指定工程树外目录。密钥、个人教材与学习记录不得提交。首次工作区为空；合成课程必须显式加载，目录中的示例状态不代表真实学习证据。

工作台“导入”窗口支持 MD、TXT、HTML 和 learnpack 的上传、预览、确认与取消；解析警告须明确确认，ID 冲突使用显式映射。原件保留并通过受权限控制的下载端点读取。PDF/DOCX 提取和正式课程 Reader 的当前实现状态见进度，不能把导入确认当作整个学习闭环完成。可配置安全预算列在 [.env.example](.env.example)，每次导入暂存时冻结实际配置。

## 验证与本地备份

```bash
make verify-spec
make lint
make typecheck
make test
make test-e2e
make backup
```

浏览器测试使用隔离数据目录和 Chromium；本机可使用已安装的 Google Chrome，CI 安装固定 Playwright 对应浏览器。make backup 通过 SQLite 在线备份 API 导出已提交 WAL 和校验过的 blob，排除秘密与有效会话；备份属于敏感个人数据，保存在数据目录，不能上传 GitHub。完整恢复预览、故障恢复与 M7 验收状态另见进度。

## 当前交付边界

工程仍按 M0 起逐阶段实施。结构／模拟／真实 Provider／真实 Codex／独立教学效果分别验收，不用目标接口清单或合成课程代替实际业务。尚未配置模型时 Agent 明示未配置，不产生伪造回答。未实现功能显示阶段状态，不返回假成功。测试命令、结果及准确代码 SHA 保存在 progress/evidence 与任务回执。

许可证待所有者选择。公开本仓库不等于另行授予开源或内容再许可；第三方依赖遵循各自许可。
