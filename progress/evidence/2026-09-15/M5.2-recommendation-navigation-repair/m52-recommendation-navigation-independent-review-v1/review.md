限定静态结论：B 冻结的推荐快速点击修复未见新增阻断。useRecommendationNavigation.ts 612e7883… 与 recommendations.test.tsx 37cdc28d… 为本次两个修改输入；原 navigation guard test 24997f11… 未改。没有源码/测试修改或独立测试运行。

修复仅把同一 owner/paused/closeSafe 依赖的 epoch reset/cleanup 从 passive effect 改为 layout effect，并加原因注释。布局提交先建立这个 guard，然后可观察到 enabled 按钮；点击本身增加的 sequence 不会再被该次已经提交的 readiness transition 的迟到 passive cleanup 吞掉。真正 workspace/access/context 改变、paused/closeSafe 改变或卸载仍触发 cleanup/setup 的 epoch 推进，不能因为随后恢复原值就复活旧 request。navigate 入口和 current 谓词、await 后及 open 前复核、当前 ready/stale、target 完整 ref、所选完整父链验证与错误处理逐字不变。Panel 仍受 global closeSafe/决策 busy/当前投影控制，打开与接受决定分离。

新永久用例使用真实 RecommendationsPanel/hooks/DraftStore 与 fake-indexeddb 及合法 application-port fixture；MutationObserver 在实际父链按钮第一次 enabled 时只发一次 click，并在 finally disconnect。它没有先等待第二次稳定状态、替换 readiness、再次点击或放宽 waitFor 原要求。核心断言仍为明确链只打开一次、原 ID 只检查一次、无决定保存且 pending 不变。移除新增用例后，原7例全文与73d归档相同。

实际证据只读回读：original-01 原单例本地1PASS；observed-03 插桩记录显示 enabled 点击后同 owner/上下文的 passive cleanup/setup 把 epoch 从本次 sequence4 推到6，inspect 返回后 current=false。该内部 epoch 观测只属于插桩实验。去除生产 transform 的 actual-04 是1FAIL1PASS，证明受控症状不依赖生产插桩，但自身不观测内部 epoch。permanent-red-05 与 green-06 的同一永久 test 原字节相同，只有 hook 输入改变，分别1FAIL/7skipped和1PASS/7skipped。随后 recommendations-green-07 为29PASS/4files，包含未改的 workspace/policy/unsafe/batch/unmount 五种旧请求负控；同一无生产插桩 harness/config 的 loop-green-08 为2PASS；lint-09实际exit0。不同轮次/重复case不可相加成唯一通过总数。

所有上述 log SHA 与原receipt匹配，声明 before/after 相同，当前冻结源与最终归档一致；每轮是13个选择输入的边界，不是整个并行工作区或全部依赖的完整快照。原guard test当前SHA另与73d Git字节核对。observed-02首次harness导入替换错误被原样保留，不能算产品反例。

这说明一个可重复的 first-enabled/迟到effect源码竞态得到最小修复。原CI只有最终0次open/失败DOM，本地原例还曾PASS，因此不能声称已证明该CI的唯一原因。上述是B实际focused unit/type运行，本代理仅静态检查和原证据回读，未运行真实API/浏览器/全套或认定阶段验收成功。
