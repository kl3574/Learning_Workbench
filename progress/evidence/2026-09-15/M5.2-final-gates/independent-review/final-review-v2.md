# M5.2 最终 native 和四个前端门禁的独立只读复核

结论：可以保留固定提交 `3dd75f01966bb5dcf0b9ea0855e6b82ce335d814` 的实际 native 88 PASS（7.6m），并限定表述为“执行代码/配置/测试输入一致，仅已识别的测试截图输出变化”。不能把原 783 项全清单写成 unchanged=true：原 native receipt 的 unchanged=false 和两个 aggregate 均正确，应保留。

## 源绑定和唯一变化

已通过固定 commit 的 Git blob 逐项核全部 783 个 tracked 非 progress 文件，均与 native before 相符。四个此前前端门禁的同一 783 项 before/after 也完全相同。native 后仅 `docs/ui/m1-session-three-way-conflict.png` 改变：141049 字节、SHA 4eb8a0555dcd6ef74600e58233d6c1708f68b4c8123402230963db5d26440e35 → 141027 字节、SHA c785cc549dbf80f7d650f80bd82b6ca6ce55ce212715ea11bccce4dd7dfc7072。第一次独立读回（10:23:07Z）与 native after 的全部 783 项相同；后续 root 归档并恢复此生成输出后，最终独立读回为 783 项全部等于 3dd before。两次观察与原 native after 均保留，不能混写成同一时刻。

原全部清单 aggregate 前 ce0233c4767bdaddd042f4fa025522d8c0944dec93872b5f14ea2d1fcd7d5349、后 01859f49b568f5c4edecf554f9ac595bc5e9c169b80862e614769b3debc25268。排除这一个经依赖审查识别的生成输出后，其余 782 项 aggregate 前后均为 97bc68ef4f3cd30f1b61152f1327468f04217b147175baa49c59c26427556031；代码、测试正文、配置、契约与锁文件没有字节变化。原库存包含文档截图，故其“inputs”字段是宽泛 tracked-file 清单，并非每项都实际被测试作为输入消费。

## 为什么是生成输出

固定 `tests/e2e/workbench.spec.ts:250–280` 的受控 quota/双页 CAS 用例，在所有三方比较 DOM 和服务端前置断言完成后，于第 275 行调用 `page.screenshot({ path: '../../docs/ui/m1-session-three-way-conflict.png' })` 写入该文件，之后继续明确选择本地并验证实际服务器保存。此代码没有读取/比较该 PNG。测试中的 quota 是显式 throw DOMException 注入，不是物理空间耗尽。

`make test-e2e` → `npm --prefix apps/web run test:e2e` → Playwright 指定 tests/e2e/playwright.config.ts；从 apps/web 执行时该相对输出正好落到仓库 docs/ui。Playwright 只匹配 `*.spec.ts`，没有配置图像基线/自定义 snapshot 路径；全 tests/e2e 与应用源搜索未发现 toHaveScreenshot、toMatchSnapshot、snapshotPath 对照调用。固定提交全 tracked 非 progress 文本中该图片名称仅另见 `docs/ui/M1_VISUAL_REVIEW.md:35`，说明它是此合成场景的运行截图。应用/Vite 没有导入该文件或 docs/ui；现有 readFileSync 只读 Reader 下载结果对照真实 fixture 字节，与此图无关。名称引用及基线 API 检索结果随报告保留。因此该变化不是被更新的断言基线，也不是应用执行输入变更。

独立实际查看了固定 commit 原 PNG 和本轮 after PNG（均 1440×900）：两图均为合成 UI 会话三方比较，能看到版本标题由 88/89 变为 92/93。仅报告这些实际可见事实，不宣称执行过图像像素级相等证明。可选 Pillow 比较因环境未装模块未执行，未安装或修改图像，错误另存且不计产品失败。

## 实际门禁与边界

五组 root runner receipt 与项目 check receipt 的 commit、spec、命令、退出码相符，日志 SHA 均匹配。native 日志包含顺序 1..88 的 88 条实际 PASS 和最终 88 passed (7.6m)，生成截图的用例为 #83，实际 PASS 6.1s。

四个前端门禁为：npm lint（实际 tsc --noEmit --noUnusedLocals --noUnusedParameters）PASS；npm typecheck（tsc --noEmit）PASS；Vitest 57 files / 346 tests PASS（3.36s）；make build（tsc --noEmit && vite build）PASS，保留超过 500 kB chunk 的构建提示。未冒称另有 ESLint 执行。第一次独立观察中，四组回执与当时文件相比仅这张随后由 native 生成的 PNG 不同；root 归档恢复后，最终 783 项全部再次等于四组门禁的 before/after。

本报告是对已有运行原件和固定源码的独立读回，未重新执行产品测试或浏览器，未修改原件/截图/仓库。无需因这一个已证实的输出变化重跑完整 suite；以后若代码、契约、测试或真正消费的基线改变，应另按实际变化验证。库存未包含已安装依赖二进制、运行时数据库和连续文件活动追踪，因此不声称验证了那些字节或运行中所有外部状态。新的 archive/publication 记录与任何后续提交应独立绑定，不把 3dd 的 source 验收改成另一个提交的测试事实。

## 补充：输出恢复与沿用门禁的精确输入范围

首轮原稿 review.md/review-receipt.json 保留在私有目录；其第一时刻 current=after 的观察有效，但写稿结束时 PNG 已再次改变，原稿未及时说明 root 的输出恢复。本文 v2 是加入第二次观察的更正，不覆盖原记录。root 已将前后图保存到公开 final-gates 目录；本审查逐字核两图与之前独立保存的原件相同，五个公开 source receipt 也与 cache 原件相同且 hash 与 acceptance 一致。最终 783 current 哈希全部等于 3dd 原提交。本审查未执行或亲历 root 的恢复命令，不能独立声称监控了其 exact-after guard；已独立证明归档字节和恢复结果。

Python 427、spec 430、gold 216 三份原始清单的实际 hash 与 root acceptance 引用相符；逐项 declared inputs 同时等于已核 3dd Git blob 和最终 current，规范 aggregate 复算相符。Python/spec 的原 before/after 相同，真实原运行属于 f9a307a9f52f2951f73a4de3ab35ffeaf223a0df；Python 原日志 1663 PASS / 2 warnings / 273.45s，spec 原日志 PASS，其 check receipt/log 绑定均吻合。gold 216 是原 benchmark passport 输入对照，此补充未重新评估 gold/ranking 或重跑基准。此证据支持按各自明示输入集合沿用原结果，不改写成“在3dd重新跑过Python/spec/gold”，不扩展到未列出的环境二进制、全前端或历史遗漏的421项清单。
