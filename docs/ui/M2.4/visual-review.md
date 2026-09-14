# M2.4 前端开发视觉审查

这些图片来自本项目原创合成学习包经过真实上传、解析、确认后的界面。未复制浏览器 profile、数据库、原始 DOM 转储或个人教材。所有 PNG 均逐张实际查看，公开版本与原始字节一致；各自哈希见开发证据 manifest。

## 已观察并修正

- `before-real-example-1440.png` 中，右栏把已读取的真实服务端引用仍标为“合成示例引用”。`after-real-example-1440.png` 和 `after-real-overview-1440.png` 已改为“已解析的准确引用”。显式 M1 合成布局入口继续使用合成标识；本次修正不声称内容已审校。
- `before-exact-note-390.png` 重复显示了正在编辑的同一份草稿恢复按钮；`after-exact-note-390.png` 移除重复入口，其他可恢复草稿仍有入口。界面真实显示冻结块 ID、修订、原始 Markdown 引文和 Unicode 码点半开范围。
- 390 × 844 图中笔记标题与关闭按钮均在视口内。真实浏览器断言检查 dialog 的 `scrollWidth <= clientWidth + 1`，并通过 `elementFromPoint` 命中关闭按钮验证未被遮挡。正文在独立弹窗内容区滚动；这张截图没有声称展示折叠区域外的全部编辑控件。
- 1440 × 900 概览实际显示课程目录、定义正文、本地 MathJax SVG 与显式阅读动作。例题来源图显示原件 SHA-256、受控下载入口和独立引用信息；长公式通过真实键盘滚动及 `overflow-x: auto` 断言，未缩小整页以伪装适配。

## 证据边界

保存了两张实际存在的 before 与三张 after。没有此前的 overview before，不补造该图。before 不代表最终实现。最后一次开发检查为 118 个 unit 与 6 个 Reader native 通过；这些图片和日志不等于父代理随后执行的精确提交 39 个 native 门禁，也不证明平台发布或全部阶段完成。
