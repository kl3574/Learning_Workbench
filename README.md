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

工作台“导入”窗口支持 MD、TXT、HTML、learnpack 及受限 PDF/DOCX 文本提取的上传、预览、确认与取消；解析警告须明确确认，ID 冲突使用显式映射。原件保留并通过受权限控制的下载端点读取。PDF 使用真实页码定位，DOCX 使用段落/表格节点定位；图片公式、OMML 和复杂版式显示诊断，扫描件不自动 OCR。DOCX 原件需作者角色读取，安全正文预览独立处理。可配置安全预算列在 [.env.example](.env.example)，每次导入暂存时冻结实际配置。

已导入课程通过教材选择器进入 Reader，支持课程目录检索、精确修订与例题定位、数学渲染、原件与诊断回查，以及明确的已读和书签操作。正文或原始 Markdown 选文可创建笔记；笔记显示精确修订和 Unicode 码点锚点，本机草稿与服务端保存分开提示，版本冲突需明确选择，软删除保留历史引用。错误引用不会静默改读 current；旧来源无法证明时保留 unresolved。导入与来源记录不代表内容或数学审校通过。实现选择见 [Reader 与笔记记录](docs/adr/0008-reader-notes-and-provenance.md)，各项实际验收状态见进度。

含题集的学习包可从 Reader 的“本节习题”或习题目录进入练习。明确开始后建立准确版本的会话，五类题目支持自动保存作答及步骤；本机未同步候选、服务端版本冲突和关闭保护分别显示。提示使用公开题型的固定规则，尚未调用模型；主动展开参考解答才记录曝光，解答保留真实审核状态。提交固定原始作答及答案修订，确定性评分只使用可判定的已审规则；未审、缺失或不支持的答案保留需复核和空分。练习分数不等于独立测试证据。旧会话和旧成绩不会自动改用新答案或新评分规则。实现选择见 [练习与曝光记录](docs/adr/0009-practice-sessions-and-exposure.md) 和 [确定性评分记录](docs/adr/0011-deterministic-grading.md)。

测试目录可按冻结策略开始独立、辅助或开卷测试。服务端控制跨标签访问，保存作答使用版本比较；提交后由真实后台任务评分，支持回读任务、结果与明确的作者人工复核。复核追加评分版本，签名绑定原提交及作者操作，不自动批准参考答案。独立测试中待复核项未解决时保留解答保护。M3.4 已实现独立复盘标签、全部真实评分版本与不可变学习证据；历史选择、原始作答、精确教材链和资格原因分别展示。已验证实现与原始失败记录见进度，PR仍待审未合并；下一阶段 M4.1 构建画像、概念状态和路线完成。

PDF/DOCX 的 M2.3 提取需要可运行的 Linux bubblewrap、libseccomp 与 prlimit；所在系统还需允许bubblewrap建立受限用户/网络命名空间；项目不自动改动系统安全策略。文档CI采用已通过固定探针的官方Ubuntu26.04配置。若隔离不可用，任务明确失败并保留原件，其他格式导入仍可使用。提取保真与权限选择见 [提取记录](docs/adr/0007-document-extraction.md)，实际验收状态仍以进度为准。

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
