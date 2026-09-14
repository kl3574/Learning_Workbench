# ADR 0001：本机工具链与运行边界

依据 PRODUCT_DESIGN.md 8、14、20.4；这是工程选择记录，不增补产品需求。

2026-09-14 查验 [Node 官方维护状态](https://nodejs.org/en/about/previous-releases)、[Vite engine 要求](https://vite.dev/guide/)、[Python 维护状态](https://devguide.python.org/versions/)。Node 24 为 LTS，Python 3.12 处于安全维护期。使用 Python 3.12.13、Node 24.21.0；不更改宿主默认版本。

Node Linux x64 官方归档 SHA-256 `fd8e59d5a511510f6a298afb548f18c7d2b1be404d8b4a27d94fbe49f56cb2d6`，与 [官方 SHASUMS256](https://nodejs.org/dist/v24.21.0/SHASUMS256.txt) 复核后解压到被忽略的 `.toolchain/`。Python 由 uv 管理，`.python-version`、`uv.lock` 和 `apps/web/package-lock.json` 固定补丁与依赖。

开发 UI 使用 127.0.0.1:5173，API 127.0.0.1:8765；生产由 FastAPI 在 8765 同源托管构建。默认数据在 XDG 用户数据目录，拒绝写进工程树。Launcher 将短效一次性 code 放入 fragment，网页消费后清除；访问日志不记录 code。启动与自动测试均不调用真实模型。

使用依赖的许可从 PyPI/npm 官方发布元数据核对：Python 直接依赖 FastAPI/Pydantic 为 MIT，Uvicorn/HTTPX 为 BSD-3-Clause；React、Vite、TypeScript 等依其各自许可，MathJax 为 Apache-2.0。这里只安装依赖，不复制未授权教材、商标或用户字体。项目本身许可证仍待所有者决定。

CI 仅运行实际存在的结构、API、UI、集成、安全和浏览器测试；不在公开 PR 自动调用付费提供商或 Codex。所有 Actions 固定至已查询官方 release tag 的 SHA。具体 CI 成功与否需另行回读运行记录。
