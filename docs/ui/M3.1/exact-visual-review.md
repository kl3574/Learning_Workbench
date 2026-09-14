# M3.1 固定提交视觉复核

源码 `0fc6340d33c26c9f6124ebb3d19f190709b860ad`，唯一规范 SHA-256 `ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c`。以下四图来自同一固定提交的完整 48 项原生浏览器运行，主代理逐图查看；图像哈希见 M3.1-exact-publication-manifest.json。材料均为原创建模的测试数据。

- `exact/practice-real-assisted-1440.png`：三栏仍在，明确显示规则提示、需审查的参考解答、已辅助状态；右栏跟随当前题目与作答。参考答案来自本机测试包，不是模型回复。
- `exact/practice-real-submitted-390.png`：窄屏结果按题排列；明确显示已结束、未评分、分数为空，未将空分数显示为零。当前滚动位置只显示部分结果，不是全页内容截图。
- `exact/practice-local-recovery-1440.png`：本机候选选择区域与服务端状态分开，状态说明“尚未同步”；选择恢复是明确按钮操作。冲突卡仍显示精确 question_id 作为候选对应标识，可读但较偏工程表达，后续统一候选显示时可改善。
- `exact/practice-restored-draft-390.png`：真实关闭 Chrome 并重启 API 后的第 2 题，未同步答案和步骤均恢复，公式正常，输入区适应窄屏。折叠引用使正文和作答保持靠前。

开发阶段已对 390px 内容密度、引用折叠与能力中文标签修正，前后图见 `restart-visual-review.md`；对待恢复候选状态文案的修正见 `frontend/visual-review.md`。这里的图与浏览器断言支持本次布局/交互验收，不代表完整可访问性审计、数学内容独立审核或学习效果验收。构建仍有 MathJax 与主包体积警告。
