# M1 运行界面复核记录

唯一规范为根目录 `PRODUCT_DESIGN.md` 3.0.0 第 4 章。参考机制来自 [Open edX Redwood 侧栏](https://docs.openedx.org/en/latest/community/release_notes/redwood/sidebar_nav.html)、[VS Code 区域布局](https://code.visualstudio.com/docs/configure/custom-layout) 与 [W3C 可访问分隔条](https://www.w3.org/WAI/ARIA/apg/patterns/windowsplitter/)。实现未使用这些产品的 Logo、截图或课程内容。

全部截图来自真实运行的 Vite + FastAPI + SQLite UI session、Google Chrome 153.0.8010.36。数据是项目生成的 8 章 × 6 节合成 fixture；首次工作区为空，模型未配置且没有联网调用。截图未包含 bootstrap fragment、密钥、真实教材或个人学习记录。

## 一轮可回读修正

| 检查 | 修正前证据 | 发现与修复 | 修正后证据 |
|---|---|---|---|
| 1440 桌面 | `m1-before-1440.png` | MathJax 错把 fontData 写作 font，触发默认字体动态加载；改为本地 tex-font。字体不支持时返回中文诊断并保留源文。 | `m1-after-1440.png`，正文公式无错误，原生测试记录无 pageerror/console error |
| 390 窄屏 | `m1-before-390.png` | 原生 hidden 去除侧栏导致 CSS Grid 自动放置把中央内容移入零宽轨；给所有区域指定固定 grid-column/row。 | `m1-after-390.png`，中央标题/正文与公式可见，页面无横向溢出 |
| 原生 200% 截图 | `m1-200-percent-initial-partial.png` | Playwright 带页面缩放的截图范围裁为左上区域；改用无 clip 的 CDP Page.captureScreenshot，保持浏览器原生缩放。 | `m1-after-200-percent-native.png` 与 `m1-native-zoom-metrics.json` |

父级审查者实际打开并检查 before/after 图片；修正包含代码变更和浏览器回归，不以美观评分代替证据。`m1-after-200-percent-css-reflow.png` 是早期等效 CSS 宽度补充图，不能替代最终原生 200% 验收。

## 最终覆盖

- `m1-before-empty-1440.png`：首次工作区空态、学习路线默认、模型未配置。
- `m1-after-1440.png`、`m1-after-1920.png`：三栏、目录层级、标签、当前小节、长标题与明确合成身份。
- `m1-after-900.png`：左栏保留，Agent 抽屉入口。
- `m1-after-390.png`、`m1-after-390-directory.png`、`m1-after-390-agent.png`：中央优先、两侧抽屉、焦点关闭路径。
- `m1-after-390-long-formula.png`：长公式内部 scrollWidth 大于 clientWidth，scrollLeft 实际变化；页面保持无横向溢出。
- `m1-after-200-percent-native.png`：隔离临时 Chrome profile 中，通过 chrome://settings/appearance 的页面缩放选择 200%；CSS 宽度 1440→720、DPR 1→2。未使用 CSS zoom 或设备模拟冒充原生缩放。

真实鼠标拖动、分隔条箭头 16px/Home/End/Enter、抽屉 Tab/Escape/焦点返回、上下文精确匹配、不同对象草稿与同对象 CAS、离线恢复、服务端 UI 会话冲突、冷加载阅读位置恢复由 `tests/e2e` 执行。截图脚本不会自动生成绿色成绩或伪造模型回复。真实 Provider/Codex/学习效果未运行。

最终命令、退出码、输出与源码 hash 见 `M1_VERIFICATION.json` 和同目录 `m1-*.log`。机器验收数量按该 JSON 的实际命令输出回读；本说明不手写替代 CI 或远端合并状态。


## 后续故障复核与重连修复

初轮 14 项浏览器用例未覆盖“本地缓存 quota 失败 + PUT 失败 + 普通重连”的组合。独立审查实际复现：未确认导航折叠只在内存，普通重连读取服务端后曾清空该修改，且没有再次 PUT。旧验证记录及源码清单保留为 `M1_VERIFICATION.before-reconnect.json`、`M1_SOURCE_MANIFEST.before-reconnect.json`，旧日志使用 `m1-pre-reconnect-*` 前缀。旧用例通过不代表这个缺口已经覆盖。

修复后同工作区普通重连首先保留未确认内存和原基准，再以原 revision 重试；服务端基准变化时显示原基准、本地待同步、服务端三方的可读布局与内容比较。只有明确选择本地版本后才以新基准 CAS 保存，或明确采用服务端；缺失旧基准显示未知。`m1-session-three-way-conflict.png` 是该真实故障注入场景的运行截图。新增用例检查实际服务端状态，防止仅靠消失的错误提示判定保存成功。


最终 M1 细项同时包含：每标签 LaTeX 详情和焦点在 A→B→A/刷新后恢复；首次问题草稿冲突先展示原基准、当前输入和已存文本；继续浏览保留 1.3 等最后阅读对象；未实现的路线保持真实空目录；原生键盘扩展选文更新准确上下文，正文有多个匹配时明确拒绝锚点。它们各有真实浏览器用例，不以全局专注模式替代每标签焦点，也不以章节列表冒充路线任务。
